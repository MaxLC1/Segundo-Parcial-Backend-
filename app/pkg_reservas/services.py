from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional, List
from datetime import datetime

from . import models, schemas
from app.pkg_sucursales.models import Sucursal


def get_reservas(
    db: Session, skip: int = 0, limit: int = 100, empresa_id: Optional[int] = None
):
    query = db.query(models.Reserva)
    if empresa_id is not None:
        query = query.filter(models.Reserva.empresa_id == empresa_id)
    return query.order_by(models.Reserva.id.desc()).offset(skip).limit(limit).all()


def create_reserva(db: Session, reserva: schemas.ReservaCreate):
    # Idempotencia por operacion_uuid
    if reserva.operacion_uuid:
        existente = (
            db.query(models.Reserva)
            .filter_by(operacion_uuid=reserva.operacion_uuid)
            .first()
        )
        if existente:
            return existente

    sucursal = (
        db.query(Sucursal).filter_by(id=reserva.sucursal_id).with_for_update().first()
    )
    if not sucursal:
        raise HTTPException(404, "Sucursal no disponible")
    if reserva.empresa_id not in (None, sucursal.empresa_id):
        raise HTTPException(403, "Empresa y sucursal no coinciden")
    from app.pkg_sucursales.models import Inventario

    cantidades = {}
    for det in reserva.detalles:
        key = (det.producto_id, det.talla_id, det.color_id)
        cantidades[key] = cantidades.get(key, 0) + det.cantidad
    for (producto, talla, color), cantidad in cantidades.items():
        inv = (
            db.query(Inventario)
            .filter_by(
                sucursal_id=sucursal.id,
                producto_id=producto,
                talla_id=talla,
                color_id=color,
            )
            .first()
        )
        if not inv or inv.cantidad < cantidad:
            raise HTTPException(409, "Existencias insuficientes para reservar")
    empresa_id = reserva.empresa_id
    if not empresa_id:
        sucursal = db.query(Sucursal).filter_by(id=reserva.sucursal_id).first()
        if sucursal:
            empresa_id = sucursal.empresa_id

    db_reserva = models.Reserva(
        usuario_id=reserva.usuario_id,
        sucursal_id=reserva.sucursal_id,
        empresa_id=empresa_id,
        operacion_uuid=reserva.operacion_uuid,
        origen=reserva.origen or "ONLINE",
        estado_sincronizacion="CONFIRMADA",
        estado="Pendiente",
        fecha_reserva=datetime.utcnow(),
    )
    db.add(db_reserva)
    db.flush()

    for detalle in reserva.detalles:
        db_detalle = models.DetalleReserva(
            reserva_id=db_reserva.id,
            producto_id=detalle.producto_id,
            talla_id=detalle.talla_id,
            color_id=detalle.color_id,
            cantidad=detalle.cantidad,
        )
        db.add(db_detalle)

    db.commit()
    db.refresh(db_reserva)
    return db_reserva


def sincronizar_reservas_lote(
    db: Session, lote: schemas.SincronizacionReservasLoteRequest
) -> schemas.SincronizacionReservasLoteResponse:
    resultados = []
    confirmadas = 0
    rechazadas = 0
    duplicadas = 0

    for res_in in lote.reservas:
        uuid_op = res_in.operacion_uuid
        if not uuid_op:
            raise HTTPException(422, "Cada reserva offline requiere UUID")
        existente = db.query(models.Reserva).filter_by(operacion_uuid=uuid_op).first()
        if existente:
            duplicadas += 1
            resultados.append(
                schemas.ResultadoSincronizacionReservaItem(
                    operacion_uuid=uuid_op,
                    estado="CONFIRMADA",
                    mensaje="Reserva previamente sincronizada",
                    id_generado=existente.id,
                )
            )
            continue

        try:
            res_in.operacion_uuid = uuid_op
            db_res = create_reserva(db, res_in)
            confirmadas += 1
            resultados.append(
                schemas.ResultadoSincronizacionReservaItem(
                    operacion_uuid=uuid_op,
                    estado="CONFIRMADA",
                    mensaje="Reserva offline confirmada y sincronizada",
                    id_generado=db_res.id,
                )
            )
        except Exception as e:
            db.rollback()
            rechazadas += 1
            resultados.append(
                schemas.ResultadoSincronizacionReservaItem(
                    operacion_uuid=uuid_op,
                    estado="RECHAZADA_CONFLICTO"
                    if isinstance(e, HTTPException)
                    else "ERROR_REINTENTABLE",
                    mensaje=str(e.detail)
                    if isinstance(e, HTTPException)
                    else "Fallo temporal; reintente",
                )
            )

    return schemas.SincronizacionReservasLoteResponse(
        total=len(lote.reservas),
        confirmadas=confirmadas,
        rechazadas=rechazadas,
        duplicadas_ignoradas=duplicadas,
        resultados=resultados,
    )


def update_estado_reserva(db: Session, reserva_id: int, estado: str):
    db_reserva = (
        db.query(models.Reserva).filter(models.Reserva.id == reserva_id).first()
    )
    if not db_reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if estado not in {"Pendiente", "Preparada", "Completada", "Cancelada"}:
        raise HTTPException(422, "Estado de reserva inválido")
    db_reserva.estado = estado
    db.commit()
    db.refresh(db_reserva)
    return db_reserva
