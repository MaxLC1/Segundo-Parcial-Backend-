import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import SessionLocal
from app.pkg_catalogo.models import Talla

TALLAS = [
    "XS",
    "S",
    "M",  # Puede que ya exista, el script verificará
    "L",
    "XL",
    "XXL",
    "36",
    "38",
    "40",
    "42",
    "44"
]

def seed_tallas():
    db = SessionLocal()
    try:
        agregados = 0
        for nombre_talla in TALLAS:
            existe = db.query(Talla).filter(Talla.nombre.ilike(nombre_talla)).first()
            if not existe:
                nueva_talla = Talla(nombre=nombre_talla)
                db.add(nueva_talla)
                agregados += 1
        
        db.commit()
        print(f"Se han agregado {agregados} tallas nuevas a la base de datos.")
    except Exception as e:
        print(f"Error insertando tallas: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando seed de tallas...")
    seed_tallas()
