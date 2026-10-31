from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.core.database import Base

class TransaccionPagoOTP(Base):
    __tablename__ = "transacciones_pagos_otp"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    transaccion_id = Column(String(50), unique=True, index=True, nullable=False)
    monto = Column(Float, nullable=False)
    metodo = Column(String(50), default="Tarjeta")
    cliente_email = Column(String(100), nullable=True)
    cliente_telefono = Column(String(50), nullable=True)
    
    codigo_otp = Column(String(6), nullable=False)
    estado = Column(String(30), default="PENDIENTE_OTP") # PENDIENTE_OTP, AUTORIZADO, RECHAZADO, EXPIRADO
    intentos = Column(Integer, default=0)
    
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=5))

    empresa = relationship("Empresa")
