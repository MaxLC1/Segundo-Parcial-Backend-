from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from . import schemas, services

router = APIRouter(tags=["Catálogo"])

@router.get("/categorias", response_model=List[schemas.CategoriaOut])
def read_categorias(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene la lista de todas las categorías de ropa."""
    return services.get_categorias(db, empresa_id=empresa_id)

@router.post("/categorias", response_model=schemas.CategoriaOut, status_code=status.HTTP_201_CREATED)
def create_categoria(categoria: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    """Crea una nueva categoría."""
    return services.create_categoria(db=db, categoria=categoria)

@router.put("/categorias/{categoria_id}", response_model=schemas.CategoriaOut)
def update_categoria(categoria_id: int, categoria: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    """Actualiza una categoría existente."""
    db_cat = services.update_categoria(db=db, categoria_id=categoria_id, categoria_data=categoria)
    if db_cat is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return db_cat

@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categoria(categoria_id: int, db: Session = Depends(get_db)):
    """Elimina una categoría."""
    success = services.delete_categoria(db=db, categoria_id=categoria_id)
    if not success:
        raise HTTPException(status_code=404, detail="Categoría no encontrada o no se puede eliminar por integridad de datos")
    return None

@router.get("/productos", response_model=List[schemas.ProductoOut])
def read_productos(skip: int = 0, limit: int = 100, empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene el catálogo de productos con paginación y filtro opcional por empresa."""
    return services.get_productos(db, skip=skip, limit=limit, empresa_id=empresa_id)

@router.post("/productos", response_model=schemas.ProductoOut, status_code=status.HTTP_201_CREATED)
def create_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db)):
    """Crea un nuevo producto en el catálogo."""
    return services.create_producto(db=db, producto=producto)

@router.put("/productos/{producto_id}", response_model=schemas.ProductoOut)
def update_producto(producto_id: int, producto: schemas.ProductoCreate, db: Session = Depends(get_db)):
    """Actualiza un producto existente en el catálogo."""
    db_producto = services.update_producto(db=db, producto_id=producto_id, producto_data=producto)
    if db_producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

@router.get("/tallas", response_model=List[schemas.TallaOut])
def read_tallas(db: Session = Depends(get_db)):
    """Obtiene la lista de tallas de ropa."""
    return services.get_tallas(db)

@router.post("/tallas", response_model=schemas.TallaOut, status_code=status.HTTP_201_CREATED)
def create_talla(talla: schemas.TallaCreate, db: Session = Depends(get_db)):
    """Crea una nueva talla de ropa."""
    return services.create_talla(db=db, talla=talla)

@router.get("/colores", response_model=List[schemas.ColorOut])
def read_colores(db: Session = Depends(get_db)):
    """Obtiene la lista de colores de ropa."""
    return services.get_colores(db)

@router.post("/colores", response_model=schemas.ColorOut, status_code=status.HTTP_201_CREATED)
def create_color(color: schemas.ColorCreate, db: Session = Depends(get_db)):
    """Crea un nuevo color."""
    return services.create_color(db=db, color=color)

@router.get("/colecciones", response_model=List[schemas.ColeccionOut])
def read_colecciones(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene la lista de colecciones."""
    return services.get_colecciones(db, empresa_id=empresa_id)

@router.post("/colecciones", response_model=schemas.ColeccionOut, status_code=status.HTTP_201_CREATED)
def create_coleccion(coleccion: schemas.ColeccionCreate, db: Session = Depends(get_db)):
    """Crea una nueva colección."""
    return services.create_coleccion(db=db, coleccion=coleccion)

@router.put("/colecciones/{coleccion_id}", response_model=schemas.ColeccionOut)
def update_coleccion(coleccion_id: int, coleccion: schemas.ColeccionUpdate, db: Session = Depends(get_db)):
    """Actualiza una colección existente."""
    col = services.update_coleccion(db, coleccion_id, coleccion)
    if not col:
        raise HTTPException(status_code=404, detail="Colección no encontrada")
    return col

@router.delete("/colecciones/{coleccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coleccion(coleccion_id: int, db: Session = Depends(get_db)):
    """Elimina una colección."""
    success = services.delete_coleccion(db, coleccion_id)
    if not success:
        raise HTTPException(status_code=404, detail="Colección no encontrada o no se puede eliminar")
    return None

@router.get("/proveedores", response_model=List[schemas.ProveedorOut])
def read_proveedores(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Obtiene la lista de proveedores."""
    return services.get_proveedores(db, empresa_id=empresa_id)

@router.post("/proveedores", response_model=schemas.ProveedorOut, status_code=status.HTTP_201_CREATED)
def create_proveedor(proveedor: schemas.ProveedorCreate, db: Session = Depends(get_db)):
    """Crea un nuevo proveedor."""
    return services.create_proveedor(db=db, proveedor=proveedor)

@router.put("/proveedores/{proveedor_id}", response_model=schemas.ProveedorOut)
def update_proveedor(proveedor_id: int, proveedor: schemas.ProveedorUpdate, db: Session = Depends(get_db)):
    """Actualiza un proveedor existente."""
    prov = services.update_proveedor(db, proveedor_id, proveedor)
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return prov

# -- ENDPOINTS DE OFERTAS Y DESCUENTOS --
@router.get("/productos-ofertas", response_model=List[schemas.ProductoOut])
def read_productos_con_ofertas(empresa_id: Optional[int] = None, es_empleado: bool = False, db: Session = Depends(get_db)):
    """
    Obtiene los productos con cálculo de ofertas y descuentos:
    - Precios de oferta aplicados (temporadas pasadas 30%/60%, descuentos directos)
    - Si es_empleado=True incluye métricas de auditoría de capital (costo, margen y estado de capital)
    """
    return services.get_productos_con_ofertas(db, empresa_id=empresa_id, es_empleado=es_empleado)

@router.get("/reglas-ofertas", response_model=List[schemas.ReglaOfertaOut])
def read_reglas_ofertas(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Lista las reglas de ofertas activas (mayoreo, liquidaciones)."""
    return services.get_reglas_ofertas(db, empresa_id=empresa_id)

@router.post("/reglas-ofertas", response_model=schemas.ReglaOfertaOut, status_code=status.HTTP_201_CREATED)
def create_regla_oferta(regla: schemas.ReglaOfertaCreate, db: Session = Depends(get_db)):
    """Crea una regla de oferta para una empresa/tenant."""
    return services.create_regla_oferta(db=db, regla=regla)

@router.put("/reglas-ofertas/{regla_id}", response_model=schemas.ReglaOfertaOut)
def update_regla_oferta(regla_id: int, regla: schemas.ReglaOfertaUpdate, db: Session = Depends(get_db)):
    """Actualiza una regla de oferta."""
    r = services.update_regla_oferta(db=db, regla_id=regla_id, regla_data=regla)
    if not r:
        raise HTTPException(status_code=404, detail="Regla de oferta no encontrada")
    return r

@router.delete("/reglas-ofertas/{regla_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_regla_oferta(regla_id: int, db: Session = Depends(get_db)):
    """Elimina una regla de oferta."""
    success = services.delete_regla_oferta(db=db, regla_id=regla_id)
    if not success:
        raise HTTPException(status_code=404, detail="Regla de oferta no encontrada")
    return None

