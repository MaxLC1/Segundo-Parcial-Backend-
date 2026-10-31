import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.pkg_catalogo.models import Coleccion

def seed_colecciones():
    db = SessionLocal()
    colecciones = ["Primavera 2026", "Verano 2026", "Otoño 2026", "Invierno 2026", "Colección Exclusiva", "Descuentos Locos"]
    
    print("Iniciando seed de colecciones...")
    nuevas = 0
    for nombre in colecciones:
        col = db.query(Coleccion).filter_by(nombre=nombre).first()
        if not col:
            col = Coleccion(nombre=nombre)
            db.add(col)
            db.commit()
            nuevas += 1
            
    print(f"Se han agregado {nuevas} colecciones nuevas a la base de datos.")
    db.close()

if __name__ == "__main__":
    seed_colecciones()
