from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from . import schemas, services

router = APIRouter(tags=["Pasarela de Pagos Digital con OTP"])


@router.get("/movimientos")
def movimientos(db: Session = Depends(get_db)):
    from .models import MovimientoPago

    query = db.query(MovimientoPago)
    if db.info.get("role") == "Cliente":
        query = query.filter_by(usuario_id=db.info["actor"].id)
    elif db.info.get("role") not in {"Administrador", "Encargado", "Cajero"}:
        raise HTTPException(403, "No autorizado")
    return query.order_by(MovimientoPago.id.desc()).limit(500).all()


@router.post("/iniciar-pasarela", response_model=schemas.IniciarPagoResponse)
def iniciar_pasarela(req: schemas.IniciarPagoRequest, db: Session = Depends(get_db)):
    """
    Inicia una transacción en la pasarela de pagos digital.
    Genera un código OTP de 6 dígitos simulado enviado al cliente con validez de 5 minutos.
    """
    return services.iniciar_pago_otp(db=db, req=req)


@router.post("/validar-otp", response_model=schemas.ValidarOTPResponse)
def validar_otp(req: schemas.ValidarOTPRequest, db: Session = Depends(get_db)):
    """
    Valida el código OTP de seguridad de 6 dígitos ingresado por el cliente.
    Si es correcto y no ha expirado, autoriza el pago y retorna un token de autorización bancaria.
    """
    return services.validar_pago_otp(db=db, req=req)
