from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional

from app.core.database import get_db
from app.core import security
from . import schemas, services

router = APIRouter(tags=["Seguridad"])


@router.get("/usuarios", response_model=List[schemas.UsuarioOut])
def get_all_usuarios(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene la lista de usuarios, opcionalmente filtrada por empresa/tenant."""
    return services.get_usuarios(db, empresa_id=empresa_id)


@router.post(
    "/register", response_model=schemas.UsuarioOut, status_code=status.HTTP_201_CREATED
)
def register(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario en la plataforma."""
    db_user = services.get_usuario_by_email(db, email=usuario.email)
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    return services.create_usuario(db=db, usuario=usuario)


@router.put("/usuarios/{user_id}", response_model=schemas.UsuarioOut)
def update_usuario(
    user_id: int, data: schemas.UsuarioUpdate, db: Session = Depends(get_db)
):
    """Actualiza la información de un usuario existente."""
    user = services.update_usuario(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


@router.get("/roles", response_model=List[schemas.RolOut])
def read_roles(db: Session = Depends(get_db)):
    """Obtiene los roles del sistema."""
    return services.get_roles(db)


@router.post(
    "/roles", response_model=schemas.RolOut, status_code=status.HTTP_201_CREATED
)
def add_rol(rol: schemas.RolCreate, db: Session = Depends(get_db)):
    """Añade un nuevo rol (Admin, Vendedor, etc)."""
    if db.info.get("role") != "AdministradorPlataforma":
        raise HTTPException(403, "Solo el administrador de plataforma gestiona roles")
    return services.create_rol(db=db, rol=rol)


@router.post("/login", response_model=schemas.Token)
def login(usuario: schemas.UsuarioLogin, request: Request, db: Session = Depends(get_db)):
    """Inicia sesión y devuelve un Token JWT con contexto de usuario y tenant."""
    from app.pkg_bitacora.services import registrar_evento
    ip = request.client.host if request.client else "127.0.0.1"
    user = services.authenticate_usuario(db, usuario.email, usuario.password)
    if not user:
        try:
            registrar_evento(
                db=db,
                accion="LOGIN_FALLIDO",
                modulo="Seguridad",
                detalle=f"Intento fallido con email: {usuario.email}",
                ip=ip,
                usuario_email=usuario.email,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Configurar expiración y crear token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    rol_nombre = user.rol.nombre if user.rol else "Cliente"
    empresa_nom = user.empresa.nombre if user.empresa else "Plataforma"

    try:
        registrar_evento(
            db=db,
            accion="LOGIN_EXITOSO",
            modulo="Seguridad",
            detalle=f"Inicio de sesión exitoso como {rol_nombre}",
            ip=ip,
            usuario_id=user.id,
            usuario_email=user.email,
            usuario_nombre=user.nombre_completo,
            rol=rol_nombre,
            empresa_id=user.empresa_id,
            empresa_nombre=empresa_nom,
        )
    except Exception:
        pass

    # Inyectamos datos en el payload
    payload = {
        "sub": user.email,
        "id": user.id,
        "rol": rol_nombre,
        "nombre": user.nombre_completo,
        "empresa_id": user.empresa_id,
        "empresa_nombre": empresa_nom,
    }
    access_token = security.create_access_token(
        data=payload, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "rol": rol_nombre,
        "nombre": user.nombre_completo,
        "empresa_id": user.empresa_id,
        "empresa_nombre": empresa_nom,
    }


@router.post("/change-password")
def change_password(data: schemas.ChangePasswordRequest, db: Session = Depends(get_db)):
    """Cambia la contraseña de un usuario."""
    actor = db.info.get("actor")
    if not actor or actor.id != data.user_id:
        raise HTTPException(403, "Solo puede cambiar su propia contraseña")
    user = services.update_password(db, actor.id, data.new_password)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"message": "Contraseña actualizada exitosamente"}
