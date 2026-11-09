from app.core.database import SessionLocal
from app.pkg_seguridad.models import Usuario, Rol
from app.core.security import get_password_hash

db = SessionLocal()
print("--- USUARIOS REGISTRADOS ---")
users = db.query(Usuario).all()
for u in users:
    rol_nombre = u.rol.nombre if u.rol else "Sin rol"
    print(f"- Email: {u.email} | Nombre: {u.nombre_completo} | Rol: {rol_nombre} | Empresa ID: {u.empresa_id}")

platform_admins = db.query(Usuario).join(Rol).filter(Rol.nombre == "AdministradorPlataforma").all()
print(f"\nTotal Superadmins (AdministradorPlataforma): {len(platform_admins)}")
for pa in platform_admins:
    print(f"  * {pa.email} ({pa.nombre_completo})")

