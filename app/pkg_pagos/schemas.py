from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class IniciarPagoRequest(BaseModel):
    monto: float
    metodo: str = "Tarjeta" # Tarjeta, QR, Transferencia
    cliente_email: Optional[str] = "cliente@correo.com"
    cliente_telefono: Optional[str] = "+591 70012345"
    empresa_id: Optional[int] = 1

class IniciarPagoResponse(BaseModel):
    transaccion_id: str
    monto: float
    metodo: str
    estado: str
    mensaje: str
    otp_simulado: str # Se expone en el prototipo para que el usuario pueda probar el OTP fácilmente
    expira_en_segundos: int = 300

class ValidarOTPRequest(BaseModel):
    transaccion_id: str
    codigo_otp: str

class ValidarOTPResponse(BaseModel):
    transaccion_id: str
    estado: str
    valido: bool
    mensaje: str
    token_autorizacion: Optional[str] = None
    monto: float
