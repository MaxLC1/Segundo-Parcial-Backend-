from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Coleccion(Base):
    __tablename__ = "colecciones"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    productos = relationship("Producto", back_populates="coleccion")

class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    contacto = Column(String(100))
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    productos = relationship("Producto", back_populates="proveedor")

class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    productos = relationship("Producto", back_populates="categoria")

class Temporada(Base):
    __tablename__ = "temporadas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    activa = Column(Boolean, default=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    productos = relationship("Producto", back_populates="temporada")

class Talla(Base):
    __tablename__ = "tallas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(10), unique=True, nullable=False)

class Color(Base):
    __tablename__ = "colores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    codigo_hex = Column(String(7))

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    precio = Column(Float, nullable=False)
    costo_adquisicion = Column(Float, default=0.0) # Para métricas de capital y pérdida
    antiguedad_temporadas = Column(Integer, default=0) # 0: actual, 1: 1 temporada pasada (-30%), 2: 2 pasadas (-60%)
    descuento_porcentaje = Column(Float, default=0.0)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    temporada_id = Column(Integer, ForeignKey("temporadas.id"))
    coleccion_id = Column(Integer, ForeignKey("colecciones.id"))
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))
    
    modelo_3d_url = Column(String(255), nullable=True)
    imagen_url = Column(String(255), nullable=True)

    categoria = relationship("Categoria", back_populates="productos")
    temporada = relationship("Temporada", back_populates="productos")
    coleccion = relationship("Coleccion", back_populates="productos")
    proveedor = relationship("Proveedor", back_populates="productos")
    empresa = relationship("Empresa")

class ReglaOferta(Base):
    __tablename__ = "reglas_ofertas"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(50), default="MAYOREO") # MAYOREO, TEMPORADA_PASADA, LIQUIDACION
    cantidad_minima = Column(Integer, default=1)
    descuento_porcentaje = Column(Float, nullable=False)
    antiguedad_temporadas = Column(Integer, default=0)
    descripcion = Column(String(255), nullable=True)
    activa = Column(Boolean, default=True)

    empresa = relationship("Empresa")

