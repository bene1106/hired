"""Unit tests for ``llm.claude_code.ClaudeCodeAdapter``.

We never invoke the real ``claude`` CLI — every test stubs
``subprocess.run`` (and ``shutil.which`` for the construction path) so
the suite stays deterministic and offline.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from llm.claude_code import ClaudeCodeAdapter
from llm.errors import LLMError, LLMNetworkError, LLMResponseError
from llm.types import CompanyBrief, Job, Profile
from llm.usage import consume_usage


def _completed(
    *,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["claude"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _adapter(monkeypatch: pytest.MonkeyPatch, run_impl) -> ClaudeCodeAdapter:
    """Build an adapter with ``shutil.which`` and ``subprocess.run`` stubbed."""
    monkeypatch.setattr("llm.claude_code.shutil.which", lambda _name: "/fake/claude")
    monkeypatch.setattr("llm.claude_code.subprocess.run", run_impl)
    return ClaudeCodeAdapter()


def _success_run(payload: dict[str, Any]):
    """Return a fake ``subprocess.run`` that captures argv + emits ``payload``."""
    captured: dict[str, Any] = {}

    def runner(argv, **kwargs):
        captured["argv"] = argv
        captured["input"] = kwargs.get("input")
        captured["timeout"] = kwargs.get("timeout")
        return _completed(stdout=json.dumps(payload))

    runner.captured = captured  # type: ignore[attr-defined]
    return runner


def test_init_raises_when_cli_not_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm.claude_code.shutil.which", lambda _name: None)
    with pytest.raises(LLMError, match="Claude Code CLI not found"):
        ClaudeCodeAdapter()


def test_init_uses_explicit_cli_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # shutil.which should be skipped when an explicit path is provided.
    monkeypatch.setattr(
        "llm.claude_code.shutil.which",
        lambda _n: pytest.fail("shutil.which was called"),  # type: ignore[arg-type]
    )
    adapter = ClaudeCodeAdapter(cli_path="/explicit/claude")
    assert adapter.cli_path == "/explicit/claude"


def test_score_job_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    consume_usage()  # clear leftover from previous tests
    payload = {
        "result": json.dumps(
            {
                "score": 81,
                "rationale": "Good fit.",
                "matched_skills": ["Python"],
                "missing_skills": [],
                "red_flags": [],
            }
        ),
        "usage": {"input_tokens": 410, "output_tokens": 92},
    }
    runner = _success_run(payload)
    adapter = _adapter(monkeypatch, runner)
    result = adapter.score_job(Profile(), Job(title="Backend Engineer"))
    assert result.score == 81
    # Usage from the JSON payload should have flowed into the contextvar.
    usage = consume_usage()
    assert usage is not None
    assert usage.input_tokens == 410
    assert usage.output_tokens == 92


def test_call_uses_print_and_json_flags_and_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _success_run({"result": '{"name": "Alex", "skills": []}'})
    adapter = _adapter(monkeypatch, runner)
    adapter.parse_cv("CV body here.")

    captured = runner.captured  # type: ignore[attr-defined]
    argv = captured["argv"]
    assert argv[0] == "/fake/claude"
    assert "-p" in argv
    assert argv[argv.index("--output-format") + 1] == "json"
    # The system prompt is passed via --append-system-prompt.
    sys_idx = argv.index("--append-system-prompt")
    assert isinstance(argv[sys_idx + 1], str)
    assert argv[sys_idx + 1]  # non-empty
    # User prompt is piped via stdin, never inlined into argv.
    assert isinstance(captured["input"], str)
    assert "CV body here." in captured["input"]
    assert captured["timeout"] == pytest.approx(120.0)


def test_subprocess_timeout_translates_to_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=120)

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMNetworkError, match="timed out"):
        adapter.parse_cv("text")


def test_oserror_when_launching_translates_to_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def runner(argv, **kwargs):
        raise OSError("ENOENT")

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMNetworkError, match="Failed to launch"):
        adapter.parse_cv("text")


def test_non_zero_exit_translates_to_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def runner(argv, **kwargs):
        return _completed(returncode=2, stderr="boom")

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="exited 2"):
        adapter.parse_cv("text")


def test_is_error_payload_translates_to_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def runner(argv, **kwargs):
        return _completed(
            stdout=json.dumps({"is_error": True, "result": "subscription expired"}),
        )

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="reported is_error"):
        adapter.parse_cv("text")


def test_invalid_json_stdout_translates_to_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def runner(argv, **kwargs):
        return _completed(stdout="this is not json at all")

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="not JSON"):
        adapter.parse_cv("text")


def test_summarize_role_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run({"result": "  Para 1.\n\nPara 2.\n  "})
    adapter = _adapter(monkeypatch, runner)
    result = adapter.summarize_role(Job(title="Backend Engineer"))
    assert result == "Para 1.\n\nPara 2."


def test_research_company_extracts_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    markdown = (
        "## What they do\nstuff\n## Sources\n- https://acme.example/a\n- https://news.example/b\n"
    )
    runner = _success_run({"result": markdown})
    adapter = _adapter(monkeypatch, runner)
    brief = adapter.research_company("Acme")
    assert isinstance(brief, CompanyBrief)
    assert brief.sources == [
        "https://acme.example/a",
        "https://news.example/b",
    ]


def test_generate_interview_questions_requires_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _success_run({"result": json.dumps({"questions": "oops"})})
    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="expected 'questions' list"):
        adapter.generate_interview_questions(Job(title="Backend Engineer"))


def test_few_shot_examples_are_flattened_into_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _success_run({"result": json.dumps({"name": "Alex", "skills": []})})
    adapter = _adapter(monkeypatch, runner)
    adapter.parse_cv("CV body here.")

    stdin = runner.captured["input"]  # type: ignore[attr-defined]
    # parse_cv has at least one few-shot example baked into the prompt
    # template; the adapter inlines those into the single user turn.
    assert "Example output:" in stdin
    assert "CV body here." in stdin
