import os
import sys
from datetime import datetime, timedelta

# Asegurar path para importar app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import engine, SessionLocal, Base
import app.pkg_catalogo.models
import app.pkg_pagos.models
import app.pkg_devoluciones.models
import app.pkg_ventas.models

def main():
    print("Iniciando migración y seed de nuevos requerimientos...")
    
    # 1. Agregar columnas a productos si no existen
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE productos 
            ADD COLUMN IF NOT EXISTS costo_adquisicion DOUBLE PRECISION DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS antiguedad_temporadas INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS descuento_porcentaje DOUBLE PRECISION DEFAULT 0.0;
        """))
        conn.commit()
        print("Columnas en 'productos' verificadas.")

    # 2. Crear nuevas tablas
    Base.metadata.create_all(bind=engine)
    print("Tablas 'reglas_ofertas', 'transacciones_pagos_otp', 'politicas_devoluciones', 'notas_devoluciones' creadas.")

    db = SessionLocal()
    try:
        from app.pkg_catalogo.models import Producto, ReglaOferta
        from app.pkg_devoluciones.models import PoliticaDevolucion, NotaDevolucion
        from app.pkg_ventas.models import Venta
        
        # 3. Asignar antigüedades y costos realistas a productos existentes
        productos = db.query(Producto).all()
        for idx, p in enumerate(productos):
            if not p.costo_adquisicion or p.costo_adquisicion == 0:
                p.costo_adquisicion = round(p.precio * 0.45, 2)
            # Marcar algunos de temporadas pasadas para demostración
            if idx % 3 == 1:
                p.antiguedad_temporadas = 1 # 1 temporada atrás (-30%)
                p.descuento_porcentaje = 30.0
            elif idx % 3 == 2:
                p.antiguedad_temporadas = 2 # 2 temporadas atrás (-60%)
                p.descuento_porcentaje = 60.0
            else:
                p.antiguedad_temporadas = 0 # temporada actual
                p.descuento_porcentaje = 0.0
        db.commit()
        print(f"Productos actualizados con temporadas y costos ({len(productos)} prendas).")

        # 4. Crear Reglas de Ofertas para Tenant 1 (Zara) y Tenant 2 (Urban Style)
        for emp_id in [1, 2]:
            regla_mayoreo = db.query(ReglaOferta).filter(ReglaOferta.empresa_id == emp_id, ReglaOferta.tipo == "MAYOREO").first()
            if not regla_mayoreo:
                r1 = ReglaOferta(
                    empresa_id=emp_id,
                    nombre="Descuento Mayorista (3+ Prendas)",
                    tipo="MAYOREO",
                    cantidad_minima=3,
                    descuento_porcentaje=15.0,
                    descripcion="15% de descuento adicional al comprar 3 o más prendas",
                    activa=True
                )
                db.add(r1)

            regla_temp1 = db.query(ReglaOferta).filter(ReglaOferta.empresa_id == emp_id, ReglaOferta.antiguedad_temporadas == 1).first()
            if not regla_temp1:
                r2 = ReglaOferta(
                    empresa_id=emp_id,
                    nombre="Liquidación 1 Temporada Anterior (-30%)",
                    tipo="TEMPORADA_PASADA",
                    cantidad_minima=1,
                    descuento_porcentaje=30.0,
                    antiguedad_temporadas=1,
                    descripcion="Prendas de la temporada pasada con 30% de descuento directo",
                    activa=True
                )
                db.add(r2)

            regla_temp2 = db.query(ReglaOferta).filter(ReglaOferta.empresa_id == emp_id, ReglaOferta.antiguedad_temporadas == 2).first()
            if not regla_temp2:
                r3 = ReglaOferta(
                    empresa_id=emp_id,
                    nombre="Outlet Liquidación 2 Temporadas Anteriores (-60%)",
                    tipo="TEMPORADA_PASADA",
                    cantidad_minima=1,
                    descuento_porcentaje=60.0,
                    antiguedad_temporadas=2,
                    descripcion="Descuento agresivo de liquidación para recuperación de capital",
                    activa=True
                )
                db.add(r3)

            # 5. Política de Devolución
            pol = db.query(PoliticaDevolucion).filter(PoliticaDevolucion.empresa_id == emp_id).first()
            if not pol:
                p_dev = PoliticaDevolucion(
                    empresa_id=emp_id,
                    nombre=f"Política Comercial Tenant {emp_id}",
                    tipo_reembolso_menor_valor="CUPON_CREDITO",
                    plazo_maximo_dias=30,
                    permite_cambio_mayor_valor=True,
                    activa=True
                )
                db.add(p_dev)

        db.commit()
        print("Reglas de ofertas y políticas de devolución registradas.")

        # 6. Crear un par de Notas de Devolución de prueba (una EN_MARCHA para delivery y una COMPLETADA)
        venta = db.query(Venta).first()
        if venta:
            nota_existente = db.query(NotaDevolucion).filter(NotaDevolucion.venta_id == venta.id).first()
            if not nota_existente:
                # Nota 1: En marcha (Cambio por mayor valor, debe pagar diferencia al delivery)
                n1 = NotaDevolucion(
                    codigo_nota="NDEV-2026-A101",
                    empresa_id=venta.empresa_id or 1,
                    venta_id=venta.id,
                    usuario_id=2, # Cliente
                    repartidor_id=None,
                    sucursal_id=1,
                    motivo="Talla pequeña y solicitud de modelo superior",
                    tipo_solicitud="Cambio por Mayor Valor",
                    estado="EN_MARCHA",
                    visible_para_cliente=True,
                    prenda_devuelta_info="Blusa Casual Algodón - Talla S (Pagado: 120.00 Bs)",
                    prenda_nueva_info="Vestido Gala Seda - Talla M (Precio: 180.00 Bs)",
                    precio_prenda_original=120.0,
                    precio_prenda_nueva=180.0,
                    diferencia_precio=60.0,
                    mensaje_notificacion="Subió de precio (+60.00 Bs). Cliente debe abonar 60.00 Bs al delivery al recibir el nuevo producto.",
                    fecha_creacion=datetime.utcnow() - timedelta(hours=3)
                )
                db.add(n1)

                # Nota 2: Completada (histórico admin, no visible para cliente)
                n2 = NotaDevolucion(
                    codigo_nota="NDEV-2026-B202",
                    empresa_id=venta.empresa_id or 1,
                    venta_id=venta.id,
                    usuario_id=2,
                    repartidor_id=None,
                    sucursal_id=1,
                    motivo="Cambio por menor valor con cupón",
                    tipo_solicitud="Cambio por Menor Valor",
                    estado="COMPLETADA",
                    visible_para_cliente=False, # Ya no visible para cliente
                    prenda_devuelta_info="Pantalón Denim Clásico (Pagado: 200.00 Bs)",
                    prenda_nueva_info="Camiseta Premium Cuello V (Precio: 140.00 Bs)",
                    precio_prenda_original=200.0,
                    precio_prenda_nueva=140.0,
                    diferencia_precio=-60.0,
                    mensaje_notificacion="Generado cupón de crédito comercial CUPON-DEV-7A8B por 60.00 Bs.",
                    cupon_generado="CUPON-DEV-7A8B",
                    fecha_creacion=datetime.utcnow() - timedelta(days=2),
                    fecha_completada=datetime.utcnow() - timedelta(days=1)
                )
                db.add(n2)
                db.commit()
                print("Notas de devolución demostrativas creadas (1 EN_MARCHA, 1 COMPLETADA).")

        print("Migración y Seed completados con ÉXITO total.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
