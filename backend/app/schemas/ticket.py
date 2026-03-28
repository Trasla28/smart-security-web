"""Pydantic schemas for ticket-related operations."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserBrief(BaseModel):
    """Lightweight user representation for embedded use."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    avatar_url: str | None = None


class AreaBrief(BaseModel):
    """Lightweight area representation for embedded use."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class CategoryBrief(BaseModel):
    """Lightweight category representation for embedded use."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class TicketCreate(BaseModel):
    """Payload to create a new ticket."""

    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=1)
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    category_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    notify_user_ids: list[uuid.UUID] | None = None


class TicketUpdate(BaseModel):
    """Payload to partially update a ticket's metadata."""

    title: str | None = Field(default=None, min_length=3, max_length=500)
    description: str | None = None
    priority: str | None = Field(default=None, pattern="^(low|medium|high|urgent)$")
    category_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None


class TicketStatusChange(BaseModel):
    """Payload to change ticket status."""

    status: str = Field(..., pattern="^(open|in_progress|pending|escalated|resolved|closed)$")


class TicketAssign(BaseModel):
    """Payload to assign a ticket to an agent."""

    agent_id: uuid.UUID


class TicketEscalate(BaseModel):
    """Payload to escalate a ticket."""

    reason: str = Field(..., min_length=1)
    area_id: uuid.UUID | None = None


class TicketReopen(BaseModel):
    """Payload to reopen a resolved or closed ticket."""

    reason: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TicketResponse(BaseModel):
    """Full ticket representation returned from endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    ticket_number: str
    title: str
    description: str
    status: str
    priority: str

    category_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    requester_id: uuid.UUID
    assigned_to: uuid.UUID | None = None

    sla_id: uuid.UUID | None = None
    sla_due_at: datetime | None = None
    sla_breached: bool
    first_response_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    recurring_template_id: uuid.UUID | None = None
    is_recurring_instance: bool
    reopen_count: int

    created_at: datetime
    updated_at: datetime

    # Computed SLA fields
    sla_status: str | None = None  # 'ok' | 'warning' | 'breached' | None
    sla_percentage: float | None = None  # 0-100, % of SLA time elapsed

    # Nested objects
    requester: UserBrief | None = None
    assignee: UserBrief | None = None
    area: AreaBrief | None = None
    category: CategoryBrief | None = None


class TicketListItem(BaseModel):
    """Condensed ticket representation for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_number: str
    title: str
    status: str
    priority: str
    sla_due_at: datetime | None = None
    sla_breached: bool
    sla_status: str | None = None
    created_at: datetime
    updated_at: datetime

    requester: UserBrief | None = None
    assignee: UserBrief | None = None
    area: AreaBrief | None = None
    category: CategoryBrief | None = None


class HistoryActorBrief(BaseModel):
    """Lightweight actor for history entries."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class TicketHistoryResponse(BaseModel):
    """Ticket history entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    action: str
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    created_at: datetime

    actor: HistoryActorBrief | None = None


class AttachmentResponse(BaseModel):
    """Ticket attachment response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    comment_id: uuid.UUID | None = None
    filename: str
    file_size: int
    mime_type: str
    uploaded_by: uuid.UUID
    created_at: datetime

    # Download URL returned when generating download links
    download_url: str | None = None
