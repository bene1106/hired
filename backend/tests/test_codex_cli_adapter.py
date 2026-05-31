"""Unit tests for ``llm.codex_cli.CodexCLIAdapter``.

We never invoke the real ``codex`` CLI — every test stubs ``subprocess.run``
(and ``shutil.which`` for the construction path), and the streaming tests stub
``subprocess.Popen``, so the suite stays deterministic and offline.

The fixtures emit Codex's ``exec --json`` JSONL event shape (captured from
``codex-cli 0.120.0``): ``thread.started`` / ``turn.started`` /
``item.completed`` (agent_message) / ``turn.completed`` (usage), plus the
``error`` / ``turn.failed`` events Codex emits on failure *while still exiting
0* — which is exactly why the adapter drives errors off the event stream.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from llm.codex_cli import CodexCLIAdapter
from llm.errors import LLMError, LLMNetworkError, LLMResponseError
from llm.types import ChatMessage, CompanyBrief, Job, Profile
from llm.usage import consume_usage


def _jsonl(*events: dict[str, Any]) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


def _agent_message(text: str) -> dict[str, Any]:
    return {
        "type": "item.completed",
        "item": {"id": "item_0", "type": "agent_message", "text": text},
    }


def _turn_completed(input_tokens: int = 100, output_tokens: int = 10) -> dict[str, Any]:
    return {
        "type": "turn.completed",
        "usage": {
            "input_tokens": input_tokens,
            "cached_input_tokens": 0,
            "output_tokens": output_tokens,
        },
    }


def _completed(
    *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["codex"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _adapter(monkeypatch: pytest.MonkeyPatch, run_impl, **kwargs: Any) -> CodexCLIAdapter:
    """Build an adapter with ``shutil.which`` and ``subprocess.run`` stubbed."""
    monkeypatch.setattr("llm.codex_cli.shutil.which", lambda _name: "/fake/codex")
    monkeypatch.setattr("llm.codex_cli.subprocess.run", run_impl)
    return CodexCLIAdapter(**kwargs)


def _success_run(text: str, *, input_tokens: int = 100, output_tokens: int = 10):
    """Return a fake ``subprocess.run`` that captures argv + emits a JSONL turn."""
    captured: dict[str, Any] = {}
    stdout = _jsonl(
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "turn.started"},
        _agent_message(text),
        _turn_completed(input_tokens, output_tokens),
    )

    def runner(argv, **kwargs):
        captured["argv"] = argv
        captured["input"] = kwargs.get("input")
        captured["timeout"] = kwargs.get("timeout")
        return _completed(stdout=stdout)

    runner.captured = captured  # type: ignore[attr-defined]
    return runner


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_init_raises_when_cli_not_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm.codex_cli.shutil.which", lambda _name: None)
    with pytest.raises(LLMError, match="Codex CLI not found"):
        CodexCLIAdapter()


def test_init_uses_explicit_cli_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm.codex_cli.shutil.which",
        lambda _n: pytest.fail("shutil.which was called"),  # type: ignore[arg-type]
    )
    adapter = CodexCLIAdapter(cli_path="/explicit/codex")
    assert adapter.cli_path == "/explicit/codex"


# ---------------------------------------------------------------------------
# Round trips + argv
# ---------------------------------------------------------------------------


def test_score_job_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    consume_usage()  # clear leftover from previous tests
    payload = json.dumps(
        {
            "score": 81,
            "rationale": "Good fit.",
            "matched_skills": ["Python"],
            "missing_skills": [],
            "red_flags": [],
        }
    )
    runner = _success_run(payload, input_tokens=410, output_tokens=92)
    adapter = _adapter(monkeypatch, runner)
    result = adapter.score_job(Profile(), Job(title="Backend Engineer"))
    assert result.score == 81
    # Usage from the turn.completed event should have flowed into the contextvar.
    usage = consume_usage()
    assert usage is not None
    assert usage.input_tokens == 410
    assert usage.output_tokens == 92


def test_call_uses_exec_json_flags_and_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run('{"name": "Alex", "skills": []}')
    adapter = _adapter(monkeypatch, runner)
    adapter.parse_cv("CV body here.")

    captured = runner.captured  # type: ignore[attr-defined]
    argv = captured["argv"]
    assert argv[0] == "/fake/codex"
    assert argv[1] == "exec"
    assert "--json" in argv
    assert "--skip-git-repo-check" in argv
    # Read-only sandbox keeps the agent from writing to the user's tree.
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    # The prompt is piped via stdin (trailing "-"), never inlined into argv.
    assert argv[-1] == "-"
    assert isinstance(captured["input"], str)
    assert "CV body here." in captured["input"]
    # The system prompt is folded into stdin (Codex has no --system flag).
    assert captured["input"].index("CV body here.") > 0
    assert captured["timeout"] == pytest.approx(180.0)


def test_no_model_flag_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run('{"name": "Alex", "skills": []}')
    adapter = _adapter(monkeypatch, runner)
    adapter.parse_cv("text")
    argv = runner.captured["argv"]  # type: ignore[attr-defined]
    assert "--model" not in argv
    assert "-m" not in argv


def test_explicit_model_is_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run('{"name": "Alex", "skills": []}')
    adapter = _adapter(monkeypatch, runner, model="gpt-5-codex")
    adapter.parse_cv("text")
    argv = runner.captured["argv"]  # type: ignore[attr-defined]
    assert argv[argv.index("--model") + 1] == "gpt-5-codex"


def test_few_shot_examples_are_flattened_into_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run('{"name": "Alex", "skills": []}')
    adapter = _adapter(monkeypatch, runner)
    adapter.parse_cv("CV body here.")
    stdin = runner.captured["input"]  # type: ignore[attr-defined]
    assert "Example output:" in stdin
    assert "CV body here." in stdin


def test_summarize_role_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run("  Para 1.\n\nPara 2.\n  ")
    adapter = _adapter(monkeypatch, runner)
    result = adapter.summarize_role(Job(title="Backend Engineer"))
    assert result == "Para 1.\n\nPara 2."


def test_research_company_extracts_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    markdown = (
        "## What they do\nstuff\n## Sources\n- https://acme.example/a\n- https://news.example/b\n"
    )
    runner = _success_run(markdown)
    adapter = _adapter(monkeypatch, runner)
    brief = adapter.research_company("Acme")
    assert isinstance(brief, CompanyBrief)
    assert brief.sources == ["https://acme.example/a", "https://news.example/b"]


def test_research_company_enables_web_search(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run("## What they do\nstuff\n")
    adapter = _adapter(monkeypatch, runner)
    adapter.research_company("Acme")
    argv = runner.captured["argv"]  # type: ignore[attr-defined]
    # `-c tools.web_search=true` is passed for the research call.
    assert "tools.web_search=true" in argv
    idx = argv.index("tools.web_search=true")
    assert argv[idx - 1] == "-c"


def test_other_calls_do_not_enable_web_search(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run('{"name": "Alex", "skills": []}')
    adapter = _adapter(monkeypatch, runner)
    adapter.parse_cv("CV body here.")
    argv = runner.captured["argv"]  # type: ignore[attr-defined]
    assert "tools.web_search=true" not in argv
    assert "-c" not in argv


def test_generate_interview_questions_requires_list(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _success_run(json.dumps({"questions": "oops"}))
    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="expected 'questions' list"):
        adapter.generate_interview_questions(Job(title="Backend Engineer"))


def test_parses_fenced_json(monkeypatch: pytest.MonkeyPatch) -> None:
    fenced = '```json\n{"name": "Alex", "skills": ["Go"]}\n```'
    runner = _success_run(fenced)
    adapter = _adapter(monkeypatch, runner)
    result = adapter.parse_cv("text")
    assert result == {"name": "Alex", "skills": ["Go"]}


# ---------------------------------------------------------------------------
# Failure mapping
# ---------------------------------------------------------------------------


def test_subprocess_timeout_translates_to_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=180)

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


def test_error_event_translates_to_response_error_even_on_exit_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex exits 0 on a model error; the failure is only in the event stream."""
    nested = json.dumps(
        {
            "type": "error",
            "status": 400,
            "error": {
                "type": "invalid_request_error",
                "message": "The 'x' model is not supported.",
            },
        }
    )
    stdout = _jsonl(
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "turn.started"},
        {"type": "error", "message": nested},
        {"type": "turn.failed", "error": {"message": nested}},
    )

    def runner(argv, **kwargs):
        return _completed(stdout=stdout, returncode=0)

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="model is not supported"):
        adapter.parse_cv("text")


def test_no_agent_message_translates_to_response_error(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = _jsonl({"type": "thread.started", "thread_id": "t1"}, {"type": "turn.started"})

    def runner(argv, **kwargs):
        return _completed(stdout=stdout)

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="no agent message"):
        adapter.parse_cv("text")


def test_nonzero_exit_without_text_translates_to_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def runner(argv, **kwargs):
        return _completed(stdout="", stderr="boom", returncode=2)

    adapter = _adapter(monkeypatch, runner)
    with pytest.raises(LLMResponseError, match="exited 2"):
        adapter.parse_cv("text")


def test_non_json_lines_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stray log noise on stdout shouldn't break parsing as long as the
    # agent_message event is present.
    stdout = "starting up...\n" + _jsonl(_agent_message('{"name": "Alex", "skills": []}'))

    def runner(argv, **kwargs):
        return _completed(stdout=stdout)

    adapter = _adapter(monkeypatch, runner)
    assert adapter.parse_cv("text") == {"name": "Alex", "skills": []}


# ---------------------------------------------------------------------------
# Streaming — interview_chat_stream
# ---------------------------------------------------------------------------


class _FakePopen:
    """Minimal ``subprocess.Popen`` stand-in for streaming tests."""

    def __init__(
        self, *, stdout_lines: list[str], stderr_text: str = "", returncode: int = 0
    ) -> None:
        import io

        self.stdin = io.StringIO()
        self.stdout = iter(stdout_lines)
        self.stderr = io.StringIO(stderr_text)
        self._returncode = returncode

    def wait(self, timeout: float | None = None) -> int:  # noqa: ARG002
        return self._returncode


def _popen_factory(captured: dict[str, Any], proc: _FakePopen):
    def factory(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return proc

    return factory


def _adapter_with_popen(monkeypatch: pytest.MonkeyPatch, factory) -> CodexCLIAdapter:
    monkeypatch.setattr("llm.codex_cli.shutil.which", lambda _name: "/fake/codex")
    monkeypatch.setattr("llm.codex_cli.subprocess.Popen", factory)
    return CodexCLIAdapter()


def test_interview_chat_stream_yields_agent_message(monkeypatch: pytest.MonkeyPatch) -> None:
    consume_usage()
    stdout_lines = [
        json.dumps({"type": "thread.started", "thread_id": "t1"}) + "\n",
        json.dumps({"type": "turn.started"}) + "\n",
        json.dumps(_agent_message("Strong opening — quantify the impact.")) + "\n",
        json.dumps(_turn_completed(350, 22)) + "\n",
    ]
    captured: dict[str, Any] = {}
    factory = _popen_factory(captured, _FakePopen(stdout_lines=stdout_lines))
    adapter = _adapter_with_popen(monkeypatch, factory)

    chunks = list(
        adapter.interview_chat_stream(
            [ChatMessage(role="user", content="Tell me about your last project.")],
            role_context="Backend role.",
        )
    )
    assert chunks == ["Strong opening — quantify the impact."]

    argv = captured["argv"]
    assert argv[0] == "/fake/codex"
    assert argv[1] == "exec"
    assert "--json" in argv

    usage = consume_usage()
    assert usage is not None
    assert usage.input_tokens == 350
    assert usage.output_tokens == 22


def test_interview_chat_stream_error_event_translates_to_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout_lines = [
        json.dumps({"type": "turn.started"}) + "\n",
        json.dumps({"type": "error", "message": "subscription expired"}) + "\n",
    ]
    factory = _popen_factory({}, _FakePopen(stdout_lines=stdout_lines))
    adapter = _adapter_with_popen(monkeypatch, factory)
    with pytest.raises(LLMResponseError, match="subscription expired"):
        list(adapter.interview_chat_stream([ChatMessage(role="user", content="hi")]))


def test_interview_chat_stream_non_zero_exit_translates_to_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _popen_factory({}, _FakePopen(stdout_lines=[], stderr_text="boom", returncode=2))
    adapter = _adapter_with_popen(monkeypatch, factory)
    with pytest.raises(LLMResponseError, match="exited 2"):
        list(adapter.interview_chat_stream([ChatMessage(role="user", content="hi")]))
