"""OllamaAdapter — talks to a local ``ollama`` server over HTTP.

Local + offline: the user installs `ollama
<https://ollama.com>`_ and pulls a model (``ollama pull qwen2.5:14b``).
This adapter then hits ``http://localhost:11434/api/chat`` and reports
back to the rest of the app via the same ``LLMProvider`` interface as
the API adapter.

Wire model:

    1. ``base_url`` defaults to ``http://localhost:11434``; tests inject
       a custom ``httpx.Client`` so we never hit a real port.
    2. We use the chat endpoint (``/api/chat``), not ``/api/generate``,
       because the chat shape carries system messages and few-shot
       turns natively — the prompts already render that way.
    3. Per-call timeout: 180s. Local inference is slower than the API
       and the UI is expected to surface "may take up to 90s" copy
       alongside a Cancel button (Phase 6 spec §6.2).
    4. Token usage flows from Ollama's ``prompt_eval_count`` and
       ``eval_count`` fields through ``llm.usage.record_usage`` so the
       recorder still has something to log (cost rolls up under the
       ``local`` label so we deliberately don't price it).

Failure mapping mirrors the other adapters: connection / timeout
errors become ``LLMNetworkError``; non-200 responses, missing models,
and malformed JSON become ``LLMResponseError`` so callers can render a
single friendly message regardless of what went wrong.

The prompts are reused unchanged. Smaller Ollama models (``llama3.2:3b``)
sometimes drift from the requested JSON schema, especially when
``score_job`` is asked to return strict JSON — the prompt's
provider-notes section explicitly suggests dropping a few-shot example
or two for tight contexts. We don't do that automatically yet; if a
real user reports trouble we'll add a per-prompt knob.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from pydantic import ValidationError

from .errors import LLMNetworkError, LLMResponseError
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

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:14b"
FALLBACK_MODEL = "llama3.2:3b"
DEFAULT_TIMEOUT_S = 180.0
DEFAULT_TEMPERATURE = 0.2


class OllamaAdapter:
    """LLMProvider implementation backed by a local Ollama server."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        # If the caller supplied a client we don't own its lifecycle.
        self._client = client if client is not None else httpx.Client(timeout=timeout_s)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------
    # LLMProvider methods
    # ------------------------------------------------------------------

    def parse_cv(self, cv_text: str) -> dict:
        rendered = load_prompt("parse_cv", cv_text=cv_text)
        text = self._call(rendered)
        return _parse_json_object(text)

    def score_job(self, profile: Profile, job: Job) -> ScoreResult:
        rendered = load_prompt(
            "score_job",
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
        )
        text = self._call(rendered)
        return _parse_pydantic(text, ScoreResult)

    def research_company(self, company: str) -> CompanyBrief:
        rendered = load_prompt(
            "research_company",
            company_name=company,
            company_url="",
            industry_hint="",
        )
        text = self._call(rendered)
        return CompanyBrief(
            company=company,
            markdown=text.strip(),
            sources=[],  # Ollama has no web access — sources are intentionally empty.
        )

    def tailor_cv(self, profile: Profile, job: Job) -> str:
        rendered = load_prompt(
            "tailor_cv",
            profile=profile.model_dump(mode="json"),
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
        )
        return self._call(rendered).strip()

    def generate_cover_letter(self, profile: Profile, job: Job, brief: CompanyBrief) -> CoverLetter:
        rendered = load_prompt(
            "generate_cover_letter",
            profile=profile.model_dump(mode="json"),
            profile_json=profile.model_dump(mode="json"),
            job=job.model_dump(mode="json"),
            company_brief=brief.markdown,
        )
        body = self._call(rendered).strip()
        return CoverLetter(body=body, word_count=len(body.split()))

    def generate_interview_questions(self, job: Job) -> list[InterviewQuestion]:
        rendered = load_prompt(
            "generate_interview_questions",
            job=job.model_dump(mode="json"),
            company_brief="",
        )
        text = self._call(rendered)
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
        text = self._call(rendered)
        return _parse_pydantic(text, AnswerFeedback)

    def summarize_role(self, job: Job) -> str:
        rendered = load_prompt("summarize_role", job=job.model_dump(mode="json"))
        return self._call(rendered).strip()

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _call(self, rendered: RenderedPrompt) -> str:
        messages = _to_chat_messages(rendered)
        url = f"{self._base_url}/api/chat"
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": DEFAULT_TEMPERATURE},
        }

        try:
            response = self._client.post(url, json=body, timeout=self._timeout_s)
        except httpx.TimeoutException as exc:
            raise LLMNetworkError(
                f"Ollama timed out after {self._timeout_s:.0f}s. The model may be loading."
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMNetworkError(
                f"Could not reach Ollama at {self._base_url}. Is the server running?"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMNetworkError(f"Ollama HTTP error: {exc}") from exc

        if response.status_code == 404:
            # Ollama returns 404 with body like
            # {"error":"model 'qwen2.5:14b' not found, try pulling it first"}.
            message = _safe_error_message(response, default="not found")
            raise LLMResponseError(
                f"Model '{self.model}' not available locally. {message}"
            )
        if response.status_code >= 400:
            message = _safe_error_message(response, default=str(response.status_code))
            raise LLMResponseError(f"Ollama returned {response.status_code}: {message}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMResponseError(f"Ollama response was not JSON: {exc}") from exc

        if payload.get("error"):
            raise LLMResponseError(f"Ollama error: {payload['error']}")

        message = payload.get("message")
        if not isinstance(message, dict):
            raise LLMResponseError("Ollama response missing 'message' object.")

        content = message.get("content")
        if not isinstance(content, str):
            raise LLMResponseError("Ollama response missing string 'message.content'.")

        record_usage(
            TokenUsage(
                input_tokens=_optional_int(payload.get("prompt_eval_count")),
                output_tokens=_optional_int(payload.get("eval_count")),
            )
        )
        return content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _to_chat_messages(rendered: RenderedPrompt) -> list[dict[str, str]]:
    """Build the Ollama ``/api/chat`` ``messages`` array from a rendered prompt."""
    messages: list[dict[str, str]] = [{"role": "system", "content": rendered.system}]
    for example in rendered.examples:
        messages.append({"role": "user", "content": example.input_text})
        messages.append({"role": "assistant", "content": example.output_text})
    messages.append({"role": "user", "content": rendered.user})
    return messages


def _safe_error_message(response: httpx.Response, *, default: str) -> str:
    try:
        body = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text or default
    if isinstance(body, dict):
        msg = body.get("error") or body.get("message") or body.get("detail")
        if isinstance(msg, str) and msg:
            return msg
    return default


def _parse_json_object(text: str) -> dict:
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
    payload = _parse_json_object(text)
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise LLMResponseError(f"{model.__name__} validation failed: {exc}") from exc


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_S",
    "FALLBACK_MODEL",
    "OllamaAdapter",
]
