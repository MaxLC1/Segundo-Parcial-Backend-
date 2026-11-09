"""Modelo de Bitácora del Sistema - Registro de eventos y auditoría."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Bitacora(Base):
    __tablename__ = "bitacora"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_email = Column(String(100), nullable=True)
    usuario_nombre = Column(String(100), nullable=True)
    rol = Column(String(50), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    empresa_nombre = Column(String(200), nullable=True)
    ip = Column(String(45), nullable=True)
    accion = Column(String(100), nullable=False)
    modulo = Column(String(100), nullable=False)
    detalle = Column(Text, nullable=True)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])

