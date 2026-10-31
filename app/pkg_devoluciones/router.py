from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.pkg_seguridad.models import Usuario
from . import schemas, services

router = APIRouter(tags=["Devoluciones y Notas de Devolución"], prefix="/devoluciones")

@router.get("/", response_model=List[schemas.DevolucionOut])
def list_devoluciones(db: Session = Depends(get_db)):
    return services.get_devoluciones(db)

@router.post("/", response_model=schemas.DevolucionOut, status_code=status.HTTP_201_CREATED)
def create_devolucion(devolucion: schemas.DevolucionCreate, db: Session = Depends(get_db)):
    return services.create_devolucion(db, devolucion)

@router.put("/{dev_id}/estado", response_model=schemas.DevolucionOut)
def update_devolucion_estado(dev_id: int, payload: schemas.DevolucionUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.rol.nombre not in ["Administrador", "Vendedor", "Encargado"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    return services.update_estado(db, dev_id, payload.estado)

# -- ENDPOINTS DE NOTAS DE DEVOLUCIÓN --
@router.get("/notas", response_model=List[schemas.NotaDevolucionOut])
def listar_notas_devolucion(empresa_id: Optional[int] = None, estado: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Obtiene las notas de devolución recopiladas para el Administrador.
    Permite filtrar por estado: 'EN_MARCHA' o 'COMPLETADA'.
    """
    return services.get_notas_devolucion(db, empresa_id=empresa_id, estado=estado)

@router.get("/mis-notas-activas", response_model=List[schemas.NotaDevolucionOut])
def listar_mis_notas_activas(usuario_id: int = 2, db: Session = Depends(get_db)):
    """
    Obtiene únicamente las notas activas para el cliente (para mostrar en pantalla al delivery).
    Al completarse la devolución, la nota se elimina de esta vista para el cliente.
    """
    return services.get_mis_notas_activas_cliente(db, usuario_id=usuario_id)

@router.post("/crear-nota", response_model=schemas.NotaDevolucionOut, status_code=status.HTTP_201_CREATED)
def crear_nota_devolucion(req: schemas.NotaDevolucionCreate, db: Session = Depends(get_db)):
    """
    Crea una Nota de Devolución digital.
    - Calcula la diferencia de precio (si sube de precio el cliente debe pagar la diferencia; si baja de precio aplica política de tienda / cupones).
    - Genera el código único NDEV para mostrar al repartidor de delivery.
    """
    return services.crear_nota_devolucion(db=db, req=req)

@router.put("/notas/{nota_id}/completar", response_model=schemas.NotaDevolucionOut)
def completar_nota(nota_id: int, req: schemas.CompletarNotaRequest, db: Session = Depends(get_db)):
    """
    El delivery o admin marca la devolución como COMPLETADA.
    Se elimina de la pestaña activa del cliente y se recopila en el histórico del administrador.
    """
    return services.completar_nota_devolucion(db=db, nota_id=nota_id, req=req)

# -- POLÍTICAS DE LA EMPRESA --
@router.get("/politica/{empresa_id}", response_model=schemas.PoliticaDevolucionOut)
def obtener_politica(empresa_id: int, db: Session = Depends(get_db)):
    """Obtiene la política de devoluciones y cambios configurada para la empresa."""
    return services.get_politica_empresa(db=db, empresa_id=empresa_id)

@router.put("/politica/{empresa_id}", response_model=schemas.PoliticaDevolucionOut)
def actualizar_politica(empresa_id: int, data: schemas.PoliticaDevolucionCreate, db: Session = Depends(get_db)):
    """Configura la política de la empresa (cupones de crédito, reembolso parcial, etc.)."""
    return services.update_politica_empresa(db=db, empresa_id=empresa_id, data=data)

