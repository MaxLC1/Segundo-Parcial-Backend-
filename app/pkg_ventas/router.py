from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from . import schemas, services

from pydantic import BaseModel, Field
from app.pkg_pagos.audit import crear_sesion
from app.pkg_pagos.models import SesionPagoSimulada

router = APIRouter(tags=["Ventas"])


@router.get("/clientes")
def clientes_para_venta(db: Session = Depends(get_db)):
    from app.pkg_seguridad.models import Usuario, Rol

    return [
        {"id": u.id, "nombre_completo": u.nombre_completo}
        for u in db.query(Usuario).join(Rol).filter(Rol.nombre == "Cliente").all()
    ]


class PaymentIntentRequest(BaseModel):
    amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = "usd"


@router.post("/create-payment-intent")
def create_payment_intent(request: PaymentIntentRequest, db: Session = Depends(get_db)):
    session = crear_sesion(db, request.amount, "Tarjeta", request.currency, "COMPLETED")
    return {"client_secret": session.id, "simulado": True}


@router.post("/", response_model=schemas.VentaOut, status_code=status.HTTP_201_CREATED)
def crear_venta(venta: schemas.VentaCreate, db: Session = Depends(get_db)):
    """Crea una nueva venta verificando stock e idempotencia."""
    return services.create_venta(db=db, venta=venta)


@router.get("/", response_model=List[schemas.VentaOut])
def obtener_ventas(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene el historial de ventas, con filtrado opcional por empresa/tenant."""
    return services.get_ventas(db=db, empresa_id=empresa_id)


@router.get("/reportes")
def obtener_reportes(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene KPIs generales de ventas para el tenant."""
    return services.get_reportes(db=db, empresa_id=empresa_id)


# ==============================================================================
# OPERACIONES OFFLINE: SINCRONIZACIÓN POR LOTES E IDEMPOTENCIA (Desafíos II y IV)
# ==============================================================================


@router.post("/sincronizar-offline", response_model=schemas.SincronizacionLoteResponse)
def sincronizar_operaciones_offline(
    lote: schemas.SincronizacionLoteRequest, db: Session = Depends(get_db)
):
    """
    Recibe un lote de ventas registradas offline desde la PWA o aplicación móvil.
    Verifica idempotencia (RNF05) mediante operacion_uuid, valida existencias de inventario (RNF04)
    y clasifica cada operación en CONFIRMADA o RECHAZADA_CONFLICTO.
    """
    from app.pkg_bitacora.services import registrar_desde_request
    res = services.sincronizar_ventas_lote(db=db, lote=lote)
    try:
        cant = len(lote.ventas)
        registrar_desde_request(
            db=db,
            accion="SINCRONIZAR_VENTAS_OFFLINE",
            modulo="Ventas",
            detalle=f"Sincronización lote offline: {cant} venta(s) procesada(s)",
        )
    except Exception:
        pass
    return res


# ==============================================================================
# CAMBIOS DE PRENDAS DE VESTIR (Desafío IV - Req 7.2)
# ==============================================================================


@router.post(
    "/cambios",
    response_model=schemas.CambioPrendaOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar_cambio(cambio: schemas.CambioPrendaCreate, db: Session = Depends(get_db)):
    """Registra un cambio de prendas dentro del plazo de 30 días, reintegrando y descontando inventario."""
    return services.registrar_cambio_prenda(db=db, cambio=cambio)


@router.get("/cambios", response_model=List[schemas.CambioPrendaOut])
def listar_cambios(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Lista los cambios de prendas registrados en el tenant."""
    return services.get_cambios_prendas(db=db, empresa_id=empresa_id)


# ==============================================================================
# SIMULACIÓN DE PAGOS QR
# ==============================================================================


class QRCodeRequest(BaseModel):
    amount: float = Field(gt=0, allow_inf_nan=False)


@router.post("/generar-qr")
def generar_qr(request: QRCodeRequest, db: Session = Depends(get_db)):
    session = crear_sesion(db, request.amount, "QR")
    tx_id = session.id
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=PagoFashionStore:{tx_id}_Monto:{request.amount}"
    return {"tx_id": tx_id, "qr_url": qr_url, "status": "PENDING"}


@router.get("/estado-pago-qr/{tx_id}")
def verificar_estado_pago(tx_id: str, db: Session = Depends(get_db)):
    session = (
        db.query(SesionPagoSimulada)
        .filter_by(id=tx_id, usuario_id=db.info["actor"].id, metodo="QR")
        .first()
    )
    return {"status": session.estado if session else "NOT_FOUND", "simulado": True}


@router.post("/simular-pago-cliente/{tx_id}")
def simular_pago_cliente(tx_id: str, db: Session = Depends(get_db)):
    session = (
        db.query(SesionPagoSimulada)
        .filter_by(id=tx_id, usuario_id=db.info["actor"].id, metodo="QR")
        .with_for_update()
        .first()
    )
    if session:
        session.estado = "COMPLETED"
        db.commit()
        return {"message": "Pago simulado con éxito"}
    raise HTTPException(status_code=404, detail="Transacción no encontrada")
