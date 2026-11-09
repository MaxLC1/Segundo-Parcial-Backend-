from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class DetalleVentaCreate(BaseModel):
    producto_id: int
    talla_id: int
    color_id: int
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0, allow_inf_nan=False)


class VentaCreate(BaseModel):
    sucursal_id: int
    usuario_id: int
    empresa_id: Optional[int] = None
    cupon_codigo: Optional[str] = None
    metodo_pago: str = "Efectivo"
    transaccion_id: Optional[str] = None
    tipo_entrega: str = "Recojo en Tienda"
    direccion_envio: Optional[str] = None
    operacion_uuid: Optional[str] = None  # UUID único offline
    origen: str = "ONLINE"  # ONLINE, PWA_OFFLINE, MOVIL_OFFLINE
    fecha: Optional[datetime] = None
    detalles: List[DetalleVentaCreate] = Field(min_length=1)


class DetalleVentaOut(BaseModel):
    id: int
    producto_id: int
    talla_id: int
    color_id: int
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0, allow_inf_nan=False)
    subtotal: float

    class Config:
        from_attributes = True


class VentaOut(BaseModel):
    id: int
    fecha: datetime
    total: float
    usuario_id: int
    sucursal_id: int
    empresa_id: Optional[int] = None
    metodo_pago: Optional[str] = None
    transaccion_id: Optional[str] = None
    tipo_entrega: Optional[str] = None
    direccion_envio: Optional[str] = None
    operacion_uuid: Optional[str] = None
    estado_sincronizacion: Optional[str] = "CONFIRMADA"
    motivo_rechazo: Optional[str] = None
    origen: Optional[str] = "ONLINE"
    detalles: List[DetalleVentaOut] = []

    class Config:
        from_attributes = True


# -- Esquemas de Sincronización Offline (Desafíos II y IV) --
class ResultadoSincronizacionItem(BaseModel):
    operacion_uuid: str
    estado: str  # "CONFIRMADA", "RECHAZADA_CONFLICTO", "YA_EXISTENTE"
    mensaje: str
    id_generado: Optional[int] = None
    fecha_proceso: datetime = Field(default_factory=datetime.utcnow)


class SincronizacionLoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: Optional[int] = None
    ventas: List[VentaCreate] = []


class SincronizacionLoteResponse(BaseModel):
    total: int
    confirmadas: int
    rechazadas: int
    duplicadas_ignoradas: int
    resultados: List[ResultadoSincronizacionItem]


# -- Esquemas de Cambios de Prendas --
class CambioPrendaCreate(BaseModel):
    venta_id: int
    sucursal_id: int
    empresa_id: Optional[int] = None
    usuario_id: Optional[int] = None
    producto_devuelto_id: int
    talla_devuelta_id: int
    color_devuelto_id: int
    cantidad_devuelta: int = 1
    producto_nuevo_id: int
    talla_nueva_id: int
    color_nuevo_id: int
    cantidad_nueva: int = 1
    motivo: Optional[str] = "Cambio de talla / modelo por el cliente"


class CambioPrendaOut(BaseModel):
    id: int
    venta_id: int
    sucursal_id: int
    empresa_id: Optional[int] = None
    fecha_cambio: datetime
    producto_devuelto_id: int
    producto_nuevo_id: int
    cantidad_devuelta: int
    cantidad_nueva: int
    diferencia_precio: float
    motivo: Optional[str] = None
    estado: str

    class Config:
        from_attributes = True
