from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from . import models, schemas, services

router = APIRouter(prefix="/comercial", tags=["Cupones, avisos y traspasos"])


@router.get("/cupones")
def cupones(db: Session = Depends(get_db)):
    return db.query(models.Cupon).order_by(models.Cupon.id.desc()).all()


@router.post("/cupones", status_code=201)
def crear_cupon(data: schemas.CuponCreate, db: Session = Depends(get_db)):
    if db.info.get("role") != "Administrador":
        raise HTTPException(403, "Solo el administrador configura cupones")
    return services.crear_cupon(db, data, db.info["tenant_id"])


@router.put("/cupones/{cupon_id}/desactivar")
def desactivar(cupon_id: int, db: Session = Depends(get_db)):
    if db.info.get("role") != "Administrador":
        raise HTTPException(403, "No autorizado")
    coupon = db.query(models.Cupon).filter_by(id=cupon_id).first()
    if not coupon:
        raise HTTPException(404, "Cupón no encontrado")
    coupon.activo = False
    db.commit()
    return {"ok": True}


@router.post("/notificaciones", status_code=201)
def aviso(data: schemas.AvisoCreate, db: Session = Depends(get_db)):
    if db.info.get("role") != "Administrador":
        raise HTTPException(403, "No autorizado")
    record = models.Notificacion(**data.model_dump(), empresa_id=db.info["tenant_id"])
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/traspasos")
def traspasos(db: Session = Depends(get_db)):
    return db.query(models.Traspaso).order_by(models.Traspaso.id.desc()).all()


@router.post("/traspasos", status_code=201)
def crear_traspaso(data: schemas.TraspasoCreate, db: Session = Depends(get_db)):
    if db.info.get("role") not in {"Administrador", "Encargado"}:
        raise HTTPException(403, "No autorizado")
    return services.traspasar(db, data)


cliente = APIRouter(prefix="/cliente", tags=["Área del cliente"])


@cliente.get("/existencias")
def existencias(db: Session = Depends(get_db)):
    from app.pkg_sucursales.models import Inventario

    return db.query(Inventario).all()


@cliente.get("/cupones")
def mis_cupones(db: Session = Depends(get_db)):
    return (
        db.query(models.Cupon)
        .filter(
            or_(
                models.Cupon.usuario_id == None,
                models.Cupon.usuario_id == db.info["actor"].id,
            ),
            models.Cupon.activo == True,
            models.Cupon.fecha_vencimiento > datetime.utcnow(),
            models.Cupon.usos < models.Cupon.max_usos,
            ~models.Cupon.id.in_(
                db.query(models.CanjeCupon.cupon_id).filter(
                    models.CanjeCupon.usuario_id == db.info["actor"].id
                )
            ),
        )
        .all()
    )


@cliente.get("/notificaciones")
def mis_avisos(db: Session = Depends(get_db)):
    return (
        db.query(models.Notificacion)
        .filter(
            or_(
                models.Notificacion.usuario_id == None,
                models.Notificacion.usuario_id == db.info["actor"].id,
            ),
            or_(
                models.Notificacion.vence == None,
                models.Notificacion.vence > datetime.utcnow(),
            ),
        )
        .order_by(models.Notificacion.id.desc())
        .all()
    )


@cliente.get("/notas")
def mis_notas(db: Session = Depends(get_db)):
    from app.pkg_devoluciones.services import get_mis_notas_activas_cliente

    return get_mis_notas_activas_cliente(db, db.info["actor"].id)


@cliente.get("/compras")
def mis_compras(db: Session = Depends(get_db)):
    from app.pkg_ventas.models import Venta
    from app.pkg_ventas.schemas import VentaOut

    return [
        VentaOut.model_validate(v)
        for v in db.query(Venta)
        .filter_by(usuario_id=db.info["actor"].id, estado_sincronizacion="CONFIRMADA")
        .order_by(Venta.id.desc())
        .all()
    ]


from app.pkg_devoluciones.schemas import NotaDevolucionCreate


@cliente.post("/solicitudes", status_code=201)
def solicitar(data: NotaDevolucionCreate, db: Session = Depends(get_db)):
    from app.pkg_devoluciones.services import crear_nota_devolucion
    from app.pkg_ventas.models import Venta

    if (
        not db.query(Venta)
        .filter_by(id=data.venta_id, usuario_id=db.info["actor"].id)
        .first()
    ):
        raise HTTPException(404, "Compra no encontrada")
    return crear_nota_devolucion(db, data)
