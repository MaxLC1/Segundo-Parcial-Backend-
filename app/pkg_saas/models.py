from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Plan(Base):
    __tablename__ = "planes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False) # "Básico", "Profesional"
    descripcion = Column(String(255), nullable=True)
    precio_mensual = Column(Float, default=0.0)
    max_sucursales = Column(Integer, nullable=False, default=2) # Básico: 2, Profesional: 10
    permite_ia_generativa = Column(Boolean, default=False) # Básico: False, Profesional: True
    permite_offline = Column(Boolean, default=True)
    permite_cambios_prendas = Column(Boolean, default=True)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    suscripciones = relationship("Suscripcion", back_populates="plan")

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, index=True, nullable=False)
    codigo = Column(String(50), unique=True, index=True, nullable=False) # "zara-bo", "urban-style"
    nit_rut = Column(String(50), nullable=True)
    telefono = Column(String(50), nullable=True)
    email_contacto = Column(String(100), nullable=True)
    direccion_fiscal = Column(String(200), nullable=True)
    logo_url = Column(String(255), nullable=True)
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones del tenant
    suscripciones = relationship("Suscripcion", back_populates="empresa", cascade="all, delete-orphan")
    sucursales = relationship("Sucursal", back_populates="empresa")
    usuarios = relationship("Usuario", back_populates="empresa")

class Suscripcion(Base):
    __tablename__ = "suscripciones"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("planes.id"), nullable=False)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_vencimiento = Column(DateTime, nullable=False)
    estado = Column(String(50), default="Activa") # "Activa", "Vencida", "Cancelada"
    auto_renovacion = Column(Boolean, default=True)
    notas = Column(Text, nullable=True)

    empresa = relationship("Empresa", back_populates="suscripciones")
    plan = relationship("Plan", back_populates="suscripciones")
