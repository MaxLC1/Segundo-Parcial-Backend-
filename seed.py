import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.pkg_seguridad.models import Rol, Usuario
from app.pkg_sucursales.models import Ciudad
from app.pkg_catalogo.models import Producto, Categoria, Talla, Color
from app.core.security import get_password_hash

def seed_db():
    db = SessionLocal()
    
    # 0. Crear Ciudades (Departamentos)
    ciudades_nombres = ["Santa Cruz", "La Paz", "Cochabamba", "Tarija", "Oruro", "Potosí", "Chuquisaca", "Beni", "Pando"]
    print("--- CREANDO CIUDADES ---")
    for nombre in ciudades_nombres:
        ciudad = db.query(Ciudad).filter(Ciudad.nombre == nombre).first()
        if not ciudad:
            ciudad = Ciudad(nombre=nombre)
            db.add(ciudad)
            db.commit()
            print(f"Ciudad '{nombre}' creada.")
        else:
            print(f"Ciudad '{nombre}' ya existía.")

    # 1. Crear los roles definidos en la Arquitectura (CU-01 a CU-07)
    roles_nombres = ["Administrador", "Encargado", "Cajero", "Cliente", "Proveedor", "Repartidor", "Vendedor"]
    roles_db = {}
    
    print("--- CREANDO ROLES ---")
    for nombre in roles_nombres:
        rol = db.query(Rol).filter(Rol.nombre == nombre).first()
        if not rol:
            rol = Rol(nombre=nombre, descripcion=f"Rol de {nombre}")
            db.add(rol)
            db.commit()
            db.refresh(rol)
            print(f"Rol '{nombre}' creado.")
        else:
            print(f"Rol '{nombre}' ya existía.")
        roles_db[nombre] = rol
        
    # 2. Crear Usuarios de prueba con la contraseña segura
    usuarios_prueba = [
        {"nombre": "Admin Supremo", "email": "admin@fashionstore.com", "rol": "Administrador"},
        {"nombre": "Encargado Tienda", "email": "encargado@fashionstore.com", "rol": "Encargado"},
        {"nombre": "Cajero 1", "email": "cajero@fashionstore.com", "rol": "Cajero"},
        {"nombre": "Vendedor Experto", "email": "vendedor@fashionstore.com", "rol": "Vendedor"},
        {"nombre": "Juan Cliente", "email": "cliente@fashionstore.com", "rol": "Cliente"},
        {"nombre": "Proveedor Textil", "email": "proveedor@fashionstore.com", "rol": "Proveedor"},
        {"nombre": "Repartidor Express", "email": "delivery@fashionstore.com", "rol": "Repartidor"}
    ]
    
    # Esta contraseña cumple con las nuevas validaciones (números, min/may y especial)
    password_segura = "Seguridad123!"
    hashed_pwd = get_password_hash(password_segura)
    
    print("\n--- CREANDO USUARIOS ---")
    for user_data in usuarios_prueba:
        usuario = db.query(Usuario).filter(Usuario.email == user_data["email"]).first()
        if not usuario:
            usuario = Usuario(
                nombre_completo=user_data["nombre"],
                email=user_data["email"],
                hashed_password=hashed_pwd,
                rol_id=roles_db[user_data["rol"]].id
            )
            db.add(usuario)
            db.commit()
            print(f"Usuario '{user_data['nombre']}' creado con email: {user_data['email']}")
        else:
            print(f"Usuario con email '{user_data['email']}' ya existía.")
            
    print("\n¡Semilla (Seed) ejecutada con éxito!")
    db.close()

if __name__ == "__main__":
    seed_db()
