"""
Script de onboarding para crear un nuevo tenant completamente funcional.

Uso:
    python -m scripts.create_tenant \\
        --name "Empresa Demo" \\
        --slug "empresa-demo" \\
        --subdomain "tickets.empresademo.com" \\
        --admin-email "admin@empresademo.com" \\
        --admin-name "Administrador" \\
        --admin-password "Admin123!" \\
        [--auth-method local|azure] \\
        [--template scripts/templates/default_tenant.yaml] \\
        [--primary-color "#1565C0"] \\
        [--send-welcome]
"""
import argparse
import asyncio
import secrets
import string
import sys
import uuid
from datetime import time
from pathlib import Path

import yaml
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Asegura que el módulo app es encontrado
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.models.area import Area
from app.models.category import Category
from app.models.sla import SLA
from app.models.tenant import Tenant, TenantConfig
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_TEMPLATE = Path(__file__).parent / "templates" / "default_tenant.yaml"


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        # Garantiza al menos una mayúscula, minúscula, dígito y símbolo
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%" for c in password)
        ):
            return password


async def create_tenant(
    name: str,
    slug: str,
    subdomain: str,
    admin_email: str,
    admin_name: str,
    admin_password: str | None,
    auth_method: str,
    primary_color: str,
    template_path: Path,
    send_welcome: bool,
) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Genera contraseña si no fue provista
    generated_password = False
    if not admin_password:
        admin_password = generate_password()
        generated_password = True

    # Carga plantilla
    template = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    async with session_factory() as db:
        # ── Tenant ───────────────────────────────────────────────────────────
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            slug=slug,
            name=name,
            subdomain=subdomain,
        )
        db.add(tenant)

        # ── TenantConfig ─────────────────────────────────────────────────────
        cfg = template.get("tenant_config", {})
        wh_start_raw = cfg.get("working_hours_start", "08:00")
        wh_end_raw = cfg.get("working_hours_end", "18:00")
        wh_start = time(*map(int, wh_start_raw.split(":")))
        wh_end = time(*map(int, wh_end_raw.split(":")))

        tenant_config = TenantConfig(
            tenant_id=tenant_id,
            primary_color=primary_color or cfg.get("primary_color", "#1565C0"),
            auth_method=auth_method,
            auto_close_days=cfg.get("auto_close_days", 3),
            urgency_abuse_threshold=cfg.get("urgency_abuse_threshold", 50),
            timezone=cfg.get("timezone", "America/Bogota"),
            working_hours_start=wh_start,
            working_hours_end=wh_end,
            working_days=cfg.get("working_days", [1, 2, 3, 4, 5]),
            weekly_report_enabled=cfg.get("weekly_report_enabled", True),
            weekly_report_day=cfg.get("weekly_report_day", 1),
            weekly_report_recipients=[admin_email],
        )
        db.add(tenant_config)

        # ── Admin user ────────────────────────────────────────────────────────
        admin_id = uuid.uuid4()
        admin = User(
            id=admin_id,
            tenant_id=tenant_id,
            email=admin_email,
            full_name=admin_name,
            password_hash=pwd_context.hash(admin_password),
            role="admin",
        )
        db.add(admin)

        # ── Áreas ─────────────────────────────────────────────────────────────
        area_map: dict[str, uuid.UUID] = {}
        for area_def in template.get("areas", []):
            area_id = uuid.uuid4()
            area = Area(
                id=area_id,
                tenant_id=tenant_id,
                name=area_def["name"],
                description=area_def.get("description"),
                manager_id=admin_id,
            )
            db.add(area)
            area_map[area_def["name"]] = area_id

        # ── Categorías ────────────────────────────────────────────────────────
        for cat_def in template.get("categories", []):
            area_id = area_map.get(cat_def.get("area", ""))
            cat = Category(
                tenant_id=tenant_id,
                name=cat_def["name"],
                description=cat_def.get("description"),
                default_area_id=area_id,
            )
            db.add(cat)

        # ── SLAs ──────────────────────────────────────────────────────────────
        for sla_def in template.get("slas", []):
            sla = SLA(
                tenant_id=tenant_id,
                priority=sla_def["priority"],
                response_hours=sla_def["response_hours"],
                resolution_hours=sla_def["resolution_hours"],
            )
            db.add(sla)

        await db.commit()

    await engine.dispose()

    # ── Resumen en consola ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Tenant creado exitosamente: {name}")
    print("=" * 60)
    print(f"  Slug:       {slug}")
    print(f"  Subdominio: {subdomain}")
    print(f"  Auth:       {auth_method}")
    print(f"  Áreas:      {len(template.get('areas', []))}")
    print(f"  Categorías: {len(template.get('categories', []))}")
    print(f"  SLAs:       {len(template.get('slas', []))}")
    print()
    print("  CREDENCIALES DE ACCESO")
    print(f"  Email:      {admin_email}")
    if generated_password:
        print(f"  Contraseña: {admin_password}  ← GUARDAR AHORA, no se volverá a mostrar")
    else:
        print(f"  Contraseña: (la que indicaste)")
    print("=" * 60 + "\n")

    # ── Correo de bienvenida ──────────────────────────────────────────────────
    if send_welcome:
        try:
            from app.utils.email import send_email

            await send_email(
                to=admin_email,
                subject=f"Bienvenido a Smart Security Tickets — {name}",
                template_name="welcome_tenant",
                context={
                    "tenant_name": name,
                    "admin_name": admin_name,
                    "admin_email": admin_email,
                    "admin_password": admin_password if generated_password else "La que configuraste",
                    "login_url": f"{settings.FRONTEND_URL}/login",
                },
            )
            print(f"  Correo de bienvenida enviado a {admin_email}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ADVERTENCIA: No se pudo enviar el correo de bienvenida: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crea un nuevo tenant completamente configurado en el sistema."
    )
    parser.add_argument("--name", required=True, help="Nombre visible del tenant (ej: 'Empresa Demo')")
    parser.add_argument("--slug", required=True, help="Slug único sin espacios (ej: 'empresa-demo')")
    parser.add_argument("--subdomain", required=True, help="Subdominio (ej: 'tickets.empresademo.com')")
    parser.add_argument("--admin-email", required=True, help="Email del administrador inicial")
    parser.add_argument("--admin-name", default="Administrador", help="Nombre completo del admin")
    parser.add_argument("--admin-password", default=None, help="Contraseña del admin (se genera si no se indica)")
    parser.add_argument("--auth-method", default="local", choices=["local", "azure"], help="Método de autenticación")
    parser.add_argument("--primary-color", default="#1565C0", help="Color primario en hex (ej: '#1565C0')")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Ruta al archivo YAML de plantilla")
    parser.add_argument("--send-welcome", action="store_true", help="Enviar correo de bienvenida al admin")

    args = parser.parse_args()

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"Error: No se encontró la plantilla en {template_path}")
        sys.exit(1)

    asyncio.run(
        create_tenant(
            name=args.name,
            slug=args.slug,
            subdomain=args.subdomain,
            admin_email=args.admin_email,
            admin_name=args.admin_name,
            admin_password=args.admin_password,
            auth_method=args.auth_method,
            primary_color=args.primary_color,
            template_path=template_path,
            send_welcome=args.send_welcome,
        )
    )


if __name__ == "__main__":
    main()
