from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class CriteriosCupon(BaseModel):
    productos: list[int] = Field(default_factory=list)
    temporadas: list[int] = Field(default_factory=list)
    tallas: list[int] = Field(default_factory=list)
    categorias: list[int] = Field(default_factory=list)


class CuponCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    usuario_id: int | None = None
    tipo: Literal["MONTO", "PORCENTAJE"] = "MONTO"
    valor: float = Field(gt=0, allow_inf_nan=False)
    criterios: CriteriosCupon = Field(default_factory=CriteriosCupon)
    fecha_vencimiento: datetime
    max_usos: int = Field(default=1, gt=0, le=100000)

    @model_validator(mode="after")
    def valid(self):
        self.fecha_vencimiento = self.fecha_vencimiento.replace(tzinfo=None)
        if self.fecha_vencimiento <= datetime.utcnow():
            raise ValueError("El vencimiento debe ser futuro")
        if self.tipo == "PORCENTAJE" and self.valor > 100:
            raise ValueError("El porcentaje no puede superar 100")
        return self


class AvisoCreate(BaseModel):
    usuario_id: int | None = None
    titulo: str = Field(min_length=1, max_length=120)
    mensaje: str = Field(min_length=1, max_length=1000)


class TraspasoDetalle(BaseModel):
    producto_id: int
    talla_id: int
    color_id: int
    cantidad: int = Field(gt=0)


class TraspasoCreate(BaseModel):
    operacion_uuid: UUID
    origen_id: int
    destino_id: int
    detalles: list[TraspasoDetalle] = Field(min_length=1)
