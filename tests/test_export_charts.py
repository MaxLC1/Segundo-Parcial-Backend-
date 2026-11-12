import io

import openpyxl
import pytest
from reportlab.lib.styles import getSampleStyleSheet

from app.pkg_ia.schemas import ConsultaReporteIAResponse
from app.pkg_ia.services import exportar_reporte_excel, exportar_reporte_pdf
from app.pkg_ia.export_charts import pdf_charts


def report(kind="bar", count=2):
    return ConsultaReporteIAResponse(
        titulo="Ventas por sucursal",
        tipo_reporte="ventas_sucursal",
        narrativa_ia="Datos de prueba",
        filtros_detectados={},
        columnas=["Sucursal", "Ingresos"],
        filas=[
            {"Sucursal": f"Sucursal {i}", "Ingresos": 20000 + i * 4000}
            for i in range(count)
        ],
        grafico_tipo=kind,
        grafico_data={
            "labels": [f"Sucursal {i}" for i in range(count)],
            "datasets": [
                {
                    "label": "Ingresos (BOB)",
                    "data": [20000 + i * 4000 for i in range(count)],
                }
            ],
        },
    )


@pytest.mark.parametrize("kind", ["bar", "line", "pie", "doughnut"])
def test_exports_include_editable_chart_and_pdf(kind):
    data = report(kind)
    wb = openpyxl.load_workbook(io.BytesIO(exportar_reporte_excel(data)))
    assert len(wb["Gráfico"]._charts) == 1
    assert list(wb["Datos del gráfico"].values) == [
        ("Categoría", "Ingresos (BOB)"),
        ("Sucursal 0", 20000),
        ("Sucursal 1", 24000),
    ]
    assert exportar_reporte_pdf(data).startswith(b"%PDF-")


def test_bar_starts_at_zero_and_large_report_is_exportable():
    chart = pdf_charts(report(), getSampleStyleSheet())[1].contents[0]
    assert chart.valueAxis.valueMin == 0
    assert chart.data == [[20000, 24000]]
    assert exportar_reporte_pdf(report(count=40)).startswith(b"%PDF-")


def test_empty_report_exports_without_invalid_chart():
    wb = openpyxl.load_workbook(io.BytesIO(exportar_reporte_excel(report(count=0))))
    assert "Gráfico" not in wb.sheetnames
    assert exportar_reporte_pdf(report(count=0)).startswith(b"%PDF-")
