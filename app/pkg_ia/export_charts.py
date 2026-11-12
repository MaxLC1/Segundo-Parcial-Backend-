"""Charts for the existing runtime exporters (no browser or image uploads)."""

import math
from xml.sax.saxutils import escape

from openpyxl.chart import BarChart, LineChart, PieChart, DoughnutChart, Reference
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer

PALETTE = ["#ea580c", "#4f46e5", "#059669", "#ca8a04", "#db2777"]


def chart_data(report):
    labels = report.grafico_data.labels
    series = report.grafico_data.datasets
    if not labels or not series:
        return None
    if any(
        len(s.data) != len(labels) or any(not math.isfinite(v) for v in s.data)
        for s in series
    ):
        return None
    return labels, series


def add_excel_chart(workbook, report):
    data = chart_data(report)
    if not data:
        return
    labels, series = data
    sheet = workbook.create_sheet("Gráfico")
    sheet["A1"] = report.titulo
    source = workbook.create_sheet("Datos del gráfico")
    source.append(["Categoría"] + [s.label for s in series])
    for i, label in enumerate(labels):
        source.append([label] + [s.data[i] for s in series])
    # Names are text even when a product/branch name begins with '='.
    for row in source:
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    source.column_dimensions["A"].width = 38
    source.freeze_panes = "B2"
    chart = {"line": LineChart, "pie": PieChart, "doughnut": DoughnutChart}.get(
        report.grafico_tipo, BarChart
    )()
    chart.title = report.titulo
    chart.width, chart.height = 26, 15
    last_column = 2 if report.grafico_tipo in ("pie", "doughnut") else len(series) + 1
    chart.add_data(
        Reference(
            source, min_col=2, max_col=last_column, min_row=1, max_row=len(labels) + 1
        ),
        titles_from_data=True,
    )
    chart.set_categories(
        Reference(source, min_col=1, min_row=2, max_row=len(labels) + 1)
    )
    if isinstance(chart, BarChart):
        chart.type = "col"
    sheet.add_chart(chart, "A3")


def pdf_charts(report, styles):
    data = chart_data(report)
    if not data:
        return [Paragraph("Sin datos suficientes para graficar.", styles["Normal"])]
    labels, series = data
    result = [Paragraph("Visualización del reporte", styles["Heading2"])]
    # Split dense charts so category labels stay legible on paper.
    for start in range(0, len(labels), 12):
        names = labels[start : start + 12]
        values = [s.data[start : start + 12] for s in series]
        drawing = Drawing(540, 280)
        circular = report.grafico_tipo in ("pie", "doughnut")
        if circular:
            # A pie must preserve the full total rather than show partial pies.
            if start:
                break
            chart = Pie()
            chart.x, chart.y, chart.width, chart.height = 170, 45, 190, 190
            chart.data = series[0].data
            chart.labels = [str(i + 1) for i in range(len(labels))]
            if report.grafico_tipo == "doughnut":
                chart.innerRadiusFraction = 0.5
            for i in range(len(labels)):
                chart.slices[i].fillColor = colors.HexColor(PALETTE[i % len(PALETTE)])
        else:
            chart = (
                HorizontalLineChart()
                if report.grafico_tipo == "line"
                else VerticalBarChart()
            )
            chart.x, chart.y, chart.width, chart.height = 65, 90, 450, 170
            chart.data = values
            chart.categoryAxis.categoryNames = [
                str(start + i + 1) for i in range(len(names))
            ]
            chart.categoryAxis.labels.fontSize = 8
            chart.valueAxis.labels.fontSize = 8
            chart.valueAxis.valueMin = min(0, min(v for row in values for v in row))
            if all(v == 0 for row in values for v in row):
                chart.valueAxis.valueMin, chart.valueAxis.valueMax = 0, 1
            for i in range(len(series)):
                if report.grafico_tipo == "line":
                    chart.lines[i].strokeColor = colors.HexColor(
                        PALETTE[i % len(PALETTE)]
                    )
                else:
                    chart.bars[i].fillColor = colors.HexColor(PALETTE[i % len(PALETTE)])
        drawing.add(chart)
        result.append(drawing)
        legend_names = labels if circular else names
        for i, name in enumerate(legend_names, 1 if circular else start + 1):
            result.append(Paragraph(f"{i}. {escape(name)}", styles["Normal"]))
        for i, s in enumerate(series[:1] if circular else series):
            result.append(
                Paragraph(
                    f'<font color="{PALETTE[i % len(PALETTE)]}">Serie: {escape(s.label)}</font>',
                    styles["Normal"],
                )
            )
        result.append(Spacer(1, 12))
    return result
