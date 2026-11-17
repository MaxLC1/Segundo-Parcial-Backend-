def test_platform_catalog_and_branches_follow_selection(setup):
    client, _, auth = setup
    for tenant in (2, 1, 2):
        branches = client.get(f'/api/v1/sucursales/sucursales?empresa_id={tenant}', headers=auth('plataforma'))
        assert branches.status_code == 200, branches.text
        assert [b['id'] for b in branches.json()] == [tenant]
        products = client.get(f'/api/v1/catalogo/productos?empresa_id={tenant}', headers=auth('plataforma'))
        assert products.status_code == 200, products.text
        assert [p['id'] for p in products.json()] == [tenant]


def test_regular_admin_cannot_select_other_tenant(setup):
    client, _, auth = setup
    res = client.get('/api/v1/sucursales/sucursales?empresa_id=2', headers=auth('admin1'))
    assert res.status_code == 403
