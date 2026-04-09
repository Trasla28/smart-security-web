"""User management endpoints (admin-facing CRUD + archive)."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, TenantId, require_role
from app.models.area import UserArea
from app.models.user import User
from app.schemas.admin import UserCreate, UserResponse, UserUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_user_or_404(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> User:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.tenant_id == tenant_id)
        .where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _sync_user_areas(
    user: User,
    area_ids: list[uuid.UUID],
    primary_area_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Replace all area memberships for a user."""
    # Remove existing
    existing = await db.execute(select(UserArea).where(UserArea.user_id == user.id))
    for ua in existing.scalars().all():
        await db.delete(ua)
    await db.flush()

    # Re-add
    for area_id in area_ids:
        ua = UserArea(
            tenant_id=tenant_id,
            user_id=user.id,
            area_id=area_id,
            is_primary=(area_id == primary_area_id),
        )
        db.add(ua)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse)
async def list_users(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    role: str | None = None,
    is_active: bool | None = None,
    include_archived: bool = False,
) -> dict:
    """List users of the tenant.

    - admin/supervisor: see all users.
    - agent/requester: see only active, non-archived users (for assignment UIs).
    """
    query = (
        select(User)
        .where(User.tenant_id == tenant_id)
        .where(User.deleted_at.is_(None))
        .order_by(User.full_name)
    )

    if current_user.role in ("agent", "requester"):
        query = query.where(User.is_active.is_(True)).where(User.is_archived.is_(False))
    else:
        if not include_archived:
            query = query.where(User.is_archived.is_(False))

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))

    total_result = await db.execute(select(User.id).where(User.tenant_id == tenant_id).where(User.deleted_at.is_(None)))
    total = len(total_result.all())

    offset = (page - 1) * size
    result = await db.execute(query.offset(offset).limit(size))
    items = result.scalars().all()
    pages = max(1, -(-total // size)) if total > 0 else 1

    # Fetch primary areas for returned users
    user_ids = [u.id for u in items]
    primary_ua_result = await db.execute(
        select(UserArea).where(
            and_(UserArea.user_id.in_(user_ids), UserArea.is_primary.is_(True))
        )
    )
    primary_area_map: dict[uuid.UUID, uuid.UUID] = {
        ua.user_id: ua.area_id for ua in primary_ua_result.scalars().all()
    }

    responses = []
    for u in items:
        r = UserResponse.model_validate(u)
        r.primary_area_id = primary_area_map.get(u.id)
        responses.append(r)

    return {
        "items": responses,
        "total": total,
        "page": page,
        "pages": pages,
        "size": size,
    }


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
async def create_user(
    data: UserCreate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user in the tenant.

    Only ``admin`` can create users. If ``password`` is provided it is hashed;
    otherwise the user must authenticate via SSO.

    Raises:
        HTTPException 409: If email already exists in the tenant.
    """
    existing = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .where(User.email == str(data.email))
        .where(User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    password_hash: str | None = None
    if data.password:
        from app.utils.security import hash_password
        password_hash = hash_password(data.password)

    user = User(
        tenant_id=tenant_id,
        email=str(data.email),
        full_name=data.full_name,
        role=data.role,
        password_hash=password_hash,
        is_active=True,
        is_archived=False,
    )
    db.add(user)
    await db.flush()

    if data.area_ids:
        await _sync_user_areas(user, data.area_ids, data.primary_area_id, tenant_id, db)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Retrieve a user profile by ID."""
    user = await _get_user_or_404(user_id, tenant_id, db)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role("admin"))])
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user's profile, role or area memberships.

    Only ``admin`` can modify users.
    """
    user = await _get_user_or_404(user_id, tenant_id, db)

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.area_ids is not None:
        await _sync_user_areas(user, data.area_ids, data.primary_area_id, tenant_id, db)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/archive", response_model=UserResponse, dependencies=[Depends(require_role("admin"))])
async def archive_user(
    user_id: uuid.UUID,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Archive a user (soft-delete for ex-employees).

    Sets ``is_archived=True`` and revokes all active refresh tokens in Redis.
    Open tickets assigned to this user are left unassigned.

    Raises:
        HTTPException 400: If trying to archive yourself.
        HTTPException 409: If the user is already archived.
    """
    from app.models.area import Area, UserArea
    from app.models.ticket import Ticket
    from app.repositories.ticket_repository import TicketRepository
    from app.services.notification_service import NotificationService

    user = await _get_user_or_404(user_id, tenant_id, db)

    if user.is_archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already archived",
        )

    user.is_archived = True
    user.is_active = False

    # Reassign open tickets to the area supervisor
    tickets_result = await db.execute(
        select(Ticket)
        .where(Ticket.tenant_id == tenant_id)
        .where(Ticket.assigned_to == user_id)
        .where(Ticket.status.not_in(["resolved", "closed"]))
    )
    open_tickets = tickets_result.scalars().all()

    for ticket in open_tickets:
        new_assignee_id: uuid.UUID | None = None

        if ticket.area_id:
            area_result = await db.execute(select(Area).where(Area.id == ticket.area_id))
            area_obj = area_result.scalar_one_or_none()
            if area_obj and area_obj.manager_id:
                new_assignee_id = area_obj.manager_id
            else:
                # Fallback: first active supervisor in the area
                sup_result = await db.execute(
                    select(User)
                    .join(UserArea, UserArea.user_id == User.id)
                    .where(UserArea.area_id == ticket.area_id)
                    .where(User.role == "supervisor")
                    .where(User.tenant_id == tenant_id)
                    .where(User.deleted_at.is_(None))
                    .where(User.is_active.is_(True))
                    .where(User.is_archived.is_(False))
                    .limit(1)
                )
                supervisor = sup_result.scalar_one_or_none()
                if supervisor:
                    new_assignee_id = supervisor.id

        ticket.assigned_to = new_assignee_id

        await TicketRepository.add_history(
            ticket_id=ticket.id,
            tenant_id=tenant_id,
            actor_id=None,
            action="assigned",
            old_value={"assigned_to": str(user_id), "reason": "agent_archived"},
            new_value={"assigned_to": str(new_assignee_id) if new_assignee_id else None},
            db=db,
        )

        if new_assignee_id:
            await NotificationService.create_and_send(
                user_id=new_assignee_id,
                tenant_id=tenant_id,
                notification_type="ticket_assigned",
                title=f"Ticket reasignado: {ticket.title}",
                db=db,
                ticket_id=ticket.id,
                body=f"El agente {user.full_name} fue archivado. El ticket #{ticket.ticket_number} fue asignado a ti para que lo reasignes.",
            )

    await db.flush()

    # Revoke Redis refresh tokens (best-effort)
    try:
        import redis.asyncio as aioredis

        from app.config import settings

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            keys = await client.keys(f"refresh:{user_id}:*")
            if keys:
                await client.delete(*keys)
        finally:
            await client.aclose()
    except Exception:  # noqa: BLE001
        pass

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
