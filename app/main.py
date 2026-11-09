from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends
from app.core.access import authorize
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.database import Base, engine, SessionLocal

# Importar todos los modelos para registro en SQLAlchemy
import app.pkg_saas.models
import app.pkg_seguridad.models
import app.pkg_catalogo.models
import app.pkg_sucursales.models
import app.pkg_ventas.models
import app.pkg_reservas.models
import app.pkg_devoluciones.models
import app.pkg_delivery.models
import app.pkg_ia.models
import app.pkg_pagos.models
import app.pkg_comercial.models
import app.pkg_bitacora

# Crear tablas automáticamente si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    dependencies=[Depends(authorize)],
    title="FashionStore SaaS & AR - API",
    description="Backend para la plataforma de comercio electrónico SaaS Multitenant, PWA Offline y Analítica IA",
    version="2.0.0",
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    # Inicializar planes SaaS por defecto (Básico y Profesional)
    db = SessionLocal()
    try:
        from app.pkg_saas.services import inicializar_planes_default

        inicializar_planes_default(db)
    finally:
        db.close()


@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a la API de FashionStore SaaS Multitenant",
        "version": "2.0.0",
        "status": "online",
    }


# Asegurar que exista la carpeta uploads
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from app.pkg_saas.router import router as saas_router
from app.pkg_seguridad.router import router as seguridad_router
from app.pkg_catalogo.router import router as catalogo_router
from app.pkg_sucursales.router import router as sucursales_router
from app.pkg_ventas.router import router as ventas_router
from app.pkg_reservas.router import router as reservas_router
from app.pkg_archivos import router as archivos_router
from app.pkg_devoluciones import router as devoluciones_router
from app.pkg_delivery import router as delivery_router
from app.pkg_ia.router import router as ia_router
from app.pkg_pagos.router import router as pagos_router

# Routers de la API
app.include_router(saas_router, prefix="/api/v1/saas")
app.include_router(seguridad_router, prefix="/api/v1/seguridad")
app.include_router(catalogo_router, prefix="/api/v1/catalogo")
app.include_router(sucursales_router, prefix="/api/v1/sucursales")
app.include_router(ventas_router, prefix="/api/v1/ventas")
app.include_router(reservas_router, prefix="/api/v1/reservas")
app.include_router(archivos_router.router, prefix="/api/v1/archivos")
app.include_router(devoluciones_router.router, prefix="/api/v1")
app.include_router(delivery_router.router, prefix="/api/v1")
app.include_router(ia_router, prefix="/api/v1/ia")
app.include_router(pagos_router, prefix="/api/v1/pagos")


from app.pkg_comercial.router import (
    router as comercial_router,
    cliente as cliente_router,
)

app.include_router(comercial_router, prefix="/api/v1")
app.include_router(cliente_router, prefix="/api/v1")

from app.pkg_bitacora.router import router as bitacora_router

app.include_router(bitacora_router, prefix="/api/v1/bitacora")
