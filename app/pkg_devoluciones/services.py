import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from . import models, schemas

from app.pkg_ventas.models import Venta

def get_devoluciones(db: Session):
    return db.query(models.Devolucion).all()

def create_devolucion(db: Session, devolucion: schemas.DevolucionCreate):
    venta = db.query(Venta).filter(Venta.id == devolucion.venta_id).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    db_devolucion = models.Devolucion(**devolucion.model_dump())
    db.add(db_devolucion)
    db.commit()
    db.refresh(db_devolucion)
    return db_devolucion

def update_estado(db: Session, dev_id: int, estado: str):
    dev = db.query(models.Devolucion).filter(models.Devolucion.id == dev_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    
    dev.estado = estado
    db.commit()
    db.refresh(dev)
    return dev

# -- GESTIÓN DE POLÍTICAS DE DEVOLUCIÓN --
def get_politica_empresa(db: Session, empresa_id: int):
    pol = db.query(models.PoliticaDevolucion).filter(
        models.PoliticaDevolucion.empresa_id == empresa_id,
        models.PoliticaDevolucion.activa == True
    ).first()
    if not pol:
        # Política por defecto
        pol = models.PoliticaDevolucion(
            empresa_id=empresa_id,
            nombre="Política Estándar de Tienda",
            tipo_reembolso_menor_valor="CUPON_CREDITO",
            plazo_maximo_dias=30,
            permite_cambio_mayor_valor=True,
            activa=True
        )
        db.add(pol)
        db.commit()
        db.refresh(pol)
    return pol

def update_politica_empresa(db: Session, empresa_id: int, data: schemas.PoliticaDevolucionCreate):
    pol = db.query(models.PoliticaDevolucion).filter(models.PoliticaDevolucion.empresa_id == empresa_id).first()
    if not pol:
        pol = models.PoliticaDevolucion(empresa_id=empresa_id, **data.model_dump())
        db.add(pol)
    else:
        for k, v in data.model_dump().items():
            setattr(pol, k, v)
    db.commit()
    db.refresh(pol)
    return pol

# -- GESTIÓN DE NOTAS DE DEVOLUCIÓN PARA CLIENTE Y DELIVERY --
def crear_nota_devolucion(db: Session, req: schemas.NotaDevolucionCreate):
    venta = db.query(Venta).filter(Venta.id == req.venta_id).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta original no encontrada")

    empresa_id = req.empresa_id or venta.empresa_id or 1
    politica = get_politica_empresa(db, empresa_id=empresa_id)

    # Validar plazo comercial (30 días por defecto)
    dias_transcurridos = (datetime.utcnow() - venta.fecha).days
    if dias_transcurridos > politica.plazo_maximo_dias:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plazo reglamentario expirado: La compra fue realizada hace {dias_transcurridos} días (Máximo permitido: {politica.plazo_maximo_dias} días)."
        )

    # Calcular diferencia de precio
    diferencia = round(float(req.precio_prenda_nueva or 0.0) - float(req.precio_prenda_original), 2)
    cupon_generado = None

    if diferencia > 0:
        tipo = "Cambio por Mayor Valor"
        mensaje = f"La prenda sustituta subió de precio (+{diferencia:.2f} Bs). Debe pagar la diferencia en efectivo al repartidor de delivery."
    elif diferencia == 0:
        tipo = "Cambio Talla/Color Sin Diferencia"
        mensaje = "Cambio de prenda exacto sin costo adicional."
    else:
        tipo = "Cambio por Menor Valor"
        monto_favor = abs(diferencia)
        if politica.tipo_reembolso_menor_valor == "CUPON_CREDITO":
            cupon_generado = f"CUPON-{uuid.uuid4().hex[:6].upper()}"
            mensaje = f"Prenda de menor valor: Se ha generado un Cupón de Crédito de {monto_favor:.2f} Bs con código {cupon_generado} para futuras compras."
        elif politica.tipo_reembolso_menor_valor == "REEMBOLSO_50_PCT":
            mensaje = f"Prenda de menor valor: Según política de tienda se reembolsa el 50% ({monto_favor*0.5:.2f} Bs) en efectivo mediante el repartidor."
        else:
            mensaje = "Prenda de menor valor: Por política de la tienda no se efectúan reintegros en efectivo para diferencias menores."

    codigo = f"NDEV-{datetime.utcnow().year}-{uuid.uuid4().hex[:5].upper()}"

    nota = models.NotaDevolucion(
        codigo_nota=codigo,
        empresa_id=empresa_id,
        venta_id=venta.id,
        usuario_id=req.usuario_id or venta.usuario_id or 2,
        repartidor_id=req.repartidor_id,
        sucursal_id=req.sucursal_id or venta.sucursal_id or 1,
        motivo=req.motivo,
        tipo_solicitud=tipo,
        estado="EN_MARCHA",
        visible_para_cliente=True,
        prenda_devuelta_info=req.prenda_devuelta_info,
        prenda_nueva_info=req.prenda_nueva_info,
        precio_prenda_original=req.precio_prenda_original,
        precio_prenda_nueva=req.precio_prenda_nueva or 0.0,
        diferencia_precio=diferencia,
        mensaje_notificacion=mensaje,
        cupon_generado=cupon_generado,
        fecha_creacion=datetime.utcnow()
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota

def get_notas_devolucion(db: Session, empresa_id: Optional[int] = None, estado: Optional[str] = None):
    query = db.query(models.NotaDevolucion)
    if empresa_id:
        query = query.filter(models.NotaDevolucion.empresa_id == empresa_id)
    if estado:
        query = query.filter(models.NotaDevolucion.estado == estado)
    return query.order_by(models.NotaDevolucion.fecha_creacion.desc()).all()

def get_mis_notas_activas_cliente(db: Session, usuario_id: int):
    # Solo las notas activas marcadas como visibles para el cliente
    return db.query(models.NotaDevolucion).filter(
        models.NotaDevolucion.usuario_id == usuario_id,
        models.NotaDevolucion.visible_para_cliente == True,
        models.NotaDevolucion.estado == "EN_MARCHA"
    ).all()

def completar_nota_devolucion(db: Session, nota_id: int, req: schemas.CompletarNotaRequest):
    nota = db.query(models.NotaDevolucion).filter(models.NotaDevolucion.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota de devolución no encontrada")

    nota.estado = "COMPLETADA"
    # Regla: Se elimina de la pestaña del cliente, pero para el admin se conserva recopilada en el histórico
    nota.visible_para_cliente = False
    nota.fecha_completada = datetime.utcnow()
    if req.repartidor_id:
        nota.repartidor_id = req.repartidor_id

    db.commit()
    db.refresh(nota)
    return nota

