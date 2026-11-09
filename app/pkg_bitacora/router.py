"""Router de Bitácora - Endpoints de auditoría del sistema."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from . import services
from .schemas import BitacoraOut

router = APIRouter(tags=["Bitácora"])


@router.get("/eventos", response_model=List[BitacoraOut])
def listar_eventos(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    usuario_email: Optional[str] = Query(None, description="Filtrar por email"),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    accion: Optional[str] = Query(None, description="Buscar en acción"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (ISO)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (ISO)"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lista eventos de la bitácora. Solo AdministradorPlataforma y Administrador."""
    role = db.info.get("role")
    if role not in ("AdministradorPlataforma", "Administrador"):
        raise HTTPException(403, "Solo administradores pueden consultar la bitácora")

    # Admin de empresa solo ve eventos de su propia empresa
    if role == "Administrador":
        tenant = db.info.get("tenant_id")
        empresa_id = tenant  # Forzar filtro por su empresa

    return services.consultar_bitacora(
        db=db,
        empresa_id=empresa_id,
        usuario_email=usuario_email,
        modulo=modulo,
        accion=accion,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
        offset=offset,
    )


@router.get("/modulos")
def listar_modulos(db: Session = Depends(get_db)):
    """Lista los módulos que han registrado eventos."""
    role = db.info.get("role")
    if role not in ("AdministradorPlataforma", "Administrador"):
        raise HTTPException(403, "Solo administradores pueden consultar la bitácora")

    from sqlalchemy import distinct
    from . import Bitacora

    query = db.query(distinct(Bitacora.modulo)).order_by(Bitacora.modulo)
    if role == "Administrador":
        tenant = db.info.get("tenant_id")
        query = query.filter(Bitacora.empresa_id == tenant)
    return [row[0] for row in query.all() if row[0]]

