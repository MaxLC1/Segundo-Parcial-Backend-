from uuid import uuid4
from .models import MovimientoPago, SesionPagoSimulada


def crear_sesion(db, monto, metodo, moneda="BOB", estado="PENDING"):
    session = SesionPagoSimulada(
        id="SIM-" + uuid4().hex,
        empresa_id=db.info["tenant_id"],
        usuario_id=db.info["actor"].id,
        monto=monto,
        metodo=metodo,
        moneda=moneda.upper(),
        estado=estado,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def registrar_cobro(db, venta):
    gross = round(sum(d.subtotal for d in venta.detalles), 2)
    db.add(
        MovimientoPago(
            empresa_id=venta.empresa_id,
            usuario_id=venta.usuario_id,
            responsable_id=venta.responsable_id,
            venta_id=venta.id,
            clave_operacion=f"VENTA:{venta.id}",
            tipo="COBRO_VENTA",
            metodo=venta.metodo_pago,
            monto_bruto=gross,
            descuento_cupon=round(gross - venta.total, 2),
            monto=venta.total,
            referencia=venta.transaccion_id,
        )
    )


def registrar_ajuste(db, nota):
    amount = (
        nota.diferencia_precio if nota.diferencia_precio > 0 else nota.monto_reembolso
    )
    if amount <= 0:
        return  # Un cupón emitido no es efectivo cobrado ni dinero reembolsado.
    db.add(
        MovimientoPago(
            empresa_id=nota.empresa_id,
            usuario_id=nota.usuario_id,
            responsable_id=db.info["actor"].id,
            venta_id=nota.venta_id,
            nota_id=nota.id,
            clave_operacion=f"NOTA:{nota.id}",
            tipo="COBRO_DIFERENCIA" if nota.diferencia_precio > 0 else "REEMBOLSO",
            metodo="AJUSTE_SIMULADO",
            monto_bruto=amount,
            descuento_cupon=0,
            monto=amount,
            referencia=nota.codigo_nota,
        )
    )
