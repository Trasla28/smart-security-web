"""Utility functions for business-hours-aware date calculations."""
from datetime import datetime, timedelta, time as time_type, timezone
from zoneinfo import ZoneInfo


def is_within_business_hours(
    now: datetime,
    timezone_str: str,
    working_days: list[int],
    working_hours_start: time_type,
    working_hours_end: time_type,
) -> bool:
    """Return True if ``now`` falls within configured business hours.

    Args:
        now: Current UTC datetime.
        timezone_str: IANA timezone string, e.g. ``"America/Bogota"``.
        working_days: List of ISO weekday numbers (1=Monday … 7=Sunday).
        working_hours_start: Start of the working day.
        working_hours_end: End of the working day.
    """
    tz = ZoneInfo(timezone_str)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now.astimezone(tz)

    if local_now.isoweekday() not in working_days:
        return False

    local_time = local_now.time().replace(tzinfo=None)
    return working_hours_start <= local_time < working_hours_end


def next_business_start(
    now: datetime,
    timezone_str: str,
    working_days: list[int],
    working_hours_start: time_type,
    working_hours_end: time_type,
) -> datetime:
    """Return the next business-hours start datetime in UTC after ``now``.

    If ``now`` is already within business hours this still returns the next
    future start (i.e., tomorrow's or the next working day's start).
    Call only when ``is_within_business_hours`` returns False.

    Args:
        now: Current UTC datetime.
        timezone_str: IANA timezone string.
        working_days: List of ISO weekday numbers.
        working_hours_start: Start of the working day.
        working_hours_end: End of the working day.
    """
    tz = ZoneInfo(timezone_str)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now.astimezone(tz)
    current = local_now

    # If today is a working day but we're before the start → return today's start
    if current.isoweekday() in working_days:
        work_start_today = current.replace(
            hour=working_hours_start.hour,
            minute=working_hours_start.minute,
            second=0,
            microsecond=0,
        )
        if current < work_start_today:
            return work_start_today.astimezone(timezone.utc).replace(tzinfo=timezone.utc)

    # Otherwise advance day by day until we find a working day
    next_date = current.date() + timedelta(days=1)
    for _ in range(14):  # safety: max 2 weeks ahead
        candidate = datetime(
            next_date.year,
            next_date.month,
            next_date.day,
            working_hours_start.hour,
            working_hours_start.minute,
            tzinfo=tz,
        )
        if candidate.isoweekday() in working_days:
            return candidate.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        next_date = next_date + timedelta(days=1)

    # Fallback: 24 h from now (should never happen)
    return (now + timedelta(hours=24)).astimezone(timezone.utc).replace(tzinfo=timezone.utc)


def calculate_due_date(
    start: datetime,
    hours: int,
    timezone_str: str,
    working_days: list[int],
    working_hours_start: time_type,
    working_hours_end: time_type,
) -> datetime:
    """Calculate when ``hours`` business hours from ``start`` will be complete.

    Skips non-working days and times outside the defined working window.

    Args:
        start: The reference start datetime (UTC or timezone-aware).
        hours: Number of business hours to add.
        timezone_str: IANA timezone string, e.g. ``"America/Bogota"``.
        working_days: List of ISO weekday numbers that are working days
            (1 = Monday … 7 = Sunday).
        working_hours_start: Beginning of the working day.
        working_hours_end: End of the working day.

    Returns:
        Timezone-aware datetime in UTC representing the due date.
    """
    if hours == 0:
        # Normalise to UTC and return immediately
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return start.astimezone(timezone.utc).replace(tzinfo=timezone.utc)

    tz = ZoneInfo(timezone_str)

    # Convert start to tenant timezone
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    current = start.astimezone(tz)

    remaining_minutes = hours * 60

    while remaining_minutes > 0:
        # Skip non-working days – advance to next day's work start
        while current.isoweekday() not in working_days:
            next_date = current.date() + timedelta(days=1)
            current = datetime(
                next_date.year,
                next_date.month,
                next_date.day,
                working_hours_start.hour,
                working_hours_start.minute,
                tzinfo=tz,
            )

        # Compute work boundaries for the current calendar day
        work_start = current.replace(
            hour=working_hours_start.hour,
            minute=working_hours_start.minute,
            second=0,
            microsecond=0,
        )
        work_end = current.replace(
            hour=working_hours_end.hour,
            minute=working_hours_end.minute,
            second=0,
            microsecond=0,
        )

        # If we are before the start of the working day, jump to it
        if current < work_start:
            current = work_start

        # If we are at or past the end of the working day, advance to next day
        if current >= work_end:
            next_date = current.date() + timedelta(days=1)
            current = datetime(
                next_date.year,
                next_date.month,
                next_date.day,
                working_hours_start.hour,
                working_hours_start.minute,
                tzinfo=tz,
            )
            continue

        # How many work-minutes remain today
        available_minutes = int((work_end - current).total_seconds() / 60)

        if remaining_minutes <= available_minutes:
            current = current + timedelta(minutes=remaining_minutes)
            remaining_minutes = 0
        else:
            remaining_minutes -= available_minutes
            next_date = current.date() + timedelta(days=1)
            current = datetime(
                next_date.year,
                next_date.month,
                next_date.day,
                working_hours_start.hour,
                working_hours_start.minute,
                tzinfo=tz,
            )

    # Return in UTC
    return current.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
