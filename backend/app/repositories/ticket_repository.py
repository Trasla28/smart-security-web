"""Repository layer for Ticket and related models."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import text

from app.models.ticket import Ticket, TicketHistory, TicketAttachment


class TicketRepository:
    """Data-access helpers for the Ticket aggregate."""

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @staticmethod
    async def get_by_id(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> Ticket | None:
        """Fetch a single ticket by PK scoped to the tenant, with all relations loaded."""
        result = await db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.requester),
                selectinload(Ticket.assignee),
                selectinload(Ticket.area),
                selectinload(Ticket.category),
                selectinload(Ticket.sla),
                selectinload(Ticket.comments),
                selectinload(Ticket.history),
                selectinload(Ticket.attachments),
            )
            .where(
                and_(
                    Ticket.id == ticket_id,
                    Ticket.tenant_id == tenant_id,
                    Ticket.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        tenant_id: uuid.UUID,
        db: AsyncSession,
        *,
        status: str | None = None,
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
    ) -> tuple[list[Ticket], int]:
        """Return a paginated list of tickets matching the given filters.

        Returns:
            Tuple of (tickets, total_count).
        """
        conditions = [
            Ticket.tenant_id == tenant_id,
            Ticket.deleted_at.is_(None),
        ]

        if status is not None:
            conditions.append(Ticket.status == status)
        if priority is not None:
            conditions.append(Ticket.priority == priority)
        if area_id is not None:
            conditions.append(Ticket.area_id == area_id)
        if category_id is not None:
            conditions.append(Ticket.category_id == category_id)
        if assigned_to is not None:
            conditions.append(Ticket.assigned_to == assigned_to)
        if requester_id is not None:
            conditions.append(Ticket.requester_id == requester_id)
        if date_from is not None:
            conditions.append(Ticket.created_at >= date_from)
        if date_to is not None:
            conditions.append(Ticket.created_at <= date_to)

        where_clause = and_(*conditions)

        # Count query
        count_result = await db.execute(
            select(func.count()).select_from(Ticket).where(where_clause)
        )
        total = count_result.scalar_one()

        # Build order clause
        PRIORITY_ORDER = case(
            (Ticket.priority == "urgent", 1),
            (Ticket.priority == "high", 2),
            (Ticket.priority == "medium", 3),
            (Ticket.priority == "low", 4),
            else_=5,
        )
        order_clause = PRIORITY_ORDER if sort_by == "priority" else Ticket.created_at.desc()

        # Data query with eager-loaded lightweight relations
        offset = (page - 1) * size
        data_result = await db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.requester),
                selectinload(Ticket.assignee),
                selectinload(Ticket.area),
                selectinload(Ticket.category),
            )
            .where(where_clause)
            .order_by(order_clause)
            .offset(offset)
            .limit(size)
        )
        tickets = list(data_result.scalars().all())
        return tickets, total

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @staticmethod
    async def create(
        data: dict[str, Any],
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> Ticket:
        """Persist a new ticket, generating a sequential ticket_number for the tenant.

        Args:
            data: Field values (must NOT include ``tenant_id`` or ``ticket_number``).
            tenant_id: The owning tenant.
            db: Active async session.

        Returns:
            Newly created (and refreshed) Ticket instance.
        """
        # Generate sequential ticket number within the tenant.
        # We use pg_advisory_xact_lock to prevent race conditions under concurrent
        # inserts for the same tenant. The lock is automatically released at the
        # end of the transaction.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:tid))"),
            {"tid": str(tenant_id)},
        )
        result = await db.execute(
            text(
                "SELECT COALESCE(MAX(CAST(REGEXP_REPLACE(ticket_number, '[^0-9]', '', 'g') AS INTEGER)), 0) "
                "FROM tickets WHERE tenant_id = :tid"
            ),
            {"tid": str(tenant_id)},
        )
        max_num: int = result.scalar_one() or 0
        ticket_number = f"#TK-{max_num + 1:04d}"

        ticket = Ticket(
            tenant_id=tenant_id,
            ticket_number=ticket_number,
            **data,
        )
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def update(
        ticket: Ticket,
        data: dict[str, Any],
        db: AsyncSession,
    ) -> Ticket:
        """Apply field updates to an existing ticket.

        Args:
            ticket: The ORM instance to update.
            data: Mapping of field names to new values.
            db: Active async session.

        Returns:
            Updated Ticket instance.
        """
        for key, value in data.items():
            setattr(ticket, key, value)
        await db.flush()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def soft_delete(ticket: Ticket, db: AsyncSession) -> None:
        """Mark a ticket as deleted without removing the row."""
        ticket.deleted_at = datetime.now(timezone.utc)
        await db.flush()

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def add_history(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        action: str,
        old_value: dict[str, Any] | None,
        new_value: dict[str, Any] | None,
        db: AsyncSession,
    ) -> TicketHistory:
        """Insert a history record for an action performed on a ticket.

        Args:
            ticket_id: Ticket being acted upon.
            tenant_id: Owning tenant.
            actor_id: User performing the action (None for system).
            action: Action label, e.g. ``"status_changed"``.
            old_value: Previous state payload (JSONB).
            new_value: New state payload (JSONB).
            db: Active async session.

        Returns:
            The persisted TicketHistory instance.
        """
        history = TicketHistory(
            ticket_id=ticket_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
        )
        db.add(history)
        await db.flush()
        await db.refresh(history)
        return history

    @staticmethod
    async def get_history(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[TicketHistory]:
        """Fetch the full history for a ticket, newest first, with actor loaded.

        Args:
            ticket_id: Target ticket.
            tenant_id: Owning tenant.
            db: Active async session.

        Returns:
            List of TicketHistory ordered by ``created_at`` DESC.
        """
        from app.models.user import User  # avoid circular import at module level

        result = await db.execute(
            select(TicketHistory)
            .options(selectinload(TicketHistory.actor))
            .where(
                and_(
                    TicketHistory.ticket_id == ticket_id,
                    TicketHistory.tenant_id == tenant_id,
                )
            )
            .order_by(TicketHistory.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Attachment helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def list_attachments(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[TicketAttachment]:
        """Fetch all attachments for a ticket ordered by creation date."""
        result = await db.execute(
            select(TicketAttachment)
            .where(
                and_(
                    TicketAttachment.ticket_id == ticket_id,
                    TicketAttachment.tenant_id == tenant_id,
                )
            )
            .order_by(TicketAttachment.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_attachment(
        attachment_id: uuid.UUID,
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> TicketAttachment | None:
        """Fetch a single attachment belonging to a ticket in the tenant."""
        result = await db.execute(
            select(TicketAttachment)
            .where(
                and_(
                    TicketAttachment.id == attachment_id,
                    TicketAttachment.ticket_id == ticket_id,
                    TicketAttachment.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_attachment(
        data: dict[str, Any],
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> TicketAttachment:
        """Persist a new attachment record.

        Args:
            data: Field values for the attachment.
            tenant_id: Owning tenant.
            db: Active async session.

        Returns:
            Newly created TicketAttachment instance.
        """
        attachment = TicketAttachment(tenant_id=tenant_id, **data)
        db.add(attachment)
        await db.flush()
        await db.refresh(attachment)
        return attachment
