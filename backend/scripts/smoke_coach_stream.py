"""Backend API smoke for PR A — provider-level streaming.

Phase 8 PR A introduces ``LLMProvider.interview_chat_stream``. No HTTP
endpoint exists yet (that's PR B), so this script drives the provider
layer directly against ``MockProvider`` and prints the chunks it yields.

The purpose is to give Bene something to look at without firing up the
sidecar — proves the streaming method is wired through ``RecordingProvider``
and is actually producing more than one event.

Run from the ``backend`` directory:

    uv run python scripts/smoke_coach_stream.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Make ``llm.*`` importable without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm import MockProvider, RecordingProvider  # noqa: E402
from llm.types import ChatMessage  # noqa: E402


def main() -> int:
    provider = RecordingProvider(MockProvider(), "mock")
    history = [
        ChatMessage(
            role="assistant",
            content="Tell me about a recent project where you owned the design end-to-end.",
        ),
        ChatMessage(
            role="user",
            content=(
                "I built a payment service from scratch. I owned the schema, "
                "the API design, and the rollout."
            ),
        ),
    ]
    print("=== interview_chat_stream smoke ===")
    print(f"history turns: {len(history)}")
    print("--- chunks ---")
    chunk_count = 0
    total_chars = 0
    started = time.perf_counter()
    for chunk in provider.interview_chat_stream(history, role_context="Backend role."):
        chunk_count += 1
        total_chars += len(chunk)
        print(f"[{chunk_count:02d}] {chunk!r}")
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    print("--- summary ---")
    print(f"chunks emitted: {chunk_count}")
    print(f"total chars:    {total_chars}")
    print(f"elapsed:        {elapsed_ms} ms")

    if chunk_count < 2:
        print("FAIL: expected at least 2 chunks from a streaming provider.")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
