"""Tests for the ``interview_coach`` prompt template.

The prompt is loaded by every adapter's ``interview_chat_stream``; if the
file's parse breaks, streaming breaks across providers. These tests guard
the file format independent of any adapter.
"""

from __future__ import annotations

from llm.prompts import load_prompt, reset_cache


def setup_function(_func: object) -> None:
    reset_cache()


def test_interview_coach_loads_and_substitutes_role_context() -> None:
    rendered = load_prompt(
        "interview_coach",
        role_context="Senior Backend Engineer at HealthTech GmbH (Python/FastAPI).",
    )
    assert rendered.system
    # The system prompt references the role context via {{role_context}}.
    assert "Senior Backend Engineer at HealthTech GmbH" in rendered.system
    # User template is the kickoff text used on empty-history starts.
    assert "Begin the practice interview" in rendered.user


def test_interview_coach_omitted_role_context_renders_empty_block() -> None:
    rendered = load_prompt("interview_coach", role_context="")
    # Empty substitution must not leave a stray "{{role_context}}" literal.
    assert "{{" not in rendered.system
    assert "}}" not in rendered.system


def test_interview_coach_has_few_shot_examples() -> None:
    # Few-shot examples anchor the coach's tone and CRITIQUE-AND-FOLLOWUP
    # shape. The loader treats the section as optional, but the prompt
    # specifically ships them — guard them against accidental deletion.
    rendered = load_prompt("interview_coach", role_context="x")
    assert len(rendered.examples) >= 2
    assert any("MongoDB" in ex.input_text for ex in rendered.examples)


def test_interview_coach_system_prompt_bans_emojis_and_json() -> None:
    rendered = load_prompt("interview_coach", role_context="x")
    # Style discipline enforced in CLAUDE.md + Phase 7: no emojis in core UI,
    # no JSON output from the coach (the chat is plain prose).
    system = rendered.system
    assert "emoji" in system.lower()
    assert "no json" in system.lower() or "plain prose" in system.lower()
