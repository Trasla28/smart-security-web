"""Area management endpoints (CRUD + member management)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import TenantId, require_role
from app.models.area import Area, UserArea
from app.models.user import User
from app.models.category import Category
from app.models.ticket import Ticket
from app.schemas.admin import AreaCreate, AreaMemberAdd, AreaMemberResponse, AreaResponse, AreaUpdate

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_area_or_404(area_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> Area:
    result = await db.execute(
        select(Area)
        .where(Area.id == area_id)
        .where(Area.tenant_id == tenant_id)
    )
    area = result.scalar_one_or_none()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return area


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[AreaResponse])
async def list_areas(
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    active_only: bool = True,
) -> list[AreaResponse]:
    """List all areas of the tenant.

    Args:
        active_only: When True (default), only returns active areas.
    """
    query = select(Area).where(Area.tenant_id == tenant_id).order_by(Area.name)
    if active_only:
        query = query.where(Area.is_active.is_(True))
    result = await db.execute(query)
    return [AreaResponse.model_validate(a) for a in result.scalars().all()]


@router.post(
    "",
    response_model=AreaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
async def create_area(
    data: AreaCreate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> AreaResponse:
    """Create a new area.

    Raises:
        HTTPException 409: If an area with the same name already exists.
    """
    existing = await db.execute(
        select(Area)
        .where(Area.tenant_id == tenant_id)
        .where(Area.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An area with this name already exists",
        )

    area = Area(
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        manager_id=data.manager_id,
        is_active=True,
    )
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return AreaResponse.model_validate(area)


@router.patch(
    "/{area_id}",
    response_model=AreaResponse,
    dependencies=[Depends(require_role("admin", "supervisor"))],
)
async def update_area(
    area_id: uuid.UUID,
    data: AreaUpdate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> AreaResponse:
    """Update an area's details."""
    area = await _get_area_or_404(area_id, tenant_id, db)

    if data.name is not None:
        area.name = data.name
    if data.description is not None:
        area.description = data.description
    if data.manager_id is not None:
        area.manager_id = data.manager_id
    if data.is_active is not None:
        area.is_active = data.is_active

    await db.commit()
    await db.refresh(area)
    return AreaResponse.model_validate(area)


@router.delete(
    "/{area_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_area(
    area_id: uuid.UUID,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete an area and all its team memberships.

    Tickets and categories that referenced this area will have their
    area_id / default_area_id set to NULL.

    Raises:
        HTTPException 404: If the area does not exist.
    """
    area = await _get_area_or_404(area_id, tenant_id, db)

    # Remove all team memberships
    members = await db.execute(select(UserArea).where(UserArea.area_id == area_id))
    for ua in members.scalars().all():
        await db.delete(ua)

    # Detach tickets that belong to this area
    await db.execute(
        sa_update(Ticket)
        .where(Ticket.tenant_id == tenant_id)
        .where(Ticket.area_id == area_id)
        .values(area_id=None)
    )

    # Detach categories that route to this area
    await db.execute(
        sa_update(Category)
        .where(Category.tenant_id == tenant_id)
        .where(Category.default_area_id == area_id)
        .values(default_area_id=None)
    )

    await db.delete(area)
    await db.commit()


@router.get("/{area_id}/members", response_model=list[AreaMemberResponse])
async def list_area_members(
    area_id: uuid.UUID,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> list[AreaMemberResponse]:
    """Return the list of users belonging to an area."""
    await _get_area_or_404(area_id, tenant_id, db)

    result = await db.execute(
        select(User, UserArea.is_primary)
        .join(UserArea, UserArea.user_id == User.id)
        .where(UserArea.area_id == area_id)
        .where(User.tenant_id == tenant_id)
        .where(User.deleted_at.is_(None))
        .order_by(User.full_name)
    )

    members = []
    for user, is_primary in result.all():
        members.append(
            AreaMemberResponse(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=user.role,
                is_primary=is_primary,
            )
        )
    return members


@router.post(
    "/{area_id}/members",
    response_model=AreaMemberResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "supervisor"))],
)
async def add_area_member(
    area_id: uuid.UUID,
    data: AreaMemberAdd,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> AreaMemberResponse:
    """Add a user to an area.

    If ``is_primary`` is True, clears any existing primary flag for that user.

    Raises:
        HTTPException 404: If area or user not found.
        HTTPException 409: If user is already a member.
    """
    await _get_area_or_404(area_id, tenant_id, db)

    # Verify user belongs to the same tenant
    user_result = await db.execute(
        select(User)
        .where(User.id == data.user_id)
        .where(User.tenant_id == tenant_id)
        .where(User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_ua = await db.execute(
        select(UserArea)
        .where(UserArea.user_id == data.user_id)
        .where(UserArea.area_id == area_id)
    )
    if existing_ua.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this area",
        )

    # If setting as primary, clear existing primary flag for this user
    if data.is_primary:
        existing_primary = await db.execute(
            select(UserArea)
            .where(UserArea.user_id == data.user_id)
            .where(UserArea.is_primary.is_(True))
        )
        for ua in existing_primary.scalars().all():
            ua.is_primary = False

    ua = UserArea(
        tenant_id=tenant_id,
        user_id=data.user_id,
        area_id=area_id,
        is_primary=data.is_primary,
    )
    db.add(ua)
    await db.commit()

    return AreaMemberResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_primary=data.is_primary,
    )


@router.delete(
    "/{area_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin", "supervisor"))],
)
async def remove_area_member(
    area_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a user from an area.

    Raises:
        HTTPException 404: If area or membership not found.
    """
    await _get_area_or_404(area_id, tenant_id, db)

    result = await db.execute(
        select(UserArea)
        .where(UserArea.area_id == area_id)
        .where(UserArea.user_id == user_id)
    )
    ua = result.scalar_one_or_none()
    if not ua:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this area",
        )

    await db.delete(ua)
    await db.commit()
