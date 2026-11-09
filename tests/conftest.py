import os

os.environ["DATABASE_URL"] = "sqlite://"
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.pkg_seguridad.models import Rol, Usuario
from app.pkg_saas.models import Empresa, Plan, Suscripcion
from app.pkg_catalogo.models import Producto, Talla, Color
from app.pkg_sucursales.models import Sucursal, Inventario, Ciudad


@pytest.fixture
def setup():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        db.add_all(
            [
                Rol(id=1, nombre="Administrador"),
                Rol(id=2, nombre="Cliente"),
                Rol(id=3, nombre="AdministradorPlataforma"),
            ]
        )
        db.add(
            Plan(
                id=1,
                nombre="Profesional",
                max_sucursales=10,
                permite_ia_generativa=True,
            )
        )
        db.add_all(
            [
                Empresa(id=i, nombre=f"Empresa {i}", codigo=f"E{i}", activa=True)
                for i in (1, 2)
            ]
        )
        db.flush()
        for i in (1, 2):
            db.add(
                Usuario(
                    id=i,
                    email=f"admin{i}@example.com",
                    nombre_completo="Admin",
                    hashed_password="unused",
                    rol_id=1,
                    empresa_id=i,
                    is_active=True,
                )
            )
            db.add(
                Suscripcion(
                    empresa_id=i,
                    plan_id=1,
                    estado="Activa",
                    fecha_vencimiento=datetime.utcnow() + timedelta(days=30),
                )
            )
            db.add(Sucursal(id=i, nombre=f"Sucursal {i}", empresa_id=i, ciudad_id=1))
            db.add(Producto(id=i, nombre=f"Producto {i}", precio=100, empresa_id=i))
        db.add(
            Usuario(
                id=3,
                email="cliente@example.com",
                nombre_completo="Cliente",
                hashed_password="unused",
                rol_id=2,
                empresa_id=1,
                is_active=True,
            )
        )
        db.add(
            Usuario(
                id=4,
                email="plataforma@example.com",
                nombre_completo="Plataforma",
                hashed_password="unused",
                rol_id=3,
                is_active=True,
            )
        )
        db.add(Ciudad(id=1, nombre="Ciudad"))
        db.add_all([Talla(id=1, nombre="M"), Color(id=1, nombre="Azul")])
        db.flush()
        db.add_all(
            [
                Inventario(
                    id=i,
                    sucursal_id=i,
                    producto_id=i,
                    talla_id=1,
                    color_id=1,
                    cantidad=10,
                )
                for i in (1, 2)
            ]
        )
        db.commit()

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    client = TestClient(app)

    def auth(who="admin1"):
        return {
            "Authorization": "Bearer "
            + create_access_token({"sub": who + "@example.com"})
        }

    yield client, factory, auth
    app.dependency_overrides.clear()
    engine.dispose()
