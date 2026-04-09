"""Business-logic service for ticket operations."""
import uuid
from datetime import datetime, timezone
from math import floor
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area, UserArea
from app.models.ticket import Ticket
from app.models.user import User
from app.models.sla import SLA
from app.models.tenant import TenantConfig
from app.models.category import Category
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import (
    AttachmentResponse,
    TicketAssign,
    TicketCreate,
    TicketEscalate,
    TicketHistoryResponse,
    TicketListItem,
    TicketReopen,
    TicketResponse,
    TicketUpdate,
)

# ---------------------------------------------------------------------------
# Valid status transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "pending", "escalated"},
    "in_progress": {"pending", "escalated", "resolved"},
    "pending": {"in_progress", "escalated"},
    "escalated": {"in_progress", "resolved"},
    "resolved": {"closed"},
    "closed": set(),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_sla_fields(ticket: Ticket) -> tuple[str | None, float | None]:
    """Derive sla_status and sla_percentage from a Ticket instance.

    Returns:
        A tuple ``(sla_status, sla_percentage)``.
        ``sla_status`` is one of ``"ok"``, ``"warning"``, ``"breached"``, or ``None``.
        ``sla_percentage`` is a float 0–100 or ``None`` if no SLA is set.
    """
    if ticket.sla_due_at is None or ticket.created_at is None:
        return None, None

    now = datetime.now(timezone.utc)
    created = ticket.created_at
    due = ticket.sla_due_at

    # Ensure timezone-aware
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)

    total_seconds = (due - created).total_seconds()
    if total_seconds <= 0:
        return "breached", 100.0

    elapsed_seconds = (now - created).total_seconds()
    percentage = min(100.0, max(0.0, (elapsed_seconds / total_seconds) * 100))

    if ticket.sla_breached or now > due:
        sla_status = "breached"
    elif percentage >= 75:
        sla_status = "warning"
    else:
        sla_status = "ok"

    return sla_status, round(percentage, 2)


def _to_response(ticket: Ticket) -> TicketResponse:
    """Convert a Ticket ORM instance to a TicketResponse schema."""
    sla_status, sla_percentage = _compute_sla_fields(ticket)
    resp = TicketResponse.model_validate(ticket)
    resp.sla_status = sla_status
    resp.sla_percentage = sla_percentage
    return resp


def _to_list_item(ticket: Ticket) -> TicketListItem:
    """Convert a Ticket ORM instance to a TicketListItem schema."""
    sla_status, _ = _compute_sla_fields(ticket)
    item = TicketListItem.model_validate(ticket)
    item.sla_status = sla_status
    return item


async def _get_tenant_config(tenant_id: uuid.UUID, db: AsyncSession) -> TenantConfig | None:
    """Fetch the TenantConfig for the given tenant."""
    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def _find_best_sla(
    category_id: uuid.UUID | None,
    priority: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> SLA | None:
    """Find the most specific active SLA rule for the given category + priority.

    Precedence (most specific first):
    1. category + priority
    2. category only (priority IS NULL)
    3. priority only (category IS NULL)
    4. global (both NULL)
    """
    candidates: list[SLA] = []

    result = await db.execute(
        select(SLA).where(
            and_(
                SLA.tenant_id == tenant_id,
                SLA.is_active.is_(True),
            )
        )
    )
    all_slas: list[SLA] = list(result.scalars().all())

    for sla in all_slas:
        if category_id and sla.category_id == category_id and sla.priority == priority:
            return sla  # Most specific – return immediately

    for sla in all_slas:
        if category_id and sla.category_id == category_id and sla.priority is None:
            candidates.append(sla)

    if candidates:
        return candidates[0]

    for sla in all_slas:
        if sla.category_id is None and sla.priority == priority:
            candidates.append(sla)

    if candidates:
        return candidates[0]

    for sla in all_slas:
        if sla.category_id is None and sla.priority is None:
            candidates.append(sla)

    return candidates[0] if candidates else None


async def _calculate_sla_due_at(
    ticket: Ticket,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> datetime | None:
    """Calculate the SLA due datetime for a ticket using tenant business hours."""
    if ticket.sla_id is None:
        return None

    result = await db.execute(select(SLA).where(SLA.id == ticket.sla_id))
    sla: SLA | None = result.scalar_one_or_none()
    if sla is None:
        return None

    config = await _get_tenant_config(tenant_id, db)
    if config is None:
        # Fallback to calendar hours
        from datetime import timedelta

        created = ticket.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created + timedelta(hours=sla.resolution_hours)

    from app.utils.business_hours import calculate_due_date

    created = ticket.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    return calculate_due_date(
        start=created,
        hours=sla.resolution_hours,
        timezone_str=config.timezone,
        working_days=config.working_days,
        working_hours_start=config.working_hours_start,
        working_hours_end=config.working_hours_end,
    )


async def _assert_ticket_visible(
    ticket: Ticket,
    user: User,
    db: AsyncSession,
) -> None:
    """Raise 404 if the user does not have visibility over the ticket."""
    if user.role in ("admin", "supervisor"):
        return
    if user.role == "requester":
        if ticket.requester_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        return
    # agent – can see tickets they created, are assigned to, or belong to their areas
    if ticket.requester_id == user.id or ticket.assigned_to == user.id:
        return
    if ticket.area_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    area_result = await db.execute(
        select(UserArea).where(
            and_(
                UserArea.user_id == user.id,
                UserArea.area_id == ticket.area_id,
            )
        )
    )
    if area_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


class TicketService:
    """Service layer for all ticket business operations."""

    @staticmethod
    async def create_ticket(
        data: TicketCreate,
        requester_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> TicketResponse:
        """Create a new ticket and apply automatic routing and SLA assignment.

        Args:
            data: Validated create payload.
            requester_id: UUID of the user opening the ticket.
            tenant_id: Owning tenant.
            db: Active async session.

        Returns:
            Full TicketResponse of the created ticket.
        """
        category: Category | None = None
        if data.category_id is not None:
            cat_result = await db.execute(
                select(Category).where(
                    and_(
                        Category.id == data.category_id,
                        Category.tenant_id == tenant_id,
                        Category.is_active.is_(True),
                    )
                )
            )
            category = cat_result.scalar_one_or_none()
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Category not found or inactive in this tenant",
                )

        # Automatic routing from category defaults when no area specified
        area_id = data.area_id
        # Manual assignment has priority; fall back to category default
        assigned_to: uuid.UUID | None = data.assigned_to
        if category is not None:
            if area_id is None and category.default_area_id is not None:
                area_id = category.default_area_id
            if assigned_to is None and category.default_agent_id is not None:
                assigned_to = category.default_agent_id

        # If agent assigned but no area: auto-fill from agent's primary area
        if assigned_to is not None and area_id is None:
            primary_ua_result = await db.execute(
                select(UserArea).where(
                    and_(
                        UserArea.user_id == assigned_to,
                        UserArea.is_primary.is_(True),
                    )
                )
            )
            primary_ua = primary_ua_result.scalar_one_or_none()
            if primary_ua is not None:
                area_id = primary_ua.area_id

        # Validate: without an agent, area is required so supervisors can manage the ticket
        if assigned_to is None and area_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debe asignar un área o un agente al ticket",
            )

        ticket_data: dict[str, Any] = {
            "title": data.title,
            "description": data.description,
            "priority": data.priority,
            "category_id": data.category_id,
            "area_id": area_id,
            "requester_id": requester_id,
            "assigned_to": assigned_to,
            "status": "open",
        }

        ticket = await TicketRepository.create(ticket_data, tenant_id, db)

        # Assign best SLA and compute due date
        best_sla = await _find_best_sla(data.category_id, data.priority, tenant_id, db)
        if best_sla is not None:
            ticket.sla_id = best_sla.id
            await db.flush()
            due_at = await _calculate_sla_due_at(ticket, tenant_id, db)
            ticket.sla_due_at = due_at
            await db.flush()

        # History
        await TicketRepository.add_history(
            ticket_id=ticket.id,
            tenant_id=tenant_id,
            actor_id=requester_id,
            action="created",
            old_value=None,
            new_value={"status": "open", "priority": data.priority},
            db=db,
        )

        # Reload with all relations
        ticket = await TicketRepository.get_by_id(ticket.id, tenant_id, db)

        from app.services.notification_service import NotificationService

        # Notify assigned agent (if any)
        if ticket.assigned_to:
            await NotificationService.create_and_send(
                user_id=ticket.assigned_to,
                tenant_id=tenant_id,
                notification_type="ticket_assigned",
                title=f"Ticket asignado: {ticket.title}",
                db=db,
                ticket_id=ticket.id,
                body=f"Se te ha asignado el ticket #{ticket.ticket_number}.",
            )
        elif ticket.area_id:
            # No agent assigned — notify the area supervisor so they can assign it
            area_result = await db.execute(
                select(Area).where(Area.id == ticket.area_id)
            )
            area_obj = area_result.scalar_one_or_none()
            supervisor_ids: set[uuid.UUID] = set()
            if area_obj and area_obj.manager_id:
                supervisor_ids.add(area_obj.manager_id)
            else:
                # Fallback: notify all supervisors who are members of the area
                sup_result = await db.execute(
                    select(User)
                    .join(UserArea, UserArea.user_id == User.id)
                    .where(UserArea.area_id == ticket.area_id)
                    .where(User.role == "supervisor")
                    .where(User.deleted_at.is_(None))
                )
                for sup in sup_result.scalars().all():
                    supervisor_ids.add(sup.id)
            supervisor_ids.discard(requester_id)
            for uid in supervisor_ids:
                await NotificationService.create_and_send(
                    user_id=uid,
                    tenant_id=tenant_id,
                    notification_type="ticket_assigned",
                    title=f"Ticket sin asignar: {ticket.title}",
                    db=db,
                    ticket_id=ticket.id,
                    body=f"El ticket #{ticket.ticket_number} fue creado en tu área sin agente asignado. Por favor asígnalo.",
                )

        # Notify mentioned users
        if data.notify_user_ids:
            requester_result = await db.execute(
                select(User).where(User.id == requester_id)
            )
            requester = requester_result.scalar_one_or_none()
            requester_name = requester.full_name if requester else "Un usuario"
            for uid in data.notify_user_ids:
                if uid != requester_id:
                    await NotificationService.create_and_send(
                        user_id=uid,
                        tenant_id=tenant_id,
                        notification_type="ticket_mentioned",
                        title=f"{requester_name} te mencionó en un ticket",
                        db=db,
                        ticket_id=ticket.id,
                        body=f"Fuiste etiquetado en el ticket #{ticket.ticket_number}: {ticket.title}",
                    )

        return _to_response(ticket)

    @staticmethod
    async def get_ticket(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Retrieve a single ticket, enforcing role-based visibility.

        Args:
            ticket_id: Target ticket UUID.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            Full TicketResponse.

        Raises:
            HTTPException 404: If the ticket does not exist or is not visible.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)
        return _to_response(ticket)

    @staticmethod
    async def list_tickets(
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
        *,
        status_filter: str | None = None,
        priority: str | None = None,
        area_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        assigned_to: uuid.UUID | None = None,
        requester_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "created_at",
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of tickets filtered by the caller's visibility.

        Args:
            tenant_id: Owning tenant.
            user: Authenticated user (visibility applied automatically).
            db: Active async session.

        Returns:
            Dict with keys ``items``, ``total``, ``page``, ``pages``, ``size``.
        """
        # Scope query to visible tickets based on role
        if user.role == "requester":
            requester_id = user.id  # requester can only see own tickets
        elif user.role == "agent":
            # Restrict to tickets in the agent's areas
            area_result = await db.execute(
                select(UserArea.area_id).where(UserArea.user_id == user.id)
            )
            agent_area_ids = [row for row in area_result.scalars().all()]
            # If filtering by specific area, validate it's one of the agent's areas
            if area_id is not None and area_id not in agent_area_ids:
                return {"items": [], "total": 0, "page": page, "pages": 0, "size": size}
            if area_id is None and not agent_area_ids:
                # Agent has no area assignments: show tickets directly assigned to them
                # or tickets they created
                assigned_ts, _ = await TicketRepository.get_list(
                    tenant_id,
                    db,
                    status=status_filter,
                    priority=priority,
                    area_id=None,
                    category_id=category_id,
                    assigned_to=user.id,
                    requester_id=requester_id,
                    date_from=date_from,
                    date_to=date_to,
                    page=1,
                    size=10000,
                )
                created_ts, _ = await TicketRepository.get_list(
                    tenant_id,
                    db,
                    status=status_filter,
                    priority=priority,
                    area_id=None,
                    category_id=category_id,
                    assigned_to=assigned_to,
                    requester_id=user.id,
                    date_from=date_from,
                    date_to=date_to,
                    page=1,
                    size=10000,
                )
                no_area_tickets: list[Ticket] = list(assigned_ts)
                seen_no_area: set[uuid.UUID] = {t.id for t in no_area_tickets}
                for t in created_ts:
                    if t.id not in seen_no_area:
                        no_area_tickets.append(t)
                        seen_no_area.add(t.id)
                PRIORITY_RANK_NO_AREA = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
                if sort_by == "priority":
                    no_area_tickets.sort(key=lambda t: PRIORITY_RANK_NO_AREA.get(t.priority, 9))
                else:
                    no_area_tickets.sort(key=lambda t: t.created_at, reverse=True)
                total_no_area = len(no_area_tickets)
                start_no_area = (page - 1) * size
                pages = max(1, -(-total_no_area // size)) if total_no_area > 0 else 1
                return {
                    "items": [_to_list_item(t) for t in no_area_tickets[start_no_area : start_no_area + size]],
                    "total": total_no_area,
                    "page": page,
                    "pages": pages,
                    "size": size,
                }
            if area_id is None and agent_area_ids:
                # We cannot pass a list to get_list directly; return union
                all_tickets: list[Ticket] = []
                for aid in agent_area_ids:
                    ts, _ = await TicketRepository.get_list(
                        tenant_id,
                        db,
                        status=status_filter,
                        priority=priority,
                        area_id=aid,
                        category_id=category_id,
                        assigned_to=assigned_to,
                        requester_id=requester_id,
                        date_from=date_from,
                        date_to=date_to,
                        page=1,
                        size=10000,  # fetch all, then paginate manually
                    )
                    all_tickets.extend(ts)
                # Also include tickets assigned directly to the agent in any area
                assigned_ts, _ = await TicketRepository.get_list(
                    tenant_id,
                    db,
                    status=status_filter,
                    priority=priority,
                    area_id=None,
                    category_id=category_id,
                    assigned_to=user.id,
                    requester_id=requester_id,
                    date_from=date_from,
                    date_to=date_to,
                    page=1,
                    size=10000,
                )
                # Deduplicate by id
                seen_ids: set[uuid.UUID] = {t.id for t in all_tickets}
                for t in assigned_ts:
                    if t.id not in seen_ids:
                        all_tickets.append(t)
                        seen_ids.add(t.id)

                # Also include tickets the agent created (may be outside their areas)
                created_by_agent_ts, _ = await TicketRepository.get_list(
                    tenant_id,
                    db,
                    status=status_filter,
                    priority=priority,
                    area_id=None,
                    category_id=category_id,
                    assigned_to=assigned_to,
                    requester_id=user.id,
                    date_from=date_from,
                    date_to=date_to,
                    page=1,
                    size=10000,
                )
                for t in created_by_agent_ts:
                    if t.id not in seen_ids:
                        all_tickets.append(t)
                        seen_ids.add(t.id)

                total_count = len(all_tickets)
                PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
                if sort_by == "priority":
                    all_tickets.sort(key=lambda t: PRIORITY_RANK.get(t.priority, 9))
                else:
                    all_tickets.sort(key=lambda t: t.created_at, reverse=True)
                start = (page - 1) * size
                page_tickets = all_tickets[start : start + size]
                pages = max(1, -(-total_count // size))  # ceiling division
                return {
                    "items": [_to_list_item(t) for t in page_tickets],
                    "total": total_count,
                    "page": page,
                    "pages": pages,
                    "size": size,
                }

        tickets, total = await TicketRepository.get_list(
            tenant_id,
            db,
            status=status_filter,
            priority=priority,
            area_id=area_id,
            category_id=category_id,
            assigned_to=assigned_to,
            requester_id=requester_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            page=page,
            size=size,
        )
        pages = max(1, -(-total // size)) if total > 0 else 1
        return {
            "items": [_to_list_item(t) for t in tickets],
            "total": total,
            "page": page,
            "pages": pages,
            "size": size,
        }

    @staticmethod
    async def update_ticket(
        ticket_id: uuid.UUID,
        data: TicketUpdate,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Update ticket metadata with role-based permission checks.

        Args:
            ticket_id: Target ticket UUID.
            data: Validated update payload (only non-None fields are applied).
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            Updated TicketResponse.

        Raises:
            HTTPException 403: If the user is not permitted to edit the ticket.
            HTTPException 404: If the ticket is not found.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        # Permission checks
        if user.role == "requester":
            if ticket.status != "open":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requesters can only edit open tickets",
                )
            if ticket.requester_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not your ticket",
                )

        update_data: dict[str, Any] = {}
        old_values: dict[str, Any] = {}
        new_values: dict[str, Any] = {}

        for field in ("title", "description", "priority", "category_id", "area_id"):
            val = getattr(data, field, None)
            if val is not None:
                old_val = getattr(ticket, field)
                if old_val != val:
                    old_values[field] = str(old_val) if old_val is not None else None
                    new_values[field] = str(val) if val is not None else None
                    update_data[field] = val

        if update_data:
            await TicketRepository.update(ticket, update_data, db)
            await TicketRepository.add_history(
                ticket_id=ticket.id,
                tenant_id=tenant_id,
                actor_id=user.id,
                action="updated",
                old_value=old_values,
                new_value=new_values,
                db=db,
            )

        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        return _to_response(ticket)

    @staticmethod
    async def change_status(
        ticket_id: uuid.UUID,
        new_status: str,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Transition a ticket to a new status, enforcing valid transition rules.

        Args:
            ticket_id: Target ticket UUID.
            new_status: Desired new status.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            Updated TicketResponse.

        Raises:
            HTTPException 422: If the transition is not valid.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        allowed = VALID_TRANSITIONS.get(ticket.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot transition from '{ticket.status}' to '{new_status}'",
            )

        # --- Permission rules based purely on assignment ---
        if new_status == "closed":
            # Only the ticket creator can confirm resolution
            if ticket.requester_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo el solicitante del ticket puede confirmar su resolución",
                )
        else:
            # Only the assigned user can drive the workflow, regardless of role
            if ticket.assigned_to != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo el usuario asignado al ticket puede cambiar su estado",
                )

        now = datetime.now(timezone.utc)
        update_data: dict[str, Any] = {"status": new_status}

        if new_status == "in_progress" and ticket.first_response_at is None:
            update_data["first_response_at"] = now
        if new_status == "resolved":
            update_data["resolved_at"] = now
        if new_status == "closed":
            update_data["closed_at"] = now

        old_status = ticket.status
        await TicketRepository.update(ticket, update_data, db)
        await TicketRepository.add_history(
            ticket_id=ticket.id,
            tenant_id=tenant_id,
            actor_id=user.id,
            action="status_changed",
            old_value={"status": old_status},
            new_value={"status": new_status},
            db=db,
        )

        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)

        # Notify requester and assigned agent about status change
        from app.services.notification_service import NotificationService

        body = f"El estado del ticket #{ticket.ticket_number} cambió a '{new_status}'."
        notify_ids: set[uuid.UUID] = set()
        if ticket.requester_id:
            notify_ids.add(ticket.requester_id)
        if ticket.assigned_to:
            notify_ids.add(ticket.assigned_to)
        notify_ids.discard(user.id)  # don't notify the actor

        notif_type = "ticket_resolved" if new_status == "resolved" else "status_changed"
        for uid in notify_ids:
            await NotificationService.create_and_send(
                user_id=uid,
                tenant_id=tenant_id,
                notification_type=notif_type,
                title=f"Ticket {new_status}: {ticket.title}",
                db=db,
                ticket_id=ticket.id,
                body=body,
            )

        return _to_response(ticket)

    @staticmethod
    async def assign_ticket(
        ticket_id: uuid.UUID,
        data: TicketAssign,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Assign a ticket to an agent.

        Args:
            ticket_id: Target ticket UUID.
            data: TicketAssign payload containing ``agent_id``.
            tenant_id: Owning tenant.
            user: Authenticated user (supervisor or admin).
            db: Active async session.

        Returns:
            Updated TicketResponse.

        Raises:
            HTTPException 422: If the agent does not exist or is archived/inactive.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        if user.role == "admin":
            pass  # admins can assign any ticket
        elif user.role == "supervisor":
            # Supervisor can assign if they are the area manager OR a member of the area
            if ticket.area_id:
                area_chk = await db.execute(
                    select(Area).where(Area.id == ticket.area_id)
                )
                area_obj = area_chk.scalar_one_or_none()
                is_manager = area_obj is not None and area_obj.manager_id == user.id
                if not is_manager:
                    member_result = await db.execute(
                        select(UserArea).where(
                            and_(
                                UserArea.user_id == user.id,
                                UserArea.area_id == ticket.area_id,
                            )
                        )
                    )
                    if member_result.scalar_one_or_none() is None:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Supervisors can only assign tickets within their own areas",
                        )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and supervisors of the ticket's area can assign tickets",
            )

        # Validate agent
        agent_result = await db.execute(
            select(User).where(
                and_(
                    User.id == data.agent_id,
                    User.tenant_id == tenant_id,
                    User.deleted_at.is_(None),
                )
            )
        )
        agent: User | None = agent_result.scalar_one_or_none()
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Agent not found in this tenant",
            )
        if agent.is_archived or not agent.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Agent is archived or inactive",
            )

        old_assigned = ticket.assigned_to
        await TicketRepository.update(ticket, {"assigned_to": data.agent_id}, db)
        await TicketRepository.add_history(
            ticket_id=ticket.id,
            tenant_id=tenant_id,
            actor_id=user.id,
            action="assigned",
            old_value={"assigned_to": str(old_assigned) if old_assigned else None},
            new_value={"assigned_to": str(data.agent_id)},
            db=db,
        )

        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)

        # Notify newly assigned agent
        from app.services.notification_service import NotificationService

        await NotificationService.create_and_send(
            user_id=data.agent_id,
            tenant_id=tenant_id,
            notification_type="ticket_assigned",
            title=f"Ticket asignado: {ticket.title}",
            db=db,
            ticket_id=ticket.id,
            body=f"Se te ha asignado el ticket #{ticket.ticket_number}.",
        )

        return _to_response(ticket)

    @staticmethod
    async def escalate_ticket(
        ticket_id: uuid.UUID,
        data: TicketEscalate,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Escalate a ticket, optionally moving it to a new area.

        Args:
            ticket_id: Target ticket UUID.
            data: TicketEscalate payload.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            Updated TicketResponse.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        allowed = VALID_TRANSITIONS.get(ticket.status, set())
        if "escalated" not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot escalate a ticket in '{ticket.status}' state",
            )

        update_data: dict[str, Any] = {"status": "escalated"}
        if data.area_id is not None:
            update_data["area_id"] = data.area_id

        old_status = ticket.status
        await TicketRepository.update(ticket, update_data, db)
        await TicketRepository.add_history(
            ticket_id=ticket.id,
            tenant_id=tenant_id,
            actor_id=user.id,
            action="escalated",
            old_value={"status": old_status},
            new_value={"status": "escalated", "reason": data.reason, "area_id": str(data.area_id) if data.area_id else None},
            db=db,
        )

        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        return _to_response(ticket)

    @staticmethod
    async def resolve_ticket(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Resolve a ticket (delegates to change_status)."""
        return await TicketService.change_status(ticket_id, "resolved", tenant_id, user, db)

    @staticmethod
    async def close_ticket(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Close a ticket (delegates to change_status)."""
        return await TicketService.change_status(ticket_id, "closed", tenant_id, user, db)

    @staticmethod
    async def reopen_ticket(
        ticket_id: uuid.UUID,
        data: TicketReopen,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> TicketResponse:
        """Reopen a resolved or closed ticket.

        Args:
            ticket_id: Target ticket UUID.
            data: TicketReopen payload with mandatory ``reason``.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            Updated TicketResponse.

        Raises:
            HTTPException 422: If the ticket is not in 'resolved' or 'closed' state.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        if ticket.status not in ("resolved", "closed"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only resolved or closed tickets can be reopened",
            )

        old_status = ticket.status
        await TicketRepository.update(
            ticket,
            {
                "status": "open",
                "reopen_count": ticket.reopen_count + 1,
                "resolved_at": None,
                "closed_at": None,
            },
            db,
        )
        await TicketRepository.add_history(
            ticket_id=ticket.id,
            tenant_id=tenant_id,
            actor_id=user.id,
            action="reopened",
            old_value={"status": old_status},
            new_value={"status": "open", "reason": data.reason},
            db=db,
        )

        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        return _to_response(ticket)

    @staticmethod
    async def delete_ticket(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> None:
        """Soft-delete a ticket (admin only).

        Args:
            ticket_id: Target ticket UUID.
            tenant_id: Owning tenant.
            user: Authenticated admin user.
            db: Active async session.

        Raises:
            HTTPException 403: If the user is not an admin.
            HTTPException 404: If the ticket is not found.
        """
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete tickets",
            )
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await TicketRepository.soft_delete(ticket, db)

    @staticmethod
    async def get_history(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> list[TicketHistoryResponse]:
        """Return the history for a ticket.

        Args:
            ticket_id: Target ticket UUID.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            List of TicketHistoryResponse ordered newest-first.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        history = await TicketRepository.get_history(ticket_id, tenant_id, db)
        return [TicketHistoryResponse.model_validate(h) for h in history]

    @staticmethod
    async def list_attachments(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> list[AttachmentResponse]:
        """Return all attachments for a ticket with signed download URLs."""
        from app.utils.storage import generate_signed_url

        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        attachments = await TicketRepository.list_attachments(ticket_id, tenant_id, db)
        result = []
        for a in attachments:
            resp = AttachmentResponse.model_validate(a)
            token = generate_signed_url(a.file_path, a.id)
            resp.download_url = f"/api/v1/files/download?path={a.file_path}&token={token}"
            result.append(resp)
        return result

    @staticmethod
    async def upload_attachment(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        db: AsyncSession,
        comment_id: uuid.UUID | None = None,
    ) -> AttachmentResponse:
        """Save attachment metadata after the file has been persisted to disk.

        Args:
            ticket_id: Target ticket UUID.
            tenant_id: Owning tenant.
            user: Authenticated user uploading the file.
            filename: Original file name.
            file_path: Absolute path where file was saved.
            file_size: Size in bytes.
            mime_type: MIME type string.
            db: Active async session.

        Returns:
            AttachmentResponse.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        attachment_data: dict = {
            "ticket_id": ticket_id,
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": mime_type,
            "uploaded_by": user.id,
        }
        if comment_id is not None:
            attachment_data["comment_id"] = comment_id
        attachment = await TicketRepository.create_attachment(attachment_data, tenant_id, db)
        return AttachmentResponse.model_validate(attachment)

    @staticmethod
    async def get_download_url(
        ticket_id: uuid.UUID,
        attachment_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> AttachmentResponse:
        """Generate a signed download URL for an attachment.

        Args:
            ticket_id: Target ticket UUID.
            attachment_id: Target attachment UUID.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            AttachmentResponse including a signed ``download_url``.
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        await _assert_ticket_visible(ticket, user, db)

        attachment = await TicketRepository.get_attachment(attachment_id, ticket_id, tenant_id, db)
        if attachment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

        from app.utils.storage import generate_signed_url

        token = generate_signed_url(attachment.file_path, attachment.id)
        resp = AttachmentResponse.model_validate(attachment)
        resp.download_url = f"/api/v1/files/download?path={attachment.file_path}&token={token}"
        return resp
