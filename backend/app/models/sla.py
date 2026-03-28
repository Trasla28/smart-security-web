import uuid

from sqlalchemy import Boolean, String, Integer, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SLA(BaseModel):
    __tablename__ = "slas"

    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    response_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category | None"] = relationship("Category", foreign_keys=[category_id])
