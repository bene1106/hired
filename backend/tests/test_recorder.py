"""RecordingProvider + provider_call_log + provider_stats tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from db.migrations import run_migrations
from db.models import ProviderCallLog
from db.session import get_session
from llm import MockProvider, RecordingProvider
from llm.errors import LLMAuthError, LLMResponseError
from llm.types import ChatMessage, Job, Profile
from services.provider_stats import get_provider_stats


def test_recording_wraps_mock_and_inserts_row() -> None:
    run_migrations()

    inner = MockProvider()
    provider = RecordingProvider(inner, "mock")

    result = provider.parse_cv("hi")
    assert isinstance(result, dict)

    with get_session() as session:
        rows = session.execute(select(ProviderCallLog)).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "mock"
    assert row.method == "parse_cv"
    assert row.success is True
    assert row.error_type is None
    assert row.latency_ms >= 0


def test_recording_logs_failures_and_reraises() -> None:
    run_migrations()

    class ExplodingProvider:
        def parse_cv(self, _cv_text: str) -> dict:
            raise LLMAuthError("nope")

        # Stubs so RecordingProvider type-checks at runtime; not exercised here.
        def score_job(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def research_company(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def tailor_cv(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def generate_cover_letter(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def generate_interview_questions(
            self, *_a: object, **_k: object
        ) -> object:  # pragma: no cover
            raise NotImplementedError

        def evaluate_answer(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def summarize_role(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def interview_chat_stream(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

    provider = RecordingProvider(ExplodingProvider(), "mock")  # type: ignore[arg-type]

    try:
        provider.parse_cv("anything")
    except LLMAuthError:
        pass
    else:
        raise AssertionError("LLMAuthError should have propagated")

    with get_session() as session:
        rows = session.execute(select(ProviderCallLog)).scalars().all()

    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].error_type == "LLMAuthError"


def test_provider_stats_aggregates_calls_today() -> None:
    run_migrations()

    inner = MockProvider()
    provider = RecordingProvider(inner, "mock")

    provider.parse_cv("a")
    provider.parse_cv("b")
    provider.score_job(Profile(), Job(title="t"))

    stats = get_provider_stats("mock")
    assert stats["calls_today"] == 3
    assert stats["last_latency_ms"] is not None
    assert stats["last_success"] is True
    assert stats["success_rate_today"] == 1.0


def test_provider_stats_empty_when_no_calls() -> None:
    run_migrations()

    stats = get_provider_stats("anthropic_api")

    assert stats == {
        "last_latency_ms": None,
        "last_success": None,
        "calls_today": 0,
        "success_rate_today": None,
    }


def test_recording_stream_logs_one_row_on_completion() -> None:
    run_migrations()

    inner = MockProvider()
    provider = RecordingProvider(inner, "mock")

    chunks = list(
        provider.interview_chat_stream(
            [ChatMessage(role="user", content="Ready.")],
            role_context=None,
        )
    )
    assert len(chunks) >= 2  # Mock streams >1 event

    with get_session() as session:
        rows = session.execute(select(ProviderCallLog)).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "mock"
    assert row.method == "interview_chat_stream"
    assert row.success is True
    assert row.error_type is None
    assert row.latency_ms >= 0


def test_recording_stream_logs_failure_when_inner_raises() -> None:
    run_migrations()

    from collections.abc import Iterator

    class ExplodingProvider:
        def interview_chat_stream(
            self, _msgs: list[ChatMessage], _role: str | None = None
        ) -> Iterator[str]:
            yield "first chunk "
            raise LLMResponseError("upstream failure")

        # Stubs so RecordingProvider type-checks at runtime; not exercised.
        def parse_cv(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def score_job(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def research_company(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def tailor_cv(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def generate_cover_letter(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def generate_interview_questions(
            self, *_a: object, **_k: object
        ) -> object:  # pragma: no cover
            raise NotImplementedError

        def evaluate_answer(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

        def summarize_role(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise NotImplementedError

    provider = RecordingProvider(ExplodingProvider(), "mock")  # type: ignore[arg-type]
    seen: list[str] = []
    with pytest.raises(LLMResponseError):
        for chunk in provider.interview_chat_stream(
            [ChatMessage(role="user", content="hi")],
        ):
            seen.append(chunk)

    assert seen == ["first chunk "]

    with get_session() as session:
        rows = session.execute(select(ProviderCallLog)).scalars().all()

    assert len(rows) == 1
    assert rows[0].method == "interview_chat_stream"
    assert rows[0].success is False
    assert rows[0].error_type == "LLMResponseError"
