"""Recording wrapper around any ``LLMProvider``.

For every method call we measure wall-clock latency and append a row to
``provider_call_log``. Failures bubble up to the caller (we don't swallow
them) but the recording itself is best-effort: a DB error during the log
write is logged-and-ignored so observability never breaks the user flow.

The Settings UI later reads this table to render "calls today / latency"
and the per-call token / cost rollups added in Phase 5.

Token usage flows through ``llm.usage``: the adapter publishes the
response's input/output token counts via ``record_usage`` immediately
after the API call returns, and this wrapper consumes them in
``_record``. Adapters that don't publish usage (Mock, Ollama) simply
record ``None`` for both columns, which is what we want.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

from db.models import ProviderCallLog
from db.session import get_session

from .base import LLMProvider
from .errors import LLMError
from .types import (
    AnswerFeedback,
    ChatMessage,
    CompanyBrief,
    CoverLetter,
    InterviewQuestion,
    Job,
    Profile,
    ScoreResult,
)
from .usage import consume_usage

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RecordingProvider:
    """Wraps an ``LLMProvider`` and logs every call to ``provider_call_log``."""

    def __init__(self, inner: LLMProvider, provider_name: str) -> None:
        self._inner = inner
        self._provider_name = provider_name

    @property
    def inner(self) -> LLMProvider:
        return self._inner

    def parse_cv(self, cv_text: str) -> dict:
        return self._record("parse_cv", lambda: self._inner.parse_cv(cv_text))

    def score_job(self, profile: Profile, job: Job) -> ScoreResult:
        return self._record("score_job", lambda: self._inner.score_job(profile, job))

    def research_company(self, company: str) -> CompanyBrief:
        return self._record("research_company", lambda: self._inner.research_company(company))

    def tailor_cv(self, profile: Profile, job: Job) -> str:
        return self._record("tailor_cv", lambda: self._inner.tailor_cv(profile, job))

    def generate_cover_letter(self, profile: Profile, job: Job, brief: CompanyBrief) -> CoverLetter:
        return self._record(
            "generate_cover_letter",
            lambda: self._inner.generate_cover_letter(profile, job, brief),
        )

    def generate_interview_questions(self, job: Job) -> list[InterviewQuestion]:
        return self._record(
            "generate_interview_questions",
            lambda: self._inner.generate_interview_questions(job),
        )

    def evaluate_answer(self, question: str, answer: str) -> AnswerFeedback:
        return self._record(
            "evaluate_answer", lambda: self._inner.evaluate_answer(question, answer)
        )

    def summarize_role(self, job: Job) -> str:
        return self._record("summarize_role", lambda: self._inner.summarize_role(job))

    def interview_chat_stream(
        self,
        messages: list[ChatMessage],
        role_context: str | None = None,
    ) -> Iterator[str]:
        return self._record_stream(
            "interview_chat_stream",
            lambda: self._inner.interview_chat_stream(messages, role_context),
        )

    def _record(self, method: str, call: Callable[[], T]) -> T:
        # Clear any stale usage left over from a previous call so we never
        # attribute one method's tokens to another.
        consume_usage()
        started = time.perf_counter()
        success = True
        error_type: str | None = None
        try:
            return call()
        except LLMError as exc:
            success = False
            error_type = type(exc).__name__
            raise
        except Exception as exc:  # noqa: BLE001 - we re-raise after recording
            success = False
            error_type = type(exc).__name__
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = consume_usage()
            _safe_insert_log(
                provider=self._provider_name,
                method=method,
                latency_ms=latency_ms,
                success=success,
                error_type=error_type,
                tokens_in=usage.input_tokens if usage else None,
                tokens_out=usage.output_tokens if usage else None,
            )

    def _record_stream(self, method: str, call: Callable[[], Iterator[str]]) -> Iterator[str]:
        """Stream variant of ``_record``.

        Latency is measured from method-call to iterator exhaustion. Token
        usage is captured once the underlying adapter has finished consuming
        its stream — every streaming adapter publishes usage on the final
        event, so ``consume_usage`` after the inner iterator drains has the
        right numbers.
        """
        consume_usage()
        started = time.perf_counter()
        success = True
        error_type: str | None = None
        try:
            yield from call()
        except LLMError as exc:
            success = False
            error_type = type(exc).__name__
            raise
        except Exception as exc:  # noqa: BLE001 - we re-raise after recording
            success = False
            error_type = type(exc).__name__
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = consume_usage()
            _safe_insert_log(
                provider=self._provider_name,
                method=method,
                latency_ms=latency_ms,
                success=success,
                error_type=error_type,
                tokens_in=usage.input_tokens if usage else None,
                tokens_out=usage.output_tokens if usage else None,
            )


def _safe_insert_log(
    *,
    provider: str,
    method: str,
    latency_ms: int,
    success: bool,
    error_type: str | None,
    tokens_in: int | None,
    tokens_out: int | None,
) -> None:
    """Insert one row. Best-effort: DB errors are logged, never raised."""
    try:
        with get_session() as session:
            row = ProviderCallLog(
                provider=provider,
                method=method,
                latency_ms=latency_ms,
                success=success,
                error_type=error_type,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            session.add(row)
            session.commit()
    except Exception as exc:  # noqa: BLE001 - observability must not break callers
        logger.warning("provider_call_log insert failed: %s", exc)


__all__ = ["RecordingProvider"]
