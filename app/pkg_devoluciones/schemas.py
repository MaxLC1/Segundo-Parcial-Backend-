from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class DevolucionBase(BaseModel):
    venta_id: int
    motivo: str
    tipo_solicitud: str = "Devolución"
    requiere_delivery: int = 0

class DevolucionCreate(DevolucionBase):
    pass

class DevolucionOut(DevolucionBase):
    id: int
    estado: str
    fecha_solicitud: datetime

    class Config:
        from_attributes = True

class DevolucionUpdate(BaseModel):
    estado: str

# -- POLÍTICAS DE DEVOLUCIÓN --
class PoliticaDevolucionBase(BaseModel):
    nombre: str = "Política Oficial de Devoluciones y Cambios"
    tipo_reembolso_menor_valor: str = "CUPON_CREDITO" # CUPON_CREDITO, REEMBOLSO_50_PCT, REEMBOLSO_100_PCT, SIN_REEMBOLSO
    plazo_maximo_dias: int = 30
    permite_cambio_mayor_valor: bool = True
    activa: bool = True
    empresa_id: Optional[int] = None

class PoliticaDevolucionCreate(PoliticaDevolucionBase):
    pass

class PoliticaDevolucionOut(PoliticaDevolucionBase):
    id: int
    class Config:
        from_attributes = True

# -- NOTAS DE DEVOLUCIÓN --
class NotaDevolucionCreate(BaseModel):
    venta_id: int
    empresa_id: Optional[int] = 1
    usuario_id: Optional[int] = 2 # Cliente
    repartidor_id: Optional[int] = None
    sucursal_id: Optional[int] = 1
    motivo: str
    tipo_solicitud: str = "Cambio por Mayor Valor" # Cambio por Mayor Valor, Cambio por Menor Valor, Devolución Directa
    
    prenda_devuelta_info: str
    prenda_nueva_info: Optional[str] = None
    
    precio_prenda_original: float
    precio_prenda_nueva: Optional[float] = 0.0

class NotaDevolucionOut(BaseModel):
    id: int
    codigo_nota: str
    empresa_id: Optional[int] = None
    venta_id: int
    usuario_id: Optional[int] = None
    repartidor_id: Optional[int] = None
    sucursal_id: Optional[int] = None
    
    motivo: str
    tipo_solicitud: str
    estado: str
    visible_para_cliente: bool
    
    prenda_devuelta_info: str
    prenda_nueva_info: Optional[str] = None
    precio_prenda_original: float
    precio_prenda_nueva: float
    diferencia_precio: float
    
    mensaje_notificacion: Optional[str] = None
    cupon_generado: Optional[str] = None
    
    fecha_creacion: datetime
    fecha_completada: Optional[datetime] = None

    class Config:
        from_attributes = True

class CompletarNotaRequest(BaseModel):
    repartidor_id: Optional[int] = None
    observaciones: Optional[str] = None

