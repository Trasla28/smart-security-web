"""Superadmin router — protegido con API key, no requiere JWT de tenant.

Permite gestionar tenants desde fuera del contexto de cualquier tenant específico.
La API key se configura en la variable de entorno SUPERADMIN_API_KEY.
"""
import secrets
import uuid
from datetime import time
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Header, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.area import Area
from app.models.category import Category
from app.models.sla import SLA
from app.models.tenant import Tenant, TenantConfig
from app.models.user import User

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DEFAULT_TEMPLATE = Path(__file__).parent.parent.parent / "scripts" / "templates" / "default_tenant.yaml"


# ── Auth dependency ────────────────────────────────────────────────────────────

def verify_superadmin_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if not settings.SUPERADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Superadmin API key no configurada")
    if not secrets.compare_digest(x_api_key, settings.SUPERADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="API key inválida")


# ── Schemas ────────────────────────────────────────────────────────────────────

class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    subdomain: str = Field(..., min_length=3, max_length=100)
    admin_email: EmailStr
    admin_name: str = Field(default="Administrador", max_length=255)
    admin_password: str | None = Field(default=None, min_length=8)
    auth_method: str = Field(default="local", pattern=r"^(local|azure)$")
    primary_color: str = Field(default="#1565C0", pattern=r"^#[0-9a-fA-F]{6}$")
    send_welcome: bool = False


class TenantCreateResponse(BaseModel):
    tenant_id: str
    slug: str
    admin_email: str
    admin_password_generated: bool
    message: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _generate_password(length: int = 12) -> str:
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%" for c in password)
        ):
            return password


async def _provision_tenant(
    db: AsyncSession,
    req: TenantCreateRequest,
) -> tuple[uuid.UUID, str, bool]:
    """Crea tenant, config, admin, áreas, categorías y SLAs. Retorna (tenant_id, password, was_generated)."""

    # Carga plantilla
    template: dict = {}
    if _DEFAULT_TEMPLATE.exists():
        template = yaml.safe_load(_DEFAULT_TEMPLATE.read_text(encoding="utf-8"))

    # Contraseña
    generated = False
    password = req.admin_password
    if not password:
        password = _generate_password()
        generated = True

    tenant_id = uuid.uuid4()

    # Tenant
    db.add(Tenant(id=tenant_id, slug=req.slug, name=req.name, subdomain=req.subdomain))

    # TenantConfig
    cfg = template.get("tenant_config", {})
    wh_start = time(*map(int, cfg.get("working_hours_start", "08:00").split(":")))
    wh_end = time(*map(int, cfg.get("working_hours_end", "18:00").split(":")))
    db.add(TenantConfig(
        tenant_id=tenant_id,
        primary_color=req.primary_color,
        auth_method=req.auth_method,
        auto_close_days=cfg.get("auto_close_days", 3),
        urgency_abuse_threshold=cfg.get("urgency_abuse_threshold", 50),
        timezone=cfg.get("timezone", "America/Bogota"),
        working_hours_start=wh_start,
        working_hours_end=wh_end,
        working_days=cfg.get("working_days", [1, 2, 3, 4, 5]),
        weekly_report_enabled=cfg.get("weekly_report_enabled", True),
        weekly_report_day=cfg.get("weekly_report_day", 1),
        weekly_report_recipients=[req.admin_email],
    ))

    # Admin user
    admin_id = uuid.uuid4()
    db.add(User(
        id=admin_id,
        tenant_id=tenant_id,
        email=req.admin_email,
        full_name=req.admin_name,
        password_hash=pwd_context.hash(password),
        role="admin",
    ))

    # Áreas
    area_map: dict[str, uuid.UUID] = {}
    for area_def in template.get("areas", []):
        area_id = uuid.uuid4()
        db.add(Area(
            id=area_id,
            tenant_id=tenant_id,
            name=area_def["name"],
            description=area_def.get("description"),
            manager_id=admin_id,
        ))
        area_map[area_def["name"]] = area_id

    # Categorías
    for cat_def in template.get("categories", []):
        db.add(Category(
            tenant_id=tenant_id,
            name=cat_def["name"],
            description=cat_def.get("description"),
            default_area_id=area_map.get(cat_def.get("area", "")),
        ))

    # SLAs
    for sla_def in template.get("slas", []):
        db.add(SLA(
            tenant_id=tenant_id,
            priority=sla_def["priority"],
            response_hours=sla_def["response_hours"],
            resolution_hours=sla_def["resolution_hours"],
        ))

    await db.commit()
    return tenant_id, password, generated


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/tenants",
    response_model=TenantCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_superadmin_key)],
    summary="Crear un nuevo tenant",
    description=(
        "Crea un tenant completo: registro, configuración, usuario admin, "
        "áreas, categorías y SLAs desde la plantilla por defecto. "
        "Requiere el header `X-API-Key` con la clave de superadmin."
    ),
)
async def create_tenant(
    req: TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantCreateResponse:
    # Verificar unicidad de slug y subdomain
    from sqlalchemy import select
    existing_slug = await db.execute(select(Tenant).where(Tenant.slug == req.slug))
    if existing_slug.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"El slug '{req.slug}' ya está en uso")

    existing_sub = await db.execute(select(Tenant).where(Tenant.subdomain == req.subdomain))
    if existing_sub.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"El subdominio '{req.subdomain}' ya está en uso")

    tenant_id, password, generated = await _provision_tenant(db, req)

    # Correo de bienvenida (opcional, no bloquea si falla)
    if req.send_welcome and settings.FRONTEND_URL:
        try:
            from app.utils.email import send_email
            await send_email(
                to=req.admin_email,
                subject=f"Bienvenido a Smart Security Tickets — {req.name}",
                template_name="welcome_tenant",
                context={
                    "tenant_name": req.name,
                    "admin_name": req.admin_name,
                    "admin_email": req.admin_email,
                    "admin_password": password if generated else "La que configuraste",
                    "login_url": f"{settings.FRONTEND_URL}/login",
                },
            )
        except Exception:  # noqa: BLE001
            pass  # El tenant ya fue creado; el correo es best-effort

    return TenantCreateResponse(
        tenant_id=str(tenant_id),
        slug=req.slug,
        admin_email=req.admin_email,
        admin_password_generated=generated,
        message=(
            f"Tenant '{req.name}' creado exitosamente. "
            + ("La contraseña generada se incluye en la respuesta — guárdala ahora." if generated else "")
        ),
    )
