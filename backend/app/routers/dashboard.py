"""Dashboard and report endpoints."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, TenantId
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    AgentPerformanceItem,
    DashboardSummary,
    SLAComplianceResponse,
    TicketsByAreaItem,
    TicketsByStatusItem,
    UrgencyAbuseItem,
    UserPerformanceItem,
    WeeklyReportResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_dashboard_access(current_user: CurrentUser) -> CurrentUser:
    """Supervisors and admins have full dashboard access; agents/requesters see only their own."""
    return current_user


# ---------------------------------------------------------------------------
# Dashboard endpoints
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> DashboardSummary:
    """Return general ticket counts and performance indicators.

    Args:
        days: Look-back window in days for averages and SLA compliance.
    """
    data = await DashboardRepository.get_summary(tenant_id, db, date_range_days=days)
    return DashboardSummary(**data)


@router.get("/tickets-by-area", response_model=list[TicketsByAreaItem])
async def get_tickets_by_area(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[TicketsByAreaItem]:
    """Return ticket distribution aggregated by area.

    Args:
        days: Look-back window in days.
    """
    rows = await DashboardRepository.get_tickets_by_area(tenant_id, db, date_range_days=days)
    return [TicketsByAreaItem(**row) for row in rows]


@router.get("/tickets-by-status", response_model=list[TicketsByStatusItem])
async def get_tickets_by_status(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> list[TicketsByStatusItem]:
    """Return count and percentage of all active tickets grouped by status."""
    rows = await DashboardRepository.get_tickets_by_status(tenant_id, db)
    return [TicketsByStatusItem(**row) for row in rows]


@router.get("/sla-compliance", response_model=SLAComplianceResponse)
async def get_sla_compliance(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> SLAComplianceResponse:
    """Return overall SLA compliance rate and a breakdown by priority.

    Args:
        days: Look-back window in days.
    """
    if current_user.role not in ("admin", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SLA compliance report is only available to supervisors and admins",
        )
    data = await DashboardRepository.get_sla_compliance(tenant_id, db, date_range_days=days)
    return SLAComplianceResponse(**data)


@router.get("/agent-performance", response_model=list[AgentPerformanceItem])
async def get_agent_performance(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[AgentPerformanceItem]:
    """Return per-agent metrics: volume, resolution time and SLA compliance.

    Only supervisors and admins can access this endpoint.

    Args:
        days: Look-back window in days.
    """
    if current_user.role not in ("admin", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent performance report is only available to supervisors and admins",
        )
    rows = await DashboardRepository.get_agent_performance(tenant_id, db, date_range_days=days)
    return [AgentPerformanceItem(**row) for row in rows]


@router.get("/user-performance", response_model=list[UserPerformanceItem])
async def get_user_performance(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[UserPerformanceItem]:
    """Detailed per-agent performance for management/bonus decisions."""
    if current_user.role not in ("admin", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User performance report is only available to supervisors and admins",
        )
    rows = await DashboardRepository.get_user_performance(tenant_id, db, date_range_days=days)
    return [UserPerformanceItem(**row) for row in rows]


@router.get("/urgency-abuse", response_model=list[UrgencyAbuseItem])
async def get_urgency_abuse(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[UrgencyAbuseItem]:
    """Return urgency abuse report: % of urgent tickets per requester with trend.

    Access is restricted to the user configured in
    ``tenant_config.urgency_report_visible_to`` and admins.

    Args:
        days: Look-back window in days.
    """
    from sqlalchemy import select

    from app.models.tenant import TenantConfig

    cfg_result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    config = cfg_result.scalar_one_or_none()

    allowed = current_user.role == "admin"
    if config and config.urgency_report_visible_to == current_user.id:
        allowed = True

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view the urgency abuse report",
        )

    rows = await DashboardRepository.get_urgency_abuse(tenant_id, db, date_range_days=days)
    return [UrgencyAbuseItem(**row) for row in rows]


@router.get("/weekly-report", response_model=WeeklyReportResponse)
async def get_weekly_report(
    current_user: CurrentUser,
    tenant_id: TenantId,
    db: AsyncSession = Depends(get_db),
) -> WeeklyReportResponse:
    """Return the data that would be included in the weekly email report.

    Only supervisors and admins can access this endpoint.
    """
    if current_user.role not in ("admin", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Weekly report is only available to supervisors and admins",
        )

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=7)

    summary_data = await DashboardRepository.get_summary(tenant_id, db, date_range_days=7)
    area_data = await DashboardRepository.get_tickets_by_area(tenant_id, db, date_range_days=7)
    status_data = await DashboardRepository.get_tickets_by_status(tenant_id, db)
    agent_data = await DashboardRepository.get_agent_performance(tenant_id, db, date_range_days=7)

    return WeeklyReportResponse(
        period_start=period_start,
        period_end=now,
        summary=DashboardSummary(**summary_data),
        tickets_by_area=[TicketsByAreaItem(**row) for row in area_data],
        tickets_by_status=[TicketsByStatusItem(**row) for row in status_data],
        top_agents=[AgentPerformanceItem(**row) for row in agent_data[:5]],
    )
