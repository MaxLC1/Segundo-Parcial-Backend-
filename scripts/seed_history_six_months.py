"""Add identifiable simulated history; default is a rolled-back preview.

This is an import of historical operations preceding the current stock snapshot.
It does not issue receipts, call payment providers, or change current stock.
"""

import argparse
import calendar
import json
import random
from datetime import datetime
from decimal import Decimal
from uuid import uuid5, NAMESPACE_URL

from sqlalchemy import text
from app.core import model_registry  # noqa: F401
from app.core.database import SessionLocal
from app.pkg_saas.models import Empresa
from app.pkg_seguridad.models import Usuario
from app.pkg_catalogo.models import Producto, Talla, Color
from app.pkg_sucursales.models import Sucursal, Inventario
from app.pkg_ventas.models import Venta, DetalleVenta
from app.pkg_pagos.models import MovimientoPago
from app.pkg_bitacora import Bitacora

BATCH = "SIM-HIST6-20261111"
MONTH_COUNTS = [(6, 24), (7, 28), (8, 32), (9, 36), (10, 30), (11, 18)]


def seed(db, company_ids=(1, 2, 3, 4)):
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(202611116)"))
    result = []
    for company_id in company_ids:
        company = db.query(Empresa).filter_by(id=company_id, activa=True).one()
        products = (
            db.query(Producto)
            .filter(Producto.empresa_id == company_id, Producto.precio > 0)
            .order_by(Producto.id)
            .all()
        )
        branches = (
            db.query(Sucursal)
            .filter_by(empresa_id=company_id)
            .order_by(Sucursal.id)
            .all()
        )
        customers = (
            db.query(Usuario)
            .filter(Usuario.empresa_id == company_id, Usuario.rol.has(nombre="Cliente"))
            .order_by(Usuario.id)
            .all()
        )
        staff = (
            db.query(Usuario)
            .filter(
                Usuario.empresa_id == company_id,
                Usuario.is_active.is_(True),
                Usuario.rol.has(nombre="Administrador"),
            )
            .order_by(Usuario.id)
            .first()
        )
        if not products or not branches or not staff:
            raise ValueError(
                f"Empresa {company_id}: faltan productos, sucursales o administrador"
            )
        # Existing customers only; no new accounts or credentials are created.
        customers = customers or [staff]
        size, color = (
            db.query(Talla).order_by(Talla.id).first(),
            db.query(Color).order_by(Color.id).first(),
        )
        if not size or not color:
            raise ValueError("Faltan tallas o colores")
        stock_before = list(
            db.query(Inventario.id, Inventario.cantidad)
            .join(Sucursal)
            .filter(Sucursal.empresa_id == company_id)
            .order_by(Inventario.id)
        )
        added = 0
        for month, count in MONTH_COUNTS:
            total = Decimal("0")
            created = 0
            for i in range(count):
                key = f"{BATCH}-{company_id}-{month:02d}-{i:03d}"
                op = str(uuid5(NAMESPACE_URL, key))
                existing = db.query(Venta).filter_by(operacion_uuid=op).first()
                if existing:
                    total += Decimal(str(existing.total))
                    continue
                rng = random.Random(key)
                last_day = 11 if month == 11 else calendar.monthrange(2026, month)[1]
                day = 1 + i * last_day // count
                date = datetime(
                    2026, month, day, rng.randint(10, 18), rng.randint(0, 59)
                )
                branch = branches[i % len(branches)]
                customer = customers[rng.randrange(len(customers))]
                sale = Venta(
                    empresa_id=company_id,
                    sucursal_id=branch.id,
                    usuario_id=customer.id,
                    responsable_id=staff.id,
                    fecha=date,
                    origen="DEMO_HISTORICA",
                    operacion_uuid=op,
                    transaccion_id=key,
                    estado_sincronizacion="CONFIRMADA",
                    metodo_pago=["Efectivo", "QR", "Tarjeta"][i % 3],
                    tipo_entrega="Recojo en Tienda",
                )
                amount = Decimal("0")
                for product in rng.sample(
                    products, min(len(products), rng.randint(1, 3))
                ):
                    variant = (
                        db.query(Inventario)
                        .filter_by(sucursal_id=branch.id, producto_id=product.id)
                        .order_by(Inventario.id)
                        .first()
                    )
                    quantity = rng.randint(1, 3)
                    price = Decimal(str(product.precio)).quantize(Decimal("0.01"))
                    subtotal = price * quantity
                    amount += subtotal
                    sale.detalles.append(
                        DetalleVenta(
                            producto_id=product.id,
                            talla_id=variant.talla_id if variant else size.id,
                            color_id=variant.color_id if variant else color.id,
                            cantidad=quantity,
                            precio_unitario=float(price),
                            subtotal=float(subtotal),
                        )
                    )
                sale.total = float(amount)
                db.add(sale)
                db.flush()
                db.add(
                    MovimientoPago(
                        empresa_id=company_id,
                        usuario_id=customer.id,
                        responsable_id=staff.id,
                        venta_id=sale.id,
                        clave_operacion=f"VENTA:{sale.id}",
                        tipo="COBRO_VENTA",
                        metodo=sale.metodo_pago,
                        monto_bruto=float(amount),
                        descuento_cupon=0,
                        monto=float(amount),
                        moneda="BOB",
                        referencia=key,
                        estado="CONFIRMADO_SIMULADO",
                        simulado=True,
                        fecha=date,
                    )
                )
                created += 1
                total += amount
            added += created
            result.append(
                {
                    "empresa": company.nombre,
                    "empresa_id": company_id,
                    "mes": f"2026-{month:02d}",
                    "nuevas": created,
                    "ventas_lote": count,
                    "total_lote_bob": float(total),
                }
            )
        if added:
            db.add(
                Bitacora(
                    empresa_id=company_id,
                    empresa_nombre=company.nombre,
                    usuario_id=staff.id,
                    rol="Administrador",
                    accion="IMPORTACION_HISTORICA_SIMULADA",
                    modulo="Ventas",
                    detalle=json.dumps(
                        {
                            "lote": BATCH,
                            "ventas": added,
                            "periodo": "2026-06-01/2026-11-11",
                            "pagos": "simulados",
                            "inventario": "Histórico previo al saldo actual; sin descuento adicional de stock",
                        }
                    ),
                )
            )
        db.flush()
        stock_after = list(
            db.query(Inventario.id, Inventario.cantidad)
            .join(Sucursal)
            .filter(Sucursal.empresa_id == company_id)
            .order_by(Inventario.id)
        )
        assert stock_before == stock_after
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        try:
            result = seed(db)
            print(
                json.dumps(
                    {"lote": BATCH, "aplicar": args.apply, "resumen": result},
                    ensure_ascii=False,
                )
            )
            if args.apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise
