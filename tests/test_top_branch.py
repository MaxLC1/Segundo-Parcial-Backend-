from datetime import date, datetime
from collections import Counter
from app.pkg_ia import reporting
from app.pkg_catalogo.models import Producto
from app.pkg_sucursales.models import Sucursal
from app.pkg_ventas.models import Venta, DetalleVenta

PROMPT = "Mostrar los 10 productos más vendidos durante los últimos 3 meses agrupados por sucursal"


def test_plan_rolling_months(monkeypatch):
    monkeypatch.setattr(reporting, "today_bolivia", lambda: date(2026, 11, 12))
    plan = reporting.local_plan(PROMPT)
    assert plan.tipo == "top_productos_sucursal"
    assert (plan.desde, plan.hasta, plan.limite) == (
        date(2026, 8, 12),
        date(2026, 11, 12),
        10,
    )
    monkeypatch.setattr(reporting, "today_bolivia", lambda: date(2026, 5, 31))
    assert reporting.local_plan(PROMPT).desde == date(2026, 2, 28)


def test_ten_per_branch_dates_and_discounts(setup, monkeypatch):
    client, factory, auth = setup
    monkeypatch.setenv("REPORT_AI_URL", "")
    monkeypatch.setattr(reporting, "today_bolivia", lambda: date(2026, 11, 12))
    with factory() as db:
        db.add(Sucursal(id=3, nombre="Otra sucursal", empresa_id=1, ciudad_id=1))
        products = [
            Producto(id=100 + i, nombre=f"Prenda {i}", precio=100, empresa_id=1)
            for i in range(12)
        ]
        db.add_all(products)
        db.flush()

        def sale(branch, product, qty, when, state="CONFIRMADA", company=1):
            v = Venta(
                empresa_id=company,
                sucursal_id=branch,
                usuario_id=company,
                responsable_id=company,
                fecha=when,
                total=qty * 80,
                estado_sincronizacion=state,
            )
            v.detalles = [
                DetalleVenta(
                    producto_id=product,
                    talla_id=1,
                    color_id=1,
                    cantidad=qty,
                    precio_unitario=100,
                    subtotal=qty * 100,
                )
            ]
            db.add(v)

        for branch in (1, 3):
            for i, p in enumerate(products):
                sale(
                    branch,
                    p.id,
                    (12 - i) if branch == 1 else (i + 1),
                    datetime(2026, 9, 1),
                )
        sale(1, 100, 500, datetime(2026, 8, 11, 23, 59))
        sale(1, 100, 500, datetime(2026, 11, 13))
        sale(1, 100, 500, datetime(2026, 10, 1), "RECHAZADA")
        sale(2, 2, 900, datetime(2026, 10, 1), company=2)
        db.commit()
    res = client.post(
        "/api/v1/ia/reporte-generativo",
        json={"query": PROMPT, "empresa_id": 1},
        headers=auth("plataforma"),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    rows = data["filas"]
    assert len(rows) == 20
    assert Counter(r["Sucursal"] for r in rows) == {
        "Sucursal 1": 10,
        "Otra sucursal": 10,
    }
    assert rows[0]["Producto"] == "Prenda 0" and rows[10]["Producto"] == "Prenda 11"
    assert [r["Posición"] for r in rows] == list(range(1, 11)) * 2
    assert all(r["Ingresos (BOB)"] == r["Unidades"] * 80 for r in rows)
    assert data["grafico_data"]["datasets"][0]["data"] == [r["Unidades"] for r in rows]
    assert data["grafico_data"]["labels"][0] == "Sucursal 1 · Prenda 0"
    for ext in ("pdf", "excel"):
        export = client.post(
            "/api/v1/ia/exportar-" + ext, json=data, headers=auth("plataforma")
        )
        assert export.status_code == 200, export.text
