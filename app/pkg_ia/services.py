from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from datetime import datetime, timedelta
import io
import json
from xml.sax.saxutils import escape
import numpy as np
from fastapi import HTTPException
from typing import Dict, Any, List

from . import models, schemas
from app.pkg_saas.services import validar_permiso_ia
from app.pkg_ventas.models import Venta, DetalleVenta
from app.pkg_sucursales.models import Sucursal, Inventario
from app.pkg_catalogo.models import Producto, Categoria, Talla, Color

# -- Exportación --
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from .export_charts import add_excel_chart, pdf_charts

# -- Machine Learning --
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.metrics import r2_score, mean_squared_error, silhouette_score


def procesar_reporte_generativo(db, request):
    from .reporting import generate

    return generate(db, request)


def exportar_reporte_excel(datos: schemas.ConsultaReporteIAResponse) -> bytes:
    """Construye un libro Excel XLSX con formato corporativo para el reporte generado dinámicamente."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Ejecutivo"

    # Estilos
    fuente_titulo = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    fuente_subtitulo = Font(name="Calibri", size=11, italic=True, color="475569")
    fuente_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fill_header = PatternFill(
        start_color="3B82F6", end_color="3B82F6", fill_type="solid"
    )
    fill_zebra = PatternFill(
        start_color="F8FAFC", end_color="F8FAFC", fill_type="solid"
    )
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    # Encabezado
    ws["A1"] = "FASHIONSTORE SAAS - REPORTE GENERATIVO INTELIGENTE"
    ws["A1"].font = fuente_titulo
    ws["A2"] = datos.titulo
    ws["A2"].font = Font(name="Calibri", size=13, bold=True, color="334155")
    ws["A3"] = f"Generado el: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC"
    ws["A3"].font = fuente_subtitulo

    # Resumen Narrativo
    ws["A5"] = "Análisis e Interpretación Ejecutiva (IA):"
    ws["A5"].font = Font(name="Calibri", size=11, bold=True, color="1E293B")
    ws["A6"] = datos.narrativa_ia
    ws["A6"].font = Font(name="Calibri", size=10, italic=True, color="334155")

    # Tabla de Datos
    start_row = 8
    for col_idx, col_name in enumerate(datos.columnas, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=col_name)
        cell.font = fuente_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_idx, fila in enumerate(datos.filas, start=start_row + 1):
        for col_idx, col_name in enumerate(datos.columnas, 1):
            val = fila.get(col_name, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border
            if row_idx % 2 == 0:
                cell.fill = fill_zebra

    # Autoajuste de ancho de columnas
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

    add_excel_chart(wb, datos)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def exportar_reporte_pdf(datos: schemas.ConsultaReporteIAResponse) -> bytes:
    """Construye un documento PDF formal y estilizado para el reporte dinámico."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=14,
    )
    narrative_style = ParagraphStyle(
        "NarrativeStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=16,
        leading=14,
    )

    story.append(
        Paragraph("FashionStore SaaS - Plataforma Empresarial", subtitle_style)
    )
    story.append(Paragraph(escape(datos.titulo), title_style))
    story.append(
        Paragraph(
            f"Fecha de emisión: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            f"<b>Interpretación Generativa (IA):</b> {escape(datos.narrativa_ia)}",
            narrative_style,
        )
    )
    story.append(Spacer(1, 12))

    story.extend(pdf_charts(datos, styles))

    # Construir tabla
    cell_style = ParagraphStyle(
        "TableCell", parent=styles["Normal"], fontSize=8, leading=10
    )
    header_style = ParagraphStyle(
        "TableHeader", parent=cell_style, textColor=colors.white
    )
    tabla_data = [[Paragraph(escape(col), header_style) for col in datos.columnas]]
    for fila in datos.filas:
        fila_data = [
            Paragraph(escape(str(fila.get(col, ""))), cell_style)
            for col in datos.columnas
        ]
        tabla_data.append(fila_data)

    widths = (
        [125, 45, 170, 65, 135]
        if datos.tipo_reporte == "top_productos_sucursal"
        else [540 / max(len(datos.columnas), 1)] * len(datos.columnas)
    )
    t = Table(tabla_data, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
            ]
        )
    )
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ==============================================================================
# MÓDULO DE MACHINE LEARNING (Secciones 8.4 y 8.5)
# Supervisado (Regresión Ventas) + No Supervisado (Clustering K-Means Clientes)
# ==============================================================================


def generar_datos_sinteticos_ml(empresa_id: int, n_samples: int = 150):
    """Genera datos sintéticos consistentes con la dinámica comercial del tenant para entrenamiento."""
    rng = np.random.default_rng(42 + empresa_id)
    # Variables: dia_semana (0-6), dia_mes (1-30), stock_promedio, promocion_activa (0 o 1)
    dias_semana = rng.integers(0, 7, n_samples)
    dias_mes = rng.integers(1, 31, n_samples)
    stock_promedio = rng.uniform(5, 50, n_samples)
    promocion_activa = rng.binomial(1, 0.3, n_samples)

    # Variable objetivo: Ventas del día (BOB)
    # Viernes/Sábado (dias 4 y 5) tienen picos, promociones incrementan 40%
    base_ventas = (
        800
        + (dias_semana * 150)
        + (promocion_activa * 900)
        + (stock_promedio * 20)
        + rng.normal(0, 120, n_samples)
    )
    base_ventas = np.maximum(base_ventas, 200)

    X = np.column_stack([dias_semana, dias_mes, stock_promedio, promocion_activa])
    y = base_ventas
    return X, y


def entrenar_modelo_supervisado(empresa_id: int) -> Dict[str, Any]:
    """Entrena un modelo de regresión lineal para predicción de demanda/ventas."""
    X, y = generar_datos_sinteticos_ml(empresa_id, n_samples=180)

    # Split train/test
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = float(r2_score(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))

    return {
        "algoritmo": "Regresión Lineal Multivariable",
        "r2_score": round(r2, 4),
        "mse": round(mse, 2),
        "coeficientes": [round(float(c), 2) for c in model.coef_],
        "intercept": round(float(model.intercept_), 2),
        "muestras": len(X),
    }


def entrenar_modelo_no_supervisado_clustering(
    empresa_id: int, return_metrics=False
) -> List[schemas.SegmentoClienteItem]:
    """Entrena modelo no supervisado (K-Means) para segmentar clientes en 3 perfiles."""
    rng = np.random.default_rng(10 + empresa_id)
    n_clientes = 120
    # Features: Frecuencia mensual de compras, Ticket promedio en BOB
    # Generar 3 poblaciones naturales sintéticas
    c1 = rng.normal(loc=[1.5, 90.0], scale=[0.5, 20.0], size=(60, 2))  # Ocasionales
    c2 = rng.normal(loc=[4.0, 260.0], scale=[0.8, 40.0], size=(45, 2))  # Recurrentes
    c3 = rng.normal(loc=[8.5, 680.0], scale=[1.2, 90.0], size=(15, 2))  # VIP
    X_clientes = np.vstack([c1, c2, c3])
    X_clientes = np.maximum(X_clientes, 1.0)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
    from sklearn.preprocessing import StandardScaler

    scaled = StandardScaler().fit_transform(X_clientes)
    labels = kmeans.fit_predict(scaled)
    silhouette = float(silhouette_score(scaled, labels))

    # Identificar nombres de segmentos según ticket promedio
    centros = kmeans.cluster_centers_
    orden_indices = np.argsort(centros[:, 1])  # ordenados por ticket ascendente

    nombres = [
        "Clientes Ocasionales",
        "Compradores Frecuentes",
        "Clientes VIP / Alta Fidelidad",
    ]
    segmentos = []

    for pos, idx_cluster in enumerate(orden_indices):
        cluster_mask = labels == idx_cluster
        cant = int(np.sum(cluster_mask))
        porc = round((cant / n_clientes) * 100, 1)
        frec_media = round(float(np.mean(X_clientes[cluster_mask, 0])), 1)
        ticket_medio = round(float(np.mean(X_clientes[cluster_mask, 1])), 2)

        segmentos.append(
            schemas.SegmentoClienteItem(
                cluster_id=int(idx_cluster),
                nombre_segmento=nombres[pos],
                cantidad_clientes=cant,
                porcentaje=porc,
                ticket_promedio_bob=ticket_medio,
                frecuencia_compras_mes=frec_media,
            )
        )

    return (segmentos, silhouette) if return_metrics else segmentos


def predecir_demanda_futura(
    empresa_id: int, dias_a_futuro: int = 7
) -> schemas.PrediccionVentaResponse:
    """Ejecuta predicción de ventas para los próximos N días utilizando el modelo supervisado."""
    sup_info = entrenar_modelo_supervisado(empresa_id)

    hoy = datetime.utcnow()
    predicciones = []

    for d in range(1, dias_a_futuro + 1):
        fecha_target = hoy + timedelta(days=d)
        dia_sem = fecha_target.weekday()
        dia_mes = fecha_target.day
        # Estimar variables
        promocion = 1 if dia_sem in [4, 5] else 0
        stock_estimado = 35.0

        monto_estimado = (
            sup_info["intercept"]
            + (dia_sem * sup_info["coeficientes"][0])
            + (dia_mes * sup_info["coeficientes"][1])
            + (stock_estimado * sup_info["coeficientes"][2])
            + (promocion * sup_info["coeficientes"][3])
        )
        monto_estimado = round(max(monto_estimado, 0.0), 2)
        pedidos = int(round(monto_estimado / 180.0))

        predicciones.append(
            schemas.PrediccionVentaItem(
                fecha=fecha_target.strftime("%Y-%m-%d (%a)"),
                ventas_estimadas_monto=monto_estimado,
                pedidos_estimados=max(pedidos, 0),
            )
        )

    return schemas.PrediccionVentaResponse(
        empresa_id=empresa_id,
        modelo_utilizado="Regresión Lineal Supervisada con Ajuste Multivariable",
        r2_score=sup_info["r2_score"],
        predicciones=predicciones,
    )


def obtener_dashboard_analitico(
    db: Session, empresa_id: int
) -> schemas.DashboardAnaliticoMLResponse:
    """Consolida las métricas del modelo supervisado y la segmentación no supervisada en un dashboard ejecutivo."""
    validar_permiso_ia(db, empresa_id)

    supervisado = entrenar_modelo_supervisado(empresa_id)
    clustering, silhouette = entrenar_modelo_no_supervisado_clustering(
        empresa_id, return_metrics=True
    )

    insights = [
        "Modelos entrenados y evaluados con datos sintéticos para la demostración académica; no representan clientes reales.",
        f"R² medido en el conjunto de prueba: {supervisado['r2_score']}. No garantiza resultados futuros.",
        f"Silhouette de K-Means con variables estandarizadas: {silhouette:.4f}.",
        "Los segmentos describen las poblaciones sintéticas generadas.",
    ]

    return schemas.DashboardAnaliticoMLResponse(
        empresa_id=empresa_id,
        supervisado=supervisado,
        segmentacion_clientes=clustering,
        insights_ia=insights,
    )
