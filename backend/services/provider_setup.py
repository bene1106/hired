"""End-to-end "does this provider actually work?" check.

Used by ``POST /api/setup/test-provider``. For real providers we make one
small round-trip and time it; for ``mock`` we trivially succeed. Errors are
classified into a stable string set so the frontend can render a friendly
message without parsing free text.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from typing import Literal

import httpx
from typing_extensions import TypedDict

from llm.anthropic_api import DEFAULT_MODEL, AnthropicAPIAdapter
from llm.claude_code import CLAUDE_CLI_NAME
from llm.codex_cli import CODEX_CLI_NAME
from llm.errors import (
    LLMAuthError,
    LLMError,
    LLMNetworkError,
    LLMRateLimitError,
    LLMResponseError,
)
from llm.ollama import DEFAULT_BASE_URL as OLLAMA_BASE_URL
from llm.ollama import DEFAULT_MODEL as OLLAMA_DEFAULT_MODEL

logger = logging.getLogger(__name__)

ErrorKind = Literal[
    "missing_api_key",
    "auth_failed",
    "rate_limited",
    "network_error",
    "bad_response",
    "model_unavailable",
    "binary_missing",
    "unknown",
    "unsupported_provider",
]

_CLAUDE_VERSION_TIMEOUT_S = 10.0
_OLLAMA_TAGS_TIMEOUT_S = 5.0


class TestProviderResult(TypedDict):
    ok: bool
    latency_ms: int
    error: str | None
    error_kind: ErrorKind | None


def test_provider(
    provider: str,
    api_key: str | None = None,
    *,
    model: str | None = None,
) -> TestProviderResult:
    """Run a tiny round-trip against ``provider`` and return latency + result."""
    if provider == "mock":
        # Trivially OK — surfaces "MockProvider is wired up" in the UI.
        return {"ok": True, "latency_ms": 0, "error": None, "error_kind": None}

    if provider == "anthropic_api":
        return _test_anthropic_api(api_key)

    if provider == "claude_code":
        return _test_claude_code()

    if provider == "codex_cli":
        return _test_codex_cli()

    if provider == "ollama":
        return _test_ollama(model or OLLAMA_DEFAULT_MODEL)

    return {
        "ok": False,
        "latency_ms": 0,
        "error": f"Unknown provider '{provider}'.",
        "error_kind": "unsupported_provider",
    }


def _test_claude_code() -> TestProviderResult:
    """Verify the ``claude`` CLI is installed and responds to ``--version``.

    We deliberately don't run a real prompt here. ``claude --version`` is
    free, fast, and confirms the binary exists and is executable. A
    failed prompt round-trip is far more likely to be a transient
    subscription/network issue than a missing CLI; the user finds out
    on their first real generation either way.
    """
    path = shutil.which(CLAUDE_CLI_NAME)
    if not path:
        return {
            "ok": False,
            "latency_ms": 0,
            "error": (
                "Claude Code CLI not found on PATH. Install Claude Code "
                "(https://docs.anthropic.com/claude-code) and try again."
            ),
            "error_kind": "binary_missing",
        }
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=_CLAUDE_VERSION_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": "claude --version timed out.",
            "error_kind": "network_error",
        }
    except OSError as exc:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": f"Could not run claude CLI: {exc}",
            "error_kind": "binary_missing",
        }
    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or "<no stderr>"
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": f"claude --version exited {result.returncode}: {stderr}",
            "error_kind": "bad_response",
        }
    return {"ok": True, "latency_ms": _elapsed_ms(started), "error": None, "error_kind": None}


def _test_codex_cli() -> TestProviderResult:
    """Verify the ``codex`` CLI is installed and logged in.

    Like ``_test_claude_code`` we avoid a real (billable, slow) generation.
    But Codex is useless until the user runs ``codex login``, so we check
    ``codex login status`` — a free, fast round-trip that confirms both the
    binary exists and an account/key is wired up. A missing login surfaces as
    ``auth_failed`` so the wizard can prompt the user to run ``codex login``.
    """
    path = shutil.which(CODEX_CLI_NAME)
    if not path:
        return {
            "ok": False,
            "latency_ms": 0,
            "error": (
                "OpenAI Codex CLI not found on PATH. Install Codex "
                "(https://github.com/openai/codex) and try again."
            ),
            "error_kind": "binary_missing",
        }
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [path, "login", "status"],
            capture_output=True,
            text=True,
            timeout=_CLAUDE_VERSION_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": "codex login status timed out.",
            "error_kind": "network_error",
        }
    except OSError as exc:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": f"Could not run codex CLI: {exc}",
            "error_kind": "binary_missing",
        }
    out = (result.stdout or result.stderr or "").lower()
    logged_in = result.returncode == 0 and "logged in" in out and "not logged in" not in out
    if not logged_in:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": "Codex is installed but not logged in. Run `codex login` and try again.",
            "error_kind": "auth_failed",
        }
    return {"ok": True, "latency_ms": _elapsed_ms(started), "error": None, "error_kind": None}


def _test_ollama(model: str) -> TestProviderResult:
    """Verify the local Ollama server is reachable and the model is pulled.

    Hitting ``/api/tags`` is the one round-trip that confirms both
    server-up and model-available without paying for a real generation.
    Models that aren't pulled return ``model_unavailable`` so the UI can
    suggest ``ollama pull <model>``.
    """
    started = time.perf_counter()
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=_OLLAMA_TAGS_TIMEOUT_S)
    except httpx.ConnectError:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": (
                f"Could not reach Ollama at {OLLAMA_BASE_URL}. Make sure "
                "the server is running (`ollama serve`)."
            ),
            "error_kind": "network_error",
        }
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": f"Ollama HTTP error: {exc}",
            "error_kind": "network_error",
        }
    if response.status_code != 200:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": f"Ollama returned status {response.status_code}.",
            "error_kind": "bad_response",
        }
    try:
        body = response.json()
    except json.JSONDecodeError:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": "Ollama returned non-JSON for /api/tags.",
            "error_kind": "bad_response",
        }
    available = {
        m.get("name")
        for m in (body.get("models") or [])
        if isinstance(m, dict) and isinstance(m.get("name"), str)
    }
    if model not in available:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "error": (
                f"Model '{model}' is not pulled. Run `ollama pull {model}` "
                f"or pick from: {sorted(available)}"
            ),
            "error_kind": "model_unavailable",
        }
    return {"ok": True, "latency_ms": _elapsed_ms(started), "error": None, "error_kind": None}


def _test_anthropic_api(api_key: str | None) -> TestProviderResult:
    try:
        adapter = AnthropicAPIAdapter(api_key=api_key, model=DEFAULT_MODEL)
    except LLMAuthError as exc:
        return {
            "ok": False,
            "latency_ms": 0,
            "error": str(exc),
            "error_kind": "missing_api_key",
        }

    started = time.perf_counter()
    try:
        adapter._client.messages.create(  # type: ignore[attr-defined]
            model=adapter.model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:  # noqa: BLE001 - re-classified below
        kind, msg = _classify(exc)
        return {"ok": False, "latency_ms": _elapsed_ms(started), "error": msg, "error_kind": kind}

    return {"ok": True, "latency_ms": _elapsed_ms(started), "error": None, "error_kind": None}


def _classify(exc: Exception) -> tuple[ErrorKind, str]:
    # LLMError subclasses come from the adapter layer; raw anthropic errors
    # appear when the SDK call raises directly (e.g. the auth error above
    # would have surfaced at construction, but rate limits show up here).
    import anthropic  # local import to keep cold path cheap

    if isinstance(exc, (LLMAuthError, anthropic.AuthenticationError)):
        return "auth_failed", "API key was rejected."
    if isinstance(exc, (LLMRateLimitError, anthropic.RateLimitError)):
        return "rate_limited", "Anthropic rate limit hit. Try again in a moment."
    if isinstance(exc, (LLMNetworkError, anthropic.APIConnectionError)):
        return "network_error", "Could not reach the Anthropic API."
    if isinstance(exc, (LLMResponseError, anthropic.APIStatusError, anthropic.APIError)):
        return "bad_response", f"Anthropic returned an error: {exc}"
    if isinstance(exc, LLMError):
        return "unknown", str(exc)
    return "unknown", f"Unexpected error: {exc}"


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


__all__ = ["TestProviderResult", "test_provider"]
