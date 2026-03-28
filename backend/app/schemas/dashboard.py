"""Pydantic schemas for dashboard and report responses."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_open: int
    total_in_progress: int
    total_pending: int
    total_escalated: int
    total_resolved_today: int
    total_closed_today: int
    avg_resolution_hours: float | None = None
    sla_compliance_pct: float | None = None
    new_today: int


class TicketsByAreaItem(BaseModel):
    area_id: uuid.UUID | None = None
    area_name: str
    total: int
    open: int
    in_progress: int
    resolved: int


class TicketsByStatusItem(BaseModel):
    status: str
    count: int
    percentage: float


class SLAComplianceResponse(BaseModel):
    total_with_sla: int
    resolved_on_time: int
    compliance_pct: float
    by_priority: list[dict]


class AgentPerformanceItem(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    assigned_total: int
    resolved_total: int
    avg_resolution_hours: float | None = None
    sla_compliance_pct: float | None = None


class UserPerformanceItem(BaseModel):
    user_id: uuid.UUID
    user_name: str
    user_email: str
    role: str
    # Volumen
    assigned_total: int
    resolved_total: int
    closed_total: int
    active_total: int
    # Tiempos
    avg_resolution_hours: float | None = None
    avg_first_response_hours: float | None = None
    # SLA
    sla_breached_total: int
    sla_compliance_pct: float | None = None
    # Calidad
    tickets_reopened: int
    reopen_rate_pct: float | None = None
    # Score compuesto (0-100) para decisión de bonos
    performance_score: int
    score_label: str  # "Excelente" | "Bueno" | "Regular" | "Bajo"


class UrgencyAbuseItem(BaseModel):
    user_id: uuid.UUID
    user_name: str
    area_name: str | None = None
    total_tickets: int
    urgent_tickets: int
    urgent_pct: float
    prev_period_pct: float | None = None
    trend: str  # "improved" | "worsened" | "stable"


class WeeklyReportResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    summary: DashboardSummary
    tickets_by_area: list[TicketsByAreaItem]
    tickets_by_status: list[TicketsByStatusItem]
    top_agents: list[AgentPerformanceItem]
