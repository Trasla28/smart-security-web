import uuid

from sqlalchemy import Boolean, String, Text, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Area(BaseModel):
    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_areas_tenant_name"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    manager: Mapped["User | None"] = relationship("User", foreign_keys=[manager_id])
    members: Mapped[list["UserArea"]] = relationship("UserArea", back_populates="area")


class UserArea(BaseModel):
    __tablename__ = "user_areas"
    __table_args__ = (UniqueConstraint("user_id", "area_id", name="uq_user_areas_user_area"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="areas")
    area: Mapped["Area"] = relationship("Area", back_populates="members")
