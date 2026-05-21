"""Phase 5 stats panel — provider activity + cost rollups for Settings.

v0.3.5: the provider endpoint also tries ``get_provider()`` so the
Settings panel reflects the *current* construction outcome, not just
historical call-log rows. Before this, a panel could read "Healthy ·
100% success · 8 calls today" while the next real request 500'd with
``LLMAuthError`` because the keychain entry had quietly disappeared.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from db.models import AppConfig
from db.session import get_session
from llm import get_provider
from llm.errors import LLMError
from services.cost_service import CostBreakdown, get_cost_summary
from services.provider_stats import get_provider_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])


class CostResponse(BaseModel):
    provider: str
    label: str
    today_usd: float | None
    week_usd: float | None
    calls_today: int
    calls_week: int


class ProviderStatsResponse(BaseModel):
    provider: str
    last_latency_ms: int | None
    last_success: bool | None
    calls_today: int
    success_rate_today: float | None
    # v0.3.5: live construction state. ``construct_ok=False`` means the
    # next real request will fail — typically because the keychain
    # entry is missing or the provider config points at something the
    # adapter can't reach. The Settings panel surfaces this as a
    # "Disconnected" pill so the user knows to re-enter their key.
    construct_ok: bool
    construct_error: str | None


@router.get("/cost", response_model=CostResponse)
def get_cost() -> CostResponse:
    provider = _read_active_provider()
    summary: CostBreakdown = get_cost_summary(provider)
    return CostResponse(
        provider=provider,
        label=summary.label,
        today_usd=summary.today_usd,
        week_usd=summary.week_usd,
        calls_today=summary.calls_today,
        calls_week=summary.calls_week,
    )


@router.get("/provider", response_model=ProviderStatsResponse)
def get_provider_activity() -> ProviderStatsResponse:
    provider = _read_active_provider()
    stats = get_provider_stats(provider)
    construct_ok, construct_error = _probe_provider_construct()
    return ProviderStatsResponse(
        provider=provider,
        last_latency_ms=stats["last_latency_ms"],
        last_success=stats["last_success"],
        calls_today=stats["calls_today"],
        success_rate_today=stats["success_rate_today"],
        construct_ok=construct_ok,
        construct_error=construct_error,
    )


def _read_active_provider() -> str:
    with get_session() as session:
        row = session.execute(
            select(AppConfig.value).where(AppConfig.key == "provider")
        ).scalar_one_or_none()
        return (row or "mock").strip() or "mock"


def _probe_provider_construct() -> tuple[bool, str | None]:
    """Try building the configured provider; report the failure class.

    Keeps the probe cheap — we don't fire a real LLM call, we just exercise
    the adapter constructor (which reads the keychain / env var / CLI
    binary). The construction failure modes are exactly the ones we want
    to surface in Settings: ``LLMAuthError`` for a missing key,
    ``LLMError`` for a missing Claude Code binary, etc.
    """
    try:
        get_provider()
    except LLMError as exc:
        return False, type(exc).__name__
    except Exception:  # noqa: BLE001 — unexpected, log + treat as down
        logger.exception("provider construct probe raised unexpected exception")
        return False, "UnexpectedError"
    return True, None
