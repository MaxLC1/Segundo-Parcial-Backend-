import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from . import models, schemas

from app.pkg_ventas.models import Venta


def get_devoluciones(db: Session):
    return db.query(models.Devolucion).all()


def create_devolucion(db: Session, devolucion: schemas.DevolucionCreate):
    venta = db.query(Venta).filter(Venta.id == devolucion.venta_id).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    db_devolucion = models.Devolucion(**devolucion.model_dump())
    db.add(db_devolucion)
    db.commit()
    db.refresh(db_devolucion)
    return db_devolucion


def update_estado(db: Session, dev_id: int, estado: str):
    dev = db.query(models.Devolucion).filter(models.Devolucion.id == dev_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")

    dev.estado = estado
    db.commit()
    db.refresh(dev)
    return dev


# -- GESTIÓN DE POLÍTICAS DE DEVOLUCIÓN --
def get_politica_empresa(db: Session, empresa_id: int, persist: bool = True):
    pol = (
        db.query(models.PoliticaDevolucion)
        .filter(
            models.PoliticaDevolucion.empresa_id == empresa_id,
            models.PoliticaDevolucion.id != None,
        )
        .first()
    )
    if not pol:
        # Política por defecto
        pol = models.PoliticaDevolucion(
            empresa_id=empresa_id,
            nombre="Política Estándar de Tienda",
            tipo_reembolso_menor_valor="CUPON_CREDITO",
            plazo_maximo_dias=30,
            permite_cambio_mayor_valor=True,
            activa=True,
        )
        db.add(pol)
        db.flush()
        if persist:
            db.commit()
        db.refresh(pol)
    return pol


def update_politica_empresa(
    db: Session, empresa_id: int, data: schemas.PoliticaDevolucionCreate
):
    pol = (
        db.query(models.PoliticaDevolucion)
        .filter(models.PoliticaDevolucion.empresa_id == empresa_id)
        .first()
    )
    if not pol:
        pol = models.PoliticaDevolucion(
            **{**data.model_dump(), "empresa_id": empresa_id}
        )
        db.add(pol)
    else:
        for k, v in data.model_dump(exclude={"empresa_id"}).items():
            setattr(pol, k, v)
    db.commit()
    db.refresh(pol)
    return pol


# -- GESTIÓN DE NOTAS DE DEVOLUCIÓN PARA CLIENTE Y DELIVERY --
def crear_nota_devolucion(db: Session, req: schemas.NotaDevolucionCreate):
    from app.pkg_ventas.models import DetalleVenta
    from app.pkg_catalogo.models import Producto
    from sqlalchemy import func, and_, or_

    venta = db.query(Venta).filter_by(id=req.venta_id).with_for_update().first()
    if not venta or venta.estado_sincronizacion != "CONFIRMADA":
        raise HTTPException(404, "Compra confirmada no encontrada")
    detalle = (
        db.query(DetalleVenta)
        .filter_by(id=req.detalle_venta_id, venta_id=venta.id)
        .first()
    )
    if not detalle:
        raise HTTPException(422, "La prenda no pertenece a la compra")
    politica = get_politica_empresa(db, venta.empresa_id, persist=False)
    if not politica.activa:
        raise HTTPException(409, "La empresa no admite cambios ni devoluciones")
    if datetime.utcnow() > venta.fecha + timedelta(days=politica.plazo_maximo_dias):
        raise HTTPException(409, "El plazo de devolución de esta compra venció")
    used = (
        db.query(func.coalesce(func.sum(models.NotaDevolucion.cantidad), 0))
        .filter(
            models.NotaDevolucion.detalle_venta_id == detalle.id,
            or_(
                models.NotaDevolucion.estado == "COMPLETADA",
                and_(
                    models.NotaDevolucion.estado == "EN_MARCHA",
                    or_(
                        models.NotaDevolucion.fecha_expiracion == None,
                        models.NotaDevolucion.fecha_expiracion > datetime.utcnow(),
                    ),
                ),
            ),
        )
        .scalar()
    )
    if used + req.cantidad > detalle.cantidad:
        raise HTTPException(409, "La cantidad ya fue solicitada o devuelta")
    gross = sum(d.subtotal for d in venta.detalles)
    paid_ratio = venta.total / gross if gross else 0
    original = round(detalle.precio_unitario * req.cantidad * paid_ratio, 2)
    nuevo = None
    precio_nuevo = 0
    if req.tipo_solicitud != "Devolución Directa":
        nuevo = db.query(Producto).filter_by(id=req.producto_nuevo_id).first()
        if not nuevo or not req.talla_nueva_id or not req.color_nuevo_id:
            raise HTTPException(422, "Seleccione producto, talla y color de reemplazo")
        from app.pkg_catalogo.models import Talla, Color

        if (
            not db.query(Talla).filter_by(id=req.talla_nueva_id).first()
            or not db.query(Color).filter_by(id=req.color_nuevo_id).first()
        ):
            raise HTTPException(422, "Talla o color inexistente")
        precio_nuevo = round(nuevo.precio * req.cantidad, 2)
    diferencia = round(precio_nuevo - original, 2)
    if req.tipo_solicitud == "Cambio por Mayor Valor" and (
        diferencia <= 0 or not politica.permite_cambio_mayor_valor
    ):
        raise HTTPException(
            409, "El cambio de mayor valor no cumple la política o los precios"
        )
    if req.tipo_solicitud == "Cambio por Menor Valor" and diferencia >= 0:
        raise HTTPException(409, "Seleccione una prenda de menor valor")
    if req.tipo_solicitud == "Cambio de Talla o Color" and (
        nuevo.id != detalle.producto_id
    ):
        raise HTTPException(409, "El cambio de talla/color debe ser del mismo producto")
    if req.tipo_solicitud == "Cambio de Talla o Color":
        precio_nuevo = original
        diferencia = 0
    mode = politica.tipo_reembolso_menor_valor
    porcentaje = (
        100
        if mode == "REEMBOLSO_100_PCT"
        else 50
        if mode == "REEMBOLSO_50_PCT"
        else politica.porcentaje_reembolso
    )
    monto = (
        round(abs(diferencia) * porcentaje / 100, 2)
        if diferencia < 0 and mode.startswith("REEMBOLSO")
        else 0
    )
    mensaje = (
        f"Diferencia a pagar: Bs. {diferencia:.2f}"
        if diferencia > 0
        else f"Reembolso al completar: Bs. {monto:.2f}"
        if monto
        else "Sin ajuste monetario"
    )
    if diferencia < 0 and mode == "CUPON_CREDITO":
        mensaje = f"Crédito al completar: Bs. {abs(diferencia):.2f}"
    nota = models.NotaDevolucion(
        codigo_nota="NDEV-" + uuid.uuid4().hex[:12].upper(),
        empresa_id=venta.empresa_id,
        venta_id=venta.id,
        usuario_id=venta.usuario_id,
        sucursal_id=venta.sucursal_id,
        motivo=req.motivo,
        tipo_solicitud=req.tipo_solicitud,
        estado="EN_MARCHA",
        visible_para_cliente=True,
        detalle_venta_id=detalle.id,
        cantidad=req.cantidad,
        prenda_devuelta_info=detalle.producto.nombre,
        prenda_nueva_info=nuevo.nombre if nuevo else None,
        precio_prenda_original=original,
        precio_prenda_nueva=precio_nuevo,
        diferencia_precio=diferencia,
        monto_reembolso=monto,
        resolucion=mode,
        producto_nuevo_id=nuevo.id if nuevo else None,
        talla_nueva_id=req.talla_nueva_id if nuevo else None,
        color_nuevo_id=req.color_nuevo_id if nuevo else None,
        mensaje_notificacion=mensaje,
        fecha_expiracion=datetime.utcnow()
        + timedelta(days=politica.vigencia_nota_dias),
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota


def get_notas_devolucion(db, empresa_id=None, estado=None):
    query = db.query(models.NotaDevolucion)
    if empresa_id:
        query = query.filter_by(empresa_id=empresa_id)
    if estado:
        query = query.filter_by(estado=estado)
    return query.order_by(models.NotaDevolucion.fecha_creacion.desc()).all()


def get_mis_notas_activas_cliente(db, usuario_id):
    from sqlalchemy import or_

    return (
        db.query(models.NotaDevolucion)
        .filter(
            models.NotaDevolucion.usuario_id == usuario_id,
            models.NotaDevolucion.visible_para_cliente == True,
            models.NotaDevolucion.estado == "EN_MARCHA",
            or_(
                models.NotaDevolucion.fecha_expiracion == None,
                models.NotaDevolucion.fecha_expiracion > datetime.utcnow(),
            ),
        )
        .all()
    )


def completar_nota_devolucion(db, nota_id, req):
    from app.pkg_sucursales.models import Sucursal, Inventario
    from app.pkg_ventas.models import DetalleVenta
    from app.pkg_comercial.models import Cupon, Notificacion

    nota = db.query(models.NotaDevolucion).filter_by(id=nota_id).first()
    if not nota:
        raise HTTPException(404, "Nota no encontrada")
    # Same lock order as sales and transfers.
    db.query(Sucursal).filter_by(id=nota.sucursal_id).with_for_update().first()
    nota = (
        db.query(models.NotaDevolucion)
        .filter_by(id=nota_id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    if nota.estado == "COMPLETADA":
        return nota
    if nota.estado != "EN_MARCHA" or (
        nota.fecha_expiracion and nota.fecha_expiracion < datetime.utcnow()
    ):
        raise HTTPException(409, "Nota cancelada o vencida")
    detalle = db.query(DetalleVenta).filter_by(id=nota.detalle_venta_id).first()
    if not detalle:
        raise HTTPException(
            409, "La nota antigua debe revisarse y vincularse a una prenda de la compra"
        )
    try:
        returned = (
            db.query(Inventario)
            .filter_by(
                sucursal_id=nota.sucursal_id,
                producto_id=detalle.producto_id,
                talla_id=detalle.talla_id,
                color_id=detalle.color_id,
            )
            .with_for_update()
            .first()
        )
        if returned is None:
            returned = Inventario(
                sucursal_id=nota.sucursal_id,
                producto_id=detalle.producto_id,
                talla_id=detalle.talla_id,
                color_id=detalle.color_id,
                cantidad=0,
            )
            db.add(returned)
        returned.cantidad += nota.cantidad
        if nota.producto_nuevo_id:
            replacement = (
                db.query(Inventario)
                .filter_by(
                    sucursal_id=nota.sucursal_id,
                    producto_id=nota.producto_nuevo_id,
                    talla_id=nota.talla_nueva_id,
                    color_id=nota.color_nuevo_id,
                )
                .with_for_update()
                .first()
            )
            if not replacement or replacement.cantidad < nota.cantidad:
                raise HTTPException(409, "Stock insuficiente para completar el cambio")
            replacement.cantidad -= nota.cantidad
        if nota.diferencia_precio < 0 and nota.resolucion == "CUPON_CREDITO":
            nota.cupon_generado = "CUPON-" + uuid.uuid4().hex[:12].upper()
            db.add(
                Cupon(
                    empresa_id=nota.empresa_id,
                    usuario_id=nota.usuario_id,
                    codigo=nota.cupon_generado,
                    nombre="Crédito por " + nota.codigo_nota,
                    tipo="MONTO",
                    valor=abs(nota.diferencia_precio),
                    criterios={},
                    fecha_vencimiento=datetime.utcnow() + timedelta(days=365),
                    max_usos=1,
                )
            )
        from app.pkg_pagos.audit import registrar_ajuste

        registrar_ajuste(db, nota)
        nota.estado = "COMPLETADA"
        nota.visible_para_cliente = False
        nota.fecha_completada = datetime.utcnow()
        db.add(
            Notificacion(
                empresa_id=nota.empresa_id,
                usuario_id=nota.usuario_id,
                titulo="Devolución completada",
                mensaje=f"{nota.codigo_nota}: {nota.mensaje_notificacion}",
            )
        )
        db.commit()
        db.refresh(nota)
        return nota
    except Exception:
        db.rollback()
        raise
