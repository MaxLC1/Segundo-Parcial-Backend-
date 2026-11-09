from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from app.core.database import Base


class Cupon(Base):
    __tablename__ = "cupones"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    tipo = Column(String(20), nullable=False)
    valor = Column(Float, nullable=False)
    criterios = Column(JSON, default=dict)
    fecha_vencimiento = Column(DateTime, nullable=False)
    max_usos = Column(Integer, default=1)
    usos = Column(Integer, default=0)
    activo = Column(Boolean, default=True)


class CanjeCupon(Base):
    __tablename__ = "canjes_cupones"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cupon_id = Column(Integer, ForeignKey("cupones.id"), nullable=False)
    venta_id = Column(Integer, ForeignKey("ventas.id"), unique=True, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    monto = Column(Float, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)


class Notificacion(Base):
    __tablename__ = "notificaciones"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    titulo = Column(String(120), nullable=False)
    mensaje = Column(String(1000), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    vence = Column(DateTime, nullable=True)


class Traspaso(Base):
    __tablename__ = "traspasos"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    operacion_uuid = Column(String(36), unique=True, nullable=False)
    origen_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    destino_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    detalles = Column(JSON, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(20), default="CONFIRMADO")
