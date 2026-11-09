"""Create schema and reference roles without changing existing business data."""

from app.core import model_registry
from app.core.database import engine, SessionLocal
from app.pkg_seguridad.models import Rol
from app.pkg_saas.services import inicializar_planes_default
from scripts.upgrade_commercial import upgrade


def main():
    with engine.begin() as connection:
        upgrade(connection)
    with SessionLocal() as db:
        for name in [
            "AdministradorPlataforma",
            "Administrador",
            "Encargado",
            "Cajero",
            "Vendedor",
            "Cliente",
            "Proveedor",
            "Repartidor",
        ]:
            if not db.query(Rol).filter_by(nombre=name).first():
                db.add(Rol(nombre=name))
        db.commit()
        inicializar_planes_default(db)
    print("Esquema, roles y planes preparados. No se crearon cuentas ni contraseñas.")


if __name__ == "__main__":
    main()
