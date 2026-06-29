from __future__ import annotations

from datetime import date, timedelta

Period = str  # last_month | this_month | last_30_days | all


def last_month_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    first_of_month = today.replace(day=1)
    last_day_prev = first_of_month - timedelta(days=1)
    first_day_prev = last_day_prev.replace(day=1)
    return first_day_prev, last_day_prev


def this_month_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    return today.replace(day=1), today


def last_30_days_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    return today - timedelta(days=30), today


def resolve_period(period: str | None) -> tuple[date | None, date | None]:
    """Map a relative period label to concrete start/end dates."""
    if not period or period == "all":
        return None, None
    if period == "last_month":
        return last_month_range()
    if period == "this_month":
        return this_month_range()
    if period == "last_30_days":
        return last_30_days_range()
    return None, None


def resolve_aggregate_dates(args: dict) -> tuple[date | None, date | None]:
    """Resolve start/end from period (preferred) or explicit ISO date strings."""
    period = args.get("period")
    if period:
        return resolve_period(str(period))
    start = args.get("start_date")
    end = args.get("end_date")
    start_d = date.fromisoformat(start) if start else None
    end_d = date.fromisoformat(end) if end else None
    return start_d, end_d
