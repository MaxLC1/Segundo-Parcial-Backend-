from fastapi import APIRouter, Depends, Response, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from . import schemas, services

router = APIRouter(tags=["Inteligencia Artificial y Analítica"])

@router.post("/reporte-generativo", response_model=schemas.ConsultaReporteIAResponse)
def generar_reporte_lenguaje_natural(request: schemas.ConsultaReporteIARequest, db: Session = Depends(get_db)):
    """
    Interpreta consultas en lenguaje natural (escrito o voz) y ejecuta consultas dinámicas
    a la base de datos real del tenant (restringido a Plan Profesional).
    """
    return services.procesar_reporte_generativo(db=db, request=request)

@router.post("/exportar-excel")
def exportar_reporte_a_excel(reporte_data: schemas.ConsultaReporteIAResponse):
    """Genera y descarga un archivo Excel (.xlsx) estructurado a partir del reporte dinámico de IA."""
    excel_bytes = services.exportar_reporte_excel(reporte_data)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="reporte_inteligente_fashionstore.xlsx"'}
    )

@router.post("/exportar-pdf")
def exportar_reporte_a_pdf(reporte_data: schemas.ConsultaReporteIAResponse):
    """Genera y descarga un documento PDF formal con el reporte dinámico y tablas analíticas."""
    pdf_bytes = services.exportar_reporte_pdf(reporte_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reporte_inteligente_fashionstore.pdf"'}
    )

# ==============================================================================
# MACHINE LEARNING: APRENDIZAJE SUPERVISADO Y NO SUPERVISADO (Secciones 8.4 y 8.5)
# ==============================================================================

@router.get("/ml/dashboard/{empresa_id}", response_model=schemas.DashboardAnaliticoMLResponse)
def obtener_dashboard_ml(empresa_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el Dashboard Analítico de Machine Learning con resultados de modelos
    supervisados (regresión de ventas) y no supervisados (clustering K-Means de clientes).
    """
    return services.obtener_dashboard_analitico(db=db, empresa_id=empresa_id)

@router.post("/ml/predecir-demanda", response_model=schemas.PrediccionVentaResponse)
def predecir_demanda(request: schemas.PrediccionVentaRequest, db: Session = Depends(get_db)):
    """
    Aplica el modelo supervisado entrenado para predecir la demanda y volumen de ventas
    para los próximos N días.
    """
    services.validar_permiso_ia(db, request.empresa_id)
    return services.predecir_demanda_futura(empresa_id=request.empresa_id, dias_a_futuro=request.dias_a_futuro)
