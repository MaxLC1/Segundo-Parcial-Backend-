import os
import sys
import random
import uuid
from datetime import datetime, timedelta

# Asegurar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.pkg_seguridad.models import Usuario, Rol
from app.pkg_catalogo.models import Producto, Categoria, Temporada, Talla, Color
from app.pkg_sucursales.models import Sucursal, Inventario, Ciudad
from app.pkg_ventas.models import Venta, DetalleVenta
from app.pkg_pagos.models import MovimientoPago
from app.pkg_comercial.models import Cupon, CanjeCupon, Traspaso
from app.pkg_devoluciones.models import PoliticaDevolucion, NotaDevolucion
from app.pkg_reservas.models import Reserva, DetalleReserva
from app.pkg_saas.models import Empresa, Plan, Suscripcion
from app.pkg_bitacora import Bitacora

def run_seed():
    db = SessionLocal()
    print("[1/8] Verificando empresas y sucursales...")

    # 1. Empresas
    empresa1 = db.query(Empresa).filter_by(id=1).first()
    if not empresa1:
        empresa1 = Empresa(id=1, nombre="Zara Bolivia S.A.", codigo="zara-bo", activa=True)
        db.add(empresa1)
        db.flush()

    empresa2 = db.query(Empresa).filter_by(id=2).first()
    if not empresa2:
        empresa2 = Empresa(id=2, nombre="Urban Style SRL", codigo="urban-style", activa=True)
        db.add(empresa2)
        db.flush()

    # Ciudad
    scz = db.query(Ciudad).first()
    if not scz:
        scz = Ciudad(nombre="Santa Cruz de la Sierra", codigo="SCZ")
        db.add(scz)
        db.flush()

    # Sucursales Zara (Empresa 1)
    sucursales_e1 = db.query(Sucursal).filter_by(empresa_id=1).all()
    if len(sucursales_e1) < 2:
        s1 = Sucursal(nombre="Sucursal Equipetrol", direccion="Av. San Martín #450", ciudad_id=scz.id, empresa_id=1, activa=True)
        s2 = Sucursal(nombre="Sucursal Ventura Mall", direccion="4to Anillo y Av. San Martín", ciudad_id=scz.id, empresa_id=1, activa=True)
        s3 = Sucursal(nombre="Sucursal Centro", direccion="Calle 21 de Calacoto", ciudad_id=scz.id, empresa_id=1, activa=True)
        db.add_all([s1, s2, s3])
        db.flush()
        sucursales_e1 = [s1, s2, s3]

    # Sucursales Urban Style (Empresa 2)
    sucursales_e2 = db.query(Sucursal).filter_by(empresa_id=2).all()
    if len(sucursales_e2) < 2:
        s4 = Sucursal(nombre="Sucursal Casco Viejo", direccion="Plaza 24 de Septiembre", ciudad_id=scz.id, empresa_id=2, activa=True)
        s5 = Sucursal(nombre="Sucursal Mall Las Brisas", direccion="Av. Cristo Redentor 4to Anillo", ciudad_id=scz.id, empresa_id=2, activa=True)
        db.add_all([s4, s5])
        db.flush()
        sucursales_e2 = [s4, s5]

    print(f"  Empresa 1 tiene {len(sucursales_e1)} sucursales. Empresa 2 tiene {len(sucursales_e2)} sucursales.")

    # 2. Clientes y Empleados
    print("[2/8] Verificando usuarios para transacciones...")
    clientes_e1 = db.query(Usuario).filter(Usuario.empresa_id == 1, Usuario.rol.has(nombre="Cliente")).all()
    if not clientes_e1:
        rol_cliente = db.query(Rol).filter_by(nombre="Cliente").first()
        c1 = Usuario(nombre_completo="Carlos Mendoza", email="carlos.mendoza@gmail.com", hashed_password="x", rol_id=rol_cliente.id, empresa_id=1, is_active=True)
        c2 = Usuario(nombre_completo="María Flores", email="maria.flores@gmail.com", hashed_password="x", rol_id=rol_cliente.id, empresa_id=1, is_active=True)
        c3 = Usuario(nombre_completo="Valeria Suárez", email="valeria.suarez@gmail.com", hashed_password="x", rol_id=rol_cliente.id, empresa_id=1, is_active=True)
        db.add_all([c1, c2, c3])
        db.flush()
        clientes_e1 = [c1, c2, c3]

    admin_e1 = db.query(Usuario).filter(Usuario.empresa_id == 1, Usuario.rol.has(nombre="Administrador")).first()
    responsable_id = admin_e1.id if admin_e1 else clientes_e1[0].id

    # 3. Productos y Tallas/Colores
    print("[3/8] Verificando productos e inventario...")
    productos_e1 = db.query(Producto).filter_by(empresa_id=1).all()
    tallas = db.query(Talla).all()
    colores = db.query(Color).all()

    if not tallas:
        tallas = [Talla(nombre=t) for t in ["S", "M", "L", "XL"]]
        db.add_all(tallas)
        db.flush()
    if not colores:
        colores = [Color(nombre=c, codigo_hex=h) for c, h in [("Negro", "#000000"), ("Blanco", "#FFFFFF"), ("Azul", "#0000FF"), ("Rojo", "#FF0000")]]
        db.add_all(colores)
        db.flush()

    # Asegurar stock crítico y normal
    for p in productos_e1[:5]:
        for s in sucursales_e1:
            inv = db.query(Inventario).filter_by(producto_id=p.id, sucursal_id=s.id).first()
            if not inv:
                db.add(Inventario(producto_id=p.id, sucursal_id=s.id, talla_id=tallas[0].id, color_id=colores[0].id, cantidad=random.randint(2, 45), empresa_id=1))
    db.flush()

    # 4. Generar Ventas históricas (Septiembre, Octubre, Noviembre 2026)
    print("[4/8] Generando historial de ventas distribuido por meses (Septiembre - Noviembre 2026)...")
    base_date = datetime(2026, 9, 1, 10, 0, 0)
    end_date = datetime(2026, 11, 8, 18, 0, 0)
    total_days = (end_date - base_date).days

    ventas_creadas = 0
    metodos = ["EFECTIVO", "QR", "TARJETA"]

    for _ in range(80):
        # Distribución en los últimos 70 días
        dias_offset = random.randint(0, total_days)
        horas_offset = random.randint(9, 20)
        min_offset = random.randint(0, 59)
        fecha_venta = base_date + timedelta(days=dias_offset, hours=horas_offset, minutes=min_offset)

        sucursal = random.choice(sucursales_e1)
        cliente = random.choice(clientes_e1)
        metodo = random.choice(metodos)

        # 1 a 3 productos por venta
        items_count = random.randint(1, 3)
        prod_samples = random.sample(productos_e1, min(items_count, len(productos_e1)))

        total_venta = 0.0
        detalles = []
        for pr in prod_samples:
            cant = random.randint(1, 3)
            precio = float(pr.precio) if pr.precio else 150.0
            sub = cant * precio
            total_venta += sub
            detalles.append(
                DetalleVenta(
                    producto_id=pr.id,
                    talla_id=random.choice(tallas).id,
                    color_id=random.choice(colores).id,
                    cantidad=cant,
                    precio_unitario=precio,
                    subtotal=sub
                )
            )

        v = Venta(
            fecha=fecha_venta,
            total=total_venta,
            usuario_id=cliente.id,
            responsable_id=responsable_id,
            sucursal_id=sucursal.id,
            empresa_id=1,
            operacion_uuid=str(uuid.uuid4()),
            estado_sincronizacion="CONFIRMADA",
            origen="ONLINE" if random.random() > 0.4 else "LOCAL_OFFLINE",
            metodo_pago=metodo,
            transaccion_id=f"TX-{random.randint(100000, 999999)}",
            tipo_entrega="EN_TIENDA",
            detalles=detalles
        )
        db.add(v)
        db.flush()

        # Registrar MovimientoPago
        mov = MovimientoPago(
            empresa_id=1,
            usuario_id=cliente.id,
            responsable_id=responsable_id,
            venta_id=v.id,
            clave_operacion=f"PAG-{v.id}-{random.randint(100, 999)}",
            tipo="VENTA",
            metodo=metodo,
            monto_bruto=total_venta,
            descuento_cupon=0.0,
            monto=total_venta,
            moneda="BOB",
            referencia=v.transaccion_id,
            estado="CONFIRMADO_SIMULADO",
            simulado=True,
            fecha=fecha_venta
        )
        db.add(mov)
        ventas_creadas += 1

    print(f"  {ventas_creadas} ventas y pagos históricos registrados con éxito para Zara Bolivia.")

    # 5. Cupones
    print("[5/8] Verificando cupones comerciales...")
    cupones_demo = [
        ("PROMO20", "20% de Descuento General", "PORCENTAJE", 20.0, 100),
        ("ZARAVIP50", "Bs 50 Descuento en compras mayores a Bs 200", "MONTO_FIJO", 50.0, 50),
        ("BIENVENIDA10", "10% Descuento de Bienvenida", "PORCENTAJE", 10.0, 200),
        ("BLACKFASHION", "25% de Descuento Especial", "PORCENTAJE", 25.0, 30)
    ]
    for cod, nom, tipo, val, usos_max in cupones_demo:
        c_exist = db.query(Cupon).filter_by(codigo=cod, empresa_id=1).first()
        if not c_exist:
            c_nuevo = Cupon(
                empresa_id=1,
                codigo=cod,
                nombre=nom,
                tipo=tipo,
                valor=val,
                criterios={},
                fecha_vencimiento=datetime(2027, 12, 31),
                max_usos=usos_max,
                usos=random.randint(2, 12),
                activo=True
            )
            db.add(c_nuevo)
    db.flush()

    # 6. Políticas y Notas de Devolución
    print("[6/8] Registrando políticas y notas de devolución...")
    pol_e1 = db.query(PoliticaDevolucion).filter_by(empresa_id=1).first()
    if not pol_e1:
        pol_e1 = PoliticaDevolucion(
            empresa_id=1,
            nombre="Política Estándar Zara Bolivia",
            tipo_reembolso_menor_valor="CUPON",
            plazo_maximo_dias=15,
            porcentaje_reembolso=100.0,
            vigencia_nota_dias=30,
            permite_cambio_mayor_valor=True,
            activa=True
        )
        db.add(pol_e1)
        db.flush()

    # Notas de devolución
    notas_count = db.query(NotaDevolucion).filter_by(empresa_id=1).count()
    if notas_count == 0:
        ultimas_ventas = db.query(Venta).filter_by(empresa_id=1).order_by(Venta.id.desc()).limit(4).all()
        for idx, uv in enumerate(ultimas_ventas):
            det = uv.detalles[0] if uv.detalles else None
            if not det:
                continue
            pr = db.query(Producto).filter_by(id=det.producto_id).first()
            prod_nombre = pr.nombre if pr else "Prenda Zara"
            estado_nota = "COMPLETADA" if idx < 2 else "PENDIENTE"

            nd = NotaDevolucion(
                codigo_nota=f"DEV-{uv.id}-{random.randint(100, 999)}",
                empresa_id=1,
                venta_id=uv.id,
                usuario_id=uv.usuario_id,
                sucursal_id=uv.sucursal_id,
                detalle_venta_id=det.id,
                cantidad=1,
                motivo="Talla no adecuada o ajuste de prenda" if idx % 2 == 0 else "Preferencia de color",
                tipo_solicitud="CAMBIO" if idx % 2 == 0 else "REEMBOLSO",
                estado=estado_nota,
                visible_para_cliente=True,
                prenda_devuelta_info=f"{prod_nombre} - Cantidad: 1",
                precio_prenda_original=det.precio_unitario,
                precio_prenda_nueva=det.precio_unitario,
                diferencia_precio=0.0,
                mensaje_notificacion="Su solicitud de cambio ha sido procesada correctamente.",
                cupon_generado=f"CUPON-DEV-{random.randint(1000, 9999)}" if idx == 0 else None,
                fecha_creacion=datetime.now() - timedelta(days=random.randint(1, 10)),
                fecha_completada=datetime.now() if estado_nota == "COMPLETADA" else None,
                fecha_expiracion=datetime.now() + timedelta(days=20),
                monto_reembolso=det.precio_unitario if estado_nota == "COMPLETADA" and idx == 1 else 0.0,
                resolucion="APROBADA" if estado_nota == "COMPLETADA" else None
            )
            db.add(nd)
        db.flush()

    # 7. Reservas
    print("[7/8] Registrando reservas comerciales...")
    reservas_count = db.query(Reserva).filter_by(empresa_id=1).count()
    if reservas_count < 4:
        estados_res = ["CONFIRMADA", "PREPARADA", "PENDIENTE", "CANCELADA"]
        for idx, est in enumerate(estados_res):
            res = Reserva(
                fecha_reserva=datetime.now() - timedelta(days=idx * 2),
                estado=est,
                empresa_id=1,
                operacion_uuid=str(uuid.uuid4()),
                estado_sincronizacion="CONFIRMADA",
                origen="ONLINE",
                usuario_id=clientes_e1[idx % len(clientes_e1)].id,
                sucursal_id=sucursales_e1[idx % len(sucursales_e1)].id
            )
            db.add(res)
            db.flush()
            # Detalle
            prod_r = productos_e1[idx % len(productos_e1)]
            det_r = DetalleReserva(
                reserva_id=res.id,
                producto_id=prod_r.id,
                talla_id=tallas[0].id,
                color_id=colores[0].id,
                cantidad=random.randint(1, 2)
            )
            db.add(det_r)
        db.flush()

    # 8. Eventos de Bitácora
    print("[8/8] Generando eventos de auditoría y bitácora...")
    eventos_demo = [
        ("AUTENTICACION", "LOGIN_EXITOSO", "Inicio de sesión de Administrador Plataforma", "superadmin@fashionstore.com", "127.0.0.1"),
        ("AUTENTICACION", "LOGIN_EXITOSO", "Inicio de sesión de cajero en Sucursal Equipetrol", "cajero@zara.bo", "192.168.1.10"),
        ("SAAS", "PLAN_ACTUALIZADO", "Actualización de suscripción de Zara Bolivia al Plan Profesional", "superadmin@fashionstore.com", "127.0.0.1"),
        ("VENTAS", "SINCRONIZACION_OFFLINE", "Lote de 3 ventas offline sincronizado exitosamente", "cajero@zara.bo", "192.168.1.10"),
        ("INVENTARIO", "AJUSTE_STOCK", "Ajuste de inventario en Sucursal Ventura Mall por reposición", "admin@zara.bo", "192.168.1.12"),
        ("DEVOLUCIONES", "NOTA_COMPLETADA", "Aprobación y cierre de nota de devolución DEV-102", "admin@zara.bo", "192.168.1.12"),
        ("PAGOS", "COBRO_CONFIRMADO", "Cobro simulado confirmado por Bs 380 vía QR", "sistema@fashionstore.com", "127.0.0.1"),
        ("COMERCIAL", "CUPON_CREADO", "Creación de cupón de temporada BLACKFASHION con 25% descuento", "admin@zara.bo", "192.168.1.12")
    ]
    for mod, ev_tipo, desc, actor, ip in eventos_demo:
        b = Bitacora(
            empresa_id=1,
            empresa_nombre="Zara Bolivia S.A.",
            modulo=mod,
            accion=ev_tipo,
            detalle=desc,
            usuario_email=actor,
            usuario_nombre="Usuario Demo",
            rol="Administrador",
            ip=ip,
            fecha=datetime.now() - timedelta(hours=random.randint(1, 72))
        )
        db.add(b)

    db.commit()
    db.close()
    print(">>> Sincronización de datos completada exitosamente. La base de datos contiene ahora información rica y coherente para todas las vistas y reportes.")

if __name__ == "__main__":
    run_seed()
