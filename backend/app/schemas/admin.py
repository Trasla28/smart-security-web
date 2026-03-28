"""Pydantic schemas for admin, users, areas, categories, SLAs, config and recurring templates."""
import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field("requester", pattern="^(admin|supervisor|agent|requester)$")
    password: str | None = Field(None, min_length=8)
    area_ids: list[uuid.UUID] = []
    primary_area_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    role: str | None = Field(None, pattern="^(admin|supervisor|agent|requester)$")
    is_active: bool | None = None
    area_ids: list[uuid.UUID] | None = None
    primary_area_id: uuid.UUID | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_archived: bool
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Area schemas
# ---------------------------------------------------------------------------


class AreaCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    manager_id: uuid.UUID | None = None


class AreaUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    manager_id: uuid.UUID | None = None
    is_active: bool | None = None


class AreaMemberAdd(BaseModel):
    user_id: uuid.UUID
    is_primary: bool = False


class AreaMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: str
    is_primary: bool = False


class AreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None = None
    manager_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Category schemas
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    default_area_id: uuid.UUID | None = None
    default_agent_id: uuid.UUID | None = None
    requires_approval: bool = False
    approver_role: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    default_area_id: uuid.UUID | None = None
    default_agent_id: uuid.UUID | None = None
    requires_approval: bool | None = None
    approver_role: str | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None = None
    default_area_id: uuid.UUID | None = None
    default_agent_id: uuid.UUID | None = None
    requires_approval: bool
    approver_role: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# SLA schemas
# ---------------------------------------------------------------------------


class SLACreate(BaseModel):
    category_id: uuid.UUID | None = None
    priority: str | None = Field(None, pattern="^(low|medium|high|urgent)$")
    response_hours: int = Field(..., ge=0)
    resolution_hours: int = Field(..., ge=1)


class SLAUpdate(BaseModel):
    response_hours: int | None = Field(None, ge=0)
    resolution_hours: int | None = Field(None, ge=1)
    is_active: bool | None = None


class SLAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    category_id: uuid.UUID | None = None
    priority: str | None = None
    response_hours: int
    resolution_hours: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Tenant Config schemas
# ---------------------------------------------------------------------------


class TenantConfigUpdate(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = Field(None, pattern="^#[0-9a-fA-F]{6}$")
    auto_close_days: int | None = Field(None, ge=1, le=365)
    urgency_abuse_threshold: int | None = Field(None, ge=1, le=100)
    urgency_report_visible_to: uuid.UUID | None = None
    timezone: str | None = None
    working_hours_start: time | None = None
    working_hours_end: time | None = None
    working_days: list[int] | None = None
    weekly_report_enabled: bool | None = None
    weekly_report_day: int | None = Field(None, ge=1, le=7)
    weekly_report_recipients: list[str] | None = None


class TenantConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    logo_url: str | None = None
    primary_color: str
    auth_method: str
    auto_close_days: int
    urgency_abuse_threshold: int
    urgency_report_visible_to: uuid.UUID | None = None
    timezone: str
    working_hours_start: time
    working_hours_end: time
    working_days: list[int]
    weekly_report_enabled: bool
    weekly_report_day: int
    weekly_report_recipients: list[str]
    updated_at: datetime


# ---------------------------------------------------------------------------
# Recurring Template schemas
# ---------------------------------------------------------------------------


class RecurringTemplateCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str | None = None
    category_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")
    assigned_to: uuid.UUID | None = None
    recurrence_type: str = Field(..., pattern="^(daily|weekly|monthly|day_of_month)$")
    recurrence_value: int | None = Field(None, ge=1, le=31)
    recurrence_day: int | None = Field(None, ge=0, le=6)
    if_holiday_action: str = Field(
        "previous_business_day",
        pattern="^(previous_business_day|next_business_day|same_day)$",
    )


class RecurringTemplateUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=500)
    description: str | None = None
    category_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    priority: str | None = Field(None, pattern="^(low|medium|high|urgent)$")
    assigned_to: uuid.UUID | None = None
    recurrence_type: str | None = Field(None, pattern="^(daily|weekly|monthly|day_of_month)$")
    recurrence_value: int | None = Field(None, ge=1, le=31)
    recurrence_day: int | None = Field(None, ge=0, le=6)
    if_holiday_action: str | None = Field(
        None,
        pattern="^(previous_business_day|next_business_day|same_day)$",
    )
    is_active: bool | None = None


class RecurringTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None = None
    category_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    priority: str
    assigned_to: uuid.UUID | None = None
    recurrence_type: str
    recurrence_value: int | None = None
    recurrence_day: int | None = None
    if_holiday_action: str
    is_active: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
