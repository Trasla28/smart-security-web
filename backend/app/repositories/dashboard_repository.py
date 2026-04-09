"""Repository for dashboard aggregate metric queries."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area, UserArea
from app.models.ticket import Ticket
from app.models.user import User


class DashboardRepository:
    """Optimized aggregate SQL queries for dashboard metrics.

    All queries always scope by ``tenant_id`` and respect soft-delete.
    """

    @staticmethod
    async def get_summary(
        tenant_id: uuid.UUID,
        db: AsyncSession,
        date_range_days: int = 30,
    ) -> dict:
        """Return general ticket counts and performance indicators.

        Args:
            tenant_id: Owning tenant.
            db: Active async session.
            date_range_days: Look-back window for avg resolution and SLA compliance.

        Returns:
            Dict matching ``DashboardSummary`` schema fields.
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = now - timedelta(days=date_range_days)

        # --- Counts by status (active tickets only) ---
        status_result = await db.execute(
            select(Ticket.status, func.count(Ticket.id).label("cnt"))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .group_by(Ticket.status)
        )
        status_counts: dict[str, int] = {row.status: row.cnt for row in status_result}

        # --- New tickets created today ---
        new_today_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.created_at >= today_start)
        )
        new_today: int = new_today_result.scalar_one() or 0

        # --- Resolved today ---
        resolved_today_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.resolved_at >= today_start)
        )
        resolved_today: int = resolved_today_result.scalar_one() or 0

        # --- Closed today ---
        closed_today_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.closed_at >= today_start)
        )
        closed_today: int = closed_today_result.scalar_one() or 0

        # --- Average resolution time (hours) in the look-back period ---
        avg_result = await db.execute(
            select(
                func.avg(
                    func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600
                ).label("avg_hours")
            )
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.resolved_at.is_not(None))
            .where(Ticket.resolved_at >= period_start)
        )
        avg_hours = avg_result.scalar_one()

        # --- SLA compliance ---
        sla_total_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.sla_id.is_not(None))
            .where(Ticket.status.in_(["resolved", "closed"]))
            .where(Ticket.resolved_at >= period_start)
        )
        sla_total: int = sla_total_result.scalar_one() or 0

        sla_ok_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.sla_id.is_not(None))
            .where(Ticket.sla_breached.is_(False))
            .where(Ticket.status.in_(["resolved", "closed"]))
            .where(Ticket.resolved_at >= period_start)
        )
        sla_ok: int = sla_ok_result.scalar_one() or 0
        compliance_pct = round(sla_ok / sla_total * 100, 1) if sla_total > 0 else None

        return {
            "total_open": status_counts.get("open", 0),
            "total_in_progress": status_counts.get("in_progress", 0),
            "total_pending": status_counts.get("pending", 0),
            "total_escalated": status_counts.get("escalated", 0),
            "total_resolved_today": resolved_today,
            "total_closed_today": closed_today,
            "avg_resolution_hours": round(float(avg_hours), 2) if avg_hours else None,
            "sla_compliance_pct": compliance_pct,
            "new_today": new_today,
        }

    @staticmethod
    async def get_tickets_by_area(
        tenant_id: uuid.UUID,
        db: AsyncSession,
        date_range_days: int = 30,
    ) -> list[dict]:
        """Return ticket distribution aggregated by area.

        Args:
            tenant_id: Owning tenant.
            db: Active async session.
            date_range_days: Look-back window for counts.

        Returns:
            List of dicts matching ``TicketsByAreaItem`` schema fields.
        """
        period_start = datetime.now(timezone.utc) - timedelta(days=date_range_days)

        result = await db.execute(
            select(
                Area.id.label("area_id"),
                Area.name.label("area_name"),
                func.count(Ticket.id).label("total"),
                func.sum(case((Ticket.status == "open", 1), else_=0)).label("open"),
                func.sum(case((Ticket.status == "in_progress", 1), else_=0)).label("in_progress"),
                func.sum(
                    case((Ticket.status.in_(["resolved", "closed"]), 1), else_=0)
                ).label("resolved"),
            )
            .outerjoin(
                Ticket,
                and_(
                    Ticket.area_id == Area.id,
                    Ticket.tenant_id == tenant_id,
                    Ticket.deleted_at.is_(None),
                    Ticket.created_at >= period_start,
                ),
            )
            .where(Area.tenant_id == tenant_id)
            .where(Area.is_active.is_(True))
            .group_by(Area.id, Area.name)
            .order_by(func.count(Ticket.id).desc())
        )

        return [
            {
                "area_id": row.area_id,
                "area_name": row.area_name,
                "total": row.total or 0,
                "open": row.open or 0,
                "in_progress": row.in_progress or 0,
                "resolved": row.resolved or 0,
            }
            for row in result.all()
        ]

    @staticmethod
    async def get_tickets_by_status(
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Return count and percentage of all active tickets by status.

        Args:
            tenant_id: Owning tenant.
            db: Active async session.

        Returns:
            List of dicts matching ``TicketsByStatusItem`` schema fields.
        """
        result = await db.execute(
            select(Ticket.status, func.count(Ticket.id).label("cnt"))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .group_by(Ticket.status)
        )
        rows = result.all()
        total = sum(r.cnt for r in rows) or 1
        return [
            {
                "status": row.status,
                "count": row.cnt,
                "percentage": round(row.cnt / total * 100, 1),
            }
            for row in rows
        ]

    @staticmethod
    async def get_sla_compliance(
        tenant_id: uuid.UUID,
        db: AsyncSession,
        date_range_days: int = 30,
    ) -> dict:
        """Return overall SLA compliance and a breakdown by priority.

        Args:
            tenant_id: Owning tenant.
            db: Active async session.
            date_range_days: Look-back window.

        Returns:
            Dict matching ``SLAComplianceResponse`` schema fields.
        """
        period_start = datetime.now(timezone.utc) - timedelta(days=date_range_days)

        total_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.sla_id.is_not(None))
            .where(Ticket.status.in_(["resolved", "closed"]))
            .where(Ticket.resolved_at >= period_start)
            .where(Ticket.deleted_at.is_(None))
        )
        total_with_sla: int = total_result.scalar_one() or 0

        ok_result = await db.execute(
            select(func.count(Ticket.id))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.sla_id.is_not(None))
            .where(Ticket.sla_breached.is_(False))
            .where(Ticket.status.in_(["resolved", "closed"]))
            .where(Ticket.resolved_at >= period_start)
            .where(Ticket.deleted_at.is_(None))
        )
        resolved_on_time: int = ok_result.scalar_one() or 0
        compliance_pct = (
            round(resolved_on_time / total_with_sla * 100, 1) if total_with_sla > 0 else 0.0
        )

        # Breakdown by priority
        bp_result = await db.execute(
            select(
                Ticket.priority,
                func.count(Ticket.id).label("total"),
                func.sum(case((Ticket.sla_breached.is_(False), 1), else_=0)).label("on_time"),
            )
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.sla_id.is_not(None))
            .where(Ticket.status.in_(["resolved", "closed"]))
            .where(Ticket.resolved_at >= period_start)
            .where(Ticket.deleted_at.is_(None))
            .group_by(Ticket.priority)
        )
        by_priority = [
            {
                "priority": row.priority,
                "total": row.total,
                "on_time": row.on_time or 0,
                "compliance_pct": round((row.on_time or 0) / row.total * 100, 1)
                if row.total > 0
                else 0.0,
            }
            for row in bp_result.all()
        ]

        return {
            "total_with_sla": total_with_sla,
            "resolved_on_time": resolved_on_time,
            "compliance_pct": compliance_pct,
            "by_priority": by_priority,
        }

    @staticmethod
    async def get_agent_performance(
        tenant_id: uuid.UUID,
        db: AsyncSession,
        date_range_days: int = 30,
        area_ids: list[uuid.UUID] | None = None,
    ) -> list[dict]:
        """Per-agent metrics: volume, resolution time, SLA compliance.

        Args:
            tenant_id: Owning tenant.
            db: Active async session.
            date_range_days: Look-back window.

        Returns:
            List of dicts matching ``AgentPerformanceItem`` schema fields.
        """
        period_start = datetime.now(timezone.utc) - timedelta(days=date_range_days)

        query = (
            select(
                User.id.label("agent_id"),
                User.full_name.label("agent_name"),
                func.count(Ticket.id).label("assigned_total"),
                func.sum(
                    case((Ticket.status.in_(["resolved", "closed"]), 1), else_=0)
                ).label("resolved_total"),
                func.avg(
                    case(
                        (
                            and_(
                                Ticket.resolved_at.is_not(None),
                                Ticket.status.in_(["resolved", "closed"]),
                            ),
                            func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600,
                        ),
                        else_=None,
                    )
                ).label("avg_resolution_hours"),
                func.sum(
                    case(
                        (
                            and_(
                                Ticket.sla_id.is_not(None),
                                Ticket.status.in_(["resolved", "closed"]),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("sla_total"),
                func.sum(
                    case(
                        (
                            and_(
                                Ticket.sla_id.is_not(None),
                                Ticket.sla_breached.is_(False),
                                Ticket.status.in_(["resolved", "closed"]),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("sla_ok"),
            )
            .join(Ticket, Ticket.assigned_to == User.id)
            .where(User.tenant_id == tenant_id)
            .where(User.is_archived.is_(False))
            .where(User.deleted_at.is_(None))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.created_at >= period_start)
        )

        if area_ids:
            query = (
                query.join(UserArea, UserArea.user_id == User.id)
                .where(UserArea.area_id.in_(area_ids))
                .distinct()
            )

        result = await db.execute(
            query.group_by(User.id, User.full_name).order_by(func.count(Ticket.id).desc())
        )

        agents = []
        for row in result.all():
            sla_total: int = row.sla_total or 0
            sla_ok: int = row.sla_ok or 0
            sla_pct = round(sla_ok / sla_total * 100, 1) if sla_total > 0 else None
            agents.append(
                {
                    "agent_id": row.agent_id,
                    "agent_name": row.agent_name,
                    "assigned_total": row.assigned_total,
                    "resolved_total": row.resolved_total or 0,
                    "avg_resolution_hours": round(float(row.avg_resolution_hours), 2)
                    if row.avg_resolution_hours
                    else None,
                    "sla_compliance_pct": sla_pct,
                }
            )
        return agents

    @staticmethod
    async def get_user_performance(
        tenant_id: uuid.UUID,
        db: AsyncSession,
        date_range_days: int = 30,
    ) -> list[dict]:
        """Detailed per-agent performance metrics for management bonus decisions."""
        period_start = datetime.now(timezone.utc) - timedelta(days=date_range_days)

        result = await db.execute(
            select(
                User.id.label("user_id"),
                User.full_name.label("user_name"),
                User.email.label("user_email"),
                User.role.label("role"),
                func.count(Ticket.id).label("assigned_total"),
                func.sum(case((Ticket.status.in_(["resolved", "closed"]), 1), else_=0)).label("resolved_total"),
                func.sum(case((Ticket.status == "closed", 1), else_=0)).label("closed_total"),
                func.sum(case((~Ticket.status.in_(["resolved", "closed"]), 1), else_=0)).label("active_total"),
                func.avg(
                    case(
                        (Ticket.resolved_at.is_not(None),
                         func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600),
                        else_=None,
                    )
                ).label("avg_resolution_hours"),
                func.avg(
                    case(
                        (Ticket.first_response_at.is_not(None),
                         func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600),
                        else_=None,
                    )
                ).label("avg_first_response_hours"),
                func.sum(case((Ticket.sla_breached.is_(True), 1), else_=0)).label("sla_breached_total"),
                func.sum(
                    case((and_(Ticket.sla_id.is_not(None), Ticket.sla_breached.is_(False),
                               Ticket.status.in_(["resolved", "closed"])), 1), else_=0)
                ).label("sla_ok"),
                func.sum(
                    case((and_(Ticket.sla_id.is_not(None), Ticket.status.in_(["resolved", "closed"])), 1), else_=0)
                ).label("sla_total"),
                func.sum(
                    case((and_(Ticket.reopen_count > 0, Ticket.status.in_(["resolved", "closed"])), 1), else_=0)
                ).label("tickets_reopened"),
            )
            .join(Ticket, Ticket.assigned_to == User.id)
            .where(User.tenant_id == tenant_id)
            .where(User.is_archived.is_(False))
            .where(User.deleted_at.is_(None))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.created_at >= period_start)
            .group_by(User.id, User.full_name, User.email, User.role)
            .order_by(func.sum(case((Ticket.status.in_(["resolved", "closed"]), 1), else_=0)).desc())
        )

        items = []
        for row in result.all():
            assigned: int = row.assigned_total or 0
            resolved: int = row.resolved_total or 0
            sla_total: int = row.sla_total or 0
            sla_ok: int = row.sla_ok or 0
            sla_compliance = round(sla_ok / sla_total * 100, 1) if sla_total > 0 else None
            tickets_reopened: int = row.tickets_reopened or 0
            reopen_rate = round(tickets_reopened / resolved * 100, 1) if resolved > 0 else None
            sla_breached: int = row.sla_breached_total or 0

            # Score 0-100 for bonus decisions
            eficiencia = (resolved / max(assigned, 1)) * 40
            sla_pts = (sla_compliance / 100) * 30 if sla_compliance is not None else 15.0
            calidad = max(0.0, 20.0 - min(tickets_reopened * 5, 20))
            respuesta = max(0.0, 10.0 - min(sla_breached * 2, 10))
            score = round(eficiencia + sla_pts + calidad + respuesta)

            if score >= 90:
                label = "Excelente"
            elif score >= 75:
                label = "Bueno"
            elif score >= 60:
                label = "Regular"
            else:
                label = "Bajo"

            items.append({
                "user_id": row.user_id,
                "user_name": row.user_name,
                "user_email": row.user_email,
                "role": row.role,
                "assigned_total": assigned,
                "resolved_total": resolved,
                "closed_total": row.closed_total or 0,
                "active_total": row.active_total or 0,
                "avg_resolution_hours": round(float(row.avg_resolution_hours), 1) if row.avg_resolution_hours else None,
                "avg_first_response_hours": round(float(row.avg_first_response_hours), 1) if row.avg_first_response_hours else None,
                "sla_breached_total": sla_breached,
                "sla_compliance_pct": sla_compliance,
                "tickets_reopened": tickets_reopened,
                "reopen_rate_pct": reopen_rate,
                "performance_score": score,
                "score_label": label,
            })
        return items

    @staticmethod
    async def get_urgency_abuse(
        tenant_id: uuid.UUID,
        db: AsyncSession,
        date_range_days: int = 30,
    ) -> list[dict]:
        """Urgency abuse report: % of urgent tickets per requester.

        Compares current period vs previous period to compute trend.

        Args:
            tenant_id: Owning tenant.
            db: Active async session.
            date_range_days: Current period length in days.

        Returns:
            List of dicts matching ``UrgencyAbuseItem`` schema fields, sorted by
            ``urgent_pct`` descending.
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=date_range_days)
        prev_period_start = period_start - timedelta(days=date_range_days)

        # Current period: group by requester
        curr_result = await db.execute(
            select(
                User.id.label("user_id"),
                User.full_name.label("user_name"),
                func.count(Ticket.id).label("total"),
                func.sum(case((Ticket.priority == "urgent", 1), else_=0)).label("urgent"),
            )
            .join(Ticket, Ticket.requester_id == User.id)
            .where(User.tenant_id == tenant_id)
            .where(User.is_archived.is_(False))
            .where(User.deleted_at.is_(None))
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.created_at >= period_start)
            .group_by(User.id, User.full_name)
            .having(func.count(Ticket.id) > 0)
        )
        curr_rows = {row.user_id: row for row in curr_result.all()}

        # Previous period for trend comparison
        prev_result = await db.execute(
            select(
                User.id.label("user_id"),
                func.count(Ticket.id).label("total"),
                func.sum(case((Ticket.priority == "urgent", 1), else_=0)).label("urgent"),
            )
            .join(Ticket, Ticket.requester_id == User.id)
            .where(User.tenant_id == tenant_id)
            .where(Ticket.tenant_id == tenant_id)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.created_at >= prev_period_start)
            .where(Ticket.created_at < period_start)
            .group_by(User.id)
        )
        prev_rows = {row.user_id: row for row in prev_result.all()}

        items = []
        for user_id, row in curr_rows.items():
            total = row.total or 0
            urgent = row.urgent or 0
            curr_pct = round(urgent / total * 100, 1) if total > 0 else 0.0

            prev_pct: float | None = None
            trend = "stable"
            prev_row = prev_rows.get(user_id)
            if prev_row and (prev_row.total or 0) > 0:
                prev_pct = round((prev_row.urgent or 0) / prev_row.total * 100, 1)
                if curr_pct < prev_pct - 2:
                    trend = "improved"
                elif curr_pct > prev_pct + 2:
                    trend = "worsened"

            items.append(
                {
                    "user_id": user_id,
                    "user_name": row.user_name,
                    "area_name": None,
                    "total_tickets": total,
                    "urgent_tickets": urgent,
                    "urgent_pct": curr_pct,
                    "prev_period_pct": prev_pct,
                    "trend": trend,
                }
            )

        return sorted(items, key=lambda x: x["urgent_pct"], reverse=True)
