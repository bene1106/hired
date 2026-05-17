"""AnthropicAPIAdapter — first real LLM provider.

Uses the official `anthropic` SDK against the public API. ToS-clean and
officially supported, which is why we ship it before ClaudeCodeAdapter
(see ADR-0005).

Wiring:

    1. Read API key from the OS keychain via `backend.llm.credentials`.
    2. Read default model from `app_config.model`.
    3. For each method, load the corresponding prompt template, render it
       with the typed inputs, call the API, parse JSON output into a
       Pydantic model, raise typed `LLMError` subclasses on failure.

TODO(phase-6): split off a smaller, cheaper model for classification-shaped
calls (`score_job`, `evaluate_answer`) once we have cost data. Until then
every call uses the configured generation model.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import anthropic
from pydantic import ValidationError

from .credentials import get_credential
from .errors import (
    LLMAuthError,
    LLMNetworkError,
    LLMRateLimitError,
    LLMResponseError,
)
from .prompts import RenderedPrompt, load_prompt
from .types import (
    AnswerFeedback,
    CompanyBrief,
    CoverLetter,
    InterviewQuestion,
    Job,
    Profile,
    ScoreResult,
)
from .usage import TokenUsage, record_usage

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-7"
ANTHROPIC_API_KEY_NAME = "anthropic_api_key"

# Token budgets per task. Generous enough that legitimate outputs aren't
# truncated; prompts are still the cheapest way to reduce spend.
_MAX_TOKENS = {
    "parse_cv": 2048,
    "score_job": 1024,
    "research_company": 2048,
    "tailor_cv": 2048,
    "generate_cover_letter": 2048,
    "generate_interview_questions": 2048,
    "evaluate_answer": 1024,
    "summarize_role": 768,
}


class AnthropicAPIAdapter:
    """LLMProvider implementation backed by the Anthropic public API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.model = model
        if client is not None:
            self._client = client
        else:
            resolved_key = (
                api_key or get_credential(ANTHROPIC_API_KEY_NAME) or os.getenv("ANTHROPIC_API_KEY")
            )
            if not resolved_key:
                raise LLMAuthError(
                    "Anthropic API key not found. Set it via `set_credential"
                    "('anthropic_api_key', ...)` or the ANTHROPIC_API_KEY env var."
                )
            self._client = anthropic.Anthropic(api_key=resolved_key)

    # ------------------------------------------------------------------
    # LLMProvider methods
    # ------------------------------------------------------------------

    def parse_cv(self, cv_text: str) -> dict:
        rendered = load_prompt("parse_cv", cv_text=cv_text)
        text = self._call(rendered, max_tokens=_MAX_TOKENS["parse_cv"])
        return _parse_json_object(text)

    def score_job(self, profile: Profile, job: Job) -> ScoreResult:
        rendered = load_prompt(
            "score_job",
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["score_job"])
        return _parse_pydantic(text, ScoreResult)

    def research_company(self, company: str) -> CompanyBrief:
        rendered = load_prompt(
            "research_company",
            company_name=company,
            company_url="",
            industry_hint="",
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["research_company"])
        return CompanyBrief(
            company=company,
            markdown=text.strip(),
            sources=_extract_markdown_sources(text),
        )

    def tailor_cv(self, profile: Profile, job: Job) -> str:
        rendered = load_prompt(
            "tailor_cv",
            profile=profile.model_dump(mode="json"),
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["tailor_cv"])
        return text.strip()

    def generate_cover_letter(self, profile: Profile, job: Job, brief: CompanyBrief) -> CoverLetter:
        rendered = load_prompt(
            "generate_cover_letter",
            profile=profile.model_dump(mode="json"),
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
            company_brief=brief.markdown,
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["generate_cover_letter"])
        body = text.strip()
        return CoverLetter(body=body, word_count=len(body.split()))

    def generate_interview_questions(self, job: Job) -> list[InterviewQuestion]:
        rendered = load_prompt(
            "generate_interview_questions",
            job=job.model_dump(mode="json"),
            company_brief="",
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["generate_interview_questions"])
        payload = _parse_json_object(text)
        questions = payload.get("questions")
        if not isinstance(questions, list):
            kind = type(questions).__name__
            raise LLMResponseError(
                f"generate_interview_questions: expected 'questions' list, got {kind}"
            )
        try:
            return [InterviewQuestion.model_validate(q) for q in questions]
        except ValidationError as e:
            raise LLMResponseError(f"InterviewQuestion validation failed: {e}") from e

    def evaluate_answer(self, question: str, answer: str) -> AnswerFeedback:
        rendered = load_prompt(
            "evaluate_answer",
            question=question,
            answer=answer,
            what_theyre_assessing="",
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["evaluate_answer"])
        return _parse_pydantic(text, AnswerFeedback)

    def summarize_role(self, job: Job) -> str:
        rendered = load_prompt("summarize_role", job=job.model_dump(mode="json"))
        text = self._call(rendered, max_tokens=_MAX_TOKENS["summarize_role"])
        return text.strip()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call(self, rendered: RenderedPrompt, *, max_tokens: int) -> str:
        """Send `rendered` to the API and return the assistant's text reply."""
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=rendered.system,
                messages=rendered.to_messages(),
            )
        except anthropic.AuthenticationError as e:
            raise LLMAuthError("Anthropic rejected the API key.") from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError("Anthropic rate limit hit.") from e
        except anthropic.APIConnectionError as e:
            raise LLMNetworkError("Network error talking to Anthropic.") from e
        except anthropic.APIStatusError as e:
            raise LLMResponseError(f"Anthropic returned status {e.status_code}: {e.message}") from e
        except anthropic.APIError as e:
            raise LLMResponseError(f"Anthropic API error: {e}") from e

        _record_usage_from_response(response)
        return _extract_text(response)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _record_usage_from_response(response: Any) -> None:
    """Publish token usage from a Messages response so RecordingProvider sees it."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    record_usage(
        TokenUsage(
            input_tokens=_optional_int(getattr(usage, "input_tokens", None)),
            output_tokens=_optional_int(getattr(usage, "output_tokens", None)),
        )
    )


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _extract_text(response: Any) -> str:
    """Concatenate all text blocks from a Messages API response."""
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    if not parts:
        raise LLMResponseError("Anthropic returned no text content.")
    return "".join(parts)


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object out of `text`, tolerating ``` fences."""
    candidate = text.strip()
    fenced = _FENCED_JSON_RE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        result = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise LLMResponseError(f"Response is not valid JSON: {e}") from e

    if not isinstance(result, dict):
        raise LLMResponseError(f"Expected JSON object, got {type(result).__name__}.")
    return result


def _parse_pydantic(text: str, model: type) -> Any:
    """Parse `text` as JSON and validate it against the given Pydantic model."""
    payload = _parse_json_object(text)
    try:
        return model.model_validate(payload)
    except ValidationError as e:
        raise LLMResponseError(f"{model.__name__} validation failed: {e}") from e


_SOURCES_HEADER_RE = re.compile(r"^##\s*Sources\s*$", re.MULTILINE | re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$", re.MULTILINE)


def _extract_markdown_sources(text: str) -> list[str]:
    """Pull bullet items under a `## Sources` heading, if present."""
    match = _SOURCES_HEADER_RE.search(text)
    if not match:
        return []
    section = text[match.end() :]
    next_section = re.search(r"^##\s+(?!#)", section, re.MULTILINE)
    if next_section:
        section = section[: next_section.start()]
    return [m.group(1).strip() for m in _BULLET_RE.finditer(section)]


__all__ = ["ANTHROPIC_API_KEY_NAME", "DEFAULT_MODEL", "AnthropicAPIAdapter"]
