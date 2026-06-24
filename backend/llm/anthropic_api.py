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
from collections.abc import Iterator
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
    ChatMessage,
    CompanyBrief,
    CoverLetter,
    InterviewQuestion,
    Job,
    MockInterviewContext,
    MockInterviewEvaluation,
    MockInterviewPlan,
    MockQAPair,
    Profile,
    ScoreResult,
)
from .usage import TokenUsage, record_usage

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_API_KEY_NAME = "anthropic_api_key"

# The stable server-side web-search tool. Works with the current generation
# models and needs no extra deps (the newer ``web_search_20260209`` variant
# requires the code-execution tool, which is overkill here). Activating it lets
# ``research_company`` ground its brief in real results instead of fabricating
# for small/new companies. See backend/prompts/research_company.md.
WEB_SEARCH_TOOL: dict[str, str] = {"type": "web_search_20250305", "name": "web_search"}

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
    "interview_chat_stream": 1024,
    "generate_mock_interview_questions": 2048,
    "evaluate_mock_interview": 2048,
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
        # Activate the real web-search tool *for this call only* so the brief is
        # grounded in live sources rather than the model's memory.
        response = self._raw_call(
            rendered,
            max_tokens=_MAX_TOKENS["research_company"],
            tools=[WEB_SEARCH_TOOL],
        )
        text = _extract_text(response)
        # Prefer real URLs returned by the web-search tool; fall back to scraping
        # the model's ``## Sources`` section only when the tool returned nothing
        # (e.g. it found no results and the model wrote them inline).
        sources = _extract_web_search_sources(response) or _extract_markdown_sources(text)
        return CompanyBrief(
            company=company,
            markdown=text.strip(),
            sources=sources,
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

    def generate_mock_interview_questions(
        self,
        job: Job,
        profile: Profile,
        context: MockInterviewContext,
    ) -> MockInterviewPlan:
        rendered = load_prompt(
            "generate_mock_interview_questions",
            job=job.model_dump(mode="json"),
            profile_json=profile.model_dump(mode="json"),
            context=context.model_dump(mode="json"),
            target_count=context.num_questions,
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["generate_mock_interview_questions"])
        return _parse_pydantic(text, MockInterviewPlan)

    def evaluate_mock_interview(
        self,
        job: Job,
        context: MockInterviewContext,
        qa_pairs: list[MockQAPair],
    ) -> MockInterviewEvaluation:
        rendered = load_prompt(
            "evaluate_mock_interview",
            job=job.model_dump(mode="json"),
            context=context.model_dump(mode="json"),
            qa_json=[qa.model_dump(mode="json") for qa in qa_pairs],
        )
        text = self._call(rendered, max_tokens=_MAX_TOKENS["evaluate_mock_interview"])
        return _parse_pydantic(text, MockInterviewEvaluation)

    def interview_chat_stream(
        self,
        messages: list[ChatMessage],
        role_context: str | None = None,
    ) -> Iterator[str]:
        rendered = load_prompt("interview_coach", role_context=role_context or "")
        provider_messages = _to_anthropic_messages(messages, rendered)
        try:
            with self._client.messages.stream(
                model=self.model,
                max_tokens=_MAX_TOKENS["interview_chat_stream"],
                system=rendered.system,
                messages=provider_messages,
            ) as stream:
                for delta in stream.text_stream:
                    if delta:
                        yield delta
                final = stream.get_final_message()
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

        _record_usage_from_response(final)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call(self, rendered: RenderedPrompt, *, max_tokens: int) -> str:
        """Send `rendered` to the API and return the assistant's text reply."""
        response = self._raw_call(rendered, max_tokens=max_tokens)
        return _extract_text(response)

    def _raw_call(
        self,
        rendered: RenderedPrompt,
        *,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Send `rendered` to the API and return the raw Messages response.

        Most callers want the concatenated text (``_call``); the company-research
        path needs the full response so it can pull real source URLs out of the
        web-search tool-result blocks. ``tools`` is omitted entirely when
        ``None`` so we never force tool use onto plain prompt-only calls.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": rendered.system,
            "messages": rendered.to_messages(),
        }
        if tools is not None:
            kwargs["tools"] = tools
        try:
            response = self._client.messages.create(**kwargs)
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
        return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _to_anthropic_messages(
    history: list[ChatMessage], rendered: RenderedPrompt
) -> list[dict[str, str]]:
    """Convert a chat history into Anthropic's messages array.

    If the history is empty (new session), the prompt's user-template kickoff
    becomes the single first user turn. Otherwise the history is forwarded
    verbatim. Anthropic requires the conversation to start with a user turn
    and alternate; we trust callers to honour that (the PR B endpoint will).
    """
    if not history:
        return [{"role": "user", "content": rendered.user}]
    return [{"role": m.role, "content": m.content} for m in history]


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


def _extract_web_search_sources(response: Any) -> list[str]:
    """Collect real source URLs from a web-search-enabled Messages response.

    Walks ``response.content`` and pulls URLs from two places, de-duplicated and
    order-preserving:

    1. ``web_search_tool_result`` blocks → their ``.content`` list of
       ``web_search_result`` items (each carrying ``url`` / ``title``).
    2. Inline ``citations`` on text blocks — entries of type
       ``web_search_result_location`` (also carry ``url`` / ``title``).

    Blocks may be SDK objects (attribute access) or plain dicts; we use
    ``getattr`` with a dict fallback so this stays robust to SDK shape changes
    and is unit-testable with simple fakes.
    """
    urls: list[str] = []
    seen: set[str] = set()

    def _add(url: Any) -> None:
        if isinstance(url, str) and url and url not in seen:
            seen.add(url)
            urls.append(url)

    for block in getattr(response, "content", []) or []:
        block_type = _get(block, "type")
        if block_type == "web_search_tool_result":
            results = _get(block, "content") or []
            for item in results:
                if _get(item, "type") == "web_search_result":
                    _add(_get(item, "url"))
        else:
            # Text blocks may carry inline web-search citations.
            for citation in _get(block, "citations") or []:
                if _get(citation, "type") == "web_search_result_location":
                    _add(_get(citation, "url"))
    return urls


def _get(obj: Any, name: str) -> Any:
    """Attribute-or-key access for SDK objects and plain dicts alike."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


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
