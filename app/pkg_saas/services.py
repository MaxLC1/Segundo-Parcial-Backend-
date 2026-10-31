from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from typing import List, Optional

from . import models, schemas
from app.pkg_sucursales.models import Sucursal

def inicializar_planes_default(db: Session):
    """Crea los planes Básico y Profesional por defecto si no existen."""
    plan_basico = db.query(models.Plan).filter_by(nombre="Básico").first()
    if not plan_basico:
        plan_basico = models.Plan(
            nombre="Básico",
            descripcion="Plan para pequeños comercios y tiendas emergentes",
            precio_mensual=29.99,
            max_sucursales=2,
            permite_ia_generativa=False,
            permite_offline=True,
            permite_cambios_prendas=True,
            activo=True
        )
        db.add(plan_basico)
        db.commit()
        db.refresh(plan_basico)

    plan_pro = db.query(models.Plan).filter_by(nombre="Profesional").first()
    if not plan_pro:
        plan_pro = models.Plan(
            nombre="Profesional",
            descripcion="Plan integral con analítica avanzada, hasta 10 sucursales y reportes generativos con IA",
            precio_mensual=89.99,
            max_sucursales=10,
            permite_ia_generativa=True,
            permite_offline=True,
            permite_cambios_prendas=True,
            activo=True
        )
        db.add(plan_pro)
        db.commit()
        db.refresh(plan_pro)

    return plan_basico, plan_pro

def get_planes(db: Session) -> List[models.Plan]:
    inicializar_planes_default(db)
    return db.query(models.Plan).filter_by(activo=True).all()

def get_plan_by_id(db: Session, plan_id: int) -> Optional[models.Plan]:
    return db.query(models.Plan).filter_by(id=plan_id).first()

def create_plan(db: Session, plan_data: schemas.PlanCreate) -> models.Plan:
    db_plan = models.Plan(**plan_data.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

def get_empresas(db: Session) -> List[models.Empresa]:
    return db.query(models.Empresa).all()

def get_empresa_by_id(db: Session, empresa_id: int) -> Optional[models.Empresa]:
    return db.query(models.Empresa).filter_by(id=empresa_id).first()

def get_empresa_by_codigo(db: Session, codigo: str) -> Optional[models.Empresa]:
    return db.query(models.Empresa).filter_by(codigo=codigo).first()

def create_empresa(db: Session, data: schemas.EmpresaCreate) -> models.Empresa:
    existente = get_empresa_by_codigo(db, data.codigo)
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una empresa con código '{data.codigo}'")

    inicializar_planes_default(db)
    
    empresa = models.Empresa(
        nombre=data.nombre,
        codigo=data.codigo,
        nit_rut=data.nit_rut,
        telefono=data.telefono,
        email_contacto=data.email_contacto,
        direccion_fiscal=data.direccion_fiscal,
        logo_url=data.logo_url,
        activa=data.activa
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    plan_id = data.plan_id or 1
    plan = get_plan_by_id(db, plan_id)
    if not plan:
        plan = db.query(models.Plan).first()

    # Asignar suscripción inicial por 1 año
    suscripcion = models.Suscripcion(
        empresa_id=empresa.id,
        plan_id=plan.id,
        fecha_inicio=datetime.utcnow(),
        fecha_vencimiento=datetime.utcnow() + timedelta(days=365),
        estado="Activa",
        auto_renovacion=True,
        notas="Suscripción inicial al crear empresa"
    )
    db.add(suscripcion)
    db.commit()
    db.refresh(empresa)
    return empresa

def asignar_plan(db: Session, data: schemas.SuscripcionCreate) -> models.Suscripcion:
    empresa = get_empresa_by_id(db, data.empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    plan = get_plan_by_id(db, data.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    # Marcar suscripciones anteriores como renovadas/canceladas
    db.query(models.Suscripcion).filter_by(empresa_id=empresa.id, estado="Activa").update({"estado": "Renovada"})

    nueva = models.Suscripcion(
        empresa_id=empresa.id,
        plan_id=plan.id,
        fecha_inicio=datetime.utcnow(),
        fecha_vencimiento=datetime.utcnow() + timedelta(days=data.dias_duracion),
        estado="Activa",
        auto_renovacion=True,
        notas=data.notas or f"Cambio/Asignación de plan a {plan.nombre}"
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def get_suscripcion_activa(db: Session, empresa_id: int) -> Optional[models.Suscripcion]:
    return db.query(models.Suscripcion).filter(
        models.Suscripcion.empresa_id == empresa_id,
        models.Suscripcion.estado == "Activa"
    ).order_by(models.Suscripcion.id.desc()).first()

def verificar_limites_empresa(db: Session, empresa_id: int) -> schemas.LimitesEmpresaOut:
    empresa = get_empresa_by_id(db, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    suscripcion = get_suscripcion_activa(db, empresa_id)
    if not suscripcion:
        # Default a Básico
        plan = db.query(models.Plan).filter_by(nombre="Básico").first()
        plan_nombre = plan.nombre if plan else "Básico"
        max_sucursales = plan.max_sucursales if plan else 2
        permite_ia = False
        permite_offline = True
        activa = False
        vencimiento = None
    else:
        plan = suscripcion.plan
        plan_nombre = plan.nombre
        max_sucursales = plan.max_sucursales
        permite_ia = plan.permite_ia_generativa
        permite_offline = plan.permite_offline
        activa = (suscripcion.estado == "Activa" and suscripcion.fecha_vencimiento >= datetime.utcnow())
        vencimiento = suscripcion.fecha_vencimiento

    sucursales_activas = db.query(Sucursal).filter_by(empresa_id=empresa_id).count()

    return schemas.LimitesEmpresaOut(
        empresa_id=empresa.id,
        empresa_nombre=empresa.nombre,
        plan_nombre=plan_nombre,
        max_sucursales=max_sucursales,
        sucursales_activas=sucursales_activas,
        permite_ia_generativa=permite_ia,
        permite_offline=permite_offline,
        suscripcion_activa=activa,
        fecha_vencimiento=vencimiento
    )

def validar_puede_crear_sucursal(db: Session, empresa_id: int):
    limites = verificar_limites_empresa(db, empresa_id)
    if not limites.suscripcion_activa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"La suscripción de la empresa '{limites.empresa_nombre}' está vencida o inactiva."
        )
    if limites.sucursales_activas >= limites.max_sucursales:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ha alcanzado el límite de {limites.max_sucursales} sucursales permitidas por su plan ({limites.plan_nombre}). Actualice a Plan Profesional para agregar más sucursales."
        )

def validar_permiso_ia(db: Session, empresa_id: int):
    limites = verificar_limites_empresa(db, empresa_id)
    if not limites.permite_ia_generativa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Los reportes generativos con IA no están incluidos en el plan actual ({limites.plan_nombre}). Actualice a Plan Profesional para acceder a esta función."
        )
