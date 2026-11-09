"""Schemas de Bitácora para serialización."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BitacoraOut(BaseModel):
    id: int
    fecha: datetime
    usuario_id: Optional[int] = None
    usuario_email: Optional[str] = None
    usuario_nombre: Optional[str] = None
    rol: Optional[str] = None
    empresa_id: Optional[int] = None
    empresa_nombre: Optional[str] = None
    ip: Optional[str] = None
    accion: str
    modulo: str
    detalle: Optional[str] = None

    class Config:
        from_attributes = True

