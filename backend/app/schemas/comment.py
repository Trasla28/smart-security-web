"""Pydantic schemas for ticket comment operations."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ticket import UserBrief


class CommentCreate(BaseModel):
    """Payload to add a new comment to a ticket."""

    body: str = Field(..., min_length=1)
    is_internal: bool = False


class CommentUpdate(BaseModel):
    """Payload to edit an existing comment."""

    body: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    """Full comment representation returned from endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime

    author: UserBrief | None = None
