from app.pkg_sucursales.models import Inventario
from app.pkg_ventas.models import Venta


def sale(**overrides):
    return dict(
        sucursal_id=1,
        usuario_id=3,
        metodo_pago="Efectivo",
        operacion_uuid="11111111-1111-4111-8111-111111111111",
        detalles=[
            dict(producto_id=1, talla_id=1, color_id=1, cantidad=2, precio_unitario=100)
        ],
        **overrides,
    )


def test_tenant_and_roles(setup):
    client, factory, auth = setup
    assert client.get("/api/v1/ventas/").status_code == 401
    rows = client.get("/api/v1/sucursales/sucursales", headers=auth()).json()
    assert [x["id"] for x in rows] == [1]
    assert (
        client.get(
            "/api/v1/sucursales/sucursales?empresa_id=2", headers=auth()
        ).status_code
        == 403
    )
    assert client.get("/api/v1/saas/empresas/2", headers=auth()).status_code == 403
    assert (
        client.get("/api/v1/saas/empresas", headers=auth("cliente")).status_code == 403
    )
    assert len(client.get("/api/v1/saas/empresas", headers=auth()).json()) == 1
    assert (
        len(client.get("/api/v1/saas/empresas", headers=auth("plataforma")).json()) == 2
    )


def test_sale_retry_is_idempotent(setup):
    client, factory, auth = setup
    for _ in range(2):
        response = client.post(
            "/api/v1/ventas/sincronizar-offline",
            json={"ventas": [sale()]},
            headers=auth(),
        )
        assert response.status_code == 200, response.text
        assert response.json()["resultados"][0]["estado"] == "CONFIRMADA"
    with factory() as db:
        assert db.query(Venta).count() == 1
        assert db.query(Inventario).filter_by(id=1).one().cantidad == 8


def test_failed_sale_rolls_back_all_inventory(setup):
    client, factory, auth = setup
    payload = sale()
    payload["detalles"].append(
        dict(producto_id=1, talla_id=1, color_id=1, cantidad=100, precio_unitario=100)
    )
    response = client.post("/api/v1/ventas/", json=payload, headers=auth())
    assert response.status_code == 409, response.text
    with factory() as db:
        assert db.query(Venta).count() == 0
        assert db.query(Inventario).filter_by(id=1).one().cantidad == 10


def test_cross_tenant_references_and_customer_identity(setup):
    client, _, auth = setup
    payload = sale()
    payload["usuario_id"] = 2
    assert (
        client.post("/api/v1/ventas/", json=payload, headers=auth()).status_code == 403
    )
    payload = sale()
    payload["usuario_id"] = 1
    assert (
        client.post(
            "/api/v1/ventas/", json=payload, headers=auth("cliente")
        ).status_code
        == 403
    )


def test_batch_typo_and_negative_quantity_rejected(setup):
    client, _, auth = setup
    assert (
        client.post(
            "/api/v1/ventas/sincronizar-offline",
            json={"operaciones": [sale()]},
            headers=auth(),
        ).status_code
        == 422
    )
    payload = sale()
    payload["detalles"][0]["cantidad"] = -1
    assert (
        client.post("/api/v1/ventas/", json=payload, headers=auth()).status_code == 422
    )
