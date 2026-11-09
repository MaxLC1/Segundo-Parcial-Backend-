from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from . import schemas, services

router = APIRouter(tags=["SaaS y Multitenant"])


@router.get("/planes", response_model=List[schemas.PlanOut])
def listar_planes(db: Session = Depends(get_db)):
    """Obtiene los planes de suscripción disponibles (Básico, Profesional)."""
    return services.get_planes(db)


@router.post(
    "/planes", response_model=schemas.PlanOut, status_code=status.HTTP_201_CREATED
)
def crear_plan(plan: schemas.PlanCreate, db: Session = Depends(get_db)):
    """Crea un nuevo plan de suscripción."""
    return services.create_plan(db, plan)


@router.get("/empresas", response_model=List[schemas.EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    """Obtiene la lista de empresas registradas en la plataforma SaaS."""
    return services.get_empresas(db)


@router.post(
    "/empresas", response_model=schemas.EmpresaOut, status_code=status.HTTP_201_CREATED
)
def registrar_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    """Registra una nueva empresa contratante (Tenant) con su plan."""
    from app.pkg_bitacora.services import registrar_desde_request
    nueva = services.create_empresa(db, empresa)
    try:
        registrar_desde_request(
            db=db,
            accion="CREAR_EMPRESA",
            modulo="SaaS",
            detalle=f"Se creó la empresa '{nueva.nombre}' (código: {nueva.codigo})",
        )
    except Exception:
        pass
    return nueva


@router.get("/empresas/{empresa_id}", response_model=schemas.EmpresaOut)
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Obtiene detalles de una empresa específica."""
    emp = services.get_empresa_by_id(db, empresa_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return emp


@router.post("/suscripciones/asignar", response_model=schemas.SuscripcionOut)
def asignar_o_cambiar_plan(
    data: schemas.SuscripcionCreate, db: Session = Depends(get_db)
):
    """Asigna o cambia el plan de suscripción de una empresa."""
    from app.pkg_bitacora.services import registrar_desde_request
    suscripcion = services.asignar_plan(db, data)
    try:
        registrar_desde_request(
            db=db,
            accion="CAMBIAR_PLAN_SUSCRIPCION",
            modulo="SaaS",
            detalle=f"Se asignó plan ID {data.plan_id} a empresa ID {data.empresa_id} por {data.dias_duracion} días",
        )
    except Exception:
        pass
    return suscripcion


@router.get("/empresas/{empresa_id}/limites", response_model=schemas.LimitesEmpresaOut)
def consultar_limites_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Verifica límites de sucursales, estado de suscripción y acceso a IA para una empresa."""
    return services.verificar_limites_empresa(db, empresa_id)


@router.put("/empresas/{empresa_id}", response_model=schemas.EmpresaOut)
def actualizar_empresa(
    empresa_id: int, data: schemas.EmpresaUpdate, db: Session = Depends(get_db)
):
    from app.pkg_bitacora.services import registrar_desde_request
    empresa = services.get_empresa_by_id(db, empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(empresa, key, value)
    db.commit()
    db.refresh(empresa)
    try:
        registrar_desde_request(
            db=db,
            accion="ACTUALIZAR_EMPRESA",
            modulo="SaaS",
            detalle=f"Actualización empresa ID {empresa_id}: {'Activa' if empresa.activa else 'Desactivada'}",
        )
    except Exception:
        pass
    return empresa
