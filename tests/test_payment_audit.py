from datetime import datetime, timedelta
from app.pkg_pagos.models import MovimientoPago, SesionPagoSimulada, TransaccionPagoOTP
from app.pkg_comercial.models import CanjeCupon, Cupon
from tests.test_business import sale
from tests.test_commercial import purchase, request_return


def test_coupon_larger_than_sale_has_no_wallet_and_payment_is_persisted(setup):
    client, factory, auth = setup
    response = client.post(
        "/api/v1/comercial/cupones",
        headers=auth(),
        json={
            "nombre": "Descuento único",
            "tipo": "MONTO",
            "valor": 250,
            "max_usos": 1,
            "criterios": {},
            "fecha_vencimiento": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    code = response.json()["codigo"]
    payload = sale(cupon_codigo=code)
    for _ in range(2):
        response = client.post("/api/v1/ventas/", headers=auth(), json=payload)
        assert response.status_code == 201, response.text
        assert response.json()["total"] == 0
    with factory() as db:
        movement = db.query(MovimientoPago).one()
        assert (movement.monto_bruto, movement.descuento_cupon, movement.monto) == (
            200,
            200,
            0,
        )
        assert movement.simulado and movement.estado == "CONFIRMADO_SIMULADO"
        assert db.query(CanjeCupon).one().monto == 200
        assert db.query(Cupon).one().usos == 1
    # The remaining 50 never becomes wallet balance or a new coupon.
    assert client.get("/api/v1/cliente/cupones", headers=auth("cliente")).json() == []
    assert (
        len(client.get("/api/v1/pagos/movimientos", headers=auth("cliente")).json())
        == 1
    )
    assert client.get("/api/v1/pagos/movimientos", headers=auth("admin2")).json() == []


def test_qr_session_survives_new_request_and_is_tenant_scoped(setup):
    client, factory, auth = setup
    response = client.post(
        "/api/v1/ventas/generar-qr", json={"amount": 200}, headers=auth()
    )
    assert response.status_code == 200, response.text
    key = response.json()["tx_id"]
    with factory() as db:
        assert db.query(SesionPagoSimulada).filter_by(id=key).one().estado == "PENDING"
    assert (
        client.post(
            "/api/v1/ventas/simular-pago-cliente/" + key, headers=auth("admin2")
        ).status_code
        == 404
    )
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/ventas/simular-pago-cliente/" + key, headers=auth()
            ).status_code
            == 200
        )
    assert (
        client.get("/api/v1/ventas/estado-pago-qr/" + key, headers=auth()).json()[
            "status"
        ]
        == "COMPLETED"
    )
    with factory() as db:
        assert db.query(SesionPagoSimulada).count() == 1


def test_otp_authorization_reference_is_persistent_and_repeatable(setup):
    client, factory, auth = setup
    response = client.post(
        "/api/v1/pagos/iniciar-pasarela", json={"monto": 200}, headers=auth("cliente")
    )
    assert response.status_code == 200, response.text
    data = response.json()
    payload = {
        "transaccion_id": data["transaccion_id"],
        "codigo_otp": data["otp_simulado"],
    }
    first = client.post(
        "/api/v1/pagos/validar-otp", json=payload, headers=auth("cliente")
    ).json()
    second = client.post(
        "/api/v1/pagos/validar-otp", json=payload, headers=auth("cliente")
    ).json()
    assert (
        first["valido"] and first["token_autorizacion"] == second["token_autorizacion"]
    )
    with factory() as db:
        row = db.query(TransaccionPagoOTP).one()
        assert (
            row.simulado
            and row.usuario_id == 3
            and row.token_autorizacion == first["token_autorizacion"]
        )


def test_refund_movement_is_persisted_once(setup):
    client, factory, auth = setup
    client.put(
        "/api/v1/devoluciones/politica/1",
        json={
            "tipo_reembolso_menor_valor": "REEMBOLSO_PORCENTAJE",
            "porcentaje_reembolso": 50,
        },
        headers=auth(),
    )
    note = request_return(client, auth, purchase(client, auth)).json()
    for _ in range(2):
        response = client.put(
            f"/api/v1/devoluciones/notas/{note['id']}/completar",
            json={},
            headers=auth(),
        )
        assert response.status_code == 200, response.text
    with factory() as db:
        refund = db.query(MovimientoPago).filter_by(tipo="REEMBOLSO").one()
        assert refund.monto == 50 and refund.nota_id == note["id"]
        assert db.query(MovimientoPago).count() == 2


def test_failed_sale_leaves_no_payment_record(setup):
    client, factory, auth = setup
    response = client.post(
        "/api/v1/ventas/", json=sale(cupon_codigo="NO-EXISTE"), headers=auth()
    )
    assert response.status_code == 409
    with factory() as db:
        assert db.query(MovimientoPago).count() == 0
