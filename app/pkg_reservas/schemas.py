from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DetalleReservaBase(BaseModel):
    producto_id: int
    talla_id: int
    color_id: int
    cantidad: int = 1

class DetalleReservaCreate(DetalleReservaBase):
    pass

class DetalleReservaOut(DetalleReservaBase):
    id: int
    reserva_id: int
    class Config:
        from_attributes = True

class ReservaBase(BaseModel):
    usuario_id: int
    sucursal_id: int
    empresa_id: Optional[int] = None
    operacion_uuid: Optional[str] = None
    origen: Optional[str] = "ONLINE"

class ReservaCreate(ReservaBase):
    detalles: List[DetalleReservaCreate]

class ReservaOut(ReservaBase):
    id: int
    fecha_reserva: datetime
    estado: str
    estado_sincronizacion: Optional[str] = "CONFIRMADA"
    motivo_rechazo: Optional[str] = None
    detalles: List[DetalleReservaOut] = []
    
    class Config:
        from_attributes = True

class SincronizacionReservasLoteRequest(BaseModel):
    empresa_id: Optional[int] = None
    reservas: List[ReservaCreate] = []

class ResultadoSincronizacionReservaItem(BaseModel):
    operacion_uuid: str
    estado: str
    mensaje: str
    id_generado: Optional[int] = None

class SincronizacionReservasLoteResponse(BaseModel):
    total: int
    confirmadas: int
    rechazadas: int
    duplicadas_ignoradas: int
    resultados: List[ResultadoSincronizacionReservaItem]
