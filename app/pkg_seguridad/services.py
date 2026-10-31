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
    # Encriptamos la contraseña
    hashed_password = security.get_password_hash(usuario.password)
    
    # Preparamos el objeto de SQLAlchemy
    db_user = models.Usuario(
        nombre_completo=usuario.nombre_completo,
        email=usuario.email,
        hashed_password=hashed_password,
        rol_id=usuario.rol_id,
        empresa_id=usuario.empresa_id
    )
    
    # Guardamos en base de datos
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_usuario(db: Session, email: str, password: str):
    usuario = get_usuario_by_email(db, email)
    if not usuario:
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
