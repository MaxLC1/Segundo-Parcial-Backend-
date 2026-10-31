import os
import sys
from datetime import datetime, timedelta
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.pkg_saas.models import Plan, Empresa, Suscripcion
from app.pkg_seguridad.models import Rol, Usuario
from app.pkg_sucursales.models import Ciudad, Sucursal, Inventario
from app.pkg_catalogo.models import Categoria, Coleccion, Proveedor, Temporada, Talla, Color, Producto
from app.pkg_ventas.models import Venta, DetalleVenta

def run_seed():
    print("Iniciando creación de tablas y datos semilla SaaS...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. ROLES
        roles_data = ["Administrador", "Encargado", "Cajero", "Proveedor", "Cliente", "Repartidor"]
        roles_dict = {}
        for r_name in roles_data:
            rol = db.query(Rol).filter_by(nombre=r_name).first()
            if not rol:
                rol = Rol(nombre=r_name, descripcion=f"Rol de {r_name}")
                db.add(rol)
                db.commit()
                db.refresh(rol)
            roles_dict[r_name] = rol

        # 2. PLANES SAAS (Desafío VI - Sección 9.4)
        plan_basico = db.query(Plan).filter_by(nombre="Básico").first()
        if not plan_basico:
            plan_basico = Plan(
                nombre="Básico",
                descripcion="Plan para pequeños comercios y tiendas emergentes",
                precio_mensual=29.99,
                max_sucursales=2,
                permite_ia_generativa=False,
                permite_offline=True,
                permite_cambios_prendas=True,
                activo=True
            )
            db.add(plan_basico)

        plan_pro = db.query(Plan).filter_by(nombre="Profesional").first()
        if not plan_pro:
            plan_pro = Plan(
                nombre="Profesional",
                descripcion="Plan integral con analítica avanzada, hasta 10 sucursales y reportes generativos con IA",
                precio_mensual=89.99,
                max_sucursales=10,
                permite_ia_generativa=True,
                permite_offline=True,
                permite_cambios_prendas=True,
                activo=True
            )
            db.add(plan_pro)
        db.commit()
        db.refresh(plan_basico)
        db.refresh(plan_pro)

        # 3. CIUDADES
        ciudades_nombres = ["La Paz", "Santa Cruz", "Cochabamba"]
        ciudades_dict = {}
        for c_nom in ciudades_nombres:
            ciudad = db.query(Ciudad).filter_by(nombre=c_nom).first()
            if not ciudad:
                ciudad = Ciudad(nombre=c_nom)
                db.add(ciudad)
                db.commit()
                db.refresh(ciudad)
            ciudades_dict[c_nom] = ciudad

        # 4. TALLAS Y COLORES GLOBALES
        tallas_nombres = ["S", "M", "L", "XL"]
        tallas_dict = {}
        for t_nom in tallas_nombres:
            talla = db.query(Talla).filter_by(nombre=t_nom).first()
            if not talla:
                talla = Talla(nombre=t_nom)
                db.add(talla)
                db.commit()
                db.refresh(talla)
            tallas_dict[t_nom] = talla

        colores_data = [
            ("Negro", "#000000"),
            ("Blanco", "#FFFFFF"),
            ("Azul Marino", "#000080"),
            ("Rojo Vino", "#800000"),
            ("Beige", "#F5F5DC")
        ]
        colores_dict = {}
        for c_nom, c_hex in colores_data:
            color = db.query(Color).filter_by(nombre=c_nom).first()
            if not color:
                color = Color(nombre=c_nom, codigo_hex=c_hex)
                db.add(color)
                db.commit()
                db.refresh(color)
            colores_dict[c_nom] = color

        # =====================================================================
        # EMPRESA 1 (TENANT 1): ZARA BOLIVIA S.A. (PLAN PROFESIONAL)
        # =====================================================================
        empresa_1 = db.query(Empresa).filter_by(codigo="zara-bo").first()
        if not empresa_1:
            empresa_1 = Empresa(
                nombre="Zara Bolivia S.A.",
                codigo="zara-bo",
                nit_rut="1029384021",
                telefono="+591 2 2791000",
                email_contacto="contacto@zara.bo",
                direccion_fiscal="Av. Ballivián #850, Calacoto, La Paz",
                activa=True
            )
            db.add(empresa_1)
            db.commit()
            db.refresh(empresa_1)

            # Suscripción Profesional
            sub_1 = Suscripcion(
                empresa_id=empresa_1.id,
                plan_id=plan_pro.id,
                fecha_inicio=datetime.utcnow() - timedelta(days=60),
                fecha_vencimiento=datetime.utcnow() + timedelta(days=305),
                estado="Activa",
                auto_renovacion=True,
                notas="Suscripción anual empresarial Plan Profesional"
            )
            db.add(sub_1)
            db.commit()

        # Usuarios de Zara Bolivia
        users_zara = [
            ("Admin Zara", "admin@zara.bo", "Password123!", "Administrador"),
            ("Encargado Zara", "encargado@zara.bo", "Password123!", "Encargado"),
            ("Cajero Zara", "cajero@zara.bo", "Password123!", "Cajero"),
        ]
        users_zara_dict = {}
        for nom, mail, pwd, rol_nom in users_zara:
            u = db.query(Usuario).filter_by(email=mail).first()
            if not u:
                u = Usuario(
                    nombre_completo=nom,
                    email=mail,
                    hashed_password=get_password_hash(pwd),
                    rol_id=roles_dict[rol_nom].id,
                    empresa_id=empresa_1.id,
                    is_active=True
                )
                db.add(u)
                db.commit()
                db.refresh(u)
            users_zara_dict[rol_nom] = u

        # Sucursales de Zara Bolivia (3 sucursales, permitidas por Plan Profesional)
        suc_zara_data = [
            ("Zara - Megacenter", "Av. Rafael Pabón s/n, Zona Irpavi", ciudades_dict["La Paz"].id),
            ("Zara - Ventura Mall", "4to Anillo y Av. San Martín", ciudades_dict["Santa Cruz"].id),
            ("Zara - Hupermall", "Av. Pando #123", ciudades_dict["Cochabamba"].id)
        ]
        sucs_zara = []
        for s_nom, s_dir, c_id in suc_zara_data:
            s = db.query(Sucursal).filter_by(nombre=s_nom, empresa_id=empresa_1.id).first()
            if not s:
                s = Sucursal(nombre=s_nom, direccion=s_dir, ciudad_id=c_id, empresa_id=empresa_1.id)
                db.add(s)
                db.commit()
                db.refresh(s)
            sucs_zara.append(s)

        # Categorías Zara
        cats_zara_nom = ["Elegante / Trajes", "Vestidos de Fiesta", "Casual Premium", "Calzado y Abrigos"]
        cats_zara = []
        for cat_n in cats_zara_nom:
            cat = db.query(Categoria).filter_by(nombre=cat_n, empresa_id=empresa_1.id).first()
            if not cat:
                cat = Categoria(nombre=cat_n, descripcion=f"Colección Zara de {cat_n}", activo=True, empresa_id=empresa_1.id)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cats_zara.append(cat)

        # Productos Zara
        prods_zara_data = [
            ("Blazer Slim Fit Italiano", 480.0, cats_zara[0].id),
            ("Vestido Midi Seda Floral", 360.0, cats_zara[1].id),
            ("Pantalón Chino Beige", 220.0, cats_zara[2].id),
            ("Camisa Lino Cuello Mao", 190.0, cats_zara[2].id),
            ("Abrigo Trench Clásico", 650.0, cats_zara[3].id),
            ("Botines Cuero Genuino", 520.0, cats_zara[3].id)
        ]
        prods_zara = []
        for p_nom, p_prec, c_id in prods_zara_data:
            p = db.query(Producto).filter_by(nombre=p_nom, empresa_id=empresa_1.id).first()
            if not p:
                p = Producto(
                    nombre=p_nom,
                    descripcion=f"Prenda exclusiva de alta calidad confeccionada por Zara",
                    precio=p_prec,
                    categoria_id=c_id,
                    empresa_id=empresa_1.id,
                    imagen_url="/uploads/polera_fachera_nobg.png"
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            prods_zara.append(p)

        # Stock en Sucursales de Zara
        for suc in sucs_zara:
            for prod in prods_zara:
                for talla_k in ["M", "L"]:
                    for col_k in ["Negro", "Blanco"]:
                        inv = db.query(Inventario).filter_by(
                            sucursal_id=suc.id,
                            producto_id=prod.id,
                            talla_id=tallas_dict[talla_k].id,
                            color_id=colores_dict[col_k].id
                        ).first()
                        if not inv:
                            cant = random.randint(5, 30)
                            inv = Inventario(
                                sucursal_id=suc.id,
                                producto_id=prod.id,
                                talla_id=tallas_dict[talla_k].id,
                                color_id=colores_dict[col_k].id,
                                cantidad=cant
                            )
                            db.add(inv)
        db.commit()

        # Ventas de demostración para Zara (para alimentar reportes generativos y ML)
        ventas_existentes_zara = db.query(Venta).filter_by(empresa_id=empresa_1.id).count()
        if ventas_existentes_zara < 15:
            print("Generando ventas históricas de muestra para Zara Bolivia...")
            for i in range(25):
                fecha_v = datetime.utcnow() - timedelta(days=random.randint(1, 45), hours=random.randint(1, 12))
                suc_sel = random.choice(sucs_zara)
                prod_sel = random.choice(prods_zara)
                cant = random.randint(1, 3)
                subtot = prod_sel.precio * cant

                v = Venta(
                    total=subtot,
                    usuario_id=users_zara_dict["Cajero"].id,
                    sucursal_id=suc_sel.id,
                    empresa_id=empresa_1.id,
                    metodo_pago=random.choice(["Efectivo", "QR", "Stripe"]),
                    operacion_uuid=f"zara-seed-v{i}-{int(fecha_v.timestamp())}",
                    origen="ONLINE",
                    estado_sincronizacion="CONFIRMADA",
                    fecha=fecha_v
                )
                db.add(v)
                db.commit()
                db.refresh(v)

                det = DetalleVenta(
                    venta_id=v.id,
                    producto_id=prod_sel.id,
                    talla_id=tallas_dict["M"].id,
                    color_id=colores_dict["Negro"].id,
                    cantidad=cant,
                    precio_unitario=prod_sel.precio,
                    subtotal=subtot
                )
                db.add(det)
                db.commit()

        # =====================================================================
        # EMPRESA 2 (TENANT 2): URBAN STYLE SRL (PLAN BÁSICO - MÁX 2 SUCURSALES)
        # =====================================================================
        empresa_2 = db.query(Empresa).filter_by(codigo="urban-style").first()
        if not empresa_2:
            empresa_2 = Empresa(
                nombre="Urban Style SRL",
                codigo="urban-style",
                nit_rut="3049582012",
                telefono="+591 3 3345000",
                email_contacto="ventas@urbanstyle.bo",
                direccion_fiscal="Calle 21 de Mayo #402, Santa Cruz",
                activa=True
            )
            db.add(empresa_2)
            db.commit()
            db.refresh(empresa_2)

            # Suscripción Básica (máx 2 sucursales, sin IA generativa)
            sub_2 = Suscripcion(
                empresa_id=empresa_2.id,
                plan_id=plan_basico.id,
                fecha_inicio=datetime.utcnow() - timedelta(days=20),
                fecha_vencimiento=datetime.utcnow() + timedelta(days=345),
                estado="Activa",
                auto_renovacion=True,
                notas="Suscripción anual Plan Básico"
            )
            db.add(sub_2)
            db.commit()

        # Usuarios de Urban Style
        users_urban = [
            ("Admin Urban", "admin@urbanstyle.bo", "Password123!", "Administrador"),
            ("Cajero Urban", "cajero@urbanstyle.bo", "Password123!", "Cajero"),
        ]
        users_urban_dict = {}
        for nom, mail, pwd, rol_nom in users_urban:
            u = db.query(Usuario).filter_by(email=mail).first()
            if not u:
                u = Usuario(
                    nombre_completo=nom,
                    email=mail,
                    hashed_password=get_password_hash(pwd),
                    rol_id=roles_dict[rol_nom].id,
                    empresa_id=empresa_2.id,
                    is_active=True
                )
                db.add(u)
                db.commit()
                db.refresh(u)
            users_urban_dict[rol_nom] = u

        # Sucursales de Urban Style (2 sucursales, que es su límite de Plan Básico)
        suc_urban_data = [
            ("Urban Style - Centro", "Calle Ayacucho #150", ciudades_dict["La Paz"].id),
            ("Urban Style - Equipetrol", "Av. San Martín #720", ciudades_dict["Santa Cruz"].id)
        ]
        sucs_urban = []
        for s_nom, s_dir, c_id in suc_urban_data:
            s = db.query(Sucursal).filter_by(nombre=s_nom, empresa_id=empresa_2.id).first()
            if not s:
                s = Sucursal(nombre=s_nom, direccion=s_dir, ciudad_id=c_id, empresa_id=empresa_2.id)
                db.add(s)
                db.commit()
                db.refresh(s)
            sucs_urban.append(s)

        # Categorías Urban Style
        cats_urban_nom = ["Streetwear", "Sudaderas Urban", "Gorras y Sneakers"]
        cats_urban = []
        for cat_n in cats_urban_nom:
            cat = db.query(Categoria).filter_by(nombre=cat_n, empresa_id=empresa_2.id).first()
            if not cat:
                cat = Categoria(nombre=cat_n, descripcion=f"Ropa urbana {cat_n}", activo=True, empresa_id=empresa_2.id)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cats_urban.append(cat)

        # Productos Urban Style
        prods_urban_data = [
            ("Hoodie Oversize Grafito", 180.0, cats_urban[1].id),
            ("Jogger Cargo Negro", 140.0, cats_urban[0].id),
            ("Gorra Snapback Urban", 65.0, cats_urban[2].id),
            ("Camiseta Estampada Vintage", 90.0, cats_urban[0].id)
        ]
        prods_urban = []
        for p_nom, p_prec, c_id in prods_urban_data:
            p = db.query(Producto).filter_by(nombre=p_nom, empresa_id=empresa_2.id).first()
            if not p:
                p = Producto(
                    nombre=p_nom,
                    descripcion="Ropa urbana juvenil moderna y cómoda",
                    precio=p_prec,
                    categoria_id=c_id,
                    empresa_id=empresa_2.id,
                    imagen_url="/uploads/polera_fachera_nobg.png"
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            prods_urban.append(p)

        # Stock en Sucursales de Urban Style
        for suc in sucs_urban:
            for prod in prods_urban:
                for talla_k in ["S", "M", "L"]:
                    for col_k in ["Negro", "Beige"]:
                        inv = db.query(Inventario).filter_by(
                            sucursal_id=suc.id,
                            producto_id=prod.id,
                            talla_id=tallas_dict[talla_k].id,
                            color_id=colores_dict[col_k].id
                        ).first()
                        if not inv:
                            cant = random.randint(3, 20)
                            inv = Inventario(
                                sucursal_id=suc.id,
                                producto_id=prod.id,
                                talla_id=tallas_dict[talla_k].id,
                                color_id=colores_dict[col_k].id,
                                cantidad=cant
                            )
                            db.add(inv)
        db.commit()

        # Ventas de Urban Style
        ventas_existentes_urban = db.query(Venta).filter_by(empresa_id=empresa_2.id).count()
        if ventas_existentes_urban < 8:
            for i in range(10):
                fecha_v = datetime.utcnow() - timedelta(days=random.randint(1, 20))
                suc_sel = random.choice(sucs_urban)
                prod_sel = random.choice(prods_urban)
                cant = random.randint(1, 2)
                subtot = prod_sel.precio * cant

                v = Venta(
                    total=subtot,
                    usuario_id=users_urban_dict["Cajero"].id,
                    sucursal_id=suc_sel.id,
                    empresa_id=empresa_2.id,
                    metodo_pago="Efectivo",
                    operacion_uuid=f"urban-seed-v{i}-{int(fecha_v.timestamp())}",
                    origen="ONLINE",
                    estado_sincronizacion="CONFIRMADA",
                    fecha=fecha_v
                )
                db.add(v)
                db.commit()
                db.refresh(v)

                det = DetalleVenta(
                    venta_id=v.id,
                    producto_id=prod_sel.id,
                    talla_id=tallas_dict["M"].id,
                    color_id=colores_dict["Negro"].id,
                    cantidad=cant,
                    precio_unitario=prod_sel.precio,
                    subtotal=subtot
                )
                db.add(det)
                db.commit()

        print("\n========================================================")
        print("SEED SAAS COMPLETADO EXITOSAMENTE!")
        print("========================================================")
        print("Empresa 1 (Plan Profesional con IA y hasta 10 sucursales):")
        print("  - Empresa: Zara Bolivia S.A. (codigo: zara-bo)")
        print("  - Admin: admin@zara.bo / Password123!")
        print("  - Cajero: cajero@zara.bo / Password123!")
        print("  - Sucursales: Megacenter (LP), Ventura Mall (SC), Hupermall (CBBA)")
        print("\nEmpresa 2 (Plan Básico sin IA y máx 2 sucursales):")
        print("  - Empresa: Urban Style SRL (codigo: urban-style)")
        print("  - Admin: admin@urbanstyle.bo / Password123!")
        print("  - Cajero: cajero@urbanstyle.bo / Password123!")
        print("  - Sucursales: Centro (LP), Equipetrol (SC)")
        print("========================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
