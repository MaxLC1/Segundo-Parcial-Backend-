from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas
from app.core import security


def get_usuario_by_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()


def get_usuarios(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Usuario)
    if empresa_id is not None:
        query = query.filter(models.Usuario.empresa_id == empresa_id)
    return query.all()


def get_roles(db: Session):
    return db.query(models.Rol).all()


def create_rol(db: Session, rol: schemas.RolCreate):
    db_rol = models.Rol(**rol.model_dump())
    db.add(db_rol)
    db.commit()
    db.refresh(db_rol)
    return db_rol


def create_usuario(db: Session, usuario: schemas.UsuarioCreate):
    from fastapi import HTTPException
    from app.pkg_saas.models import Empresa

    actor = db.info.get("actor")
    role = db.info.get("role", "Cliente")
    if not actor:
        cliente = db.query(models.Rol).filter_by(nombre="Cliente").first()
        if not cliente:
            raise HTTPException(409, "Configure primero el rol Cliente")
        usuario.rol_id = cliente.id
        if (
            not usuario.empresa_id
            or not db.query(Empresa)
            .filter_by(id=usuario.empresa_id, activa=True)
            .first()
        ):
            raise HTTPException(400, "Seleccione una empresa activa")
    elif role not in {"Administrador", "AdministradorPlataforma"}:
        raise HTTPException(403, "No autorizado")
    elif role != "AdministradorPlataforma":
        usuario.empresa_id = actor.empresa_id
        selected_role = db.query(models.Rol).filter_by(id=usuario.rol_id).first()
        if not selected_role or selected_role.nombre == "AdministradorPlataforma":
            raise HTTPException(403, "Rol no permitido")
    # Encriptamos la contraseña
    hashed_password = security.get_password_hash(usuario.password)

    # Preparamos el objeto de SQLAlchemy
    db_user = models.Usuario(
        nombre_completo=usuario.nombre_completo,
        email=usuario.email,
        hashed_password=hashed_password,
        rol_id=usuario.rol_id,
        empresa_id=usuario.empresa_id,
    )

    # Guardamos en base de datos
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_usuario(db: Session, email: str, password: str):
    usuario = get_usuario_by_email(db, email)
    if not usuario or not usuario.is_active:
        return False
    if not security.verify_password(password, usuario.hashed_password):
        return False
    return usuario


def update_password(db: Session, user_id: int, new_password: str):
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        return None
    user.hashed_password = security.get_password_hash(new_password)
    db.commit()
    return user


def update_usuario(db: Session, user_id: int, data: schemas.UsuarioUpdate):
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        return None

    from fastapi import HTTPException

    if db.info.get("role") != "AdministradorPlataforma":
        if data.empresa_id not in (None, db.info.get("tenant_id")):
            raise HTTPException(403, "No puede cambiar la empresa")
        if data.rol_id:
            role = db.query(models.Rol).filter_by(id=data.rol_id).first()
            if not role or role.nombre == "AdministradorPlataforma":
                raise HTTPException(403, "Rol no permitido")
    if data.nombre_completo is not None:
        user.nombre_completo = data.nombre_completo
    if data.email is not None:
        user.email = data.email
    if data.rol_id is not None:
        user.rol_id = data.rol_id
    if data.empresa_id is not None:
        user.empresa_id = data.empresa_id
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password:
        user.hashed_password = security.get_password_hash(data.password)

    db.commit()
    db.refresh(user)
    return user
