"""
Utility helpers for date/time operations.
All times are handled in IST (UTC+5:30) for display,
but stored/compared in UTC for consistency.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc


def now_ist() -> datetime:
    """Return current time in IST."""
    return datetime.now(tz=IST)


def now_utc() -> datetime:
    """Return current time in UTC."""
    return datetime.now(tz=UTC)


def today_ist() -> date:
    """Return today's date in IST."""
    return now_ist().date()


def format_date_display(d: date) -> str:
    """Format a date for display, e.g. 'Monday, September 7, 2026'."""
    # %-d is Linux-only; use explicit day integer for cross-platform support
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")


def format_date_iso(d: date) -> str:
    """Format a date as ISO 8601 string, e.g. '2026-09-07'."""
    return d.isoformat()


def format_datetime_log(dt: datetime) -> str:
    """Format a datetime for log lines, e.g. '2026-09-07 18:00:01'."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_trading_day(d: date | None = None) -> bool:
    """
    Return True if the given date (default: today IST) is a weekday.
    Does NOT account for market holidays — a simple weekday check.
    """
    if d is None:
        d = today_ist()
    return d.weekday() < 5  # Monday=0 … Friday=4


def idempotency_key(prefix: str, d: date | None = None) -> str:
    """
    Build an idempotency key for a given date.
    e.g. 'daily-digest-2026-09-07'
    """
    if d is None:
        d = today_ist()
    return f"{prefix}-{format_date_iso(d)}"


def parse_iso_date(s: str) -> date:
    """Parse an ISO 8601 date string into a date object."""
    return date.fromisoformat(s)
