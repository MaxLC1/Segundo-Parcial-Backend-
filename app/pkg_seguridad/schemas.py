from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re

# -- ROLES --
class RolBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class RolCreate(RolBase):
    pass

class RolOut(RolBase):
    id: int
    class Config:
        from_attributes = True

# -- USUARIOS --
class UsuarioBase(BaseModel):
    nombre_completo: str
    email: EmailStr
    is_active: bool = True
    rol_id: Optional[int] = None
    empresa_id: Optional[int] = None # Multitenant

class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    rol_id: Optional[int] = None
    empresa_id: Optional[int] = None
    password: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validar_password_fuerte(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[^a-zA-Z0-9]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial')
        return v

class UsuarioCreate(UsuarioBase):
    password: str  # Lo recibimos en texto plano, pero se guardará encriptado

    @field_validator('password')
    @classmethod
    def validar_password_fuerte(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[^a-zA-Z0-9]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial')
        return v

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class UsuarioOut(UsuarioBase):
    id: int
    rol: Optional[RolOut] = None

    class Config:
        from_attributes = True

# -- TOKENS --
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: Optional[int] = None
    email: Optional[str] = None
    rol: Optional[str] = None
    nombre: Optional[str] = None
    empresa_id: Optional[int] = None

class ChangePasswordRequest(BaseModel):
    user_id: int
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validar_password_fuerte(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[^a-zA-Z0-9]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial')
        return v
