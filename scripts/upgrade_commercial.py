"""Additive upgrade for the existing second-partial database. No data is deleted.

Run from the backend directory: python -m scripts.upgrade_commercial
Back up the configured database before applying a production upgrade.
"""

from sqlalchemy import inspect, text
from app.core import model_registry
from app.core.database import Base, engine

ADDITIONS = {
    "transacciones_pagos_otp": {
        "usuario_id": "INTEGER REFERENCES usuarios(id)",
        "token_autorizacion": "VARCHAR(80)",
        "simulado": "BOOLEAN DEFAULT TRUE",
    },
    "ventas": {"responsable_id": "INTEGER REFERENCES usuarios(id)"},
    "politicas_devoluciones": {
        "porcentaje_reembolso": "FLOAT DEFAULT 100",
        "vigencia_nota_dias": "INTEGER DEFAULT 30",
    },
    "notas_devoluciones": {
        "fecha_expiracion": "TIMESTAMP",
        "detalle_venta_id": "INTEGER REFERENCES detalle_ventas(id)",
        "cantidad": "INTEGER DEFAULT 1",
        "producto_nuevo_id": "INTEGER REFERENCES productos(id)",
        "talla_nueva_id": "INTEGER REFERENCES tallas(id)",
        "color_nuevo_id": "INTEGER REFERENCES colores(id)",
        "monto_reembolso": "FLOAT DEFAULT 0",
        "resolucion": "VARCHAR(50)",
    },
}


def upgrade(connection):
    Base.metadata.create_all(bind=connection)
    for table, columns in ADDITIONS.items():
        present = {c["name"] for c in inspect(connection).get_columns(table)}
        for name, sql_type in columns.items():
            if name not in present:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
                )


if __name__ == "__main__":
    with engine.begin() as connection:
        upgrade(connection)
    print(
        "Actualización comercial completada. Las notas antiguas se conservan para revisión."
    )
