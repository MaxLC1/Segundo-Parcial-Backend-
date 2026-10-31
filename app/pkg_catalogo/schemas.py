from pydantic import BaseModel
from typing import Optional, List

# -- COLECCIONES --
class ColeccionBase(BaseModel):
    nombre: str
    empresa_id: Optional[int] = None

class ColeccionCreate(ColeccionBase):
    pass

class ColeccionUpdate(ColeccionBase):
    pass

class ColeccionOut(ColeccionBase):
    id: int
    class Config:
        from_attributes = True

# -- PROVEEDORES --
class ProveedorBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None
    empresa_id: Optional[int] = None

class ProveedorCreate(ProveedorBase):
    pass

class ProveedorUpdate(ProveedorBase):
    pass

class ProveedorOut(ProveedorBase):
    id: int
    class Config:
        from_attributes = True

# -- CATEGORIAS --
class CategoriaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    activo: Optional[bool] = True
    empresa_id: Optional[int] = None

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaOut(CategoriaBase):
    id: int
    class Config:
        from_attributes = True

# -- TALLAS --
class TallaBase(BaseModel):
    nombre: str

class TallaCreate(TallaBase):
    pass

class TallaOut(TallaBase):
    id: int
    class Config:
        from_attributes = True

# -- COLORES --
class ColorBase(BaseModel):
    nombre: str
    codigo_hex: Optional[str] = None

class ColorCreate(ColorBase):
    pass

class ColorOut(ColorBase):
    id: int
    class Config:
        from_attributes = True

# -- TEMPORADAS --
class TemporadaBase(BaseModel):
    nombre: str
    activa: Optional[bool] = True
    empresa_id: Optional[int] = None

class TemporadaCreate(TemporadaBase):
    pass

class TemporadaOut(TemporadaBase):
    id: int
    class Config:
        from_attributes = True

# -- PRODUCTOS --
class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    costo_adquisicion: Optional[float] = 0.0
    antiguedad_temporadas: Optional[int] = 0
    descuento_porcentaje: Optional[float] = 0.0
    categoria_id: Optional[int] = None
    modelo_3d_url: Optional[str] = None
    imagen_url: Optional[str] = None
    temporada_id: Optional[int] = None
    coleccion_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    empresa_id: Optional[int] = None

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    costo_adquisicion: Optional[float] = None
    antiguedad_temporadas: Optional[int] = None
    descuento_porcentaje: Optional[float] = None
    categoria_id: Optional[int] = None
    modelo_3d_url: Optional[str] = None
    imagen_url: Optional[str] = None
    temporada_id: Optional[int] = None
    coleccion_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    empresa_id: Optional[int] = None

class ProductoOut(ProductoBase):
    id: int
    precio_oferta: Optional[float] = None
    descuento_aplicado_pct: Optional[float] = None
    ahorro_monto: Optional[float] = None
    
    # Métricas exclusivas para empleados / admins (auditoría de capital)
    costo_real: Optional[float] = None
    margen_recuperacion_monto: Optional[float] = None
    recuperacion_capital_pct: Optional[float] = None
    estado_capital: Optional[str] = None # GANANCIA, RECUPERACION_EXACTA, PERDIDA_ASUMIDA
    
    categoria: Optional[CategoriaOut] = None
    temporada: Optional[TemporadaOut] = None
    coleccion: Optional[ColeccionOut] = None
    proveedor: Optional[ProveedorOut] = None

    class Config:
        from_attributes = True

# -- REGLAS DE OFERTAS --
class ReglaOfertaBase(BaseModel):
    nombre: str
    tipo: str = "MAYOREO" # MAYOREO, TEMPORADA_PASADA, LIQUIDACION
    cantidad_minima: int = 1
    descuento_porcentaje: float
    antiguedad_temporadas: int = 0
    descripcion: Optional[str] = None
    activa: bool = True
    empresa_id: Optional[int] = None

class ReglaOfertaCreate(ReglaOfertaBase):
    pass

class ReglaOfertaUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    cantidad_minima: Optional[int] = None
    descuento_porcentaje: Optional[float] = None
    antiguedad_temporadas: Optional[int] = None
    descripcion: Optional[str] = None
    activa: Optional[bool] = None

class ReglaOfertaOut(ReglaOfertaBase):
    id: int
    class Config:
        from_attributes = True

