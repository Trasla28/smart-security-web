"""Repository layer for TicketComment model."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import TicketComment


class CommentRepository:
    """Data-access helpers for ticket comments."""

    @staticmethod
    async def get_by_id(
        comment_id: uuid.UUID,
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> TicketComment | None:
        """Fetch a single non-deleted comment scoped to a ticket and tenant."""
        result = await db.execute(
            select(TicketComment)
            .options(selectinload(TicketComment.author))
            .where(
                and_(
                    TicketComment.id == comment_id,
                    TicketComment.ticket_id == ticket_id,
                    TicketComment.tenant_id == tenant_id,
                    TicketComment.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        include_internal: bool = True,
    ) -> list[TicketComment]:
        """Return all non-deleted comments for a ticket.

        Args:
            ticket_id: Target ticket.
            tenant_id: Owning tenant.
            db: Active async session.
            include_internal: When ``False``, internal-only comments are excluded.

        Returns:
            List of TicketComment ordered by ``created_at`` ASC.
        """
        conditions = [
            TicketComment.ticket_id == ticket_id,
            TicketComment.tenant_id == tenant_id,
            TicketComment.deleted_at.is_(None),
        ]
        if not include_internal:
            conditions.append(TicketComment.is_internal.is_(False))

        result = await db.execute(
            select(TicketComment)
            .options(selectinload(TicketComment.author))
            .where(and_(*conditions))
            .order_by(TicketComment.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(data: dict[str, Any], db: AsyncSession) -> TicketComment:
        """Persist a new comment.

        Args:
            data: All required field values (must include ``tenant_id``).
            db: Active async session.

        Returns:
            Newly created TicketComment instance.
        """
        comment = TicketComment(**data)
        db.add(comment)
        await db.flush()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def update(
        comment: TicketComment,
        data: dict[str, Any],
        db: AsyncSession,
    ) -> TicketComment:
        """Apply field updates to an existing comment.

        Args:
            comment: The ORM instance to update.
            data: Mapping of field names to new values.
            db: Active async session.

        Returns:
            Updated TicketComment instance.
        """
        for key, value in data.items():
            setattr(comment, key, value)
        await db.flush()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def soft_delete(comment: TicketComment, db: AsyncSession) -> None:
        """Mark a comment as deleted without removing the row."""
        comment.deleted_at = datetime.now(timezone.utc)
        await db.flush()
