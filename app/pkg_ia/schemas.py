from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ConsultaReporteIARequest(BaseModel):
    query: str
    empresa_id: int
    usuario_id: Optional[int] = None


class GraficoDataset(BaseModel):
    label: str
    data: List[float]
    backgroundColor: Optional[Any] = None
    borderColor: Optional[Any] = None
    borderWidth: Optional[int] = 1


class GraficoData(BaseModel):
    labels: List[str]
    datasets: List[GraficoDataset]


class ConsultaReporteIAResponse(BaseModel):
    titulo: str
    tipo_reporte: str  # ventas_sucursal, top_productos, ventas_tiempo, stock_critico, ingresos_categoria, generico
    narrativa_ia: str
    filtros_detectados: Dict[str, Any]
    columnas: List[str]
    filas: List[Dict[str, Any]]
    grafico_tipo: str  # "bar", "line", "pie", "doughnut"
    grafico_data: GraficoData
    fecha_generacion: datetime = Field(default_factory=datetime.utcnow)


# Esquemas de Machine Learning
class MLModelStatusOut(BaseModel):
    empresa_id: int
    modelo_supervisado: Dict[str, Any]
    modelo_no_supervisado: Dict[str, Any]
    total_muestras_entrenamiento: int
    fecha_ultimo_entrenamiento: Optional[datetime] = None


class PrediccionVentaRequest(BaseModel):
    empresa_id: int
    dias_a_futuro: int = 7
    sucursal_id: Optional[int] = None


class PrediccionVentaItem(BaseModel):
    fecha: str
    ventas_estimadas_monto: float
    pedidos_estimados: int


class PrediccionVentaResponse(BaseModel):
    empresa_id: int
    modelo_utilizado: str
    r2_score: float
    predicciones: List[PrediccionVentaItem]


class SegmentoClienteItem(BaseModel):
    cluster_id: int
    nombre_segmento: (
        str  # "Clientes VIP", "Compradores Frecuentes", "Clientes Ocasionales"
    )
    cantidad_clientes: int
    porcentaje: float
    ticket_promedio_bob: float
    frecuencia_compras_mes: float


class DashboardAnaliticoMLResponse(BaseModel):
    empresa_id: int
    supervisado: Dict[str, Any]
    segmentacion_clientes: List[SegmentoClienteItem]
    insights_ia: List[str]
