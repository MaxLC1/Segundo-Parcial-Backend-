from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from . import schemas, services

import stripe
from pydantic import BaseModel
import uuid

router = APIRouter(tags=["Ventas"])

stripe.api_key = "sk_test_dummy_key_replace_me"

class PaymentIntentRequest(BaseModel):
    amount: float
    currency: str = "usd"

@router.post("/create-payment-intent")
def create_payment_intent(request: PaymentIntentRequest):
    try:
        fake_client_secret = f"pi_mock_{int(request.amount*100)}_secret_simulado_por_sistema"
        return {"client_secret": fake_client_secret}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
def sincronizar_operaciones_offline(lote: schemas.SincronizacionLoteRequest, db: Session = Depends(get_db)):
    """
    Recibe un lote de ventas registradas offline desde la PWA o aplicación móvil.
    Verifica idempotencia (RNF05) mediante operacion_uuid, valida existencias de inventario (RNF04)
    y clasifica cada operación en CONFIRMADA o RECHAZADA_CONFLICTO.
    """
    return services.sincronizar_ventas_lote(db=db, lote=lote)

# ==============================================================================
# CAMBIOS DE PRENDAS DE VESTIR (Desafío IV - Req 7.2)
# ==============================================================================

@router.post("/cambios", response_model=schemas.CambioPrendaOut, status_code=status.HTTP_201_CREATED)
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

qr_sessions = {}

class QRCodeRequest(BaseModel):
    amount: float

@router.post("/generar-qr")
def generar_qr(request: QRCodeRequest):
    tx_id = str(uuid.uuid4())
    qr_sessions[tx_id] = "PENDING"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=PagoFashionStore:{tx_id}_Monto:{request.amount}"
    return {"tx_id": tx_id, "qr_url": qr_url, "status": "PENDING"}

@router.get("/estado-pago-qr/{tx_id}")
def verificar_estado_pago(tx_id: str):
    estado = qr_sessions.get(tx_id, "NOT_FOUND")
    return {"status": estado}

@router.post("/simular-pago-cliente/{tx_id}")
def simular_pago_cliente(tx_id: str):
    if tx_id in qr_sessions:
        qr_sessions[tx_id] = "COMPLETED"
        return {"message": "Pago simulado con éxito"}
    raise HTTPException(status_code=404, detail="Transacción no encontrada")
