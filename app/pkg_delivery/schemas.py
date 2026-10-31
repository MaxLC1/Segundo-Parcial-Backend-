from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DeliveryBase(BaseModel):
    devolucion_id: Optional[int] = None
    venta_id: Optional[int] = None

class DeliveryCreate(DeliveryBase):
    pass

class DeliveryOut(DeliveryBase):
    id: int
    repartidor_id: Optional[int]
    estado: str
    fecha_asignacion: Optional[datetime]

    class Config:
        from_attributes = True

class DeliveryUpdate(BaseModel):
    estado: str

class DeliveryAssign(BaseModel):
    repartidor_id: int
