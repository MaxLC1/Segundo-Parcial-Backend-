from scripts.seed_history_six_months import seed
from app.pkg_ventas.models import Venta
from app.pkg_pagos.models import MovimientoPago
from app.pkg_sucursales.models import Inventario


def test_history_seed_balances_isolation_and_idempotence(setup):
    _, factory, _ = setup
    with factory() as db:
        before = list(
            db.query(Inventario.id, Inventario.cantidad).order_by(Inventario.id)
        )
        summary = seed(db, company_ids=(1, 2))
        assert sum(r["nuevas"] for r in summary) == 336
        db.commit()
        sales = db.query(Venta).all()
        assert len(sales) == 336
        assert {s.fecha.month for s in sales} == {6, 7, 8, 9, 10, 11}
        for sale in sales:
            assert sale.total == sum(d.subtotal for d in sale.detalles)
            assert sale.sucursal.empresa_id == sale.empresa_id
            assert all(d.producto.empresa_id == sale.empresa_id for d in sale.detalles)
            payment = db.query(MovimientoPago).filter_by(venta_id=sale.id).one()
            assert payment.monto == sale.total and payment.simulado
            assert payment.fecha == sale.fecha
        assert sum(r["nuevas"] for r in seed(db, company_ids=(1, 2))) == 0
        db.commit()
        assert len(sales) == db.query(Venta).count()
        assert before == list(
            db.query(Inventario.id, Inventario.cantidad).order_by(Inventario.id)
        )
