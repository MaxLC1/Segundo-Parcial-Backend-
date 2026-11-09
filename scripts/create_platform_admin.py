"""Provision an explicit platform administrator; never creates a default password."""

import argparse
from getpass import getpass
from app.core import model_registry
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.pkg_seguridad.models import Usuario, Rol
from app.pkg_seguridad.schemas import UsuarioCreate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass("Contraseña nueva (8 caracteres, número y símbolo): ")
    if password != getpass("Repetir contraseña: "):
        raise SystemExit("Las contraseñas no coinciden")
    UsuarioCreate(nombre_completo=args.name, email=args.email, password=password)
    with SessionLocal() as db:
        if db.query(Usuario).filter_by(email=args.email).first():
            raise SystemExit(
                "El correo ya existe. No se elevó el rol de ninguna cuenta."
            )
        role = db.query(Rol).filter_by(nombre="AdministradorPlataforma").first()
        if not role:
            role = Rol(
                nombre="AdministradorPlataforma",
                descripcion="Administra empresas y suscripciones",
            )
            db.add(role)
            db.flush()
        db.add(
            Usuario(
                nombre_completo=args.name,
                email=args.email,
                hashed_password=get_password_hash(password),
                rol_id=role.id,
                empresa_id=None,
                is_active=True,
            )
        )
        db.commit()
    print("Administrador de plataforma creado")


if __name__ == "__main__":
    main()
