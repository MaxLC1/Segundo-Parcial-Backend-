"""Servicio de Bitácora - Registro y consulta de eventos del sistema."""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import Bitacora


def registrar_evento(
    db: Session,
    accion: str,
    modulo: str,
    detalle: Optional[str] = None,
    ip: Optional[str] = None,
    usuario_id: Optional[int] = None,
    usuario_email: Optional[str] = None,
    usuario_nombre: Optional[str] = None,
    rol: Optional[str] = None,
    empresa_id: Optional[int] = None,
    empresa_nombre: Optional[str] = None,
):
    """Registra un evento en la bitácora del sistema."""
    evento = Bitacora(
        fecha=datetime.now(timezone.utc),
        usuario_id=usuario_id,
        usuario_email=usuario_email,
        usuario_nombre=usuario_nombre,
        rol=rol,
        empresa_id=empresa_id,
        empresa_nombre=empresa_nombre,
        ip=ip,
        accion=accion,
        modulo=modulo,
        detalle=detalle,
    )
    db.add(evento)
    db.commit()
    return evento


def registrar_desde_request(
    db: Session,
    accion: str,
    modulo: str,
    detalle: Optional[str] = None,
    ip: Optional[str] = None,
):
    """Registra evento usando el actor de la sesión actual del request."""
    actor = db.info.get("actor")
    role = db.info.get("role")
    tenant = db.info.get("tenant_id")
    empresa_nombre = None
    if actor and actor.empresa:
        empresa_nombre = actor.empresa.nombre
    elif tenant:
        from app.pkg_saas.models import Empresa
        emp = db.query(Empresa).filter_by(id=tenant).first()
        empresa_nombre = emp.nombre if emp else None

    return registrar_evento(
        db=db,
        accion=accion,
        modulo=modulo,
        detalle=detalle,
        ip=ip,
        usuario_id=actor.id if actor else None,
        usuario_email=actor.email if actor else None,
        usuario_nombre=actor.nombre_completo if actor else None,
        rol=role,
        empresa_id=actor.empresa_id if actor else tenant,
        empresa_nombre=empresa_nombre,
    )


def consultar_bitacora(
    db: Session,
    empresa_id: Optional[int] = None,
    usuario_email: Optional[str] = None,
    modulo: Optional[str] = None,
    accion: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Bitacora]:
    """Consulta eventos de la bitácora con filtros opcionales."""
    query = db.query(Bitacora)
    if empresa_id is not None:
        query = query.filter(Bitacora.empresa_id == empresa_id)
    if usuario_email:
        query = query.filter(Bitacora.usuario_email.ilike(f"%{usuario_email}%"))
    if modulo:
        query = query.filter(Bitacora.modulo == modulo)
    if accion:
        query = query.filter(Bitacora.accion.ilike(f"%{accion}%"))
    if fecha_desde:
        query = query.filter(Bitacora.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Bitacora.fecha <= fecha_hasta)
    return query.order_by(desc(Bitacora.id)).offset(offset).limit(limit).all()

