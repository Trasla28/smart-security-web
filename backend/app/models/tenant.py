import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, ForeignKey, String, Integer, Time, ARRAY, Text, DateTime, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    config: Mapped["TenantConfig"] = relationship("TenantConfig", back_populates="tenant", uselist=False)


class TenantConfig(Base, TimestampMixin):
    __tablename__ = "tenant_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)

    # Branding
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), default="#1565C0", nullable=False)

    # Auth
    auth_method: Mapped[str] = mapped_column(String(20), default="local", nullable=False)
    azure_tenant_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    azure_client_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    azure_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Behavior
    auto_close_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    urgency_abuse_threshold: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    urgency_report_visible_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Schedule
    timezone: Mapped[str] = mapped_column(String(50), default="America/Bogota", nullable=False)
    working_hours_start: Mapped[time] = mapped_column(Time, default=time(8, 0), nullable=False)
    working_hours_end: Mapped[time] = mapped_column(Time, default=time(18, 0), nullable=False)
    working_days: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=[1, 2, 3, 4, 5], nullable=False)

    # Notifications
    weekly_report_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekly_report_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    weekly_report_recipients: Mapped[list[str]] = mapped_column(ARRAY(String), default=[], nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="config")
