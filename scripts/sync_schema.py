from app.core import model_registry
from app.core.database import engine, SessionLocal, Base
from app.pkg_seguridad.models import Rol, Usuario
from app.core.security import get_password_hash
from sqlalchemy import inspect, text

columns_to_add = [
    ('usuarios', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('colecciones', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('proveedores', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('categorias', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('temporadas', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('productos', 'costo_adquisicion', 'FLOAT DEFAULT 0'),
    ('productos', 'antiguedad_temporadas', 'INTEGER DEFAULT 0'),
    ('productos', 'descuento_porcentaje', 'FLOAT DEFAULT 0'),
    ('productos', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('sucursales', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('ventas', 'responsable_id', 'INTEGER REFERENCES usuarios(id)'),
    ('ventas', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('ventas', 'operacion_uuid', 'VARCHAR(64)'),
    ('ventas', 'estado_sincronizacion', "VARCHAR(20) DEFAULT 'aplicada'"),
    ('ventas', 'motivo_rechazo', 'VARCHAR(255)'),
    ('ventas', 'origen', "VARCHAR(20) DEFAULT 'online'"),
    ('reservas', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('reservas', 'operacion_uuid', 'VARCHAR(64)'),
    ('reservas', 'estado_sincronizacion', "VARCHAR(20) DEFAULT 'aplicada'"),
    ('reservas', 'motivo_rechazo', 'VARCHAR(255)'),
    ('reservas', 'origen', "VARCHAR(20) DEFAULT 'online'"),
    ('devoluciones', 'empresa_id', 'INTEGER REFERENCES empresas(id)'),
    ('servicio_delivery', 'empresa_id', 'INTEGER REFERENCES empresas(id)')
]

with engine.begin() as conn:
    Base.metadata.create_all(bind=conn)
    insp = inspect(conn)
    for table, col, col_type in columns_to_add:
        if insp.has_table(table):
            existing = [c['name'] for c in insp.get_columns(table)]
            if col not in existing:
                print(f'Adding {col} to {table}...')
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}'))

print('Database schema synchronized.')

