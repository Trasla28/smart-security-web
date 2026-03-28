"""Service for recurring ticket template scheduling logic."""
from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.recurring import RecurringTemplate


def _is_business_day(d: date, working_days: list[int]) -> bool:
    """Return True if d's ISO weekday (1=Mon, 7=Sun) is in working_days."""
    return d.isoweekday() in working_days


def _apply_holiday_action(d: date, action: str, working_days: list[int]) -> date:
    """Shift d to a business day according to the template's holiday action."""
    if _is_business_day(d, working_days):
        return d
    if action == "previous_business_day":
        while not _is_business_day(d, working_days):
            d -= timedelta(days=1)
    elif action == "next_business_day":
        while not _is_business_day(d, working_days):
            d += timedelta(days=1)
    # same_day: return as-is even if it falls on a non-business day
    return d


def calculate_next_run(
    template: RecurringTemplate,
    *,
    after: datetime | None = None,
    timezone_str: str = "America/Bogota",
    working_days: list[int] | None = None,
) -> datetime:
    """Calculate the next execution datetime (UTC) for a recurring template.

    Args:
        template: The recurring template ORM instance.
        after: Reference point in time (defaults to now UTC).
        timezone_str: IANA timezone name for the tenant.
        working_days: ISO weekday numbers considered business days (1=Mon).

    Returns:
        UTC-aware datetime for the next scheduled run (at 08:00 local time).
    """
    if working_days is None:
        working_days = [1, 2, 3, 4, 5]  # Mon–Fri

    tz = ZoneInfo(timezone_str)
    now_utc = after or datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz)
    today = now_local.date()

    if template.recurrence_type == "daily":
        candidate = today + timedelta(days=1)

    elif template.recurrence_type == "weekly":
        # recurrence_day: 0=Mon … 6=Sun → ISO: 1=Mon … 7=Sun
        target_iso = (template.recurrence_day or 0) + 1
        days_ahead = (target_iso - today.isoweekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        candidate = today + timedelta(days=days_ahead)

    elif template.recurrence_type in ("monthly", "day_of_month"):
        day_num = template.recurrence_value or 1
        _, max_day = calendar.monthrange(today.year, today.month)
        clamped = min(day_num, max_day)
        if today.day < clamped:
            candidate = today.replace(day=clamped)
        else:
            # Move to next month
            if today.month == 12:
                yr, mo = today.year + 1, 1
            else:
                yr, mo = today.year, today.month + 1
            _, max_next = calendar.monthrange(yr, mo)
            candidate = date(yr, mo, min(day_num, max_next))

    else:
        # Fallback: tomorrow
        candidate = today + timedelta(days=1)

    candidate = _apply_holiday_action(candidate, template.if_holiday_action, working_days)

    # Schedule at 08:00 local time, converted to UTC
    run_local = datetime(candidate.year, candidate.month, candidate.day, 8, 0, 0, tzinfo=tz)
    return run_local.astimezone(timezone.utc)
