from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Devolucion(Base):
    __tablename__ = "devoluciones"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) # Tenant
    motivo = Column(String(255), nullable=False)
    tipo_solicitud = Column(String(50), default="Devolución", nullable=False)
    requiere_delivery = Column(Integer, default=0, nullable=False)
    estado = Column(String(50), default="Pendiente")
    fecha_solicitud = Column(DateTime, default=datetime.utcnow)

    venta = relationship("Venta")
    empresa = relationship("Empresa")

class PoliticaDevolucion(Base):
    __tablename__ = "politicas_devoluciones"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    nombre = Column(String(100), default="Política Oficial de Devoluciones y Cambios")
    tipo_reembolso_menor_valor = Column(String(50), default="CUPON_CREDITO") # CUPON_CREDITO, REEMBOLSO_50_PCT, REEMBOLSO_100_PCT, SIN_REEMBOLSO
    plazo_maximo_dias = Column(Integer, default=30)
    permite_cambio_mayor_valor = Column(Boolean, default=True)
    activa = Column(Boolean, default=True)

    empresa = relationship("Empresa")

class NotaDevolucion(Base):
    __tablename__ = "notas_devoluciones"

    id = Column(Integer, primary_key=True, index=True)
    codigo_nota = Column(String(30), unique=True, index=True, nullable=False) # Ej: NDEV-2026-0041
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True) # Cliente
    repartidor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True) # Delivery
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=True)

    motivo = Column(String(255), nullable=False)
    tipo_solicitud = Column(String(50), default="Cambio por Mayor Valor") # Cambio por Mayor Valor, Cambio por Menor Valor, Devolución Directa
    estado = Column(String(30), default="EN_MARCHA") # EN_MARCHA, COMPLETADA, CANCELADA
    
    # Regla: el cliente la ve mientras esté EN_MARCHA para mostrar al delivery; al completarse se elimina de su vista
    # pero el admin SIEMPRE la conserva recopilada en el histórico
    visible_para_cliente = Column(Boolean, default=True)
    
    prenda_devuelta_info = Column(String(255), nullable=False)
    prenda_nueva_info = Column(String(255), nullable=True)
    
    precio_prenda_original = Column(Float, default=0.0)
    precio_prenda_nueva = Column(Float, default=0.0)
    diferencia_precio = Column(Float, default=0.0) # >0 paga cliente, <0 tienda reembolsa/cupón
    
    mensaje_notificacion = Column(String(255), nullable=True)
    cupon_generado = Column(String(50), nullable=True)
    
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_completada = Column(DateTime, nullable=True)

    venta = relationship("Venta")
    empresa = relationship("Empresa")
    cliente = relationship("Usuario", foreign_keys=[usuario_id])
    repartidor = relationship("Usuario", foreign_keys=[repartidor_id])
    sucursal = relationship("Sucursal")

