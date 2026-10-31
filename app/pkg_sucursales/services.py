from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas
from app.pkg_saas.services import validar_puede_crear_sucursal

# -- CIUDADES --
def get_ciudades(db: Session):
    return db.query(models.Ciudad).all()

def create_ciudad(db: Session, ciudad: schemas.CiudadCreate):
    db_ciudad = models.Ciudad(nombre=ciudad.nombre)
    db.add(db_ciudad)
    db.commit()
    db.refresh(db_ciudad)
    return db_ciudad

# -- SUCURSALES --
def get_sucursales(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Sucursal)
    if empresa_id is not None:
        query = query.filter(models.Sucursal.empresa_id == empresa_id)
    return query.all()

def create_sucursal(db: Session, sucursal: schemas.SucursalCreate):
    # Validar límites de suscripción por plan del tenant (RNF01, Reglas de Negocio)
    if sucursal.empresa_id:
        validar_puede_crear_sucursal(db, sucursal.empresa_id)

    db_sucursal = models.Sucursal(**sucursal.model_dump())
    db.add(db_sucursal)
    db.commit()
    db.refresh(db_sucursal)
    return db_sucursal

def update_sucursal(db: Session, sucursal_id: int, data: schemas.SucursalUpdate):
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.id == sucursal_id).first()
    if not sucursal:
        return None
    
    if data.nombre is not None:
        sucursal.nombre = data.nombre
    if data.direccion is not None:
        sucursal.direccion = data.direccion
    if data.ciudad_id is not None:
        sucursal.ciudad_id = data.ciudad_id
    if data.empresa_id is not None:
        sucursal.empresa_id = data.empresa_id
        
    db.commit()
    db.refresh(sucursal)
    return sucursal

# -- INVENTARIOS --
def get_inventarios(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Inventario)
    if empresa_id is not None:
        query = query.join(models.Sucursal).filter(models.Sucursal.empresa_id == empresa_id)
    return query.all()

def create_inventario(db: Session, inventario: schemas.InventarioCreate):
    # Buscar si ya existe la combinación
    db_inv = db.query(models.Inventario).filter(
        models.Inventario.sucursal_id == inventario.sucursal_id,
        models.Inventario.producto_id == inventario.producto_id,
        models.Inventario.talla_id == inventario.talla_id,
        models.Inventario.color_id == inventario.color_id
    ).first()

    if db_inv:
        db_inv.cantidad += inventario.cantidad
        db.commit()
        db.refresh(db_inv)
        return db_inv
    
    db_inv = models.Inventario(**inventario.model_dump())
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)
    return db_inv

def update_inventario(db: Session, inventario_id: int, data: schemas.InventarioUpdate):
    inv = db.query(models.Inventario).filter(models.Inventario.id == inventario_id).first()
    if not inv:
        return None
    inv.cantidad = data.cantidad
    db.commit()
    db.refresh(inv)
    return inv
