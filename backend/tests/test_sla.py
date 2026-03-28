"""Unit tests for business-hours SLA date calculation."""
import pytest
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.utils.business_hours import calculate_due_date

BOGOTA_TZ = "America/Bogota"
WORKING_DAYS = [1, 2, 3, 4, 5]  # Monday–Friday
WORK_START = time(8, 0)
WORK_END = time(18, 0)

BOG = ZoneInfo(BOGOTA_TZ)


def bogota(year: int, month: int, day: int, hour: int = 8, minute: int = 0) -> datetime:
    """Return a timezone-aware datetime in America/Bogota."""
    return datetime(year, month, day, hour, minute, tzinfo=BOG)


class TestCalculateDueDate:
    """Tests for ``calculate_due_date``."""

    def test_zero_hours_returns_same_datetime(self):
        """0 business hours → same instant returned (in UTC)."""
        start = bogota(2024, 3, 11, 10, 0)  # Monday 10:00 Bogotá
        result = calculate_due_date(start, 0, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)
        # The returned value should equal the input instant regardless of TZ
        assert result == start.astimezone(timezone.utc).replace(tzinfo=timezone.utc)

    def test_8_hours_from_friday_4pm(self):
        """8 business hours from Friday 16:00 → Monday 14:00 Bogotá.

        Friday 16:00 → Friday 18:00 = 2 hours consumed.
        Remaining 6 hours starting Monday 08:00 → Monday 14:00.
        """
        # 2024-03-08 is a Friday
        start = bogota(2024, 3, 8, 16, 0)
        result = calculate_due_date(start, 8, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)

        expected_bog = bogota(2024, 3, 11, 14, 0)  # Monday 14:00
        expected_utc = expected_bog.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        assert result == expected_utc

    def test_2_hours_from_friday_1730(self):
        """2 business hours from Friday 17:30 → Monday 09:30 Bogotá.

        Friday 17:30 → Friday 18:00 = 30 minutes consumed.
        Remaining 90 minutes starting Monday 08:00 → Monday 09:30.
        """
        start = bogota(2024, 3, 8, 17, 30)
        result = calculate_due_date(start, 2, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)

        expected_bog = bogota(2024, 3, 11, 9, 30)  # Monday 09:30
        expected_utc = expected_bog.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        assert result == expected_utc

    def test_start_on_saturday_returns_monday_result(self):
        """Starting on a Saturday skips to Monday 08:00 before counting hours."""
        # 2024-03-09 is a Saturday; 4 hours should land Monday 12:00
        start = bogota(2024, 3, 9, 12, 0)
        result = calculate_due_date(start, 4, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)

        expected_bog = bogota(2024, 3, 11, 12, 0)  # Monday 12:00
        expected_utc = expected_bog.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        assert result == expected_utc

    def test_start_on_sunday_returns_monday_result(self):
        """Starting on a Sunday skips to Monday 08:00 before counting hours."""
        # 2024-03-10 is a Sunday; 1 hour should land Monday 09:00
        start = bogota(2024, 3, 10, 8, 0)
        result = calculate_due_date(start, 1, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)

        expected_bog = bogota(2024, 3, 11, 9, 0)
        expected_utc = expected_bog.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        assert result == expected_utc

    def test_within_same_day(self):
        """2 hours from Monday 10:00 → Monday 12:00."""
        start = bogota(2024, 3, 11, 10, 0)  # Monday
        result = calculate_due_date(start, 2, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)

        expected_bog = bogota(2024, 3, 11, 12, 0)
        expected_utc = expected_bog.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        assert result == expected_utc

    def test_spans_multiple_days(self):
        """16 hours from Monday 08:00 spans two full work days → Tuesday 18:00.

        Monday 08:00 → 18:00 = 10 hours consumed.
        Tuesday 08:00 + 6 remaining hours → Tuesday 14:00.
        Wait – 16 - 10 = 6 → Tuesday 14:00.
        """
        start = bogota(2024, 3, 11, 8, 0)  # Monday
        result = calculate_due_date(start, 16, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)

        expected_bog = bogota(2024, 3, 12, 14, 0)  # Tuesday 14:00
        expected_utc = expected_bog.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        assert result == expected_utc

    def test_naive_utc_start_treated_as_utc(self):
        """Naive datetime is treated as UTC and result is in UTC."""
        # Monday 13:00 UTC = Monday 08:00 Bogotá (UTC-5)
        naive_start = datetime(2024, 3, 11, 13, 0)  # naive, i.e. UTC
        result = calculate_due_date(naive_start, 1, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)

        # Bogotá 08:00 + 1h = 09:00 Bogotá = 14:00 UTC
        expected_bog = bogota(2024, 3, 11, 9, 0)
        expected_utc = expected_bog.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        assert result == expected_utc

    def test_result_is_utc(self):
        """The returned datetime is always timezone-aware UTC."""
        start = bogota(2024, 3, 11, 10, 0)
        result = calculate_due_date(start, 1, BOGOTA_TZ, WORKING_DAYS, WORK_START, WORK_END)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc
