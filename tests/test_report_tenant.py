def test_platform_uses_body_tenant_and_keeps_data_isolated(setup, monkeypatch):
    client, _, auth = setup
    monkeypatch.setenv("REPORT_AI_URL", "")
    for tenant in [2, 1, 2]:
        result = client.post(
            "/api/v1/ia/reporte-generativo",
            json={"query": "Productos con menor existencia", "empresa_id": tenant},
            headers=auth("plataforma"),
        )
        assert result.status_code == 200, result.text
        assert result.json()["filtros_detectados"]["empresa_id"] == tenant
        assert f"Producto {tenant}" in str(result.json()["filas"])
        assert f"Producto {3 - tenant}" not in str(result.json()["filas"])


def test_tenant_mismatch_rejected(setup):
    client, _, auth = setup
    for who, suffix, expected in [
        ("admin1", "", 403),
        ("plataforma", "?empresa_id=1", 422),
    ]:
        result = client.post(
            "/api/v1/ia/reporte-generativo" + suffix,
            json={"query": "Ventas por sucursal", "empresa_id": 2},
            headers=auth(who),
        )
        assert result.status_code == expected
