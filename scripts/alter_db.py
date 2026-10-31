from sqlalchemy import create_engine, text
from app.core.config import settings

def alter_db():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Alterando tabla ventas...")
        try:
            conn.execute(text("ALTER TABLE ventas ADD COLUMN tipo_entrega VARCHAR(50) DEFAULT 'Recojo en Tienda';"))
            conn.execute(text("ALTER TABLE ventas ADD COLUMN direccion_envio VARCHAR(255);"))
            print("  Ventas modificada con éxito.")
        except Exception as e:
            print(f"  Error/Ya existe (ventas): {e}")

        print("Alterando tabla servicio_delivery...")
        try:
            # Hacer devolucion_id nullable
            conn.execute(text("ALTER TABLE servicio_delivery ALTER COLUMN devolucion_id DROP NOT NULL;"))
            # Añadir venta_id
            conn.execute(text("ALTER TABLE servicio_delivery ADD COLUMN venta_id INTEGER;"))
            conn.execute(text("ALTER TABLE servicio_delivery ADD CONSTRAINT fk_servicio_venta FOREIGN KEY (venta_id) REFERENCES ventas(id);"))
            print("  Servicio Delivery modificada con éxito.")
        except Exception as e:
            print(f"  Error/Ya existe (servicio_delivery): {e}")

        conn.commit()
    print("Migración completada.")

if __name__ == "__main__":
    alter_db()
