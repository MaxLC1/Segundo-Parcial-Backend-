from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional, List
from datetime import datetime

from . import models, schemas
from app.pkg_sucursales.models import Sucursal

def get_reservas(db: Session, skip: int = 0, limit: int = 100, empresa_id: Optional[int] = None):
    query = db.query(models.Reserva)
    if empresa_id is not None:
        query = query.filter(models.Reserva.empresa_id == empresa_id)
    return query.order_by(models.Reserva.id.desc()).offset(skip).limit(limit).all()

def create_reserva(db: Session, reserva: schemas.ReservaCreate):
    # Idempotencia por operacion_uuid
    if reserva.operacion_uuid:
        existente = db.query(models.Reserva).filter_by(operacion_uuid=reserva.operacion_uuid).first()
        if existente:
            return existente

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
        fecha_reserva=datetime.utcnow()
    )
    db.add(db_reserva)
    db.commit()
    db.refresh(db_reserva)
    
    for detalle in reserva.detalles:
        db_detalle = models.DetalleReserva(
            reserva_id=db_reserva.id,
            producto_id=detalle.producto_id,
            talla_id=detalle.talla_id,
            color_id=detalle.color_id,
            cantidad=detalle.cantidad
        )
        db.add(db_detalle)
        
    db.commit()
    db.refresh(db_reserva)
    return db_reserva

def sincronizar_reservas_lote(db: Session, lote: schemas.SincronizacionReservasLoteRequest) -> schemas.SincronizacionReservasLoteResponse:
    resultados = []
    confirmadas = 0
    rechazadas = 0
    duplicadas = 0

    for res_in in lote.reservas:
        uuid_op = res_in.operacion_uuid or f"offline-res-{datetime.utcnow().timestamp()}"
        existente = db.query(models.Reserva).filter_by(operacion_uuid=uuid_op).first()
        if existente:
            duplicadas += 1
            resultados.append(schemas.ResultadoSincronizacionReservaItem(
                operacion_uuid=uuid_op,
                estado="CONFIRMADA",
                mensaje="Reserva previamente sincronizada",
                id_generado=existente.id
            ))
            continue

        try:
            res_in.operacion_uuid = uuid_op
            db_res = create_reserva(db, res_in)
            confirmadas += 1
            resultados.append(schemas.ResultadoSincronizacionReservaItem(
                operacion_uuid=uuid_op,
                estado="CONFIRMADA",
                mensaje="Reserva offline confirmada y sincronizada",
                id_generado=db_res.id
            ))
        except Exception as e:
            rechazadas += 1
            resultados.append(schemas.ResultadoSincronizacionReservaItem(
                operacion_uuid=uuid_op,
                estado="RECHAZADA_CONFLICTO",
                mensaje=str(e)
            ))

    return schemas.SincronizacionReservasLoteResponse(
        total=len(lote.reservas),
        confirmadas=confirmadas,
        rechazadas=rechazadas,
        duplicadas_ignoradas=duplicadas,
        resultados=resultados
    )

def update_estado_reserva(db: Session, reserva_id: int, estado: str):
    db_reserva = db.query(models.Reserva).filter(models.Reserva.id == reserva_id).first()
    if not db_reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    db_reserva.estado = estado
    db.commit()
    db.refresh(db_reserva)
    return db_reserva
