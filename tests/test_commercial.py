from datetime import datetime, timedelta
from app.pkg_sucursales.models import Sucursal, Inventario
from app.pkg_comercial.models import Cupon, CanjeCupon, Traspaso
from app.pkg_devoluciones.models import NotaDevolucion, PoliticaDevolucion
from tests.test_business import sale


def purchase(client, auth):
    response = client.post("/api/v1/ventas/", json=sale(), headers=auth())
    assert response.status_code == 201, response.text
    return response.json()


def request_return(client, auth, purchase, **overrides):
    payload = dict(
        venta_id=purchase["id"],
        detalle_venta_id=purchase["detalles"][0]["id"],
        cantidad=1,
        motivo="No corresponde la talla",
        tipo_solicitud="Devolución Directa",
    )
    payload.update(overrides)
    return client.post(
        "/api/v1/cliente/solicitudes", json=payload, headers=auth("cliente")
    )


def test_return_completion_is_atomic_and_idempotent(setup):
    client, factory, auth = setup
    bought = purchase(client, auth)
    note = request_return(client, auth, bought)
    assert note.status_code == 201, note.text
    assert note.json()["tipo_solicitud"] == "Devolución Directa"
    assert note.json()["cupon_generado"] is None
    note_id = note.json()["id"]
    assert (
        client.put(
            f"/api/v1/devoluciones/notas/{note_id}/completar",
            json={},
            headers=auth("cliente"),
        ).status_code
        == 403
    )
    for _ in range(2):
        response = client.put(
            f"/api/v1/devoluciones/notas/{note_id}/completar", json={}, headers=auth()
        )
        assert response.status_code == 200, response.text
    with factory() as db:
        assert db.query(Inventario).filter_by(id=1).one().cantidad == 9
        assert db.query(Cupon).count() == 1
    assert client.get("/api/v1/cliente/notas", headers=auth("cliente")).json() == []


def test_policy_percentage_and_return_quantity(setup):
    client, _, auth = setup
    policy = dict(
        tipo_reembolso_menor_valor="REEMBOLSO_PORCENTAJE", porcentaje_reembolso=75
    )
    assert (
        client.put(
            "/api/v1/devoluciones/politica/1", json=policy, headers=auth()
        ).status_code
        == 200
    )
    bought = purchase(client, auth)
    response = request_return(client, auth, bought, cantidad=2)
    assert response.status_code == 201, response.text
    assert response.json()["monto_reembolso"] == 150
    assert request_return(client, auth, bought).status_code == 409


def test_expired_note_disappears_but_is_retained(setup):
    client, factory, auth = setup
    note = request_return(client, auth, purchase(client, auth)).json()
    with factory() as db:
        db.query(NotaDevolucion).filter_by(id=note["id"]).one().fecha_expiracion = (
            datetime.utcnow() - timedelta(days=1)
        )
        db.commit()
    assert client.get("/api/v1/cliente/notas", headers=auth("cliente")).json() == []
    assert len(client.get("/api/v1/devoluciones/notas", headers=auth()).json()) == 1


def test_coupon_filters_and_retry(setup):
    client, factory, auth = setup
    coupon = dict(
        nombre="Regalo",
        tipo="PORCENTAJE",
        valor=25,
        usuario_id=3,
        criterios={"productos": [1], "tallas": [1]},
        fecha_vencimiento=(datetime.utcnow() + timedelta(days=5)).isoformat(),
        max_usos=1,
    )
    response = client.post("/api/v1/comercial/cupones", json=coupon, headers=auth())
    assert response.status_code == 201, response.text
    code = response.json()["codigo"]
    payload = sale(cupon_codigo=code)
    for _ in range(2):
        response = client.post("/api/v1/ventas/", json=payload, headers=auth())
        assert response.status_code == 201, response.text
        assert response.json()["total"] == 150
    with factory() as db:
        assert db.query(CanjeCupon).count() == 1
    payload["operacion_uuid"] = "22222222-2222-4222-8222-222222222222"
    assert (
        client.post("/api/v1/ventas/", json=payload, headers=auth()).status_code == 409
    )
    with factory() as db:
        assert db.query(Inventario).filter_by(id=1).one().cantidad == 8


def test_transfer_same_company_and_rollback(setup):
    client, factory, auth = setup
    with factory() as db:
        db.add(Sucursal(id=3, nombre="Segunda sucursal", ciudad_id=1, empresa_id=1))
        db.commit()
    payload = dict(
        operacion_uuid="33333333-3333-4333-8333-333333333333",
        origen_id=1,
        destino_id=2,
        detalles=[dict(producto_id=1, talla_id=1, color_id=1, cantidad=3)],
    )
    assert (
        client.post(
            "/api/v1/comercial/traspasos", json=payload, headers=auth()
        ).status_code
        == 403
    )
    payload["destino_id"] = 3
    for _ in range(2):
        response = client.post(
            "/api/v1/comercial/traspasos", json=payload, headers=auth()
        )
        assert response.status_code == 201, response.text
    with factory() as db:
        assert db.query(Traspaso).count() == 1
        assert db.query(Inventario).filter_by(sucursal_id=1).one().cantidad == 7
        assert db.query(Inventario).filter_by(sucursal_id=3).one().cantidad == 3
    payload["operacion_uuid"] = "44444444-4444-4444-8444-444444444444"
    payload["detalles"] *= 3
    assert (
        client.post(
            "/api/v1/comercial/traspasos", json=payload, headers=auth()
        ).status_code
        == 409
    )
    with factory() as db:
        assert db.query(Inventario).filter_by(sucursal_id=1).one().cantidad == 7


def test_platform_company_creation_is_separate(setup):
    client, _, auth = setup
    data = dict(
        nombre="Nueva",
        codigo="NUEVA",
        plan_id=1,
        admin_nombre="Administrador",
        admin_email="new@example.com",
        admin_password="Testing123!",
    )
    assert (
        client.post("/api/v1/saas/empresas", json=data, headers=auth()).status_code
        == 403
    )
    response = client.post(
        "/api/v1/saas/empresas", json=data, headers=auth("plataforma")
    )
    assert response.status_code == 201, response.text
    assert (
        client.post(
            "/api/v1/seguridad/login",
            json={"email": "new@example.com", "password": "Testing123!"},
        ).status_code
        == 200
    )
