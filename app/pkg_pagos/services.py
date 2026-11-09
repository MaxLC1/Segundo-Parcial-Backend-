import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from . import models, schemas


def iniciar_pago_otp(
    db: Session, req: schemas.IniciarPagoRequest
) -> schemas.IniciarPagoResponse:
    if req.empresa_id not in (None, db.info["tenant_id"]):
        raise HTTPException(403, "Empresa ajena a la sesión")
    otp_code = f"{random.randint(100000, 999999)}"
    txn_id = f"TXN-OTP-{uuid.uuid4().hex[:8].upper()}"

    txn = models.TransaccionPagoOTP(
        empresa_id=db.info["tenant_id"],
        usuario_id=db.info["actor"].id,
        transaccion_id=txn_id,
        monto=req.monto,
        metodo=req.metodo,
        cliente_email=req.cliente_email,
        cliente_telefono=req.cliente_telefono,
        codigo_otp=otp_code,
        estado="PENDIENTE_OTP",
        fecha_creacion=datetime.utcnow(),
        fecha_expiracion=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return schemas.IniciarPagoResponse(
        transaccion_id=txn_id,
        monto=txn.monto,
        metodo=txn.metodo,
        estado="PENDIENTE_OTP",
        mensaje="Simulación académica: usa el código mostrado. No se envió un SMS ni se efectuó un cobro bancario.",
        otp_simulado=otp_code,
        expira_en_segundos=300,
    )


def validar_pago_otp(
    db: Session, req: schemas.ValidarOTPRequest
) -> schemas.ValidarOTPResponse:
    txn = (
        db.query(models.TransaccionPagoOTP)
        .filter(
            models.TransaccionPagoOTP.transaccion_id == req.transaccion_id,
            models.TransaccionPagoOTP.usuario_id == db.info["actor"].id,
        )
        .with_for_update()
        .first()
    )

    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transacción de pasarela no encontrada",
        )

    if txn.estado == "AUTORIZADO":
        return schemas.ValidarOTPResponse(
            transaccion_id=txn.transaccion_id,
            estado="AUTORIZADO",
            valido=True,
            mensaje="La transacción ya fue autorizada previamente.",
            token_autorizacion=txn.token_autorizacion,
            monto=txn.monto,
        )

    # Verificar expiración
    if datetime.utcnow() > txn.fecha_expiracion:
        txn.estado = "EXPIRADO"
        db.commit()
        return schemas.ValidarOTPResponse(
            transaccion_id=txn.transaccion_id,
            estado="EXPIRADO",
            valido=False,
            mensaje="El código OTP ha expirado (validez de 5 minutos). Solicite uno nuevo.",
            token_autorizacion=None,
            monto=txn.monto,
        )

    # Verificar intentos
    txn.intentos += 1
    if txn.intentos > 3:
        txn.estado = "RECHAZADO"
        db.commit()
        return schemas.ValidarOTPResponse(
            transaccion_id=txn.transaccion_id,
            estado="RECHAZADO",
            valido=False,
            mensaje="Transacción bloqueada por exceder el límite de 3 intentos fallidos de OTP.",
            token_autorizacion=None,
            monto=txn.monto,
        )

    if txn.codigo_otp != req.codigo_otp.strip():
        db.commit()
        return schemas.ValidarOTPResponse(
            transaccion_id=txn.transaccion_id,
            estado="PENDIENTE_OTP",
            valido=False,
            mensaje=f"Código OTP incorrecto. Intento {txn.intentos} de 3.",
            token_autorizacion=None,
            monto=txn.monto,
        )

    # Éxito: Validado correctamente
    txn.estado = "AUTORIZADO"
    txn.token_autorizacion = f"AUTH-SIM-{uuid.uuid4().hex}"
    db.commit()

    return schemas.ValidarOTPResponse(
        transaccion_id=txn.transaccion_id,
        estado="AUTORIZADO",
        valido=True,
        mensaje="Código verificado. Autorización simulada registrada; sin cobro bancario real.",
        token_autorizacion=txn.token_autorizacion,
        monto=txn.monto,
    )
