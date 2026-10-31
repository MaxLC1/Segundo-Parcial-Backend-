from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime, timedelta

from . import models, schemas
from app.pkg_sucursales.models import Inventario, Sucursal
from app.pkg_catalogo.models import Producto

def create_venta(db: Session, venta: schemas.VentaCreate):
    # 1. Verificación de Idempotencia (RNF05): si ya existe la venta con este operacion_uuid, retornarla
    if venta.operacion_uuid:
        venta_existente = db.query(models.Venta).filter_by(operacion_uuid=venta.operacion_uuid).first()
        if venta_existente:
            return venta_existente

    # Obtener empresa_id si no vino en el payload
    empresa_id = venta.empresa_id
    if not empresa_id:
        sucursal = db.query(Sucursal).filter_by(id=venta.sucursal_id).first()
        if sucursal:
            empresa_id = sucursal.empresa_id

    # 2. Calcular total y verificar inventario
    total_venta = 0.0
    for det in venta.detalles:
        inv = db.query(Inventario).filter(
            Inventario.sucursal_id == venta.sucursal_id,
            Inventario.producto_id == det.producto_id,
            Inventario.talla_id == det.talla_id,
            Inventario.color_id == det.color_id
        ).first()
        
        if not inv or inv.cantidad < det.cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para producto ID {det.producto_id}")
            
        inv.cantidad -= det.cantidad
        total_venta += det.cantidad * det.precio_unitario
        
    # 3. Crear venta
    db_venta = models.Venta(
        total=total_venta,
        usuario_id=venta.usuario_id,
        sucursal_id=venta.sucursal_id,
        empresa_id=empresa_id,
        metodo_pago=venta.metodo_pago,
        transaccion_id=venta.transaccion_id,
        tipo_entrega=venta.tipo_entrega,
        direccion_envio=venta.direccion_envio,
        operacion_uuid=venta.operacion_uuid,
        origen=venta.origen or "ONLINE",
        estado_sincronizacion="CONFIRMADA",
        fecha=venta.fecha or datetime.utcnow()
    )
    db.add(db_venta)
    db.commit()
    db.refresh(db_venta)
    
    # 4. Crear detalles
    for det in venta.detalles:
        db_det = models.DetalleVenta(
            venta_id=db_venta.id,
            producto_id=det.producto_id,
            talla_id=det.talla_id,
            color_id=det.color_id,
            cantidad=det.cantidad,
            precio_unitario=det.precio_unitario,
            subtotal=det.cantidad * det.precio_unitario
        )
        db.add(db_det)
        
    db.commit()
    db.refresh(db_venta)

    # 5. Si es Delivery, crear la orden de servicio
    if venta.tipo_entrega == "Delivery":
        from app.pkg_delivery.models import ServicioDelivery
        db_delivery = ServicioDelivery(
            venta_id=db_venta.id,
            empresa_id=empresa_id,
            estado="Pendiente"
        )
        db.add(db_delivery)
        db.commit()

    return db_venta

def sincronizar_ventas_lote(db: Session, lote: schemas.SincronizacionLoteRequest) -> schemas.SincronizacionLoteResponse:
    """Procesa un lote de operaciones offline respetando idempotencia y detectando conflictos (Desafío II y IV)."""
    resultados: List[schemas.ResultadoSincronizacionItem] = []
    confirmadas = 0
    rechazadas = 0
    duplicadas = 0

    for venta_in in lote.ventas:
        uuid_op = venta_in.operacion_uuid or f"offline-{datetime.utcnow().timestamp()}"
        
        # 1. Idempotencia: Verificar si ya existe en la BD
        existente = db.query(models.Venta).filter_by(operacion_uuid=uuid_op).first()
        if existente:
            duplicadas += 1
            resultados.append(schemas.ResultadoSincronizacionItem(
                operacion_uuid=uuid_op,
                estado="CONFIRMADA",
                mensaje="Operación previamente confirmada (Idempotente)",
                id_generado=existente.id
            ))
            continue

        # 2. Verificar consistencia de stock en la sucursal
        conflicto = None
        for det in venta_in.detalles:
            inv = db.query(Inventario).filter(
                Inventario.sucursal_id == venta_in.sucursal_id,
                Inventario.producto_id == det.producto_id,
                Inventario.talla_id == det.talla_id,
                Inventario.color_id == det.color_id
            ).first()
            if not inv or inv.cantidad < det.cantidad:
                disp = inv.cantidad if inv else 0
                conflicto = f"Conflicto de stock: Producto ID {det.producto_id} requiere {det.cantidad}, disponible: {disp}"
                break

        if conflicto:
            # Registrar como rechazada por conflicto sin alterar inventario
            rechazadas += 1
            db_venta_rechazada = models.Venta(
                total=sum(d.cantidad * d.precio_unitario for d in venta_in.detalles),
                usuario_id=venta_in.usuario_id,
                sucursal_id=venta_in.sucursal_id,
                empresa_id=venta_in.empresa_id or lote.empresa_id,
                metodo_pago=venta_in.metodo_pago,
                operacion_uuid=uuid_op,
                origen=venta_in.origen or "PWA_OFFLINE",
                estado_sincronizacion="RECHAZADA_CONFLICTO",
                motivo_rechazo=conflicto,
                fecha=venta_in.fecha or datetime.utcnow()
            )
            db.add(db_venta_rechazada)
            db.commit()
            resultados.append(schemas.ResultadoSincronizacionItem(
                operacion_uuid=uuid_op,
                estado="RECHAZADA_CONFLICTO",
                mensaje=conflicto,
                id_generado=db_venta_rechazada.id
            ))
            continue

        # 3. Operación aceptada: descontar stock y guardar
        try:
            db_venta = create_venta(db, venta_in)
            confirmadas += 1
            resultados.append(schemas.ResultadoSincronizacionItem(
                operacion_uuid=uuid_op,
                estado="CONFIRMADA",
                mensaje="Venta sincronizada y stock actualizado exitosamente",
                id_generado=db_venta.id
            ))
        except Exception as e:
            rechazadas += 1
            resultados.append(schemas.ResultadoSincronizacionItem(
                operacion_uuid=uuid_op,
                estado="RECHAZADA_CONFLICTO",
                mensaje=f"Error durante sincronización: {str(e)}"
            ))

    return schemas.SincronizacionLoteResponse(
        total=len(lote.ventas),
        confirmadas=confirmadas,
        rechazadas=rechazadas,
        duplicadas_ignoradas=duplicadas,
        resultados=resultados
    )

def registrar_cambio_prenda(db: Session, cambio: schemas.CambioPrendaCreate):
    """Gestiona cambios de prendas en un determinado plazo (Desafío IV - Req 7.2)."""
    venta = db.query(models.Venta).filter_by(id=cambio.venta_id).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta original no encontrada")

    # Validar plazo de cambio (ej. máximo 30 días)
    dias_transcurridos = (datetime.utcnow() - venta.fecha).days
    if dias_transcurridos > 30:
        raise HTTPException(
            status_code=400,
            detail=f"El plazo máximo para cambios es de 30 días. Han transcurrido {dias_transcurridos} días desde la compra."
        )

    # 1. Devolver prenda anterior al inventario de la sucursal
    inv_devuelto = db.query(Inventario).filter(
        Inventario.sucursal_id == cambio.sucursal_id,
        Inventario.producto_id == cambio.producto_devuelto_id,
        Inventario.talla_id == cambio.talla_devuelta_id,
        Inventario.color_id == cambio.color_devuelto_id
    ).first()
    if inv_devuelto:
        inv_devuelto.cantidad += cambio.cantidad_devuelta
    else:
        inv_devuelto = Inventario(
            sucursal_id=cambio.sucursal_id,
            producto_id=cambio.producto_devuelto_id,
            talla_id=cambio.talla_devuelta_id,
            color_id=cambio.color_devuelto_id,
            cantidad=cambio.cantidad_devuelta
        )
        db.add(inv_devuelto)

    # 2. Verificar y descontar stock de la nueva prenda
    inv_nuevo = db.query(Inventario).filter(
        Inventario.sucursal_id == cambio.sucursal_id,
        Inventario.producto_id == cambio.producto_nuevo_id,
        Inventario.talla_id == cambio.talla_nueva_id,
        Inventario.color_id == cambio.color_nuevo_id
    ).first()
    if not inv_nuevo or inv_nuevo.cantidad < cambio.cantidad_nueva:
        raise HTTPException(status_code=400, detail="Stock insuficiente en sucursal para la nueva prenda solicitada")
    inv_nuevo.cantidad -= cambio.cantidad_nueva

    # 3. Calcular diferencia de precio
    prod_anterior = db.query(Producto).filter_by(id=cambio.producto_devuelto_id).first()
    prod_nuevo = db.query(Producto).filter_by(id=cambio.producto_nuevo_id).first()
    precio_ant = (prod_anterior.precio if prod_anterior else 0) * cambio.cantidad_devuelta
    precio_nuev = (prod_nuevo.precio if prod_nuevo else 0) * cambio.cantidad_nueva
    diferencia = precio_nuev - precio_ant

    # 4. Registrar CambioPrenda
    db_cambio = models.CambioPrenda(
        empresa_id=cambio.empresa_id or venta.empresa_id,
        venta_id=cambio.venta_id,
        sucursal_id=cambio.sucursal_id,
        usuario_id=cambio.usuario_id,
        producto_devuelto_id=cambio.producto_devuelto_id,
        talla_devuelta_id=cambio.talla_devuelta_id,
        color_devuelto_id=cambio.color_devuelto_id,
        cantidad_devuelta=cambio.cantidad_devuelta,
        producto_nuevo_id=cambio.producto_nuevo_id,
        talla_nueva_id=cambio.talla_nueva_id,
        color_nuevo_id=cambio.color_nuevo_id,
        cantidad_nueva=cambio.cantidad_nueva,
        diferencia_precio=diferencia,
        motivo=cambio.motivo,
        estado="Aprobado",
        fecha_cambio=datetime.utcnow()
    )
    db.add(db_cambio)
    db.commit()
    db.refresh(db_cambio)
    return db_cambio

def get_cambios_prendas(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.CambioPrenda)
    if empresa_id is not None:
        query = query.filter(models.CambioPrenda.empresa_id == empresa_id)
    return query.order_by(models.CambioPrenda.id.desc()).all()

def get_ventas(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Venta)
    if empresa_id is not None:
        query = query.filter(models.Venta.empresa_id == empresa_id)
    return query.order_by(models.Venta.id.desc()).all()

def get_reportes(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Venta).filter(models.Venta.estado_sincronizacion == "CONFIRMADA")
    if empresa_id is not None:
        query = query.filter(models.Venta.empresa_id == empresa_id)
        
    ventas = query.all()
    total_ingresos = sum(v.total for v in ventas) if ventas else 0
    total_ventas = len(ventas)
    ticket_promedio = total_ingresos / total_ventas if total_ventas > 0 else 0
    
    return {
        "total_ingresos": total_ingresos,
        "total_ventas": total_ventas,
        "ticket_promedio": ticket_promedio,
        "ventas_por_metodo": {
            "Efectivo": len([v for v in ventas if v.metodo_pago == "Efectivo"]),
            "QR": len([v for v in ventas if v.metodo_pago == "QR"]),
            "Stripe": len([v for v in ventas if v.metodo_pago == "Stripe"]),
        }
    }
