"""Request authorization and tenant scoping shared by every API router.

Session-local scope also applies to relationship loads and ORM bulk operations.
Maintenance scripts have no request scope; API sessions always have one.
"""

from datetime import datetime
from fastapi import Depends, HTTPException, Request
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, with_loader_criteria
from jose import jwt, JWTError
from app.core.database import Base, get_db
from app.core.security import SECRET_KEY, ALGORITHM

PLATFORM = "AdministradorPlataforma"
STAFF = {"Administrador", "Encargado", "Cajero", "Vendedor"}


def deny(message="Operación no autorizada"):
    raise HTTPException(403, message)


def role_of(user):
    return user.rol.nombre if user and user.rol else "Cliente"


async def authorize(request: Request, db: Session = Depends(get_db)):
    from app.pkg_seguridad.models import Usuario
    from app.pkg_saas.models import Empresa, Suscripcion

    path = request.url.path.rstrip("/")
    method = request.method
    if not path.startswith("/api/v1/"):
        return
    login = path.endswith("/seguridad/login")
    if login:
        return  # A stale token must not prevent reauthentication with credentials.
    register = path.endswith("/seguridad/register")
    catalog = method == "GET" and (
        path.startswith("/api/v1/catalogo/")
        and not path.endswith("/proveedores")
        or path in {"/api/v1/sucursales/sucursales", "/api/v1/sucursales/ciudades"}
    )
    public = (
        login
        or register
        or catalog
        or (method == "GET" and path.startswith("/api/v1/archivos/"))
    )
    token = request.headers.get("authorization", "")
    user = None
    if token.startswith("Bearer "):
        try:
            claims = jwt.decode(token[7:], SECRET_KEY, algorithms=[ALGORITHM])
            user = db.query(Usuario).filter_by(email=claims.get("sub")).first()
        except JWTError:
            if not public:
                raise HTTPException(401, "Sesión inválida o vencida")
        if (not user or not user.is_active) and not public:
            raise HTTPException(401, "Usuario inactivo o inexistente")
    elif not public:
        raise HTTPException(
            401, "Inicie sesión", headers={"WWW-Authenticate": "Bearer"}
        )
    role = role_of(user)
    db.info["actor"] = user
    db.info["role"] = role
    requested_empresa = request.query_params.get(
        "empresa_id"
    ) or request.path_params.get("empresa_id")
    if method == "POST" and path in {
        "/api/v1/ia/reporte-generativo",
        "/api/v1/ia/ml/predecir-demanda",
    }:
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(422, "Solicitud JSON inválida")
        body_empresa = body.get("empresa_id") if isinstance(body, dict) else None
        if body_empresa is not None:
            if requested_empresa is not None and str(requested_empresa) != str(
                body_empresa
            ):
                raise HTTPException(
                    422, "La empresa de la URL no coincide con la solicitud"
                )
            requested_empresa = body_empresa
    if login:
        return
    if role == PLATFORM:
        # El AdministradorPlataforma puede acceder a todos los módulos en modo
        # auditoría. Para operar sobre datos de una empresa específica usa el
        # query param ?empresa_id=N que le asigna un tenant temporal de lectura.
        audit_paths = {
            "/api/v1/saas/",
            "/api/v1/seguridad/",
            "/api/v1/bitacora/",
        }
        if any(path.startswith(p) for p in audit_paths):
            return
        if public:
            db.info["tenant_id"] = 1
            return
        if requested_empresa is not None:
            try:
                tenant = int(requested_empresa)
            except (ValueError, TypeError):
                raise HTTPException(422, "Empresa inválida")
            empresa = db.query(Empresa).filter_by(id=tenant, activa=True).first()
            if not empresa:
                deny("Empresa inactiva o inexistente")
            db.info["tenant_id"] = tenant
            db.info["platform_audit"] = True
            return
        # Si no especificó empresa_id, asignamos la primera empresa activa por defecto para auditoría
        primera_empresa = (
            db.query(Empresa).filter_by(activa=True).order_by(Empresa.id.asc()).first()
        )
        if primera_empresa:
            db.info["tenant_id"] = primera_empresa.id
            db.info["platform_audit"] = True
            return
        deny("Seleccione una empresa para auditar o use SaaS/Suscripción")
        return
    if register and not user:
        return  # Registration service restricts public accounts to Cliente.
    try:
        tenant = (
            user.empresa_id
            if user
            else int(request.query_params.get("empresa_id", "1"))
        )
    except ValueError:
        raise HTTPException(422, "Empresa inválida")
    if not tenant:
        deny("El usuario no tiene empresa asignada")
    empresa = db.query(Empresa).filter_by(id=tenant, activa=True).first()
    if not empresa:
        deny("Empresa inactiva o inexistente")
    db.info["tenant_id"] = tenant
    requested = requested_empresa
    if requested is not None and str(requested) != str(tenant):
        deny("No puede acceder a otra empresa")
    if user and role == "Cliente":
        db.info["customer_id"] = user.id
        allowed = (
            catalog
            or path.startswith("/api/v1/cliente")
            or path.startswith("/api/v1/pagos/")
            or path.startswith("/api/v1/archivos/")
            or path == "/api/v1/seguridad/change-password"
            or register
        )
        allowed = allowed or (
            path in {"/api/v1/ventas", "/api/v1/reservas"} and method in {"GET", "POST"}
        )
        allowed = allowed or (
            path
            in {
                "/api/v1/ventas/sincronizar-offline",
                "/api/v1/reservas/sincronizar-offline",
            }
            and method == "POST"
        )
        if not allowed:
            deny()
    elif user:
        if path.startswith("/api/v1/saas/") and (
            role != "Administrador" or method != "GET"
        ):
            deny(
                "La contratación y activación corresponden al administrador de plataforma"
            )
        if (
            path.startswith("/api/v1/seguridad/")
            and path != "/api/v1/seguridad/change-password"
            and role != "Administrador"
        ):
            deny()
        if path.startswith("/api/v1/bitacora/") and role != "Administrador":
            deny()
        if path.startswith("/api/v1/ia/") and role != "Administrador":
            deny()
        if role not in STAFF and not (
            catalog
            or path.startswith("/api/v1/delivery")
            or path == "/api/v1/seguridad/change-password"
        ):
            deny()
        if (
            method != "GET"
            and role in {"Cajero", "Vendedor"}
            and not (
                path.startswith("/api/v1/ventas")
                or path.startswith("/api/v1/reservas")
                or path == "/api/v1/seguridad/change-password"
            )
        ):
            deny()
    if method not in {"GET", "HEAD"} and not path.startswith("/api/v1/seguridad/"):
        subscription = (
            db.query(Suscripcion)
            .filter(
                Suscripcion.empresa_id == tenant,
                Suscripcion.estado == "Activa",
                Suscripcion.fecha_vencimiento >= datetime.utcnow(),
            )
            .first()
        )
        if not subscription:
            deny("Suscripción vencida o inactiva")


@event.listens_for(Session, "do_orm_execute")
def scope_queries(state):
    tenant = state.session.info.get("tenant_id")
    if tenant is None:
        return
    from app.pkg_saas.models import Empresa
    from app.pkg_sucursales.models import Inventario, Sucursal
    from app.pkg_ventas.models import Venta, DetalleVenta
    from app.pkg_reservas.models import Reserva, DetalleReserva
    from app.pkg_devoluciones.models import NotaDevolucion, Devolucion

    statement = state.statement
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if cls.__name__ == "Usuario":
            from sqlalchemy import or_

            statement = statement.options(
                with_loader_criteria(
                    cls,
                    or_(cls.empresa_id == tenant, cls.empresa_id == None),
                    include_aliases=True,
                )
            )
        elif hasattr(cls, "empresa_id"):
            statement = statement.options(
                with_loader_criteria(
                    cls, cls.empresa_id == tenant, include_aliases=True
                )
            )
    statement = statement.options(
        with_loader_criteria(Empresa, Empresa.id == tenant, include_aliases=True),
        with_loader_criteria(
            Inventario,
            Inventario.sucursal_id.in_(
                state.session.query(Sucursal.id).filter(Sucursal.empresa_id == tenant)
            ),
            include_aliases=True,
        ),
        with_loader_criteria(
            DetalleVenta,
            DetalleVenta.venta_id.in_(
                state.session.query(Venta.id).filter(Venta.empresa_id == tenant)
            ),
            include_aliases=True,
        ),
        with_loader_criteria(
            DetalleReserva,
            DetalleReserva.reserva_id.in_(
                state.session.query(Reserva.id).filter(Reserva.empresa_id == tenant)
            ),
            include_aliases=True,
        ),
    )
    customer = state.session.info.get("customer_id")
    if customer:
        for cls in (Venta, Reserva, NotaDevolucion):
            statement = statement.options(
                with_loader_criteria(
                    cls, cls.usuario_id == customer, include_aliases=True
                )
            )
        statement = statement.options(
            with_loader_criteria(
                Devolucion,
                Devolucion.venta_id.in_(
                    state.session.query(Venta.id).filter(Venta.usuario_id == customer)
                ),
                include_aliases=True,
            )
        )
    state.statement = statement


@event.listens_for(Session, "before_flush")
def validate_writes(db, flush_context, instances):
    tenant = db.info.get("tenant_id")
    if tenant is None:
        return
    by_table = {m.local_table.name: m.class_ for m in Base.registry.mappers}
    for obj in list(db.new) + list(db.dirty) + list(db.deleted):
        if hasattr(obj, "empresa_id"):
            if obj.empresa_id is None and obj in db.new:
                obj.empresa_id = tenant
            if obj.empresa_id != tenant:
                deny("El recurso pertenece a otra empresa")
        for column in inspect(type(obj)).columns:
            value = getattr(obj, column.key, None)
            if value is None:
                continue
            for fk in column.foreign_keys:
                cls = by_table.get(fk.column.table.name)
                if cls and (
                    hasattr(cls, "empresa_id")
                    or fk.column.table.name
                    in {"empresas", "detalle_ventas", "detalle_reservas"}
                ):
                    # Permitir al usuario AdministradorPlataforma que realiza la auditoría
                    if (
                        fk.column.table.name == "usuarios"
                        and db.info.get("role") == PLATFORM
                        and db.info.get("actor")
                        and value == db.info["actor"].id
                    ):
                        continue
                    if (
                        not db.query(cls)
                        .filter(getattr(cls, fk.column.key) == value)
                        .first()
                    ):
                        deny("Referencia inexistente o ajena a la empresa")
        customer = db.info.get("customer_id")
        from app.pkg_comercial.models import Cupon

        # Shared coupons are updated only by the redemption service, not a customer route.
        if (
            customer
            and not isinstance(obj, Cupon)
            and hasattr(obj, "usuario_id")
            and obj.usuario_id != customer
        ):
            deny("No puede operar en nombre de otro cliente")
