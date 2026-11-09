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
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    token_autorizacion = Column(String(80), nullable=True)
    simulado = Column(Boolean, default=True, nullable=False)

    codigo_otp = Column(String(6), nullable=False)
    estado = Column(
        String(30), default="PENDIENTE_OTP"
    )  # PENDIENTE_OTP, AUTORIZADO, RECHAZADO, EXPIRADO
    intentos = Column(Integer, default=0)

    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=5)
    )

    empresa = relationship("Empresa")


class SesionPagoSimulada(Base):
    __tablename__ = "sesiones_pago_simuladas"
    id = Column(String(50), primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    monto = Column(Float, nullable=False)
    moneda = Column(String(10), default="BOB", nullable=False)
    metodo = Column(String(30), nullable=False)
    estado = Column(String(30), default="PENDING", nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    simulada = Column(Boolean, default=True, nullable=False)


class MovimientoPago(Base):
    """Registro contable académico; no representa una operación bancaria real."""

    __tablename__ = "movimientos_pagos"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    responsable_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    nota_id = Column(Integer, ForeignKey("notas_devoluciones.id"), nullable=True)
    clave_operacion = Column(String(80), unique=True, nullable=False)
    tipo = Column(String(30), nullable=False)
    metodo = Column(String(50), nullable=False)
    monto_bruto = Column(Float, nullable=False)
    descuento_cupon = Column(Float, default=0, nullable=False)
    monto = Column(Float, nullable=False)
    moneda = Column(String(10), default="BOB", nullable=False)
    referencia = Column(String(100), nullable=True)
    estado = Column(String(30), default="CONFIRMADO_SIMULADO", nullable=False)
    simulado = Column(Boolean, default=True, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
