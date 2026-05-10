"""Cost rollups over ``provider_call_log`` for the Settings cost panel.

For ``anthropic_api`` we sum tokens × per-model rates from
``services.pricing`` and surface today's + this-week's totals. For
``mock`` we return ``label=unknown`` so the UI renders an em-dash; for
``claude_code`` and ``ollama`` (Phase 6 adapters) the label tells the UI
to show "$0.00 (subscription)" / "$0.00 (local)" — the rates table
deliberately doesn't carry these so we don't accidentally invent costs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from db.models import AppConfig, ProviderCallLog
from db.session import get_session

from .pricing import estimate_cost_usd


@dataclass
class CostBreakdown:
    today_usd: float | None
    week_usd: float | None
    calls_today: int
    calls_week: int
    label: str  # one of: "priced", "subscription", "local", "unknown"


_PROVIDER_LABELS: dict[str, str] = {
    "anthropic_api": "priced",
    "claude_code": "subscription",
    "ollama": "local",
    "mock": "unknown",
}


def get_cost_summary(provider: str | None = None) -> CostBreakdown:
    """Aggregate token-priced costs for the configured provider.

    Pass ``provider`` to override the configured provider (used by tests).
    """
    if provider is None:
        provider = _read_active_provider()
    label = _PROVIDER_LABELS.get(provider, "unknown")

    if label != "priced":
        # Non-priced providers return zero counts so the UI can still
        # render today/week call counts if it wants to, but cost is
        # short-circuited to None.
        today_calls, week_calls = _count_calls(provider)
        return CostBreakdown(
            today_usd=None,
            week_usd=None,
            calls_today=today_calls,
            calls_week=week_calls,
            label=label,
        )

    model = _read_active_model()
    today_start, week_start = _today_and_week_starts()

    with get_session() as session:
        rows = session.execute(
            select(
                ProviderCallLog.created_at,
                ProviderCallLog.tokens_in,
                ProviderCallLog.tokens_out,
            )
            .where(ProviderCallLog.provider == provider)
            .where(ProviderCallLog.created_at >= week_start)
        ).all()

    today_usd = 0.0
    week_usd = 0.0
    today_calls = 0
    week_calls = 0
    for created_at, tokens_in, tokens_out in rows:
        cost = estimate_cost_usd(model=model, tokens_in=tokens_in, tokens_out=tokens_out) or 0.0
        week_usd += cost
        week_calls += 1
        if created_at >= today_start:
            today_usd += cost
            today_calls += 1

    return CostBreakdown(
        today_usd=round(today_usd, 4),
        week_usd=round(week_usd, 4),
        calls_today=today_calls,
        calls_week=week_calls,
        label=label,
    )


def _read_active_provider() -> str:
    with get_session() as session:
        row = session.execute(
            select(AppConfig.value).where(AppConfig.key == "provider")
        ).scalar_one_or_none()
        return (row or "mock").strip() or "mock"


def _read_active_model() -> str | None:
    with get_session() as session:
        row = session.execute(
            select(AppConfig.value).where(AppConfig.key == "model")
        ).scalar_one_or_none()
        return (row or None) and row.strip() or None


def _today_and_week_starts() -> tuple[datetime, datetime]:
    now = datetime.now(UTC).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    return today_start, week_start


def _count_calls(provider: str) -> tuple[int, int]:
    today_start, week_start = _today_and_week_starts()
    with get_session() as session:
        today = session.execute(
            select(func.count(ProviderCallLog.id))
            .where(ProviderCallLog.provider == provider)
            .where(ProviderCallLog.created_at >= today_start)
        ).scalar_one()
        week = session.execute(
            select(func.count(ProviderCallLog.id))
            .where(ProviderCallLog.provider == provider)
            .where(ProviderCallLog.created_at >= week_start)
        ).scalar_one()
    return int(today or 0), int(week or 0)


__all__ = ["CostBreakdown", "get_cost_summary"]
