"""Per-call token usage tracking.

The Anthropic SDK returns ``response.usage.input_tokens`` /
``output_tokens`` on every Messages call. ``RecordingProvider`` sits one
layer above the adapter and needs to record those numbers in
``provider_call_log`` for cost rollups, but it can't observe the raw
response.

A ``ContextVar`` solves the seam without changing the ``LLMProvider``
Protocol. The adapter publishes usage right after each successful API
call; the recorder consumes it at the end of ``_record`` and clears it.

Cleared-on-consume semantics matter so that a method that doesn't make
a Provider API call (a future MockProvider, a cached path) doesn't
accidentally inherit a stale reading from a prior call.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None


_LAST_USAGE: contextvars.ContextVar[TokenUsage | None] = contextvars.ContextVar(
    "hired_last_usage", default=None
)


def record_usage(usage: TokenUsage) -> None:
    """Publish token usage from an adapter; consumed once and then cleared."""
    _LAST_USAGE.set(usage)


def consume_usage() -> TokenUsage | None:
    """Return the most recently recorded usage and clear the slot."""
    usage = _LAST_USAGE.get()
    if usage is not None:
        _LAST_USAGE.set(None)
    return usage


__all__ = ["TokenUsage", "consume_usage", "record_usage"]
