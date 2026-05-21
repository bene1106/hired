"""LLMProvider Protocol — the contract the rest of the app talks to.

Business logic ALWAYS depends on this interface, never on a concrete adapter.
Phase 2 shipped MockProvider + AnthropicAPIAdapter. Phase 6 adds
ClaudeCodeAdapter and OllamaAdapter, plus ``summarize_role`` so the
interview-prep view can show a synthesized 2-paragraph role explanation.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

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


@runtime_checkable
class LLMProvider(Protocol):
    """Every LLM adapter implements these nine methods."""

    def parse_cv(self, cv_text: str) -> dict:
        """Extract a structured profile dict from raw CV text."""
        ...

    def score_job(self, profile: Profile, job: Job) -> ScoreResult:
        """Rate how well a job matches a profile (0–100, with rationale)."""
        ...

    def research_company(self, company: str) -> CompanyBrief:
        """Produce a one-page brief for a company."""
        ...

    def tailor_cv(self, profile: Profile, job: Job) -> str:
        """Suggest CV emphasis changes for a specific job. Returns markdown."""
        ...

    def generate_cover_letter(self, profile: Profile, job: Job, brief: CompanyBrief) -> CoverLetter:
        """Generate a tailored cover letter."""
        ...

    def generate_interview_questions(self, job: Job) -> list[InterviewQuestion]:
        """Produce a likely set of interview questions for a role."""
        ...

    def evaluate_answer(self, question: str, answer: str) -> AnswerFeedback:
        """Give feedback on a candidate's answer to a practice question."""
        ...

    def summarize_role(self, job: Job) -> str:
        """Two-paragraph plain-text summary of what the role actually involves."""
        ...

    def interview_chat_stream(
        self,
        messages: list[ChatMessage],
        role_context: str | None = None,
    ) -> Iterator[str]:
        """Stream a coach reply for a multi-turn interview conversation.

        ``messages`` is the full prior conversation; the last entry should be
        a ``user`` turn that the coach is replying to. ``role_context`` is the
        role summary string (typically from ``summarize_role``) injected into
        the coach's system prompt so it knows what role it's coaching for.

        Yields text chunks in arrival order. Callers concatenate them to form
        the final assistant message and persist it. Token usage is recorded
        once the iterator drains.
        """
        ...


__all__ = ["LLMProvider"]
