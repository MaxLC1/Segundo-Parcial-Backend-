from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
from . import models, schemas
from app.pkg_sucursales.models import Inventario, Sucursal
from app.pkg_catalogo.models import Producto


def create_venta(db: Session, venta: schemas.VentaCreate):
    # A branch lock serializes inventory changes, including retry checks.
    sucursal = (
        db.query(Sucursal).filter_by(id=venta.sucursal_id).with_for_update().first()
    )
    if not sucursal:
        raise HTTPException(404, "Sucursal no disponible")
    if venta.empresa_id not in (None, sucursal.empresa_id):
        raise HTTPException(403, "Empresa y sucursal no coinciden")
    if venta.operacion_uuid:
        previous = (
            db.query(models.Venta)
            .filter_by(operacion_uuid=venta.operacion_uuid)
            .first()
        )
        if previous:
            return previous
    if venta.origen != "ONLINE" and venta.metodo_pago.lower() not in {
        "efectivo",
        "contado",
    }:
        raise HTTPException(400, "Las ventas offline solo admiten efectivo")
    total = 0
    details = []
    try:
        for det in venta.detalles:
            producto = db.query(Producto).filter_by(id=det.producto_id).first()
            if not producto or producto.empresa_id != sucursal.empresa_id:
                raise HTTPException(403, "Producto ajeno a la empresa")
            if db.info.get("role") == "Cliente":
                from app.pkg_catalogo.models import ReglaOferta

                discount = producto.descuento_porcentaje or 0
                age = producto.antiguedad_temporadas or 0
                if age:
                    seasonal = 30 if age == 1 else 60
                    for rule in (
                        db.query(ReglaOferta)
                        .filter_by(activa=True, tipo="TEMPORADA_PASADA")
                        .all()
                    ):
                        if rule.antiguedad_temporadas == age or (
                            age >= 2 and rule.antiguedad_temporadas >= 2
                        ):
                            seasonal = rule.descuento_porcentaje
                    discount = max(discount, seasonal)
                offered = round(
                    producto.precio * (1 - min(100, max(0, discount)) / 100), 2
                )
                if round(det.precio_unitario, 2) not in {
                    round(producto.precio, 2),
                    offered,
                }:
                    raise HTTPException(
                        409, "El precio cambió o es inválido; actualice el catálogo"
                    )
            inv = (
                db.query(Inventario)
                .filter_by(
                    sucursal_id=sucursal.id,
                    producto_id=det.producto_id,
                    talla_id=det.talla_id,
                    color_id=det.color_id,
                )
                .with_for_update()
                .first()
            )
            if not inv or inv.cantidad < det.cantidad:
                raise HTTPException(
                    409, f"Stock insuficiente para producto {det.producto_id}"
                )
            inv.cantidad -= det.cantidad
            subtotal = round(det.cantidad * det.precio_unitario, 2)
            total += subtotal
            details.append(models.DetalleVenta(**det.model_dump(), subtotal=subtotal))
        record = models.Venta(
            total=round(total, 2),
            usuario_id=venta.usuario_id,
            responsable_id=db.info["actor"].id
            if db.info.get("actor")
            else venta.usuario_id,
            sucursal_id=sucursal.id,
            empresa_id=sucursal.empresa_id,
            metodo_pago=venta.metodo_pago,
            transaccion_id=venta.transaccion_id,
            tipo_entrega=venta.tipo_entrega,
            direccion_envio=venta.direccion_envio,
            operacion_uuid=venta.operacion_uuid,
            origen=venta.origen,
            estado_sincronizacion="CONFIRMADA",
            fecha=venta.fecha or datetime.utcnow(),
            detalles=details,
        )
        db.add(record)
        db.flush()
        if venta.cupon_codigo:
            from app.pkg_comercial.services import aplicar_cupon

            aplicar_cupon(db, venta.cupon_codigo, record, details)
        from app.pkg_pagos.audit import registrar_cobro

        registrar_cobro(db, record)
        if venta.tipo_entrega == "Delivery":
            from app.pkg_delivery.models import ServicioDelivery

            db.add(
                ServicioDelivery(
                    venta_id=record.id,
                    empresa_id=sucursal.empresa_id,
                    estado="Pendiente",
                )
            )
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise


def sincronizar_ventas_lote(db: Session, lote: schemas.SincronizacionLoteRequest):
    resultados = []
    confirmadas = rechazadas = duplicadas = 0
    for item in lote.ventas:
        if not item.operacion_uuid:
            raise HTTPException(422, "Cada operación offline requiere UUID")
        item.origen = item.origen if item.origen != "ONLINE" else "PWA_OFFLINE"
        previous = (
            db.query(models.Venta).filter_by(operacion_uuid=item.operacion_uuid).first()
        )
        if previous:
            duplicadas += 1
            resultados.append(
                schemas.ResultadoSincronizacionItem(
                    operacion_uuid=item.operacion_uuid,
                    estado=previous.estado_sincronizacion,
                    mensaje=previous.motivo_rechazo
                    or "Operación previamente confirmada",
                    id_generado=previous.id,
                )
            )
            continue
        try:
            record = create_venta(db, item)
            confirmadas += 1
            resultados.append(
                schemas.ResultadoSincronizacionItem(
                    operacion_uuid=item.operacion_uuid,
                    estado="CONFIRMADA",
                    mensaje="Venta confirmada",
                    id_generado=record.id,
                )
            )
        except HTTPException as exc:
            db.rollback()
            rechazadas += 1
            resultados.append(
                schemas.ResultadoSincronizacionItem(
                    operacion_uuid=item.operacion_uuid,
                    estado="RECHAZADA_CONFLICTO",
                    mensaje=str(exc.detail),
                )
            )
        except Exception:
            db.rollback()
            resultados.append(
                schemas.ResultadoSincronizacionItem(
                    operacion_uuid=item.operacion_uuid,
                    estado="ERROR_REINTENTABLE",
                    mensaje="Fallo temporal; conserve la operación y reintente",
                )
            )
    return schemas.SincronizacionLoteResponse(
        total=len(lote.ventas),
        confirmadas=confirmadas,
        rechazadas=rechazadas,
        duplicadas_ignoradas=duplicadas,
        resultados=resultados,
    )


def registrar_cambio_prenda(db: Session, cambio: schemas.CambioPrendaCreate):
    raise HTTPException(
        410,
        "Registre una nota en /devoluciones/crear-nota y complétela en /devoluciones/notas/{id}/completar para aplicar la política y conservar el comprobante",
    )


def get_cambios_prendas(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.CambioPrenda)
    if empresa_id is not None:
        query = query.filter(models.CambioPrenda.empresa_id == empresa_id)
    return query.order_by(models.CambioPrenda.id.desc()).all()


def get_ventas(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Venta)
    if empresa_id is not None:
        query = query.filter(models.Venta.empresa_id == empresa_id)
    return query.order_by(models.Venta.id.desc()).all()


def get_reportes(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Venta).filter(
        models.Venta.estado_sincronizacion == "CONFIRMADA"
    )
    if empresa_id is not None:
        query = query.filter(models.Venta.empresa_id == empresa_id)

    ventas = query.all()
    total_ingresos = sum(v.total for v in ventas) if ventas else 0
    total_ventas = len(ventas)
    ticket_promedio = total_ingresos / total_ventas if total_ventas > 0 else 0

    return {
        "total_ingresos": total_ingresos,
        "total_ventas": total_ventas,
        "ticket_promedio": ticket_promedio,
        "ventas_por_metodo": {
            "Efectivo": len([v for v in ventas if v.metodo_pago == "Efectivo"]),
            "QR": len([v for v in ventas if v.metodo_pago == "QR"]),
            "Stripe": len([v for v in ventas if v.metodo_pago == "Stripe"]),
        },
    }
