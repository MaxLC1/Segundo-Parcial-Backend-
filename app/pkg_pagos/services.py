import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from . import models, schemas

def iniciar_pago_otp(db: Session, req: schemas.IniciarPagoRequest) -> schemas.IniciarPagoResponse:
    otp_code = f"{random.randint(100000, 999999)}"
    txn_id = f"TXN-OTP-{uuid.uuid4().hex[:8].upper()}"
    
    txn = models.TransaccionPagoOTP(
        empresa_id=req.empresa_id,
        transaccion_id=txn_id,
        monto=req.monto,
        metodo=req.metodo,
        cliente_email=req.cliente_email,
        cliente_telefono=req.cliente_telefono,
        codigo_otp=otp_code,
        estado="PENDIENTE_OTP",
        fecha_creacion=datetime.utcnow(),
        fecha_expiracion=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return schemas.IniciarPagoResponse(
        transaccion_id=txn_id,
        monto=txn.monto,
        metodo=txn.metodo,
        estado="PENDIENTE_OTP",
        mensaje=f"Código de seguridad OTP enviado por SMS a {req.cliente_telefono} y al correo {req.cliente_email}",
        otp_simulado=otp_code,
        expira_en_segundos=300
    )

def validar_pago_otp(db: Session, req: schemas.ValidarOTPRequest) -> schemas.ValidarOTPResponse:
    txn = db.query(models.TransaccionPagoOTP).filter(
        models.TransaccionPagoOTP.transaccion_id == req.transaccion_id
    ).first()

    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transacción de pasarela no encontrada"
        )

    if txn.estado == "AUTORIZADO":
        return schemas.ValidarOTPResponse(
            transaccion_id=txn.transaccion_id,
            estado="AUTORIZADO",
            valido=True,
            mensaje="La transacción ya fue autorizada previamente.",
            token_autorizacion=f"AUTH-{txn.transaccion_id[8:]}",
            monto=txn.monto
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
            monto=txn.monto
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
            monto=txn.monto
        )

    if txn.codigo_otp != req.codigo_otp.strip():
        db.commit()
        return schemas.ValidarOTPResponse(
            transaccion_id=txn.transaccion_id,
            estado="PENDIENTE_OTP",
            valido=False,
            mensaje=f"Código OTP incorrecto. Intento {txn.intentos} de 3.",
            token_autorizacion=None,
            monto=txn.monto
        )

    # Éxito: Validado correctamente
    txn.estado = "AUTORIZADO"
    db.commit()
    token_auth = f"AUTH-SUCCESS-{uuid.uuid4().hex[:10].upper()}"

    return schemas.ValidarOTPResponse(
        transaccion_id=txn.transaccion_id,
        estado="AUTORIZADO",
        valido=True,
        mensaje="Código OTP verificado exitosamente. Pago procesado por la Pasarela Bancaria.",
        token_autorizacion=token_auth,
        monto=txn.monto
    )
