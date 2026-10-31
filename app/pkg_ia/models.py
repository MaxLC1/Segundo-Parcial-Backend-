from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class HistorialConsultaIA(Base):
    __tablename__ = "ia_consultas_historial"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    prompt_usuario = Column(Text, nullable=False)
    tipo_reporte = Column(String(50), nullable=True)
    respuesta_resumen = Column(Text, nullable=True)
    fecha_consulta = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")
    usuario = relationship("Usuario")

class MetricasModeloML(Base):
    __tablename__ = "ia_metricas_ml"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo_modelo = Column(String(50), nullable=False)
    nombre_modelo = Column(String(100), nullable=False)
    algoritmo = Column(String(100), nullable=False)
    metricas_json = Column(Text, nullable=False)
    fecha_entrenamiento = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("Empresa")
