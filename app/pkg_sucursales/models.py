from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Ciudad(Base):
    __tablename__ = "ciudades"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    
    sucursales = relationship("Sucursal", back_populates="ciudad")

class Sucursal(Base):
    __tablename__ = "sucursales"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(200))
    ciudad_id = Column(Integer, ForeignKey("ciudades.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    ciudad = relationship("Ciudad", back_populates="sucursales")
    empresa = relationship("Empresa", back_populates="sucursales")
    inventarios = relationship("Inventario", back_populates="sucursal", cascade="all, delete-orphan")

class Inventario(Base):
    __tablename__ = "inventarios"
    id = Column(Integer, primary_key=True, index=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    talla_id = Column(Integer, ForeignKey("tallas.id"), nullable=False)
    color_id = Column(Integer, ForeignKey("colores.id"), nullable=False)
    cantidad = Column(Integer, default=0)

    sucursal = relationship("Sucursal", back_populates="inventarios")
    producto = relationship("Producto")
    talla = relationship("Talla")
    color = relationship("Color")
