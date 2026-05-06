"""LLMProvider Protocol — the contract the rest of the app talks to.

Business logic ALWAYS depends on this interface, never on a concrete adapter.
Two implementations ship in Phase 2: MockProvider (deterministic, default in
tests) and AnthropicAPIAdapter. Phase 6 adds ClaudeCodeAdapter and
OllamaAdapter — they only need to satisfy this Protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import (
    AnswerFeedback,
    CompanyBrief,
    CoverLetter,
    InterviewQuestion,
    Job,
    Profile,
    ScoreResult,
)


@runtime_checkable
class LLMProvider(Protocol):
    """Every LLM adapter implements these seven methods."""

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

    def generate_cover_letter(
        self, profile: Profile, job: Job, brief: CompanyBrief
    ) -> CoverLetter:
        """Generate a tailored cover letter."""
        ...

    def generate_interview_questions(self, job: Job) -> list[InterviewQuestion]:
        """Produce a likely set of interview questions for a role."""
        ...

    def evaluate_answer(self, question: str, answer: str) -> AnswerFeedback:
        """Give feedback on a candidate's answer to a practice question."""
        ...


__all__ = ["LLMProvider"]
