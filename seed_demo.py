import os
import sys
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.pkg_catalogo.models import Producto, Categoria, Temporada, Proveedor
from app.pkg_sucursales.models import Inventario, Sucursal

def seed_demo():
    db = SessionLocal()
    try:
        # Asegurarnos que existan categorías básicas
        nombres_categorias = ["Poleras", "Pantalones", "Chaquetas", "Accesorios"]
        categorias_db = []
        for nombre in nombres_categorias:
            cat = db.query(Categoria).filter_by(nombre=nombre).first()
            if not cat:
                cat = Categoria(nombre=nombre, descripcion=f"Categoría de {nombre}")
                db.add(cat)
                db.commit()
                db.refresh(cat)
            categorias_db.append(cat)
            
        # Asegurar un proveedor, temporada y sucursal básicos
        prov = db.query(Proveedor).first()
        if not prov:
            prov = Proveedor(nombre="Proveedor Generico", contacto="contacto@generico.com")
            db.add(prov)
            db.commit()
            db.refresh(prov)
            
        temp = db.query(Temporada).first()
        if not temp:
            temp = Temporada(nombre="Temporada Actual", activa=True)
            db.add(temp)
            db.commit()
            db.refresh(temp)
            
        suc = db.query(Sucursal).first()
        if not suc:
            from app.pkg_sucursales.models import Ciudad
            ciudad = db.query(Ciudad).first()
            if not ciudad:
                ciudad = Ciudad(nombre="Sede Central")
                db.add(ciudad)
                db.commit()
                db.refresh(ciudad)
            suc = Sucursal(nombre="Sucursal Principal", direccion="Calle Principal 123", ciudad_id=ciudad.id)
            db.add(suc)
            db.commit()
            db.refresh(suc)

        # Ropa de prueba
        ropa_demo = [
            {"nombre": "Pantalón Jean Clásico", "descripcion": "Pantalón de mezclilla azul", "precio": 150.0, "cat_id": categorias_db[1].id},
            {"nombre": "Chaqueta de Cuero", "descripcion": "Chaqueta negra estilo motero", "precio": 350.0, "cat_id": categorias_db[2].id},
            {"nombre": "Gorra Deportiva", "descripcion": "Gorra de béisbol", "precio": 50.0, "cat_id": categorias_db[3].id},
            {"nombre": "Polera Blanca Básica", "descripcion": "Polera de algodón 100%", "precio": 80.0, "cat_id": categorias_db[0].id},
            {"nombre": "Pantalón Cargo", "descripcion": "Pantalón con bolsillos laterales", "precio": 180.0, "cat_id": categorias_db[1].id},
        ]

        print("--- AÑADIENDO ROPA DE DEMOSTRACIÓN ---")
        for item in ropa_demo:
            prod = db.query(Producto).filter_by(nombre=item["nombre"]).first()
            if not prod:
                prod = Producto(
                    nombre=item["nombre"],
                    descripcion=item["descripcion"],
                    precio=item["precio"],
                    imagen_url=None, # Puedes subirles imágenes después en la web
                    modelo_3d_url=None,
                    categoria_id=item["cat_id"],
                    proveedor_id=prov.id if prov else 1,
                    temporada_id=temp.id if temp else 1
                )
                db.add(prod)
                db.commit()
                db.refresh(prod)
                print(f"Producto creado: {prod.nombre}")
                
                # Añadir stock aleatorio (entre 20 y 100) en la sucursal 1, talla 1, color 1
                inv = Inventario(
                    sucursal_id=suc.id if suc else 1,
                    producto_id=prod.id,
                    talla_id=1,
                    color_id=1,
                    cantidad=random.randint(20, 100)
                )
                db.add(inv)
                db.commit()
                print(f"Stock de {inv.cantidad} unidades añadido a {prod.nombre}")
            else:
                print(f"El producto {item['nombre']} ya existe.")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo()
