"""OpenAIAPIAdapter — LLMProvider backed by the OpenAI Chat Completions API.

The direct-API counterpart to ``codex_cli`` (which shells out to the local
Codex CLI). Users who have an OpenAI API key can point the app at it and be
billed per-token like the Anthropic API adapter.

Wiring mirrors :mod:`llm.anthropic_api`:

    1. Read the API key from the OS keychain via ``llm.credentials`` (or the
       ``OPENAI_API_KEY`` env var / an explicit ``api_key``).
    2. Read the model from ``app_config.model`` (defaults to ``gpt-4o``).
    3. For each method, load the versioned prompt, render it, call the chat
       completions endpoint, and parse JSON output into a Pydantic model,
       raising typed ``LLMError`` subclasses on failure.

The prompts are provider-agnostic and reused unchanged. This adapter targets
the stable Chat Completions API and the gpt-4o family; o-series reasoning
models (which reject ``temperature`` / ``max_tokens``) are out of scope.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterator
from typing import Any

import openai
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

DEFAULT_MODEL = "gpt-4o"
OPENAI_API_KEY_NAME = "openai_api_key"

# Temperatures per shape: low for structured JSON, higher for the open-ended
# coach stream. Mirrors the Ollama adapter's split.
_JSON_TEMPERATURE = 0.2
_CHAT_TEMPERATURE = 0.5

# Token budgets per task (identical to the Anthropic adapter).
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


class OpenAIAPIAdapter:
    """LLMProvider implementation backed by the OpenAI public API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        client: openai.OpenAI | None = None,
    ) -> None:
        self.model = model
        if client is not None:
            self._client = client
        else:
            resolved_key = (
                api_key or get_credential(OPENAI_API_KEY_NAME) or os.getenv("OPENAI_API_KEY")
            )
            if not resolved_key:
                raise LLMAuthError(
                    "OpenAI API key not found. Set it via `set_credential"
                    "('openai_api_key', ...)` or the OPENAI_API_KEY env var."
                )
            self._client = openai.OpenAI(api_key=resolved_key)

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
            sources=[],  # Chat Completions has no web access — no live sources.
        )

    def tailor_cv(self, profile: Profile, job: Job) -> str:
        rendered = load_prompt(
            "tailor_cv",
            profile=profile.model_dump(mode="json"),
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
        )
        return self._call(rendered, max_tokens=_MAX_TOKENS["tailor_cv"]).strip()

    def generate_cover_letter(self, profile: Profile, job: Job, brief: CompanyBrief) -> CoverLetter:
        rendered = load_prompt(
            "generate_cover_letter",
            profile=profile.model_dump(mode="json"),
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
            company_brief=brief.markdown,
        )
        body = self._call(rendered, max_tokens=_MAX_TOKENS["generate_cover_letter"]).strip()
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
        except ValidationError as exc:
            raise LLMResponseError(f"InterviewQuestion validation failed: {exc}") from exc

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
        return self._call(rendered, max_tokens=_MAX_TOKENS["summarize_role"]).strip()

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
        provider_messages = _history_to_chat_messages(messages, rendered)
        usage: Any = None
        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=provider_messages,
                max_tokens=_MAX_TOKENS["interview_chat_stream"],
                temperature=_CHAT_TEMPERATURE,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                if getattr(chunk, "usage", None) is not None:
                    usage = chunk.usage
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                if isinstance(content, str) and content:
                    yield content
        except openai.AuthenticationError as exc:
            raise LLMAuthError("OpenAI rejected the API key.") from exc
        except openai.RateLimitError as exc:
            raise LLMRateLimitError("OpenAI rate limit hit.") from exc
        except openai.APIConnectionError as exc:
            raise LLMNetworkError("Network error talking to OpenAI.") from exc
        except openai.APIStatusError as exc:
            raise LLMResponseError(
                f"OpenAI returned status {exc.status_code}: {exc.message}"
            ) from exc
        except openai.APIError as exc:
            raise LLMResponseError(f"OpenAI API error: {exc}") from exc

        _record_usage(usage)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call(self, rendered: RenderedPrompt, *, max_tokens: int) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=_to_chat_messages(rendered),
                max_tokens=max_tokens,
                temperature=_JSON_TEMPERATURE,
            )
        except openai.AuthenticationError as exc:
            raise LLMAuthError("OpenAI rejected the API key.") from exc
        except openai.RateLimitError as exc:
            raise LLMRateLimitError("OpenAI rate limit hit.") from exc
        except openai.APIConnectionError as exc:
            raise LLMNetworkError("Network error talking to OpenAI.") from exc
        except openai.APIStatusError as exc:
            raise LLMResponseError(
                f"OpenAI returned status {exc.status_code}: {exc.message}"
            ) from exc
        except openai.APIError as exc:
            raise LLMResponseError(f"OpenAI API error: {exc}") from exc

        _record_usage(getattr(response, "usage", None))

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise LLMResponseError("OpenAI returned no choices.")
        content = getattr(getattr(choices[0], "message", None), "content", None)
        if not isinstance(content, str) or not content:
            raise LLMResponseError("OpenAI returned no text content.")
        return content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _to_chat_messages(rendered: RenderedPrompt) -> list[dict[str, str]]:
    """Build a Chat Completions ``messages`` array from a rendered prompt."""
    messages: list[dict[str, str]] = [{"role": "system", "content": rendered.system}]
    for example in rendered.examples:
        messages.append({"role": "user", "content": example.input_text})
        messages.append({"role": "assistant", "content": example.output_text})
    messages.append({"role": "user", "content": rendered.user})
    return messages


def _history_to_chat_messages(
    history: list[ChatMessage], rendered: RenderedPrompt
) -> list[dict[str, str]]:
    """Build the messages array for a multi-turn coach session.

    Prepends the system prompt, then forwards the caller's history. Empty
    history falls back to the prompt's kickoff user template.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": rendered.system}]
    if not history:
        messages.append({"role": "user", "content": rendered.user})
        return messages
    messages.extend({"role": m.role, "content": m.content} for m in history)
    return messages


def _record_usage(usage: Any) -> None:
    """Publish token usage from a chat-completions response/chunk."""
    if usage is None:
        return
    record_usage(
        TokenUsage(
            input_tokens=_optional_int(getattr(usage, "prompt_tokens", None)),
            output_tokens=_optional_int(getattr(usage, "completion_tokens", None)),
        )
    )


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object out of `text`, tolerating ``` fences."""
    candidate = text.strip()
    fenced = _FENCED_JSON_RE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        result = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"Response is not valid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise LLMResponseError(f"Expected JSON object, got {type(result).__name__}.")
    return result


def _parse_pydantic(text: str, model: type) -> Any:
    """Parse `text` as JSON and validate it against the given Pydantic model."""
    payload = _parse_json_object(text)
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise LLMResponseError(f"{model.__name__} validation failed: {exc}") from exc


__all__ = ["DEFAULT_MODEL", "OPENAI_API_KEY_NAME", "OpenAIAPIAdapter"]
