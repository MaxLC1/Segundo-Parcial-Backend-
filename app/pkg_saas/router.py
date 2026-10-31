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

@router.post("/planes", response_model=schemas.PlanOut, status_code=status.HTTP_201_CREATED)
def crear_plan(plan: schemas.PlanCreate, db: Session = Depends(get_db)):
    """Crea un nuevo plan de suscripción."""
    return services.create_plan(db, plan)

@router.get("/empresas", response_model=List[schemas.EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    """Obtiene la lista de empresas registradas en la plataforma SaaS."""
    return services.get_empresas(db)

@router.post("/empresas", response_model=schemas.EmpresaOut, status_code=status.HTTP_201_CREATED)
def registrar_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    """Registra una nueva empresa contratante (Tenant) con su plan."""
    return services.create_empresa(db, empresa)

@router.get("/empresas/{empresa_id}", response_model=schemas.EmpresaOut)
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Obtiene detalles de una empresa específica."""
    emp = services.get_empresa_by_id(db, empresa_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return emp

@router.post("/suscripciones/asignar", response_model=schemas.SuscripcionOut)
def asignar_o_cambiar_plan(data: schemas.SuscripcionCreate, db: Session = Depends(get_db)):
    """Asigna o cambia el plan de suscripción de una empresa."""
    return services.asignar_plan(db, data)

@router.get("/empresas/{empresa_id}/limites", response_model=schemas.LimitesEmpresaOut)
def consultar_limites_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Verifica límites de sucursales, estado de suscripción y acceso a IA para una empresa."""
    return services.verificar_limites_empresa(db, empresa_id)
