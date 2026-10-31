import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.pkg_sucursales.models import Inventario
from app.pkg_catalogo.models import Producto

def seed_inventory():
    db = SessionLocal()
    try:
        import random
        from app.pkg_catalogo.models import Talla, Color
        
        productos = db.query(Producto).all()
        tallas = db.query(Talla).all()
        colores = db.query(Color).all()
        
        if not tallas or not colores:
            print("Debes ejecutar seed_tallas.py y seed_colores.py primero.")
            return

        from app.pkg_sucursales.models import Sucursal
        sucursales = db.query(Sucursal).all()
        if not sucursales:
            print("No hay sucursales.")
            return

        for p in productos:
            # Elegir 3 tallas aleatorias y 3 colores aleatorios para este producto
            tallas_elegidas = random.sample(tallas, k=min(3, len(tallas)))
            colores_elegidos = random.sample(colores, k=min(3, len(colores)))
            
            for s in sucursales:
                for t in tallas_elegidas:
                    for c in colores_elegidos:
                        inv = db.query(Inventario).filter_by(
                            sucursal_id=s.id,
                            producto_id=p.id,
                            talla_id=t.id,
                            color_id=c.id
                        ).first()
                        
                        if not inv:
                            nuevo_inv = Inventario(
                                sucursal_id=s.id,
                                producto_id=p.id,
                                talla_id=t.id,
                                color_id=c.id,
                                cantidad=random.randint(15, 60)
                            )
                            db.add(nuevo_inv)
            
            print(f"Variantes de inventario añadidas para producto {p.nombre} en todas las sucursales.")
        
        db.commit()
        print("Múltiples colores y tallas añadidos al inventario correctamente.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_inventory()
