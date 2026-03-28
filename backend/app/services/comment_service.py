"""Business-logic service for ticket comment operations."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate

COMMENT_EDIT_WINDOW_MINUTES = 5


class CommentService:
    """Service layer for ticket comment business operations."""

    @staticmethod
    async def add_comment(
        ticket_id: uuid.UUID,
        data: CommentCreate,
        author_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> CommentResponse:
        """Add a comment to a ticket.

        Args:
            ticket_id: Target ticket UUID.
            data: Validated comment create payload.
            author_id: UUID of the commenting user.
            tenant_id: Owning tenant.
            user: Authenticated user (role-based restrictions applied).
            db: Active async session.

        Returns:
            CommentResponse with full author details.

        Raises:
            HTTPException 403: If a requester tries to post an internal comment.
            HTTPException 404: If the ticket is not found.
        """
        # Requesters cannot post internal comments
        if user.role == "requester" and data.is_internal:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Requesters cannot create internal comments",
            )

        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        comment = await CommentRepository.create(
            {
                "ticket_id": ticket_id,
                "tenant_id": tenant_id,
                "author_id": author_id,
                "body": data.body,
                "is_internal": data.is_internal,
            },
            db,
        )

        # Record history
        await TicketRepository.add_history(
            ticket_id=ticket_id,
            tenant_id=tenant_id,
            actor_id=author_id,
            action="comment_added",
            old_value=None,
            new_value={"comment_id": str(comment.id), "is_internal": data.is_internal},
            db=db,
        )

        # Reload with author
        comment = await CommentRepository.get_by_id(comment.id, ticket_id, tenant_id, db)

        # Notify relevant parties (skip internal comments for requesters)
        if not data.is_internal:
            from app.services.notification_service import NotificationService

            notify_ids: set[uuid.UUID] = set()
            if ticket.requester_id:
                notify_ids.add(ticket.requester_id)
            if ticket.assigned_to:
                notify_ids.add(ticket.assigned_to)
            notify_ids.discard(author_id)  # don't notify the commenter

            for uid in notify_ids:
                await NotificationService.create_and_send(
                    user_id=uid,
                    tenant_id=tenant_id,
                    notification_type="comment_added",
                    title=f"Nuevo comentario en ticket #{ticket.ticket_number}",
                    db=db,
                    ticket_id=ticket_id,
                    body=data.body[:200] if data.body else None,
                )

        return CommentResponse.model_validate(comment)

    @staticmethod
    async def list_comments(
        ticket_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> list[CommentResponse]:
        """List all comments for a ticket.

        Requesters only see public comments; agents/supervisors/admins see all.

        Args:
            ticket_id: Target ticket UUID.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            List of CommentResponse ordered by creation time (ascending).
        """
        ticket = await TicketRepository.get_by_id(ticket_id, tenant_id, db)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        include_internal = user.role != "requester"
        comments = await CommentRepository.get_list(
            ticket_id, tenant_id, db, include_internal=include_internal
        )
        return [CommentResponse.model_validate(c) for c in comments]

    @staticmethod
    async def edit_comment(
        comment_id: uuid.UUID,
        ticket_id: uuid.UUID,
        data: CommentUpdate,
        tenant_id: uuid.UUID,
        user: User,
        db: AsyncSession,
    ) -> CommentResponse:
        """Edit an existing comment within the allowed time window.

        Only the original author may edit their comment, and only within the
        first ``COMMENT_EDIT_WINDOW_MINUTES`` minutes after creation.

        Args:
            comment_id: Target comment UUID.
            ticket_id: Owning ticket UUID.
            data: Validated update payload.
            tenant_id: Owning tenant.
            user: Authenticated user.
            db: Active async session.

        Returns:
            Updated CommentResponse.

        Raises:
            HTTPException 403: If the user is not the author or the edit window has expired.
            HTTPException 404: If the comment is not found.
        """
        comment = await CommentRepository.get_by_id(comment_id, ticket_id, tenant_id, db)
        if comment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        if comment.author_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author can edit this comment",
            )

        created = comment.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        edit_deadline = created + timedelta(minutes=COMMENT_EDIT_WINDOW_MINUTES)
        if datetime.now(timezone.utc) > edit_deadline:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Comments can only be edited within {COMMENT_EDIT_WINDOW_MINUTES} minutes of creation",
            )

        comment = await CommentRepository.update(comment, {"body": data.body}, db)
        return CommentResponse.model_validate(comment)
