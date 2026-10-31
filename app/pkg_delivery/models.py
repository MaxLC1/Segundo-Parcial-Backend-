from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class ServicioDelivery(Base):
    __tablename__ = "servicio_delivery"

    id = Column(Integer, primary_key=True, index=True)
    devolucion_id = Column(Integer, ForeignKey("devoluciones.id"), nullable=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    repartidor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    estado = Column(String(50), default="Pendiente")
    fecha_asignacion = Column(DateTime, nullable=True)

    devolucion = relationship("Devolucion")
    repartidor = relationship("Usuario")
    empresa = relationship("Empresa")
