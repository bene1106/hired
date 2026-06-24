"""CodexCLIAdapter — wraps the local ``codex`` CLI via subprocess.

This is the OpenAI counterpart to :mod:`llm.claude_code`. A subset of users
have a ChatGPT Plus / Pro / Business subscription (or an ``OPENAI_API_KEY``)
wired into the OpenAI **Codex CLI** and would prefer their calls to be billed
through that rather than a separate Anthropic key. Like Claude Code, this
adapter is **experimental** — the CLI is a documented gray zone (see
ADR-0010) and the Settings / onboarding UI surfaces an "Experimental" badge
before the user selects it.

Wire model:

    1. ``shutil.which("codex")`` resolves the binary at construction. If it's
       missing we raise ``LLMError`` with a clear "install Codex first"
       message so the setup wizard can render it cleanly.
    2. For each method we render the same prompt templates the other adapters
       use. Codex's ``exec`` mode has no ``--append-system-prompt`` flag, so
       we fold the system prompt (and any flattened few-shot examples) into a
       single prompt string and run::

           codex exec --json --skip-git-repo-check --sandbox read-only \
               --color never --ephemeral -

       piping the prompt in via stdin (the trailing ``-`` tells Codex to read
       instructions from stdin). ``--sandbox read-only`` keeps the agent from
       writing to the user's working tree — our prompts are self-contained
       text-generation tasks, so the agent never needs to touch the disk.
       Per-call timeout: 180 seconds (Codex models reason before answering).
    3. ``codex exec --json`` emits **JSONL** events on stdout. We collect the
       assistant text from the ``item.completed`` event whose item type is
       ``agent_message`` and parse it the same way the other adapters do
       (JSON object, fenced JSON, or plain markdown).
    4. When the terminal ``turn.completed`` event carries a ``usage`` block we
       publish the token counts via ``llm.usage.record_usage`` so the recorder
       reports them on the call log just like the API adapter.

Failure mapping — note that ``codex exec`` exits **0 even on a model/auth
error**, surfacing the failure only as an ``error`` / ``turn.failed`` JSONL
event. So we drive error detection off the event stream, not the return code:

    - CLI missing at construction        → ``LLMError`` ("not installed")
    - subprocess timeout / ``OSError``    → ``LLMNetworkError``
    - ``error`` / ``turn.failed`` event   → ``LLMResponseError``
    - non-zero exit with no agent text    → ``LLMResponseError``
    - no ``agent_message`` / bad JSON     → ``LLMResponseError``

The interface guarantees match the other adapters; everything that takes an
``LLMProvider`` keeps working unchanged.
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
    MockInterviewContext,
    MockInterviewEvaluation,
    MockInterviewPlan,
    MockQAPair,
    Profile,
    ScoreResult,
)
from .usage import TokenUsage, record_usage

logger = logging.getLogger(__name__)

CODEX_CLI_NAME = "codex"
DEFAULT_TIMEOUT_S = 180.0

# Codex's built-in web-search tool is gated behind a config flag rather than a
# CLI switch. Verified against `codex --version` 0.120.0 in this environment:
#
#   * `codex exec --help` exposes no `--web-search` / `--search` flag.
#   * `codex features list` shows `search_tool` as **removed** and
#     `web_search_request` / `web_search_cached` as **deprecated** — so there is
#     no stable feature-flag toggle either.
#   * The documented escape hatch is the config override `-c tools.web_search=true`
#     (the same `-c key=value` mechanism `--model` etc. use). `codex exec -c
#     tools.web_search=true ...` is accepted without error.
#
# We pass this override on the research call only. Codex streams the whole reply
# as one `agent_message` (no structured web_search_result_location blocks like
# the Anthropic API), so sources are still scraped from the model's `## Sources`
# section. If a future Codex drops the key the override is simply ignored and the
# brief degrades to training-data quality — no fabricated structured sources.
WEB_SEARCH_CONFIG_OVERRIDE = "tools.web_search=true"


class CodexCLIAdapter:
    """LLMProvider implementation backed by the local ``codex`` CLI."""

    def __init__(
        self,
        *,
        cli_path: str | None = None,
        model: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        resolved = cli_path or shutil.which(CODEX_CLI_NAME)
        if not resolved:
            raise LLMError(
                "OpenAI Codex CLI not found. Install Codex "
                "(https://github.com/openai/codex) and ensure `codex` is on "
                "PATH, then run `codex login` — or switch to a different provider."
            )
        self._cli_path = resolved
        # ``model`` is intentionally optional and left unset by the factory:
        # Codex uses whatever model its own ``~/.codex/config.toml`` selects.
        # We only pass ``-m`` when a caller explicitly pins one, so the
        # app-wide ``app_config.model`` (an Anthropic default) never leaks in.
        self._model = model or None
        self._timeout_s = timeout_s

    @property
    def cli_path(self) -> str:
        return self._cli_path

    @property
    def model(self) -> str | None:
        return self._model

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
        # Enable Codex's web-search tool for this call only so the brief is
        # grounded in live results instead of training data.
        text = self._call(rendered, config_overrides=[WEB_SEARCH_CONFIG_OVERRIDE])
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
        return _parse_pydantic(self._call(rendered), MockInterviewPlan)

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
        return _parse_pydantic(self._call(rendered), MockInterviewEvaluation)

    def interview_chat_stream(
        self,
        messages: list[ChatMessage],
        role_context: str | None = None,
    ) -> Iterator[str]:
        rendered = load_prompt("interview_coach", role_context=role_context or "")
        prompt = _compose_chat_prompt(messages, rendered)
        argv = self._build_argv()
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
            raise LLMNetworkError(f"Failed to launch codex CLI: {exc}") from exc

        try:
            assert proc.stdin is not None
            proc.stdin.write(prompt)
            proc.stdin.close()
        except OSError as exc:
            proc.kill()
            raise LLMNetworkError(f"Failed to write to codex CLI: {exc}") from exc

        assert proc.stdout is not None
        deadline = time.monotonic() + self._timeout_s
        usage_payload: Any = None
        try:
            for line in proc.stdout:
                if time.monotonic() > deadline:
                    proc.kill()
                    raise LLMNetworkError(
                        f"codex CLI exceeded {self._timeout_s:.0f}s during stream."
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
                error = _extract_error(event)
                if error is not None:
                    raise LLMResponseError(f"codex CLI reported an error: {error}")
                # Codex ``exec --json`` does not stream token deltas — it emits
                # the whole reply in one ``agent_message`` ``item.completed``
                # event. We yield that as a single chunk; the SSE consumer
                # handles single- or multi-chunk streams identically.
                delta = _extract_agent_text(event)
                if delta:
                    yield delta
                usage = _extract_usage(event)
                if usage is not None:
                    usage_payload = usage
        finally:
            returncode = proc.wait(timeout=max(1.0, deadline - time.monotonic()))
            if returncode != 0:
                stderr = (proc.stderr.read() if proc.stderr else "").strip()
                raise LLMResponseError(f"codex CLI exited {returncode}: {stderr or '<no stderr>'}")

        _maybe_record_usage(usage_payload)

    # ------------------------------------------------------------------
    # Subprocess plumbing
    # ------------------------------------------------------------------

    def _build_argv(self, *, config_overrides: list[str] | None = None) -> list[str]:
        argv = [
            self._cli_path,
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--ephemeral",
        ]
        for override in config_overrides or []:
            argv += ["-c", override]
        if self._model:
            argv += ["--model", self._model]
        argv.append("-")  # read the prompt from stdin
        return argv

    def _call(self, rendered: RenderedPrompt, *, config_overrides: list[str] | None = None) -> str:
        prompt = _compose_prompt(rendered)
        argv = self._build_argv(config_overrides=config_overrides)
        try:
            completed = subprocess.run(
                argv,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMNetworkError(f"codex CLI timed out after {self._timeout_s:.0f}s.") from exc
        except OSError as exc:
            raise LLMNetworkError(f"Failed to launch codex CLI: {exc}") from exc

        return _parse_exec_output(
            completed.stdout or "",
            completed.returncode,
            completed.stderr or "",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)
_SOURCES_HEADER_RE = re.compile(r"^##\s*Sources\s*$", re.MULTILINE | re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$", re.MULTILINE)


def _parse_exec_output(stdout: str, returncode: int, stderr: str) -> str:
    """Pull the assistant text out of a ``codex exec --json`` JSONL stream.

    Also publishes any reported token usage so ``RecordingProvider`` persists
    it on ``provider_call_log``. Because ``codex exec`` returns 0 even when the
    model call fails, error detection is driven off ``error`` / ``turn.failed``
    events rather than the exit code.
    """
    texts: list[str] = []
    usage_payload: Any = None
    error_msg: str | None = None

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        error = _extract_error(event)
        if error is not None:
            error_msg = error
        text = _extract_agent_text(event)
        if text is not None:
            texts.append(text)
        usage = _extract_usage(event)
        if usage is not None:
            usage_payload = usage

    if error_msg is not None:
        raise LLMResponseError(f"codex CLI reported an error: {error_msg}")
    if returncode != 0 and not texts:
        raise LLMResponseError(f"codex CLI exited {returncode}: {stderr.strip() or '<no stderr>'}")
    if not texts:
        raise LLMResponseError("codex CLI returned no agent message.")

    _maybe_record_usage(usage_payload)
    return "".join(texts)


def _extract_agent_text(event: dict) -> str | None:
    """Return the assistant text from an ``item.completed`` agent message."""
    if event.get("type") != "item.completed":
        return None
    item = event.get("item")
    if not isinstance(item, dict) or item.get("type") != "agent_message":
        return None
    text = item.get("text")
    if isinstance(text, str) and text:
        return text
    return None


def _extract_error(event: dict) -> str | None:
    """Return a human-readable error string from an error/turn.failed event."""
    event_type = event.get("type")
    if event_type == "error":
        return _unwrap_error_message(event.get("message"))
    if event_type == "turn.failed":
        err = event.get("error")
        if isinstance(err, dict):
            return _unwrap_error_message(err.get("message"))
        return "<turn failed>"
    return None


def _unwrap_error_message(message: Any) -> str:
    """Best-effort flattening of Codex's nested error payloads.

    Codex frequently wraps the upstream API error as a JSON *string* inside
    ``message``. We dig out the innermost ``error.message`` when present so the
    UI shows "The 'x' model is not supported…" instead of a JSON blob.
    """
    if not isinstance(message, str):
        return "<no message>"
    candidate = message.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return candidate or "<no message>"
    if isinstance(parsed, dict):
        inner = parsed.get("error")
        if isinstance(inner, dict) and isinstance(inner.get("message"), str):
            return inner["message"]
        if isinstance(parsed.get("message"), str):
            return parsed["message"]
    return candidate or "<no message>"


def _extract_usage(event: dict) -> dict | None:
    if event.get("type") != "turn.completed":
        return None
    usage = event.get("usage")
    return usage if isinstance(usage, dict) else None


def _compose_prompt(rendered: RenderedPrompt) -> str:
    """Build the single prompt string Codex reads from stdin.

    Codex's ``exec`` mode has no system-prompt flag, so we prepend the system
    prompt to the (possibly few-shot-flattened) user turn as labelled blocks.
    """
    return _join_system(rendered.system, _flatten_for_single_turn(rendered))


def _flatten_for_single_turn(rendered: RenderedPrompt) -> str:
    """Inline few-shot examples into the user turn (single-turn ``exec`` mode)."""
    if not rendered.examples:
        return rendered.user
    blocks: list[str] = []
    for example in rendered.examples:
        blocks.append(
            f"Example input:\n{example.input_text}\n\nExample output:\n{example.output_text}"
        )
    blocks.append(rendered.user)
    return "\n\n---\n\n".join(blocks)


def _compose_chat_prompt(messages: list[ChatMessage], rendered: RenderedPrompt) -> str:
    """Flatten a chat history into one prompt, prefixed with the coach system."""
    if not messages:
        convo = rendered.user
    else:
        blocks: list[str] = []
        for m in messages:
            label = "Candidate" if m.role == "user" else "Coach"
            blocks.append(f"{label}:\n{m.content}")
        blocks.append("Continue as the coach. Reply with the next turn only.")
        convo = "\n\n---\n\n".join(blocks)
    return _join_system(rendered.system, convo)


def _join_system(system: str, user: str) -> str:
    system = (system or "").strip()
    if not system:
        return user
    return f"{system}\n\n---\n\n{user}"


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
    "CODEX_CLI_NAME",
    "DEFAULT_TIMEOUT_S",
    "WEB_SEARCH_CONFIG_OVERRIDE",
    "CodexCLIAdapter",
]
