"""ClaudeCodeAdapter — wraps the local ``claude`` CLI via subprocess.

Why this exists alongside ``AnthropicAPIAdapter``: a subset of users have
a Claude Pro / Max subscription and would prefer the calls to be billed
to that subscription (via the Claude Code CLI) rather than to a separate
API key. This adapter is **experimental** — see ADR-0005 R-01 for the
gray-zone discussion. The Settings UI surfaces an "Experimental" badge
before the user selects it.

Wire model:

    1. ``shutil.which("claude")`` resolves the binary at construction.
       If it's missing we raise ``LLMError`` with a clear "install Claude
       Code first" message so the setup wizard can render it cleanly.
    2. For each method we render the same prompt templates the API
       adapter uses, flatten any few-shot examples into the single user
       turn (the CLI is single-turn via ``-p``), and run::

           claude -p --output-format json --append-system-prompt <system>

       piping the user text in via stdin to avoid CLI length / quoting
       limits. Per-call timeout: 120 seconds.
    3. The CLI emits a single JSON object on stdout; we extract
       ``result`` as the assistant's text and parse it the same way the
       API adapter does (JSON object, fenced JSON, or plain markdown).
    4. When the JSON object includes a ``usage`` block we publish the
       token counts via ``llm.usage.record_usage`` so the recorder
       reports them on the call log just like the API adapter.

Failure mapping:

    - CLI missing at construction       → ``LLMError`` ("not installed")
    - subprocess timeout / OSError      → ``LLMNetworkError``
    - non-zero exit / ``is_error: true``→ ``LLMResponseError``
    - malformed JSON / missing fields   → ``LLMResponseError``

The interface guarantees match ``AnthropicAPIAdapter``; everything that
takes an ``LLMProvider`` keeps working unchanged.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import time
from collections.abc import Iterator
from typing import Any

from pydantic import ValidationError

from .errors import (
    LLMError,
    LLMNetworkError,
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
    Profile,
    ScoreResult,
)
from .usage import TokenUsage, record_usage

logger = logging.getLogger(__name__)

CLAUDE_CLI_NAME = "claude"
DEFAULT_TIMEOUT_S = 120.0

# Tool name to allow for the company-research call so the CLI can ground the
# brief in live results. Verified against `claude --help` in this environment:
#
#     --allowedTools, --allowed-tools <tools...>
#         Comma or space-separated list of tool names to allow (e.g. "Bash(git *) Edit")
#
# The built-in web-search tool is named "WebSearch" (see `--tools` help, which
# lists it among the built-in set). We scope this to the research call only;
# every other `_call` runs with no tools allowed.
WEB_SEARCH_TOOL_NAME = "WebSearch"


class ClaudeCodeAdapter:
    """LLMProvider implementation backed by the local ``claude`` CLI."""

    def __init__(
        self,
        *,
        cli_path: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        resolved = cli_path or shutil.which(CLAUDE_CLI_NAME)
        if not resolved:
            raise LLMError(
                "Claude Code CLI not found. Install Claude Code "
                "(https://docs.anthropic.com/claude-code) and ensure "
                "`claude` is on PATH, or switch to a different provider."
            )
        self._cli_path = resolved
        self._timeout_s = timeout_s

    @property
    def cli_path(self) -> str:
        return self._cli_path

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
        # Scope the web-search tool to *this* call only — every other `_call`
        # runs with no tools allowed.
        text = self._call(rendered, allowed_tools=[WEB_SEARCH_TOOL_NAME])
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

    def interview_chat_stream(
        self,
        messages: list[ChatMessage],
        role_context: str | None = None,
    ) -> Iterator[str]:
        rendered = load_prompt("interview_coach", role_context=role_context or "")
        user_text = _flatten_chat_for_single_turn(messages, rendered)
        argv = [
            self._cli_path,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--append-system-prompt",
            rendered.system,
        ]
        try:
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            raise LLMNetworkError(f"Failed to launch claude CLI: {exc}") from exc

        try:
            assert proc.stdin is not None
            proc.stdin.write(user_text)
            proc.stdin.close()
        except OSError as exc:
            proc.kill()
            raise LLMNetworkError(f"Failed to write to claude CLI: {exc}") from exc

        assert proc.stdout is not None
        deadline = time.monotonic() + self._timeout_s
        usage_payload: Any = None
        try:
            for line in proc.stdout:
                if time.monotonic() > deadline:
                    proc.kill()
                    raise LLMNetworkError(
                        f"claude CLI exceeded {self._timeout_s:.0f}s during stream."
                    )
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                delta = _extract_stream_delta(event)
                if delta:
                    yield delta
                if event.get("type") == "result":
                    if event.get("is_error") is True:
                        message = event.get("error") or event.get("result") or "<no message>"
                        raise LLMResponseError(f"claude CLI reported is_error: {message}")
                    usage_payload = event.get("usage")
        finally:
            returncode = proc.wait(timeout=max(1.0, deadline - time.monotonic()))
            if returncode != 0:
                stderr = (proc.stderr.read() if proc.stderr else "").strip()
                raise LLMResponseError(f"claude CLI exited {returncode}: {stderr or '<no stderr>'}")

        _maybe_record_usage(usage_payload)

    # ------------------------------------------------------------------
    # Subprocess plumbing
    # ------------------------------------------------------------------

    def _call(self, rendered: RenderedPrompt, *, allowed_tools: list[str] | None = None) -> str:
        user_text = _flatten_for_single_turn(rendered)
        argv = [
            self._cli_path,
            "-p",
            "--output-format",
            "json",
            "--append-system-prompt",
            rendered.system,
        ]
        if allowed_tools:
            # Comma/space-separated list of tool names to allow (see
            # `claude --help`). Without this the CLI runs prompt-only.
            argv += ["--allowedTools", ",".join(allowed_tools)]
        try:
            completed = subprocess.run(
                argv,
                input=user_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMNetworkError(f"claude CLI timed out after {self._timeout_s:.0f}s.") from exc
        except OSError as exc:
            raise LLMNetworkError(f"Failed to launch claude CLI: {exc}") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise LLMResponseError(
                f"claude CLI exited {completed.returncode}: {stderr or '<no stderr>'}"
            )

        return _extract_result_text(completed.stdout or "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)
_SOURCES_HEADER_RE = re.compile(r"^##\s*Sources\s*$", re.MULTILINE | re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$", re.MULTILINE)


def _extract_stream_delta(event: dict) -> str | None:
    """Pull a text delta out of one ``--output-format stream-json`` event.

    The CLI emits a few event shapes; we tolerate either of two text carriers
    so a future CLI update doesn't silently break us:

    1. ``stream_event`` wrapping a ``content_block_delta`` (partial messages
       mode) — the per-token shape, what we want for true streaming.
    2. ``assistant`` events that carry a full message — falls back to a
       single chunk if partial messages aren't enabled by the installed CLI.
    """
    event_type = event.get("type")
    if event_type == "stream_event":
        inner = event.get("event")
        if isinstance(inner, dict) and inner.get("type") == "content_block_delta":
            delta = inner.get("delta")
            if isinstance(delta, dict) and delta.get("type") == "text_delta":
                text = delta.get("text")
                if isinstance(text, str) and text:
                    return text
        return None
    if event_type == "assistant":
        msg = event.get("message")
        if isinstance(msg, dict):
            parts = msg.get("content")
            if isinstance(parts, list):
                texts: list[str] = []
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text")
                        if isinstance(text, str):
                            texts.append(text)
                if texts:
                    return "".join(texts)
    return None


def _flatten_chat_for_single_turn(messages: list[ChatMessage], rendered: RenderedPrompt) -> str:
    """Flatten a chat history into one user turn for the CLI's ``-p`` mode.

    The CLI has no native multi-turn input; we inline the prior turns as
    labelled blocks so the model can read them as context, then ask for the
    next coach reply.
    """
    if not messages:
        return rendered.user
    blocks: list[str] = []
    for m in messages:
        label = "Candidate" if m.role == "user" else "Coach"
        blocks.append(f"{label}:\n{m.content}")
    blocks.append("Continue as the coach. Reply with the next turn only.")
    return "\n\n---\n\n".join(blocks)


def _flatten_for_single_turn(rendered: RenderedPrompt) -> str:
    """Inline few-shot examples into the user turn.

    The CLI's ``-p`` mode is single-turn — there's no way to pass an
    explicit chat history. We mimic the Anthropic SDK's interleaving by
    concatenating each example's input and output as labelled blocks and
    finishing with the real user prompt. Smaller models occasionally
    treat this as instructions; the prompts already lead with "Return
    ONLY valid JSON" / similar guards, so this hasn't been a problem in
    spot-checking but is worth flagging in PR review for any new prompt.
    """
    if not rendered.examples:
        return rendered.user
    blocks: list[str] = []
    for example in rendered.examples:
        blocks.append(
            f"Example input:\n{example.input_text}\n\nExample output:\n{example.output_text}"
        )
    blocks.append(rendered.user)
    return "\n\n---\n\n".join(blocks)


def _extract_result_text(stdout: str) -> str:
    """Pull the assistant text out of a ``--output-format json`` payload.

    Also publishes any reported token usage so ``RecordingProvider``
    persists it on ``provider_call_log``.
    """
    raw = stdout.strip()
    if not raw:
        raise LLMResponseError("claude CLI returned no stdout.")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"claude CLI stdout was not JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise LLMResponseError(f"claude CLI returned non-object JSON: {type(payload).__name__}")

    if payload.get("is_error") is True:
        message = payload.get("error") or payload.get("result") or "<no message>"
        raise LLMResponseError(f"claude CLI reported is_error: {message}")

    text = payload.get("result")
    if not isinstance(text, str):
        raise LLMResponseError("claude CLI JSON missing string 'result' field.")

    _maybe_record_usage(payload.get("usage"))
    return text


def _maybe_record_usage(usage: Any) -> None:
    if not isinstance(usage, dict):
        return
    record_usage(
        TokenUsage(
            input_tokens=_optional_int(usage.get("input_tokens")),
            output_tokens=_optional_int(usage.get("output_tokens")),
        )
    )


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


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


def _extract_markdown_sources(text: str) -> list[str]:
    match = _SOURCES_HEADER_RE.search(text)
    if not match:
        return []
    section = text[match.end() :]
    next_section = re.search(r"^##\s+(?!#)", section, re.MULTILINE)
    if next_section:
        section = section[: next_section.start()]
    return [m.group(1).strip() for m in _BULLET_RE.finditer(section)]


__all__ = [
    "CLAUDE_CLI_NAME",
    "DEFAULT_TIMEOUT_S",
    "WEB_SEARCH_TOOL_NAME",
    "ClaudeCodeAdapter",
]
