"""Token threading + cost rollup tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.migrations import run_migrations
from db.models import AppConfig, ProviderCallLog
from db.session import get_session
from llm.anthropic_api import AnthropicAPIAdapter
from llm.recorder import RecordingProvider
from llm.usage import TokenUsage, consume_usage, record_usage
from services.cost_service import get_cost_summary
from services.pricing import estimate_cost_usd, rate_for

client = TestClient(app)


@pytest.fixture(autouse=True)
def _migrated() -> None:
    run_migrations()


# ---------------------------------------------------------------------------
# llm/usage.py
# ---------------------------------------------------------------------------


def test_consume_usage_clears_after_read() -> None:
    record_usage(TokenUsage(input_tokens=100, output_tokens=50))
    first = consume_usage()
    second = consume_usage()
    assert first == TokenUsage(input_tokens=100, output_tokens=50)
    assert second is None


# ---------------------------------------------------------------------------
# AnthropicAPIAdapter wires usage into the contextvar
# ---------------------------------------------------------------------------


def _make_response(text: str, *, input_tokens: int = 0, output_tokens: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def test_adapter_publishes_usage_after_call() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _make_response(
        '{"score": 80, "rationale": "ok"}',
        input_tokens=120,
        output_tokens=40,
    )
    consume_usage()  # clear any previous value
    adapter = AnthropicAPIAdapter(client=fake_client)
    adapter.score_job(_profile(), _job())  # fires _call

    usage = consume_usage()
    assert usage == TokenUsage(input_tokens=120, output_tokens=40)


def test_recording_provider_persists_token_counts() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _make_response(
        '{"score": 60, "rationale": "fine"}',
        input_tokens=300,
        output_tokens=80,
    )
    adapter = AnthropicAPIAdapter(client=fake_client)
    recorder = RecordingProvider(adapter, "anthropic_api")
    recorder.score_job(_profile(), _job())

    with get_session() as session:
        row = (
            session.query(ProviderCallLog)
            .order_by(ProviderCallLog.id.desc())
            .first()
        )
    assert row is not None
    assert row.tokens_in == 300
    assert row.tokens_out == 80
    assert row.method == "score_job"


def test_recording_provider_clears_stale_usage_between_calls() -> None:
    """A failing call must not inherit token counts from a prior success."""
    fake_client = MagicMock()
    # First call succeeds with usage; second call raises before publishing.
    fake_client.messages.create.side_effect = [
        _make_response('{"score": 50, "rationale": "x"}', input_tokens=10, output_tokens=5),
        RuntimeError("server hiccup"),
    ]
    adapter = AnthropicAPIAdapter(client=fake_client)
    recorder = RecordingProvider(adapter, "anthropic_api")
    recorder.score_job(_profile(), _job())
    with pytest.raises(RuntimeError):
        recorder.score_job(_profile(), _job())

    with get_session() as session:
        rows = session.query(ProviderCallLog).order_by(ProviderCallLog.id.asc()).all()
    assert [(r.tokens_in, r.tokens_out, r.success) for r in rows] == [
        (10, 5, True),
        (None, None, False),
    ]


# ---------------------------------------------------------------------------
# Pricing math
# ---------------------------------------------------------------------------


def test_pricing_known_model_returns_dollars() -> None:
    rate = rate_for("claude-opus-4-7")
    assert rate is not None
    cost = estimate_cost_usd(model="claude-opus-4-7", tokens_in=1_000_000, tokens_out=1_000_000)
    assert cost == pytest.approx(rate.input_per_mtok_usd + rate.output_per_mtok_usd)


def test_pricing_unknown_model_returns_none() -> None:
    assert estimate_cost_usd(model="unknown-model", tokens_in=1, tokens_out=1) is None


def test_pricing_handles_none_tokens_as_zero() -> None:
    cost = estimate_cost_usd(model="claude-opus-4-7", tokens_in=None, tokens_out=None)
    assert cost == 0.0


# ---------------------------------------------------------------------------
# Cost summary aggregates today and this week
# ---------------------------------------------------------------------------


def _seed_call(
    *,
    provider: str = "anthropic_api",
    tokens_in: int,
    tokens_out: int,
    when: datetime | None = None,
) -> None:
    with get_session() as session:
        row = ProviderCallLog(
            provider=provider,
            method="score_job",
            latency_ms=10,
            success=True,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        session.add(row)
        session.flush()
        if when is not None:
            row.created_at = when
        session.commit()


def _set_provider(name: str, *, model: str | None = "claude-opus-4-7") -> None:
    with get_session() as session:
        for key in ("provider", "model"):
            session.query(AppConfig).filter(AppConfig.key == key).delete()
        session.add(AppConfig(key="provider", value=name))
        if model is not None:
            session.add(AppConfig(key="model", value=model))
        session.commit()


def test_cost_summary_priced_provider_sums_today_and_week() -> None:
    _set_provider("anthropic_api")
    _seed_call(tokens_in=500_000, tokens_out=200_000)  # today
    _seed_call(
        tokens_in=1_000_000,
        tokens_out=500_000,
        when=datetime.utcnow() - timedelta(days=2),
    )

    summary = get_cost_summary()
    assert summary.label == "priced"
    assert summary.today_usd is not None and summary.today_usd > 0
    assert summary.week_usd is not None and summary.week_usd > summary.today_usd
    assert summary.calls_today == 1
    assert summary.calls_week == 2


def test_cost_summary_for_mock_returns_unknown_label() -> None:
    _set_provider("mock", model=None)
    summary = get_cost_summary()
    assert summary.label == "unknown"
    assert summary.today_usd is None
    assert summary.week_usd is None


def test_cost_summary_for_claude_code_uses_subscription_label() -> None:
    _set_provider("claude_code", model=None)
    summary = get_cost_summary()
    assert summary.label == "subscription"
    assert summary.today_usd is None


def test_cost_summary_for_ollama_uses_local_label() -> None:
    _set_provider("ollama", model=None)
    summary = get_cost_summary()
    assert summary.label == "local"
    assert summary.today_usd is None


# ---------------------------------------------------------------------------
# GET /api/stats/cost
# ---------------------------------------------------------------------------


def test_cost_endpoint_returns_priced_summary() -> None:
    _set_provider("anthropic_api")
    _seed_call(tokens_in=1_000_000, tokens_out=1_000_000)
    res = client.get("/api/stats/cost")
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "anthropic_api"
    assert body["label"] == "priced"
    assert body["today_usd"] is not None and body["today_usd"] > 0


def test_cost_endpoint_returns_unknown_label_for_mock() -> None:
    _set_provider("mock", model=None)
    res = client.get("/api/stats/cost")
    body = res.json()
    assert body["label"] == "unknown"
    assert body["today_usd"] is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile():
    from llm.types import Profile

    return Profile(name="A", target_role="Backend Engineer")


def _job():
    from llm.types import Job

    return Job(title="Backend Engineer", company="AcmeCo")
