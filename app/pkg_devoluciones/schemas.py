from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal


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
    tipo_reembolso_menor_valor: Literal[
        "CUPON_CREDITO",
        "CUPON",
        "REEMBOLSO_50_PCT",
        "REEMBOLSO_100_PCT",
        "REEMBOLSO_PORCENTAJE",
        "SIN_REEMBOLSO",
    ] = "CUPON_CREDITO"  # CUPON_CREDITO, REEMBOLSO_50_PCT, REEMBOLSO_100_PCT, SIN_REEMBOLSO
    plazo_maximo_dias: int = Field(default=30, ge=0, le=365)
    porcentaje_reembolso: float = Field(default=100, ge=0, le=100)
    vigencia_nota_dias: int = Field(default=30, ge=1, le=365)
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
    detalle_venta_id: int
    cantidad: int = Field(default=1, gt=0)
    motivo: str = Field(min_length=3, max_length=255)
    tipo_solicitud: Literal[
        "Cambio por Mayor Valor",
        "Cambio por Menor Valor",
        "Cambio de Talla o Color",
        "Devolución Directa",
    ]
    producto_nuevo_id: Optional[int] = None
    talla_nueva_id: Optional[int] = None
    color_nuevo_id: Optional[int] = None


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
    fecha_expiracion: Optional[datetime] = None
    monto_reembolso: float = 0
    resolucion: Optional[str] = None
    detalle_venta_id: Optional[int] = None
    cantidad: int = 1
    producto_nuevo_id: Optional[int] = None
    talla_nueva_id: Optional[int] = None
    color_nuevo_id: Optional[int] = None

    class Config:
        from_attributes = True


class CompletarNotaRequest(BaseModel):
    repartidor_id: Optional[int] = None
    observaciones: Optional[str] = None
