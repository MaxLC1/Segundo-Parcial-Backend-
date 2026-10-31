from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Reserva(Base):
    __tablename__ = "reservas"
    id = Column(Integer, primary_key=True, index=True)
    fecha_reserva = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(50), default="Pendiente")
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    
    operacion_uuid = Column(String(36), unique=True, index=True, nullable=True)
    estado_sincronizacion = Column(String(50), default="CONFIRMADA")
    motivo_rechazo = Column(String(255), nullable=True)
    origen = Column(String(20), default="ONLINE")

    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"))
    
    usuario = relationship("Usuario")
    sucursal = relationship("Sucursal")
    empresa = relationship("Empresa")
    detalles = relationship("DetalleReserva", back_populates="reserva", cascade="all, delete-orphan")

class DetalleReserva(Base):
    __tablename__ = "detalle_reservas"
    id = Column(Integer, primary_key=True, index=True)
    reserva_id = Column(Integer, ForeignKey("reservas.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    talla_id = Column(Integer, ForeignKey("tallas.id"))
    color_id = Column(Integer, ForeignKey("colores.id"))
    cantidad = Column(Integer, default=1)
    
    reserva = relationship("Reserva", back_populates="detalles")
    producto = relationship("Producto")
    talla = relationship("Talla")
    color = relationship("Color")
