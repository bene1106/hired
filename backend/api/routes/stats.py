"""Phase 5 stats panel — provider activity + cost rollups for Settings."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from db.models import AppConfig
from db.session import get_session
from services.cost_service import CostBreakdown, get_cost_summary
from services.provider_stats import get_provider_stats

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
    return ProviderStatsResponse(
        provider=provider,
        last_latency_ms=stats["last_latency_ms"],
        last_success=stats["last_success"],
        calls_today=stats["calls_today"],
        success_rate_today=stats["success_rate_today"],
    )


def _read_active_provider() -> str:
    with get_session() as session:
        row = session.execute(
            select(AppConfig.value).where(AppConfig.key == "provider")
        ).scalar_one_or_none()
        return (row or "mock").strip() or "mock"
