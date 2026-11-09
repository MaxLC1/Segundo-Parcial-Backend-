from app.core import model_registry
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.pkg_seguridad.models import Usuario, Rol

def create_superadmin():
    db = SessionLocal()
    try:
        rol = db.query(Rol).filter_by(nombre="AdministradorPlataforma").first()
        if not rol:
            rol = Rol(nombre="AdministradorPlataforma", descripcion="Administra empresas, planes y la plataforma global")
            db.add(rol)
            db.flush()

        email = "superadmin@fashionstore.com"
        pwd = "SuperAdmin123!"
        user = db.query(Usuario).filter_by(email=email).first()
        if user:
            user.rol_id = rol.id
            user.empresa_id = None
            user.hashed_password = get_password_hash(pwd)
            user.is_active = True
            print(f"Superadmin actualizado: {email}")
        else:
            user = Usuario(
                nombre_completo="Super Administrador Plataforma",
                email=email,
                hashed_password=get_password_hash(pwd),
                rol_id=rol.id,
                empresa_id=None,
                is_active=True
            )
            db.add(user)
            print(f"Superadmin creado: {email}")
        db.commit()
        print(f"Credenciales de Superadmin:")
        print(f"  Email: {email}")
        print(f"  Password: {pwd}")
        print(f"  Rol: {rol.nombre}")
    finally:
        db.close()

if __name__ == "__main__":
    create_superadmin()

