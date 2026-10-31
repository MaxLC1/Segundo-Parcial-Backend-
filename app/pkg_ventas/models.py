from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Venta(Base):
    __tablename__ = "ventas"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, default=0.0)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    operacion_uuid = Column(String(36), unique=True, index=True, nullable=True)
    estado_sincronizacion = Column(String(50), default="CONFIRMADA")
    motivo_rechazo = Column(String(255), nullable=True)
    origen = Column(String(20), default="ONLINE")

    metodo_pago = Column(String(50), default="Efectivo")
    transaccion_id = Column(String(100), nullable=True)
    tipo_entrega = Column(String(50), default="Recojo en Tienda")
    direccion_envio = Column(String(255), nullable=True)
    
    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    usuario = relationship("Usuario")
    sucursal = relationship("Sucursal")
    empresa = relationship("Empresa")
    cambios = relationship("CambioPrenda", back_populates="venta")

class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"
    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    talla_id = Column(Integer, ForeignKey("tallas.id"))
    color_id = Column(Integer, ForeignKey("colores.id"))
    cantidad = Column(Integer, default=1)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto")
    talla = relationship("Talla")
    color = relationship("Color")

class CambioPrenda(Base):
    __tablename__ = "cambios_prendas"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_cambio = Column(DateTime, default=datetime.utcnow)
    
    producto_devuelto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    talla_devuelta_id = Column(Integer, ForeignKey("tallas.id"), nullable=False)
    color_devuelto_id = Column(Integer, ForeignKey("colores.id"), nullable=False)
    cantidad_devuelta = Column(Integer, default=1)
    
    producto_nuevo_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    talla_nueva_id = Column(Integer, ForeignKey("tallas.id"), nullable=False)
    color_nuevo_id = Column(Integer, ForeignKey("colores.id"), nullable=False)
    cantidad_nueva = Column(Integer, default=1)
    
    diferencia_precio = Column(Float, default=0.0)
    motivo = Column(String(255), nullable=True)
    estado = Column(String(50), default="Aprobado")

    venta = relationship("Venta", back_populates="cambios")
    sucursal = relationship("Sucursal")
    producto_devuelto = relationship("Producto", foreign_keys=[producto_devuelto_id])
    producto_nuevo = relationship("Producto", foreign_keys=[producto_nuevo_id])
    talla_devuelta = relationship("Talla", foreign_keys=[talla_devuelta_id])
    talla_nueva = relationship("Talla", foreign_keys=[talla_nueva_id])
    color_devuelto = relationship("Color", foreign_keys=[color_devuelto_id])
    color_nuevo = relationship("Color", foreign_keys=[color_nuevo_id])
