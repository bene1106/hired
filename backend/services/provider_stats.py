"""Aggregations over ``provider_call_log`` for the Settings UI."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from typing_extensions import TypedDict

from db.models import ProviderCallLog
from db.session import get_session


class ProviderStats(TypedDict):
    last_latency_ms: int | None
    last_success: bool | None
    calls_today: int
    success_rate_today: float | None


def get_provider_stats(provider: str) -> ProviderStats:
    """Return latency-of-last-call + today's call count for ``provider``."""
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    # SQLite stores naive datetimes by default; strip tz for the comparison.
    today_naive = today_start.replace(tzinfo=None)

    with get_session() as session:
        last_row = session.execute(
            select(ProviderCallLog.latency_ms, ProviderCallLog.success)
            .where(ProviderCallLog.provider == provider)
            .order_by(ProviderCallLog.created_at.desc())
            .limit(1)
        ).first()

        total_today = session.execute(
            select(func.count(ProviderCallLog.id))
            .where(ProviderCallLog.provider == provider)
            .where(ProviderCallLog.created_at >= today_naive)
        ).scalar_one()
        # SUM over a Boolean column in SQLite confuses SQLAlchemy's type
        # adapter (it casts the sum back to bool). Count the True rows
        # directly instead.
        successes_today = session.execute(
            select(func.count(ProviderCallLog.id))
            .where(ProviderCallLog.provider == provider)
            .where(ProviderCallLog.created_at >= today_naive)
            .where(ProviderCallLog.success.is_(True))
        ).scalar_one()

    total_today = int(total_today or 0)
    successes_today = int(successes_today or 0)
    success_rate = (successes_today / total_today) if total_today else None

    return {
        "last_latency_ms": last_row.latency_ms if last_row else None,
        "last_success": bool(last_row.success) if last_row else None,
        "calls_today": int(total_today or 0),
        "success_rate_today": success_rate,
    }


__all__ = ["ProviderStats", "get_provider_stats"]
