from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from . import schemas, services

router = APIRouter(tags=["Reservas"])

@router.get("/", response_model=List[schemas.ReservaOut])
def read_reservas(skip: int = 0, limit: int = 100, empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene la lista de reservas registradas con filtro opcional por empresa."""
    return services.get_reservas(db, skip=skip, limit=limit, empresa_id=empresa_id)

@router.post("/", response_model=schemas.ReservaOut, status_code=status.HTTP_201_CREATED)
def create_reserva(reserva: schemas.ReservaCreate, db: Session = Depends(get_db)):
    """Crea una nueva reserva de prendas."""
    return services.create_reserva(db=db, reserva=reserva)

@router.post("/sincronizar-offline", response_model=schemas.SincronizacionReservasLoteResponse)
def sincronizar_reservas_offline(lote: schemas.SincronizacionReservasLoteRequest, db: Session = Depends(get_db)):
    """Sincroniza un lote de reservas registradas offline desde la PWA o aplicación móvil."""
    return services.sincronizar_reservas_lote(db=db, lote=lote)

@router.put("/{reserva_id}/estado", response_model=schemas.ReservaOut)
def update_estado(reserva_id: int, estado: str, db: Session = Depends(get_db)):
    """Actualiza el estado de una reserva (ej. Preparada, Cancelada, Completada)."""
    return services.update_estado_reserva(db=db, reserva_id=reserva_id, estado=estado)
