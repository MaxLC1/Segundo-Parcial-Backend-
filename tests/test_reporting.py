from datetime import datetime, timedelta
import pytest
from app.pkg_ventas.models import Venta
from app.pkg_catalogo.models import Categoria, Producto
from app.pkg_saas.models import Suscripcion
from app.pkg_ia.reporting import ReportPlan
from tests.test_business import sale


@pytest.mark.parametrize(
    "prompt,kind",
    [
        ("Ventas por sucursal", "ventas_sucursal"),
        ("Top 5 productos más vendidos", "top_productos"),
        ("Productos con menor existencia", "stock_critico"),
        ("Ingresos por categoría", "ingresos_categoria"),
        ("Ventas por semana", "ventas_tiempo"),
    ],
)
def test_five_real_report_types(setup, prompt, kind):
    client, factory, auth = setup
    with factory() as db:
        db.add(Categoria(id=1, nombre="Ropa", empresa_id=1))
        db.query(Producto).filter_by(id=1).one().categoria_id = 1
        db.commit()
    assert (
        client.post("/api/v1/ventas/", json=sale(), headers=auth()).status_code == 201
    )
    response = client.post(
        "/api/v1/ia/reporte-generativo",
        json={"query": prompt, "empresa_id": 1},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["tipo_reporte"] == kind
    assert len(response.json()["filas"]) == 1


def test_dates_empty_results_and_ambiguity(setup):
    client, factory, auth = setup
    client.post("/api/v1/ventas/", json=sale(), headers=auth())
    response = client.post(
        "/api/v1/ia/reporte-generativo",
        json={"query": "Ventas del 2020-01-01 a 2020-01-31", "empresa_id": 1},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["filas"] == []
    assert response.json()["grafico_data"]["datasets"][0]["data"] == []
    assert (
        client.post(
            "/api/v1/ia/reporte-generativo",
            json={"query": "hola", "empresa_id": 1},
            headers=auth(),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/ia/reporte-generativo",
            json={"query": "Ventas sucursal 2", "empresa_id": 1},
            headers=auth(),
        ).status_code
        == 404
    )


def test_subscription_expiry_and_cross_tenant_reports(setup):
    client, factory, auth = setup
    assert (
        client.post(
            "/api/v1/ia/reporte-generativo",
            json={"query": "Ventas por sucursal", "empresa_id": 2},
            headers=auth(),
        ).status_code
        == 403
    )
    with factory() as db:
        db.query(Suscripcion).filter_by(empresa_id=1).one().fecha_vencimiento = (
            datetime.utcnow() - timedelta(days=1)
        )
        db.commit()
    assert (
        client.post(
            "/api/v1/ia/reporte-generativo",
            json={"query": "Ventas por sucursal", "empresa_id": 1},
            headers=auth(),
        ).status_code
        == 403
    )


def test_model_cannot_return_arbitrary_queries():
    with pytest.raises(ValueError):
        ReportPlan.model_validate(
            {"tipo": "ventas_sucursal", "sql": "DELETE FROM ventas"}
        )


def test_model_transport_validates_response(monkeypatch):
    from app.pkg_ia.reporting import plan_report

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {"message": {"content": '{"tipo":"top_productos","limite":3}'}}
                ]
            }

    monkeypatch.setenv("REPORT_AI_URL", "http://localhost:1234/v1/chat/completions")
    monkeypatch.setenv("REPORT_AI_MODEL", "test-model")
    monkeypatch.setattr(
        "app.pkg_ia.reporting.httpx.post", lambda *args, **kwargs: Response()
    )
    plan, source = plan_report("Tres productos más vendidos")
    assert plan.limite == 3 and source == "modelo_ia"
