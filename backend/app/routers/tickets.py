"""FastAPI router for ticket-related endpoints."""
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, TenantId, require_role
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.ticket import (
    AttachmentResponse,
    TicketAssign,
    TicketCreate,
    TicketEscalate,
    TicketHistoryResponse,
    TicketListItem,
    TicketReopen,
    TicketResponse,
    TicketStatusChange,
    TicketUpdate,
)
from app.services.comment_service import CommentService
from app.services.ticket_service import TicketService
from app.utils.storage import save_file
from app.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Tickets – CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=dict[str, Any], summary="List tickets")
async def list_tickets(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    area_id: uuid.UUID | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    requester_id: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sort_by: str = Query(default="created_at", pattern="^(created_at|priority)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Return a paginated list of tickets visible to the authenticated user.

    Visibility is enforced automatically based on role:
    - **requester** – only their own tickets
    - **agent** – tickets in their assigned areas
    - **supervisor / admin** – all tickets in the tenant
    """
    return await TicketService.list_tickets(
        tenant_id=tenant_id,
        user=current_user,
        db=db,
        status_filter=status_filter,
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


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket",
)
async def create_ticket(
    payload: TicketCreate,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Create a new support ticket.

    Category routing and SLA assignment are applied automatically.
    """
    return await TicketService.create_ticket(
        data=payload,
        requester_id=current_user.id,
        tenant_id=tenant_id,
        db=db,
    )


@router.get("/{ticket_id}", response_model=TicketResponse, summary="Get a single ticket")
async def get_ticket(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Retrieve full details of a single ticket."""
    return await TicketService.get_ticket(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.patch("/{ticket_id}", response_model=TicketResponse, summary="Update ticket metadata")
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Partially update a ticket's metadata (title, description, priority, category, area)."""
    return await TicketService.update_ticket(
        ticket_id=ticket_id,
        data=payload,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ticket (admin only)",
)
async def delete_ticket(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> None:
    """Soft-delete a ticket. Restricted to administrators."""
    await TicketService.delete_ticket(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# Tickets – Status transitions
# ---------------------------------------------------------------------------


@router.post("/{ticket_id}/status", response_model=TicketResponse, summary="Change ticket status")
async def change_ticket_status(
    ticket_id: uuid.UUID,
    payload: TicketStatusChange,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Transition a ticket to a new status (e.g. in_progress, pending)."""
    return await TicketService.change_status(
        ticket_id=ticket_id,
        new_status=payload.status,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.post("/{ticket_id}/assign", response_model=TicketResponse, summary="Assign ticket to agent")
async def assign_ticket(
    ticket_id: uuid.UUID,
    payload: TicketAssign,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Assign a ticket to a specific agent."""
    return await TicketService.assign_ticket(
        ticket_id=ticket_id,
        data=payload,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.post("/{ticket_id}/escalate", response_model=TicketResponse, summary="Escalate a ticket")
async def escalate_ticket(
    ticket_id: uuid.UUID,
    payload: TicketEscalate,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Escalate a ticket, with an optional area transfer."""
    return await TicketService.escalate_ticket(
        ticket_id=ticket_id,
        data=payload,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.post("/{ticket_id}/resolve", response_model=TicketResponse, summary="Resolve a ticket")
async def resolve_ticket(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Mark a ticket as resolved."""
    return await TicketService.resolve_ticket(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.post("/{ticket_id}/close", response_model=TicketResponse, summary="Close a ticket")
async def close_ticket(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Close a resolved ticket."""
    return await TicketService.close_ticket(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.post("/{ticket_id}/reopen", response_model=TicketResponse, summary="Reopen a ticket")
async def reopen_ticket(
    ticket_id: uuid.UUID,
    payload: TicketReopen,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Reopen a resolved or closed ticket. A reason is required."""
    return await TicketService.reopen_ticket(
        ticket_id=ticket_id,
        data=payload,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment",
)
async def add_comment(
    ticket_id: uuid.UUID,
    payload: CommentCreate,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Add a comment to a ticket. Requesters cannot post internal notes."""
    return await CommentService.add_comment(
        ticket_id=ticket_id,
        data=payload,
        author_id=current_user.id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.get(
    "/{ticket_id}/comments",
    response_model=list[CommentResponse],
    summary="List comments",
)
async def list_comments(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> list[CommentResponse]:
    """Return all visible comments for a ticket."""
    return await CommentService.list_comments(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.patch(
    "/{ticket_id}/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Edit a comment",
)
async def edit_comment(
    ticket_id: uuid.UUID,
    comment_id: uuid.UUID,
    payload: CommentUpdate,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Edit an existing comment (author only, within 5 minutes of creation)."""
    return await CommentService.edit_comment(
        comment_id=comment_id,
        ticket_id=ticket_id,
        data=payload,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@router.get(
    "/{ticket_id}/history",
    response_model=list[TicketHistoryResponse],
    summary="Get ticket history",
)
async def get_history(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> list[TicketHistoryResponse]:
    """Return the full audit trail for a ticket, newest entry first."""
    return await TicketService.get_history(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


@router.get(
    "/{ticket_id}/attachments",
    response_model=list[AttachmentResponse],
    summary="List attachments",
)
async def list_attachments(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> list[AttachmentResponse]:
    """List all attachments for a ticket with signed download URLs."""
    return await TicketService.list_attachments(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload attachment",
)
async def upload_attachment(
    ticket_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    comment_id: uuid.UUID | None = Form(None),
) -> AttachmentResponse:
    """Upload a file attachment to a ticket. Allowed types: PDF, Word, Excel, JPG, PNG, WEBP. Max 10 MB."""
    file_path, file_size, mime_type = await save_file(
        file=file,
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        storage_path=settings.STORAGE_PATH,
    )
    return await TicketService.upload_attachment(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        user=current_user,
        filename=file.filename or "upload",
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        db=db,
        comment_id=comment_id,
    )


@router.get(
    "/{ticket_id}/attachments/{attachment_id}/download",
    response_model=AttachmentResponse,
    summary="Get signed download URL",
)
async def get_download_url(
    ticket_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> AttachmentResponse:
    """Generate a short-lived signed URL to download an attachment."""
    return await TicketService.get_download_url(
        ticket_id=ticket_id,
        attachment_id=attachment_id,
        tenant_id=tenant_id,
        user=current_user,
        db=db,
    )
