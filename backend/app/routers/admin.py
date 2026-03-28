"""Admin-only endpoints: categories, SLAs, tenant config and recurring templates."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, TenantId, require_role
from app.models.category import Category
from app.models.recurring import RecurringTemplate
from app.models.sla import SLA
from app.models.tenant import TenantConfig
from app.schemas.admin import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    RecurringTemplateCreate,
    RecurringTemplateResponse,
    RecurringTemplateUpdate,
    SLACreate,
    SLAResponse,
    SLAUpdate,
    TenantConfigResponse,
    TenantConfigUpdate,
)

router = APIRouter()
_ADMIN_DEP = [Depends(require_role("admin"))]


# ===========================================================================
# Tenant Configuration
# ===========================================================================


@router.get("/config", response_model=TenantConfigResponse, dependencies=_ADMIN_DEP)
async def get_tenant_config(
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TenantConfigResponse:
    """Retrieve the current tenant configuration."""
    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found",
        )
    return TenantConfigResponse.model_validate(config)


@router.patch("/config", response_model=TenantConfigResponse, dependencies=_ADMIN_DEP)
async def update_tenant_config(
    data: TenantConfigUpdate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TenantConfigResponse:
    """Update the tenant configuration.

    Invalidates the Redis config cache after saving.
    """
    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant configuration not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    # Invalidate Redis cache (best-effort)
    try:
        import redis.asyncio as aioredis

        from app.config import settings

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await client.delete(f"tenant_config:{tenant_id}")
        finally:
            await client.aclose()
    except Exception:  # noqa: BLE001
        pass

    return TenantConfigResponse.model_validate(config)


# ===========================================================================
# Categories
# ===========================================================================


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    tenant_id: TenantId,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    active_only: bool = False,
) -> list[CategoryResponse]:
    """List ticket categories. Admins see all; other roles see only active categories."""
    query = select(Category).where(Category.tenant_id == tenant_id).order_by(Category.name)
    if active_only or current_user.role != "admin":
        query = query.where(Category.is_active.is_(True))
    result = await db.execute(query)
    return [CategoryResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=_ADMIN_DEP)
async def create_category(
    data: CategoryCreate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Create a new ticket category.

    Raises:
        HTTPException 409: If a category with the same name already exists.
    """
    existing = await db.execute(
        select(Category)
        .where(Category.tenant_id == tenant_id)
        .where(Category.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists",
        )

    category = Category(
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        default_area_id=data.default_area_id,
        default_agent_id=data.default_agent_id,
        requires_approval=data.requires_approval,
        approver_role=data.approver_role,
        is_active=True,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryResponse, dependencies=_ADMIN_DEP)
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    """Update a ticket category."""
    result = await db.execute(
        select(Category)
        .where(Category.id == category_id)
        .where(Category.tenant_id == tenant_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


# ===========================================================================
# SLAs
# ===========================================================================


@router.get("/slas", response_model=list[SLAResponse], dependencies=_ADMIN_DEP)
async def list_slas(
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    active_only: bool = False,
) -> list[SLAResponse]:
    """List all SLA configurations for the tenant."""
    query = select(SLA).where(SLA.tenant_id == tenant_id).order_by(SLA.priority, SLA.category_id)
    if active_only:
        query = query.where(SLA.is_active.is_(True))
    result = await db.execute(query)
    return [SLAResponse.model_validate(s) for s in result.scalars().all()]


@router.post("/slas", response_model=SLAResponse, status_code=status.HTTP_201_CREATED, dependencies=_ADMIN_DEP)
async def create_sla(
    data: SLACreate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> SLAResponse:
    """Create a new SLA configuration.

    Raises:
        HTTPException 409: If an active SLA already exists for the same
        ``category_id`` + ``priority`` combination.
    """
    existing = await db.execute(
        select(SLA)
        .where(SLA.tenant_id == tenant_id)
        .where(SLA.is_active.is_(True))
        .where(
            (SLA.category_id == data.category_id)
            if data.category_id
            else SLA.category_id.is_(None)
        )
        .where(
            (SLA.priority == data.priority)
            if data.priority
            else SLA.priority.is_(None)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active SLA already exists for this category + priority combination",
        )

    sla = SLA(
        tenant_id=tenant_id,
        category_id=data.category_id,
        priority=data.priority,
        response_hours=data.response_hours,
        resolution_hours=data.resolution_hours,
        is_active=True,
    )
    db.add(sla)
    await db.commit()
    await db.refresh(sla)
    return SLAResponse.model_validate(sla)


@router.patch("/slas/{sla_id}", response_model=SLAResponse, dependencies=_ADMIN_DEP)
async def update_sla(
    sla_id: uuid.UUID,
    data: SLAUpdate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> SLAResponse:
    """Update an SLA configuration."""
    result = await db.execute(
        select(SLA).where(SLA.id == sla_id).where(SLA.tenant_id == tenant_id)
    )
    sla = result.scalar_one_or_none()
    if not sla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SLA not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sla, field, value)

    await db.commit()
    await db.refresh(sla)
    return SLAResponse.model_validate(sla)


# ===========================================================================
# Recurring Templates
# ===========================================================================


@router.get("/recurring", response_model=list[RecurringTemplateResponse], dependencies=_ADMIN_DEP)
async def list_recurring_templates(
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    active_only: bool = False,
) -> list[RecurringTemplateResponse]:
    """List all recurring ticket templates for the tenant."""
    query = (
        select(RecurringTemplate)
        .where(RecurringTemplate.tenant_id == tenant_id)
        .order_by(RecurringTemplate.title)
    )
    if active_only:
        query = query.where(RecurringTemplate.is_active.is_(True))
    result = await db.execute(query)
    return [RecurringTemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post(
    "/recurring",
    response_model=RecurringTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=_ADMIN_DEP,
)
async def create_recurring_template(
    data: RecurringTemplateCreate,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Create a new recurring ticket template.

    Calculates and stores ``next_run_at`` immediately upon creation.
    """
    from app.models.tenant import TenantConfig
    from app.services.recurring_service import calculate_next_run

    cfg_result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = cfg_result.scalar_one_or_none()
    tz_str = config.timezone if config else "America/Bogota"
    working_days = list(config.working_days) if config else [1, 2, 3, 4, 5]

    template = RecurringTemplate(
        tenant_id=tenant_id,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        area_id=data.area_id,
        priority=data.priority,
        assigned_to=data.assigned_to,
        recurrence_type=data.recurrence_type,
        recurrence_value=data.recurrence_value,
        recurrence_day=data.recurrence_day,
        if_holiday_action=data.if_holiday_action,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(template)
    await db.flush()

    # Calculate first next_run_at
    template.next_run_at = calculate_next_run(
        template, timezone_str=tz_str, working_days=working_days
    )

    await db.commit()
    await db.refresh(template)
    return RecurringTemplateResponse.model_validate(template)


@router.patch("/recurring/{template_id}", response_model=RecurringTemplateResponse, dependencies=_ADMIN_DEP)
async def update_recurring_template(
    template_id: uuid.UUID,
    data: RecurringTemplateUpdate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Update a recurring ticket template.

    If ``recurrence_type`` or ``recurrence_value``/``recurrence_day`` change,
    ``next_run_at`` is recalculated.
    """
    result = await db.execute(
        select(RecurringTemplate)
        .where(RecurringTemplate.id == template_id)
        .where(RecurringTemplate.tenant_id == tenant_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recurring template not found"
        )

    changed_schedule = any(
        f in data.model_dump(exclude_unset=True)
        for f in ("recurrence_type", "recurrence_value", "recurrence_day", "if_holiday_action")
    )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    if changed_schedule:
        from app.models.tenant import TenantConfig
        from app.services.recurring_service import calculate_next_run

        cfg_result = await db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        config = cfg_result.scalar_one_or_none()
        tz_str = config.timezone if config else "America/Bogota"
        working_days = list(config.working_days) if config else [1, 2, 3, 4, 5]
        template.next_run_at = calculate_next_run(
            template, timezone_str=tz_str, working_days=working_days
        )

    await db.commit()
    await db.refresh(template)
    return RecurringTemplateResponse.model_validate(template)


@router.delete(
    "/recurring/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_ADMIN_DEP,
)
async def deactivate_recurring_template(
    template_id: uuid.UUID,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a recurring template (soft-disable — tickets already created remain intact).

    Raises:
        HTTPException 404: If template not found.
    """
    result = await db.execute(
        select(RecurringTemplate)
        .where(RecurringTemplate.id == template_id)
        .where(RecurringTemplate.tenant_id == tenant_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recurring template not found"
        )

    template.is_active = False
    await db.commit()
