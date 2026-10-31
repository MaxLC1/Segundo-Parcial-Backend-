from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PlanBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio_mensual: float = 0.0
    max_sucursales: int = 2
    permite_ia_generativa: bool = False
    permite_offline: bool = True
    permite_cambios_prendas: bool = True
    activo: bool = True

class PlanCreate(PlanBase):
    pass

class PlanOut(PlanBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EmpresaBase(BaseModel):
    nombre: str
    codigo: str
    nit_rut: Optional[str] = None
    telefono: Optional[str] = None
    email_contacto: Optional[str] = None
    direccion_fiscal: Optional[str] = None
    logo_url: Optional[str] = None
    activa: bool = True

class EmpresaCreate(EmpresaBase):
    plan_id: Optional[int] = 1 # Por defecto Básico

class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email_contacto: Optional[str] = None
    direccion_fiscal: Optional[str] = None
    logo_url: Optional[str] = None
    activa: Optional[bool] = None

class SuscripcionBase(BaseModel):
    empresa_id: int
    plan_id: int
    fecha_inicio: Optional[datetime] = None
    fecha_vencimiento: datetime
    estado: str = "Activa"
    auto_renovacion: bool = True
    notas: Optional[str] = None

class SuscripcionCreate(BaseModel):
    empresa_id: int
    plan_id: int
    dias_duracion: int = 365
    notas: Optional[str] = None

class SuscripcionOut(SuscripcionBase):
    id: int
    plan: Optional[PlanOut] = None

    class Config:
        from_attributes = True

class EmpresaOut(EmpresaBase):
    id: int
    created_at: Optional[datetime] = None
    suscripciones: List[SuscripcionOut] = []

    class Config:
        from_attributes = True

class LimitesEmpresaOut(BaseModel):
    empresa_id: int
    empresa_nombre: str
    plan_nombre: str
    max_sucursales: int
    sucursales_activas: int
    permite_ia_generativa: bool
    permite_offline: bool
    suscripcion_activa: bool
    fecha_vencimiento: Optional[datetime] = None
