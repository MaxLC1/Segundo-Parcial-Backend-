import os
import sys
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.pkg_catalogo.models import Producto, Coleccion, Proveedor

def seed_relations():
    db = SessionLocal()
    try:
        productos = db.query(Producto).all()
        colecciones = db.query(Coleccion).all()
        proveedores = db.query(Proveedor).all()
        
        if not productos:
            print("No hay productos en la base de datos.")
            return
            
        if not colecciones:
            print("No hay colecciones. Ejecuta seed_colecciones.py primero.")
            return
            
        if not proveedores:
            # Let's create some dummy providers if there are none
            p1 = Proveedor(nombre="Proveedor Generico", contacto="123456")
            p2 = Proveedor(nombre="Fashion Supplier Co.", contacto="contact@fashionsupplier.com")
            p3 = Proveedor(nombre="Textiles Premium S.A.", contacto="ventas@textilespremium.com")
            p4 = Proveedor(nombre="Importaciones XYZ", contacto="info@importacionesxyz.com")
            db.add_all([p1, p2, p3, p4])
            db.commit()
            proveedores = db.query(Proveedor).all()

        for p in productos:
            col_elegida = random.choice(colecciones)
            prov_elegido = random.choice(proveedores)
            
            p.coleccion_id = col_elegida.id
            p.proveedor_id = prov_elegido.id
            
        db.commit()
        print(f"Relaciones aleatorias asignadas a {len(productos)} productos.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_relations()
