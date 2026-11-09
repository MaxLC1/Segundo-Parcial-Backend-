from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException
from app.pkg_catalogo.models import Producto, Temporada, Categoria, Talla
from app.pkg_sucursales.models import Inventario, Sucursal
from .models import Cupon, CanjeCupon, Notificacion, Traspaso


def crear_cupon(db, data, empresa_id):
    for key, cls in [
        ("productos", Producto),
        ("temporadas", Temporada),
        ("categorias", Categoria),
        ("tallas", Talla),
    ]:
        ids = getattr(data.criterios, key)
        if ids and db.query(cls).filter(cls.id.in_(ids)).count() != len(set(ids)):
            raise HTTPException(
                422, "Criterios de cupón inválidos o ajenos a la empresa"
            )
    coupon = Cupon(
        **data.model_dump(),
        empresa_id=empresa_id,
        codigo="CUPON-" + uuid4().hex[:12].upper(),
    )
    db.add(coupon)
    db.add(
        Notificacion(
            empresa_id=empresa_id,
            usuario_id=data.usuario_id,
            titulo="Nuevo cupón disponible",
            mensaje=f"{data.nombre}: {coupon.codigo}",
            vence=data.fecha_vencimiento,
        )
    )
    db.commit()
    db.refresh(coupon)
    return coupon


def aplicar_cupon(db, codigo, venta, detalles):
    coupon = (
        db.query(Cupon)
        .filter_by(codigo=codigo, empresa_id=venta.empresa_id)
        .with_for_update()
        .first()
    )
    if (
        not coupon
        or not coupon.activo
        or coupon.fecha_vencimiento <= datetime.utcnow()
        or coupon.usos >= coupon.max_usos
    ):
        raise HTTPException(409, "Cupón inexistente, agotado o vencido")
    if coupon.usuario_id not in (None, venta.usuario_id):
        raise HTTPException(403, "El cupón pertenece a otro cliente")
    if (
        db.query(CanjeCupon)
        .filter_by(cupon_id=coupon.id, usuario_id=venta.usuario_id)
        .first()
    ):
        raise HTTPException(409, "Este cliente ya utilizó el cupón")
    eligible = 0
    for item in detalles:
        product = db.query(Producto).filter_by(id=item.producto_id).one()
        c = coupon.criterios or {}
        if all(
            not c.get(k) or v in c[k]
            for k, v in [
                ("productos", product.id),
                ("temporadas", product.temporada_id),
                ("categorias", product.categoria_id),
                ("tallas", item.talla_id),
            ]
        ):
            eligible += item.subtotal
    if eligible <= 0:
        raise HTTPException(409, "Ninguna prenda cumple los criterios del cupón")
    amount = round(
        min(
            eligible,
            coupon.valor if coupon.tipo == "MONTO" else eligible * coupon.valor / 100,
        ),
        2,
    )
    venta.total = round(venta.total - amount, 2)
    coupon.usos += 1
    db.add(
        CanjeCupon(
            empresa_id=venta.empresa_id,
            cupon_id=coupon.id,
            venta_id=venta.id,
            usuario_id=venta.usuario_id,
            monto=amount,
        )
    )


def traspasar(db, data):
    if data.origen_id == data.destino_id:
        raise HTTPException(422, "Seleccione sucursales diferentes")
    branches = (
        db.query(Sucursal)
        .filter(Sucursal.id.in_([data.origen_id, data.destino_id]))
        .order_by(Sucursal.id)
        .with_for_update()
        .all()
    )
    if len(branches) != 2 or len({b.empresa_id for b in branches}) != 1:
        raise HTTPException(403, "Ambas sucursales deben pertenecer a su empresa")
    previous = (
        db.query(Traspaso).filter_by(operacion_uuid=str(data.operacion_uuid)).first()
    )
    if previous:
        return previous
    try:
        for item in data.detalles:
            match = dict(
                producto_id=item.producto_id,
                talla_id=item.talla_id,
                color_id=item.color_id,
            )
            source = (
                db.query(Inventario)
                .filter_by(sucursal_id=data.origen_id, **match)
                .with_for_update()
                .first()
            )
            if not source or source.cantidad < item.cantidad:
                raise HTTPException(409, "Stock insuficiente para el traspaso")
            destination = (
                db.query(Inventario)
                .filter_by(sucursal_id=data.destino_id, **match)
                .first()
            )
            if destination is None:
                destination = Inventario(
                    sucursal_id=data.destino_id, cantidad=0, **match
                )
                db.add(destination)
            source.cantidad -= item.cantidad
            destination.cantidad += item.cantidad
            db.flush()
        record = Traspaso(
            empresa_id=branches[0].empresa_id,
            usuario_id=db.info["actor"].id,
            operacion_uuid=str(data.operacion_uuid),
            origen_id=data.origen_id,
            destino_id=data.destino_id,
            detalles=[d.model_dump() for d in data.detalles],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise
