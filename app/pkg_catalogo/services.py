from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas

# -- PRODUCTOS --
def get_productos(db: Session, skip: int = 0, limit: int = 100, empresa_id: Optional[int] = None):
    query = db.query(models.Producto)
    if empresa_id is not None:
        query = query.filter(models.Producto.empresa_id == empresa_id)
    return query.offset(skip).limit(limit).all()

def create_producto(db: Session, producto: schemas.ProductoCreate):
    db_producto = models.Producto(**producto.model_dump())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

def update_producto(db: Session, producto_id: int, producto_data: schemas.ProductoCreate):
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        for key, value in producto_data.model_dump().items():
            setattr(db_producto, key, value)
        db.commit()
        db.refresh(db_producto)
    return db_producto

# -- CATEGORIAS --
def get_categorias(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Categoria)
    if empresa_id is not None:
        query = query.filter((models.Categoria.empresa_id == empresa_id) | (models.Categoria.empresa_id == None))
    return query.all()

def create_categoria(db: Session, categoria: schemas.CategoriaCreate):
    db_categoria = models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def update_categoria(db: Session, categoria_id: int, categoria_data: schemas.CategoriaCreate):
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if db_categoria:
        for key, value in categoria_data.model_dump().items():
            setattr(db_categoria, key, value)
        db.commit()
        db.refresh(db_categoria)
    return db_categoria

def delete_categoria(db: Session, categoria_id: int):
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if db_categoria:
        try:
            db.delete(db_categoria)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    return False

# -- TALLAS --
def get_tallas(db: Session):
    return db.query(models.Talla).all()

def create_talla(db: Session, talla: schemas.TallaCreate):
    db_talla = models.Talla(nombre=talla.nombre)
    db.add(db_talla)
    db.commit()
    db.refresh(db_talla)
    return db_talla

# -- COLORES --
def get_colores(db: Session):
    return db.query(models.Color).all()

def create_color(db: Session, color: schemas.ColorCreate):
    db_color = models.Color(nombre=color.nombre, codigo_hex=color.codigo_hex)
    db.add(db_color)
    db.commit()
    db.refresh(db_color)
    return db_color

# -- COLECCIONES --
def get_colecciones(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Coleccion)
    if empresa_id is not None:
        query = query.filter((models.Coleccion.empresa_id == empresa_id) | (models.Coleccion.empresa_id == None))
    return query.all()

def create_coleccion(db: Session, coleccion: schemas.ColeccionCreate):
    db_coleccion = models.Coleccion(**coleccion.model_dump())
    db.add(db_coleccion)
    db.commit()
    db.refresh(db_coleccion)
    return db_coleccion

def update_coleccion(db: Session, coleccion_id: int, coleccion_data: schemas.ColeccionUpdate):
    db_coleccion = db.query(models.Coleccion).filter(models.Coleccion.id == coleccion_id).first()
    if db_coleccion:
        for key, value in coleccion_data.model_dump().items():
            setattr(db_coleccion, key, value)
        db.commit()
        db.refresh(db_coleccion)
    return db_coleccion

def delete_coleccion(db: Session, coleccion_id: int):
    db_coleccion = db.query(models.Coleccion).filter(models.Coleccion.id == coleccion_id).first()
    if db_coleccion:
        try:
            db.delete(db_coleccion)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    return False

# -- PROVEEDORES --
def get_proveedores(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.Proveedor)
    if empresa_id is not None:
        query = query.filter((models.Proveedor.empresa_id == empresa_id) | (models.Proveedor.empresa_id == None))
    return query.all()

def create_proveedor(db: Session, proveedor: schemas.ProveedorCreate):
    db_proveedor = models.Proveedor(**proveedor.model_dump())
    db.add(db_proveedor)
    db.commit()
    db.refresh(db_proveedor)
    return db_proveedor

def update_proveedor(db: Session, proveedor_id: int, proveedor_data: schemas.ProveedorUpdate):
    db_proveedor = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id).first()
    if db_proveedor:
        for key, value in proveedor_data.model_dump().items():
            setattr(db_proveedor, key, value)
        db.commit()
        db.refresh(db_proveedor)
    return db_proveedor

# -- OFERTAS & DESCUENTOS (POR MAYOR, TEMPORADAS PASADAS Y CAPITAL DE EMPLEADO) --
def get_reglas_ofertas(db: Session, empresa_id: Optional[int] = None):
    query = db.query(models.ReglaOferta)
    if empresa_id is not None:
        query = query.filter((models.ReglaOferta.empresa_id == empresa_id) | (models.ReglaOferta.empresa_id == None))
    return query.all()

def create_regla_oferta(db: Session, regla: schemas.ReglaOfertaCreate):
    db_regla = models.ReglaOferta(**regla.model_dump())
    db.add(db_regla)
    db.commit()
    db.refresh(db_regla)
    return db_regla

def update_regla_oferta(db: Session, regla_id: int, regla_data: schemas.ReglaOfertaUpdate):
    db_regla = db.query(models.ReglaOferta).filter(models.ReglaOferta.id == regla_id).first()
    if db_regla:
        for key, value in regla_data.model_dump(exclude_unset=True).items():
            setattr(db_regla, key, value)
        db.commit()
        db.refresh(db_regla)
    return db_regla

def delete_regla_oferta(db: Session, regla_id: int):
    db_regla = db.query(models.ReglaOferta).filter(models.ReglaOferta.id == regla_id).first()
    if db_regla:
        db.delete(db_regla)
        db.commit()
        return True
    return False

def get_productos_con_ofertas(db: Session, empresa_id: Optional[int] = None, es_empleado: bool = False):
    """
    Calcula los precios de oferta y métricas comerciales:
    - Descuento por temporadas pasadas: 1 temporada = 30%, 2 temporadas = 60%
    - Descuento promocional manual directo
    - Métricas de empleado: costo real, recuperación de capital, pérdida asumida
    """
    productos = get_productos(db, skip=0, limit=200, empresa_id=empresa_id)
    reglas = get_reglas_ofertas(db, empresa_id=empresa_id)
    
    # Mapeo de reglas por temporada
    pct_temp_1 = 30.0
    pct_temp_2 = 60.0
    for r in reglas:
        if r.activa and r.tipo == "TEMPORADA_PASADA":
            if r.antiguedad_temporadas == 1:
                pct_temp_1 = r.descuento_porcentaje
            elif r.antiguedad_temporadas >= 2:
                pct_temp_2 = r.descuento_porcentaje
                
    resultados = []
    for p in productos:
        # Calcular porcentaje de descuento
        descuento_pct = p.descuento_porcentaje or 0.0
        if p.antiguedad_temporadas == 1:
            descuento_pct = max(descuento_pct, pct_temp_1)
        elif p.antiguedad_temporadas and p.antiguedad_temporadas >= 2:
            descuento_pct = max(descuento_pct, pct_temp_2)
            
        precio_original = float(p.precio)
        precio_oferta = round(precio_original * (1.0 - (descuento_pct / 100.0)), 2)
        ahorro = round(precio_original - precio_oferta, 2)
        
        # Métricas de empleado
        costo_real = float(p.costo_adquisicion) if p.costo_adquisicion and p.costo_adquisicion > 0 else round(precio_original * 0.45, 2)
        margen = round(precio_oferta - costo_real, 2)
        recuperacion_pct = round((precio_oferta / costo_real) * 100.0, 1) if costo_real > 0 else 100.0
        
        if margen > 0:
            estado_capital = "GANANCIA"
        elif margen == 0:
            estado_capital = "RECUPERACION_EXACTA"
        else:
            estado_capital = "PERDIDA_ASUMIDA_LIQUIDACION"
            
        # Convertir a esquema ProductoOut enriquecido
        prod_dict = {
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "precio": precio_original,
            "costo_adquisicion": costo_real if es_empleado else 0.0,
            "antiguedad_temporadas": p.antiguedad_temporadas or 0,
            "descuento_porcentaje": p.descuento_porcentaje or 0.0,
            "categoria_id": p.categoria_id,
            "modelo_3d_url": p.modelo_3d_url,
            "imagen_url": p.imagen_url,
            "temporada_id": p.temporada_id,
            "coleccion_id": p.coleccion_id,
            "proveedor_id": p.proveedor_id,
            "empresa_id": p.empresa_id,
            "precio_oferta": precio_oferta,
            "descuento_aplicado_pct": descuento_pct,
            "ahorro_monto": ahorro,
            "categoria": p.categoria,
            "temporada": p.temporada,
            "coleccion": p.coleccion,
            "proveedor": p.proveedor
        }
        
        if es_empleado:
            prod_dict.update({
                "costo_real": costo_real,
                "margen_recuperacion_monto": margen,
                "recuperacion_capital_pct": recuperacion_pct,
                "estado_capital": estado_capital
            })
            
        resultados.append(prod_dict)
        
    return resultados

