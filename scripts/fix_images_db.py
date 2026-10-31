import os
import sys

# Añadir el backend al path para que pueda importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.pkg_catalogo.models import Producto

def fix_image_urls():
    db: Session = SessionLocal()
    productos = db.query(Producto).all()
    
    updated = 0
    for p in productos:
        if p.imagen_url and "192.168.100.4:8000" in p.imagen_url:
            p.imagen_url = p.imagen_url.replace("192.168.100.4:8000", "localhost:8000")
            updated += 1
            
        if p.modelo_3d_url and "192.168.100.4:8000" in p.modelo_3d_url:
            p.modelo_3d_url = p.modelo_3d_url.replace("192.168.100.4:8000", "localhost:8000")
            updated += 1
            
    if updated > 0:
        db.commit()
        print(f"URLs actualizadas: {updated} ocurrencias reemplazadas.")
    else:
        print("No se encontraron URLs con 192.168.100.4:8000")
        
    db.close()

if __name__ == "__main__":
    fix_image_urls()
