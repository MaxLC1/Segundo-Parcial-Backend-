import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import SessionLocal
from app.pkg_catalogo.models import Color

COLORES = [
    {"nombre": "Blanco", "codigo_hex": "#FFFFFF"},
    {"nombre": "Negro", "codigo_hex": "#000000"},
    {"nombre": "Gris Jaspeado", "codigo_hex": "#A9A9A9"},
    {"nombre": "Azul Marino", "codigo_hex": "#000080"},
    {"nombre": "Rojo", "codigo_hex": "#FF0000"},
    {"nombre": "Guindo", "codigo_hex": "#800000"},
    {"nombre": "Verde Olivo", "codigo_hex": "#556B2F"},
    {"nombre": "Beige", "codigo_hex": "#F5F5DC"},
    {"nombre": "Celeste", "codigo_hex": "#87CEEB"},
    {"nombre": "Rosado", "codigo_hex": "#FFC0CB"},
    {"nombre": "Amarillo Mostaza", "codigo_hex": "#FFDB58"},
    {"nombre": "Café", "codigo_hex": "#8B4513"},
    {"nombre": "Naranja", "codigo_hex": "#FFA500"},
    {"nombre": "Lila", "codigo_hex": "#C8A2C8"}
]

def seed_colores():
    db = SessionLocal()
    try:
        agregados = 0
        for color_data in COLORES:
            existe = db.query(Color).filter(Color.nombre.ilike(color_data["nombre"])).first()
            if not existe:
                nuevo_color = Color(nombre=color_data["nombre"], codigo_hex=color_data["codigo_hex"])
                db.add(nuevo_color)
                agregados += 1
        
        db.commit()
        print(f"[OK] Se han agregado {agregados} colores nuevos a la base de datos.")
    except Exception as e:
        print(f"[ERROR] Error insertando colores: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando seed de colores...")
    seed_colores()
