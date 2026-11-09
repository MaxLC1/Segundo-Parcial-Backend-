from datetime import datetime, timedelta
from sqlalchemy import create_engine, inspect, text
from app.pkg_devoluciones.models import NotaDevolucion
from app.pkg_seguridad.models import Usuario
from app.pkg_sucursales.models import Inventario
from tests.test_business import sale
from tests.test_commercial import purchase, request_return


def test_registration_cannot_grant_platform_role(setup):
    client, _, auth = setup
    data = dict(
        nombre_completo="Nuevo cliente",
        email="signup@example.com",
        password="Testing123!",
        rol_id=3,
        empresa_id=1,
    )
    response = client.post("/api/v1/seguridad/register", json=data)
    assert response.status_code == 201, response.text
    assert response.json()["rol_id"] == 2
    login = client.post(
        "/api/v1/seguridad/login",
        json={"email": data["email"], "password": data["password"]},
        headers={"Authorization": "Bearer invalid-old-token"},
    )
    assert login.status_code == 200, login.text
    assert (
        client.put(
            "/api/v1/seguridad/usuarios/1", json={"rol_id": 3}, headers=auth()
        ).status_code
        == 403
    )


def test_disabled_account_cannot_reuse_token(setup):
    client, factory, auth = setup
    token = auth()
    with factory() as db:
        db.query(Usuario).filter_by(id=1).one().is_active = False
        db.commit()
    assert client.get("/api/v1/ventas/", headers=token).status_code == 401


def test_failed_replacement_keeps_stock_and_note(setup):
    client, factory, auth = setup
    from app.pkg_catalogo.models import Talla

    with factory() as db:
        db.add(Talla(id=2, nombre="XL"))
        db.commit()
    bought = purchase(client, auth)
    note = request_return(
        client,
        auth,
        bought,
        tipo_solicitud="Cambio de Talla o Color",
        producto_nuevo_id=1,
        talla_nueva_id=2,
        color_nuevo_id=1,
    )
    assert note.status_code == 201, note.text
    note_id = note.json()["id"]
    response = client.put(
        f"/api/v1/devoluciones/notas/{note_id}/completar", json={}, headers=auth()
    )
    assert response.status_code == 409, response.text
    with factory() as db:
        assert db.query(Inventario).filter_by(id=1).one().cantidad == 8
        assert (
            db.query(NotaDevolucion).filter_by(id=note_id).one().estado == "EN_MARCHA"
        )


def test_expired_request_does_not_reserve_return_quantity(setup):
    client, factory, auth = setup
    bought = purchase(client, auth)
    note = request_return(client, auth, bought, cantidad=2).json()
    with factory() as db:
        db.query(NotaDevolucion).filter_by(id=note["id"]).one().fecha_expiracion = (
            datetime.utcnow() - timedelta(days=1)
        )
        db.commit()
    assert request_return(client, auth, bought, cantidad=2).status_code == 201


def test_customer_cannot_lower_price(setup):
    client, _, auth = setup
    payload = sale()
    payload["detalles"][0]["precio_unitario"] = 0
    response = client.post("/api/v1/ventas/", json=payload, headers=auth("cliente"))
    assert response.status_code == 409, response.text


def test_additive_upgrade_can_run_twice():
    from scripts.upgrade_commercial import upgrade

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for table in ["ventas", "politicas_devoluciones", "notas_devoluciones"]:
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            connection.execute(text(f"INSERT INTO {table} (id) VALUES (73)"))
        upgrade(connection)
        upgrade(connection)
        assert "detalle_venta_id" in {
            c["name"] for c in inspect(connection).get_columns("notas_devoluciones")
        }
        assert (
            connection.execute(text("SELECT id FROM notas_devoluciones")).scalar() == 73
        )
    engine.dispose()


def test_customer_can_redeem_shared_coupon_and_it_disappears(setup):
    client, _, auth = setup
    coupon = client.post(
        "/api/v1/comercial/cupones",
        headers=auth(),
        json={
            "nombre": "Beneficio general",
            "tipo": "MONTO",
            "valor": 10,
            "criterios": {},
            "max_usos": 100,
            "fecha_vencimiento": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        },
    )
    assert coupon.status_code == 201, coupon.text
    assert (
        len(client.get("/api/v1/cliente/cupones", headers=auth("cliente")).json()) == 1
    )
    response = client.post(
        "/api/v1/ventas/",
        headers=auth("cliente"),
        json=sale(cupon_codigo=coupon.json()["codigo"]),
    )
    assert response.status_code == 201, response.text
    assert response.json()["total"] == 190
    assert client.get("/api/v1/cliente/cupones", headers=auth("cliente")).json() == []
