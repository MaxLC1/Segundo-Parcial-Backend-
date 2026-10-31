from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.pkg_seguridad.models import Usuario
from . import schemas, services

router = APIRouter(tags=["Delivery"], prefix="/delivery")

@router.get("/", response_model=List[schemas.DeliveryOut])
def list_deliveries(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.rol.nombre == "Administrador":
        return services.get_todas_entregas(db)
    elif current_user.rol.nombre == "Repartidor":
        return services.get_entregas_by_repartidor(db, current_user.id)
    else:
        raise HTTPException(status_code=403, detail="No autorizado")

@router.post("/", response_model=schemas.DeliveryOut, status_code=status.HTTP_201_CREATED)
def create_delivery(delivery: schemas.DeliveryCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.rol.nombre != "Administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear servicios")
    return services.create_servicio(db, delivery)

@router.put("/{delivery_id}/asignar", response_model=schemas.DeliveryOut)
def asignar_repartidor(delivery_id: int, payload: schemas.DeliveryAssign, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.rol.nombre != "Administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden asignar")
    return services.assign_repartidor(db, delivery_id, payload.repartidor_id)

@router.put("/{delivery_id}/estado", response_model=schemas.DeliveryOut)
def update_estado_delivery(delivery_id: int, payload: schemas.DeliveryUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    # Un repartidor solo puede actualizar si está asignado (o puede auto-asignarse si estaba Pendiente)
    return services.update_estado(db, delivery_id, payload.estado, current_user.id)
