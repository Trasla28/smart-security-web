import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, Integer, DateTime, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class RecurringTemplate(BaseModel):
    __tablename__ = "recurring_templates"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    area_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    recurrence_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recurrence_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurrence_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    if_holiday_action: Mapped[str] = mapped_column(String(20), default="previous_business_day", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    category: Mapped["Category | None"] = relationship("Category", foreign_keys=[category_id])
    area: Mapped["Area | None"] = relationship("Area", foreign_keys=[area_id])
    assignee: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to])
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
