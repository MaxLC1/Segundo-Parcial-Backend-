"""Natural-language report planning and bounded, tenant-scoped query execution.

The optional model receives only the question and schema, never SQL credentials
or a database connection. Its output is validated before selecting a fixed query.
"""

import calendar
import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Literal
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import func, desc
from app.pkg_ventas.models import Venta, DetalleVenta
from app.pkg_catalogo.models import Producto, Categoria
from app.pkg_sucursales.models import Sucursal, Inventario
from app.pkg_saas.services import validar_permiso_ia
from .schemas import ConsultaReporteIAResponse


class ReportPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo: Literal[
        "ventas_sucursal",
        "top_productos",
        "top_productos_sucursal",
        "stock_critico",
        "ingresos_categoria",
        "ventas_tiempo",
    ]
    desde: date | None = None
    hasta: date | None = None
    sucursal_id: int | None = None
    categoria_id: int | None = None
    producto_id: int | None = None
    limite: int = Field(default=10, ge=1, le=100)
    agrupacion: Literal["dia", "semana", "mes"] = "dia"

    @model_validator(mode="after")
    def check_dates(self):
        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("El inicio debe preceder al final")
        return self


def normalize(value):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(c) != "Mn"
    )


def today_bolivia():
    return datetime.now(timezone(timedelta(hours=-4))).date()


def local_plan(question):
    q = normalize(question)
    plan = {}
    if any(w in q for w in ["stock", "existencia", "inventario"]):
        plan["tipo"] = "stock_critico"
    elif any(w in q for w in ["mas vendido", "top ", "populares"]):
        plan["tipo"] = "top_productos_sucursal" if "sucursal" in q else "top_productos"
    elif "categoria" in q:
        plan["tipo"] = "ingresos_categoria"
    elif "sucursal" in q or "compar" in q:
        plan["tipo"] = "ventas_sucursal"
    elif any(w in q for w in ["venta", "ingreso", "tendencia"]):
        plan["tipo"] = "ventas_tiempo"
    else:
        raise HTTPException(
            422,
            "Especifique ventas por sucursal, productos más vendidos, existencias, ingresos por categoría o ventas por período",
        )
    today = today_bolivia()
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", q)
    if dates:
        plan["desde"] = dates[0]
        plan["hasta"] = dates[-1]
    elif "este mes" in q:
        plan.update(desde=today.replace(day=1), hasta=today)
    elif "hoy" in q:
        plan.update(desde=today, hasta=today)
    else:
        months = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        found = [i + 1 for i, m in enumerate(months) if m in q]
        if len(found) > 1:
            raise HTTPException(422, "Indique el rango como AAAA-MM-DD a AAAA-MM-DD")
        if found:
            year = re.search(r"\b(20\d{2})\b", q)
            year = int(year[1]) if year else today.year
            month = found[0]
            plan.update(
                desde=date(year, month, 1),
                hasta=date(year, month, calendar.monthrange(year, month)[1]),
            )
        elif "ultimos" in q:
            q_num = (
                q.replace("un mes", "1 meses")
                .replace("dos meses", "2 meses")
                .replace("tres meses", "3 meses")
                .replace("cuatro meses", "4 meses")
                .replace("cinco meses", "5 meses")
                .replace("seis meses", "6 meses")
            )
            period = re.search(r"ultimos\s+(\d+)\s+(dias|meses)", q_num)
            if not period:
                raise HTTPException(
                    422, "Indique cuántos días o meses, por ejemplo: últimos 3 meses"
                )
            n = int(period[1])
            if not 1 <= n <= 366:
                raise HTTPException(422, "Rango fuera de límites")
            if period[2] == "dias":
                plan.update(desde=today - timedelta(days=n - 1), hasta=today)
            else:
                month_index = today.year * 12 + today.month - 1 - n
                year, month = month_index // 12, month_index % 12 + 1
                plan.update(
                    desde=date(
                        year, month, min(today.day, calendar.monthrange(year, month)[1])
                    ),
                    hasta=today,
                )
    for label, key in [
        ("sucursal", "sucursal_id"),
        ("categoria", "categoria_id"),
        ("producto", "producto_id"),
    ]:
        match = re.search(rf"\b{label}\s+#?(\d+)\b", q)
        if match:
            plan[key] = int(match[1])
    limit = re.search(r"\b(?:top|primeros|los)\s+(\d+)\b", q)
    if limit:
        plan["limite"] = int(limit[1])
    if "seman" in q:
        plan["agrupacion"] = "semana"
    elif "por mes" in q or "mensual" in q:
        plan["agrupacion"] = "mes"
    return ReportPlan.model_validate(plan)


def plan_report(question):
    url = os.environ.get("REPORT_AI_URL")
    if not url:
        return local_plan(question), "reglas_locales"
    model = os.environ.get("REPORT_AI_MODEL")
    if not model:
        raise HTTPException(503, "Configure REPORT_AI_MODEL")
    headers = (
        {"Authorization": "Bearer " + os.environ["REPORT_AI_KEY"]}
        if os.environ.get("REPORT_AI_KEY")
        else {}
    )
    try:
        response = httpx.post(
            url,
            headers=headers,
            timeout=30,
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": 'Interpreta la solicitud de reporte. Devuelve únicamente JSON conforme al esquema. No generes SQL. Si no corresponde, devuelve {"error":"Solicitud no soportada"}. Hoy es '
                        + today_bolivia().isoformat()
                        + ". Para productos más vendidos agrupados por sucursal usa top_productos_sucursal: el límite se aplica POR CADA sucursal, ordenando por unidades. Últimos N meses significa desde el mismo día N meses atrás hasta hoy, inclusive, ajustando al último día si no existe. No confundas agrupación por sucursal con filtrar una sucursal. "
                        + ". Esquema: "
                        + json.dumps(ReportPlan.model_json_schema()),
                    },
                    {"role": "user", "content": question},
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
        payload = json.loads(content)
        if "error" in payload:
            raise HTTPException(
                422,
                "La solicitud es ambigua o no está soportada. Indique tipo de reporte, período y filtros.",
            )
        plan = ReportPlan.model_validate(payload)
        q = normalize(question)
        if (
            plan.tipo == "top_productos"
            and "sucursal" in q
            and any(w in q for w in ["agrupad", "por sucursal", "cada sucursal"])
        ):
            plan.tipo = "top_productos_sucursal"
        # One deterministic relative-date definition for model and local mode.
        if re.search(
            r"ultimos\s+(?:\d+|dos|tres|cuatro|cinco|seis)\s+meses", q
        ) and not re.search(r"\d{4}-\d{2}-\d{2}", q):
            dates = local_plan(question)
            plan.desde, plan.hasta = dates.desde, dates.hasta
        return plan, "modelo_ia"
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        raise HTTPException(
            502,
            "El servicio de IA no devolvió un plan válido; no se ejecutó ninguna consulta",
        )


def generate(db, request):
    validar_permiso_ia(db, request.empresa_id)
    if not request.query.strip() or len(request.query) > 2000:
        raise HTTPException(422, "Escriba una solicitud de hasta 2000 caracteres")
    try:
        plan, source = plan_report(request.query)
    except ValueError:
        raise HTTPException(422, "Revise las fechas y los filtros de su solicitud")
    for value, cls in [
        (plan.sucursal_id, Sucursal),
        (plan.categoria_id, Categoria),
        (plan.producto_id, Producto),
    ]:
        if (
            value
            and not db.query(cls)
            .filter_by(id=value, empresa_id=request.empresa_id)
            .first()
        ):
            raise HTTPException(404, "Un filtro no pertenece a su empresa")

    def sales(query):
        query = query.filter(
            Venta.empresa_id == request.empresa_id,
            Venta.estado_sincronizacion == "CONFIRMADA",
        )
        if plan.desde:
            query = query.filter(
                Venta.fecha >= datetime.combine(plan.desde, datetime.min.time())
            )
        if plan.hasta:
            query = query.filter(
                Venta.fecha
                < datetime.combine(plan.hasta + timedelta(days=1), datetime.min.time())
            )
        if plan.sucursal_id:
            query = query.filter(Venta.sucursal_id == plan.sucursal_id)
        if plan.categoria_id:
            query = query.filter(Producto.categoria_id == plan.categoria_id)
        if plan.producto_id:
            query = query.filter(Producto.id == plan.producto_id)
        return query

    if plan.tipo == "stock_critico":
        query = (
            db.query(
                Producto.nombre,
                Sucursal.nombre,
                Inventario.talla_id,
                Inventario.color_id,
                Inventario.cantidad,
            )
            .select_from(Inventario)
            .join(Producto, Producto.id == Inventario.producto_id)
            .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
            .filter(Sucursal.empresa_id == request.empresa_id)
        )
        if plan.sucursal_id:
            query = query.filter(Sucursal.id == plan.sucursal_id)
        if plan.producto_id:
            query = query.filter(Producto.id == plan.producto_id)
        if plan.categoria_id:
            query = query.filter(Producto.categoria_id == plan.categoria_id)
        if plan.desde or plan.hasta:
            raise HTTPException(
                422,
                "Las existencias son actuales; no existe un histórico de stock para ese período",
            )
        rows = query.order_by(Inventario.cantidad).limit(plan.limite).all()
        columns = ["Producto", "Sucursal", "Talla", "Color", "Existencias"]
        values = [list(r) for r in rows]
        title = "Existencias actuales"
        labels = [f"{r[0]} · {r[1]}" for r in rows]
        amounts = [r[-1] for r in rows]
    else:
        # Allocate discounts proportionally so category/product totals reconcile
        # with the actual amount paid in the sale (including coupon discounts).
        subtotal = (
            db.query(
                DetalleVenta.venta_id.label("sale_id"),
                func.sum(DetalleVenta.subtotal).label("gross"),
            )
            .group_by(DetalleVenta.venta_id)
            .subquery()
        )
        amount = DetalleVenta.subtotal * Venta.total / func.nullif(subtotal.c.gross, 0)
        query = (
            db.query(DetalleVenta)
            .join(Venta, Venta.id == DetalleVenta.venta_id)
            .join(Producto, Producto.id == DetalleVenta.producto_id)
            .join(subtotal, subtotal.c.sale_id == Venta.id)
        )
        query = sales(query)
        if plan.tipo == "ventas_sucursal":
            rows = (
                query.join(Sucursal, Sucursal.id == Venta.sucursal_id)
                .with_entities(Sucursal.nombre, func.sum(amount).label("importe"))
                .group_by(Sucursal.id, Sucursal.nombre)
                .order_by(desc("importe"))
                .limit(plan.limite)
                .all()
            )
            columns = ["Sucursal", "Ingresos (BOB)"]
            title = "Ventas por sucursal"
            values = [[r[0], round(float(r[1] or 0), 2)] for r in rows]
        elif plan.tipo == "top_productos_sucursal":
            grouped = (
                query.join(Sucursal, Sucursal.id == Venta.sucursal_id)
                .with_entities(
                    Sucursal.id.label("sucursal_id"),
                    Sucursal.nombre.label("sucursal"),
                    Producto.id.label("producto_id"),
                    Producto.nombre.label("producto"),
                    func.sum(DetalleVenta.cantidad).label("unidades"),
                    func.sum(amount).label("importe"),
                )
                .group_by(Sucursal.id, Sucursal.nombre, Producto.id, Producto.nombre)
                .subquery()
            )
            ranked = db.query(
                grouped,
                func.row_number()
                .over(
                    partition_by=grouped.c.sucursal_id,
                    order_by=(grouped.c.unidades.desc(), grouped.c.producto_id.asc()),
                )
                .label("posicion"),
            ).subquery()
            rows = (
                db.query(ranked)
                .filter(ranked.c.posicion <= plan.limite)
                .order_by(ranked.c.sucursal_id, ranked.c.posicion)
                .all()
            )
            columns = ["Sucursal", "Posición", "Producto", "Unidades", "Ingresos (BOB)"]
            title = f"Top {plan.limite} productos por sucursal"
            values = [
                [
                    r.sucursal,
                    r.posicion,
                    r.producto,
                    int(r.unidades),
                    round(float(r.importe or 0), 2),
                ]
                for r in rows
            ]
        elif plan.tipo == "top_productos":
            rows = (
                query.with_entities(
                    Producto.nombre,
                    func.sum(DetalleVenta.cantidad).label("unidades"),
                    func.sum(amount),
                )
                .group_by(Producto.id, Producto.nombre)
                .order_by(desc("unidades"))
                .limit(plan.limite)
                .all()
            )
            columns = ["Producto", "Unidades", "Ingresos (BOB)"]
            title = "Productos más vendidos"
            values = [[r[0], int(r[1]), round(float(r[2] or 0), 2)] for r in rows]
        elif plan.tipo == "ingresos_categoria":
            rows = (
                query.join(Categoria, Categoria.id == Producto.categoria_id)
                .with_entities(Categoria.nombre, func.sum(amount).label("importe"))
                .group_by(Categoria.id, Categoria.nombre)
                .order_by(desc("importe"))
                .limit(plan.limite)
                .all()
            )
            columns = ["Categoría", "Ingresos (BOB)"]
            title = "Ingresos por categoría"
            values = [[r[0], round(float(r[1] or 0), 2)] for r in rows]
        else:
            rows = (
                query.with_entities(Venta.fecha, amount)
                .order_by(Venta.fecha)
                .limit(10001)
                .all()
            )
            if len(rows) > 10000:
                raise HTTPException(
                    422, "Acote el período: el reporte supera 10.000 detalles"
                )
            grouped = {}
            for when, value in rows:
                key = (
                    when.strftime("%Y-%m")
                    if plan.agrupacion == "mes"
                    else (when - timedelta(days=when.weekday())).strftime("%Y-%m-%d")
                    if plan.agrupacion == "semana"
                    else when.strftime("%Y-%m-%d")
                )
                grouped[key] = grouped.get(key, 0) + float(value or 0)
            columns = ["Período", "Ingresos (BOB)"]
            title = "Ventas por " + plan.agrupacion
            values = [[k, round(v, 2)] for k, v in grouped.items()]
        labels = [
            f"{v[0]} · {v[2]}" if plan.tipo == "top_productos_sucursal" else str(v[0])
            for v in values
        ]
        amounts = [
            v[3]
            if plan.tipo == "top_productos_sucursal"
            else v[1]
            if plan.tipo == "top_productos"
            else v[-1]
            for v in values
        ]
    narrative = (
        f"{len(values)} filas obtenidas de las operaciones reales de su empresa."
        if values
        else "No hay datos para los filtros solicitados."
    )
    if plan.tipo == "top_productos_sucursal":
        narrative += f" Hasta {plan.limite} productos por cada sucursal, ordenados por unidades vendidas. Las sucursales con menos productos vendidos muestran solo los disponibles."
    if plan.desde or plan.hasta:
        narrative += f" Período: {plan.desde or 'sin inicio'} al {plan.hasta or 'hoy'} (inclusive)."
    response = ConsultaReporteIAResponse(
        titulo=title,
        tipo_reporte=plan.tipo,
        narrativa_ia=narrative,
        filtros_detectados={
            **plan.model_dump(mode="json"),
            "empresa_id": request.empresa_id,
            "interpretacion": source,
            "fuente": "base_de_datos",
        },
        columnas=columns,
        filas=[dict(zip(columns, row)) for row in values],
        grafico_tipo="line" if plan.tipo == "ventas_tiempo" else "bar",
        grafico_data={
            "labels": labels,
            "datasets": [
                {
                    "label": "Unidades"
                    if plan.tipo in {"top_productos", "top_productos_sucursal"}
                    else columns[-1],
                    "data": amounts,
                }
            ],
        },
    )
    from .models import HistorialConsultaIA

    db.add(
        HistorialConsultaIA(
            empresa_id=request.empresa_id,
            usuario_id=db.info.get("actor").id if db.info.get("actor") else 1,
            prompt_usuario=request.query,
            tipo_reporte=plan.tipo,
            respuesta_resumen=narrative,
        )
    )
    db.commit()
    return response
