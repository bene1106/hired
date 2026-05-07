"""End-to-end "does this provider actually work?" check.

Used by ``POST /api/setup/test-provider``. For real providers we make one
small round-trip and time it; for ``mock`` we trivially succeed. Errors are
classified into a stable string set so the frontend can render a friendly
message without parsing free text.
"""

from __future__ import annotations

import logging
import time
from typing import Literal

from typing_extensions import TypedDict

from llm.anthropic_api import DEFAULT_MODEL, AnthropicAPIAdapter
from llm.errors import (
    LLMAuthError,
    LLMError,
    LLMNetworkError,
    LLMRateLimitError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)

ErrorKind = Literal[
    "missing_api_key",
    "auth_failed",
    "rate_limited",
    "network_error",
    "bad_response",
    "unknown",
    "unsupported_provider",
]


class TestProviderResult(TypedDict):
    ok: bool
    latency_ms: int
    error: str | None
    error_kind: ErrorKind | None


def test_provider(provider: str, api_key: str | None = None) -> TestProviderResult:
    """Run a tiny round-trip against ``provider`` and return latency + result."""
    if provider == "mock":
        # Trivially OK — surfaces "MockProvider is wired up" in the UI.
        return {"ok": True, "latency_ms": 0, "error": None, "error_kind": None}

    if provider == "anthropic_api":
        return _test_anthropic_api(api_key)

    if provider in {"claude_code", "ollama"}:
        # Adapters land in Phase 6. We still want detection in Phase 3 so
        # users see the cards, but selecting them is blocked at the UI.
        return {
            "ok": False,
            "latency_ms": 0,
            "error": f"{provider} adapter is not yet implemented (Phase 6).",
            "error_kind": "unsupported_provider",
        }

    return {
        "ok": False,
        "latency_ms": 0,
        "error": f"Unknown provider '{provider}'.",
        "error_kind": "unsupported_provider",
    }


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
