"""Unit tests for ``llm.ollama.OllamaAdapter``.

We never reach a real Ollama server — every test uses
``httpx.MockTransport`` so the suite stays deterministic and offline.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from llm.errors import LLMNetworkError, LLMResponseError
from llm.ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OllamaAdapter,
)
from llm.types import ChatMessage, CompanyBrief, Job, Profile
from llm.usage import consume_usage


def _make_adapter(handler: Callable[[httpx.Request], httpx.Response]) -> OllamaAdapter:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return OllamaAdapter(client=client)


def _ok(content: str, *, prompt_tokens: int = 100, eval_tokens: int = 30) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": DEFAULT_MODEL,
            "message": {"role": "assistant", "content": content},
            "done": True,
            "prompt_eval_count": prompt_tokens,
            "eval_count": eval_tokens,
        },
    )


def test_score_job_round_trip_records_usage() -> None:
    consume_usage()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return _ok(
            json.dumps(
                {
                    "score": 73,
                    "rationale": "Solid skill overlap.",
                    "matched_skills": ["Python"],
                    "missing_skills": [],
                    "red_flags": [],
                }
            ),
            prompt_tokens=512,
            eval_tokens=64,
        )

    adapter = _make_adapter(handler)
    result = adapter.score_job(Profile(), Job(title="Backend Engineer"))
    assert result.score == 73
    assert captured["url"] == f"{DEFAULT_BASE_URL}/api/chat"
    body = captured["body"]
    assert body["model"] == DEFAULT_MODEL  # type: ignore[index]
    assert body["stream"] is False  # type: ignore[index]
    assert body["messages"][0]["role"] == "system"  # type: ignore[index]
    assert body["messages"][-1]["role"] == "user"  # type: ignore[index]

    usage = consume_usage()
    assert usage is not None
    assert usage.input_tokens == 512
    assert usage.output_tokens == 64


def test_few_shot_examples_become_user_assistant_turns() -> None:
    captured_messages: list[list[dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured_messages.append(body["messages"])
        return _ok(json.dumps({"name": "Alex", "skills": []}))

    adapter = _make_adapter(handler)
    adapter.parse_cv("CV body")
    messages = captured_messages[0]
    roles = [m["role"] for m in messages]
    # System first, real user last; somewhere in between we expect at
    # least one user/assistant pair from the prompt's few-shot examples.
    assert roles[0] == "system"
    assert roles[-1] == "user"
    paired = list(zip(roles, roles[1:], strict=False))
    assert ("user", "assistant") in paired


def test_summarize_role_strips_whitespace() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok("  Para 1.\n\nPara 2.  \n")

    adapter = _make_adapter(handler)
    assert adapter.summarize_role(Job(title="Backend Engineer")) == "Para 1.\n\nPara 2."


def test_research_company_returns_brief_with_empty_sources() -> None:
    markdown = "## What they do\nfoo\n## Sources\n- ignored.example/x\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(markdown)

    adapter = _make_adapter(handler)
    brief = adapter.research_company("Acme")
    assert isinstance(brief, CompanyBrief)
    # Ollama has no web access, so we never claim sources even if the
    # model hallucinated some — better to render an empty list than
    # surface fabricated URLs.
    assert brief.sources == []


def test_404_with_model_not_found_translates_to_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"error": "model 'qwen2.5:14b' not found, try pulling it first"},
        )

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="not available locally"):
        adapter.parse_cv("text")


def test_500_translates_to_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal server error")

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="500"):
        adapter.parse_cv("text")


def test_connect_error_translates_to_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    adapter = _make_adapter(handler)
    with pytest.raises(LLMNetworkError, match="Could not reach Ollama"):
        adapter.parse_cv("text")


def test_timeout_translates_to_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    adapter = _make_adapter(handler)
    with pytest.raises(LLMNetworkError, match="timed out"):
        adapter.parse_cv("text")


def test_response_with_error_field_translates_to_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "context length exceeded"})

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="context length"):
        adapter.parse_cv("text")


def test_missing_message_content_translates_to_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"message": {"role": "assistant"}, "done": True},
        )

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="message.content"):
        adapter.parse_cv("text")


def test_generate_interview_questions_requires_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(json.dumps({"questions": "not a list"}))

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="expected 'questions' list"):
        adapter.generate_interview_questions(Job(title="Backend Engineer"))


def test_invalid_json_payload_translates_to_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"not valid json", headers={"content-type": "application/json"}
        )

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="not JSON"):
        adapter.parse_cv("text")


def test_score_job_strips_fenced_block() -> None:
    fenced = (
        "```json\n"
        '{"score": 60, "rationale": "ok", "matched_skills": [],'
        ' "missing_skills": [], "red_flags": []}\n'
        "```"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(fenced)

    adapter = _make_adapter(handler)
    result = adapter.score_job(Profile(), Job(title="Backend Engineer"))
    assert result.score == 60


# ---------------------------------------------------------------------------
# Streaming — interview_chat_stream
# ---------------------------------------------------------------------------


def _ndjson_stream(*lines: dict) -> bytes:
    return ("\n".join(json.dumps(line) for line in lines) + "\n").encode("utf-8")


def test_interview_chat_stream_yields_chunks_and_records_usage() -> None:
    consume_usage()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        body = _ndjson_stream(
            {"message": {"role": "assistant", "content": "Hello "}, "done": False},
            {"message": {"role": "assistant", "content": "there."}, "done": False},
            {
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "prompt_eval_count": 220,
                "eval_count": 18,
            },
        )
        return httpx.Response(200, content=body)

    adapter = _make_adapter(handler)
    history = [ChatMessage(role="user", content="Ready.")]
    chunks = list(adapter.interview_chat_stream(history, role_context="Backend role."))
    assert chunks == ["Hello ", "there."]

    body = captured["body"]
    assert body["stream"] is True  # type: ignore[index]
    # System prompt is first, candidate's history follows.
    assert body["messages"][0]["role"] == "system"  # type: ignore[index]
    assert "practice-interview coach" in body["messages"][0]["content"]  # type: ignore[index]
    assert body["messages"][-1] == {"role": "user", "content": "Ready."}  # type: ignore[index]

    usage = consume_usage()
    assert usage is not None
    assert usage.input_tokens == 220
    assert usage.output_tokens == 18


def test_interview_chat_stream_uses_kickoff_when_history_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        # On empty-history kickoff, the prompt's user template ("Begin the
        # practice interview…") becomes the first user turn after the system
        # prompt.
        assert body["messages"][-1]["role"] == "user"
        assert "Begin the practice interview" in body["messages"][-1]["content"]
        return httpx.Response(
            200,
            content=_ndjson_stream(
                {"message": {"content": "ok"}, "done": True, "eval_count": 1},
            ),
        )

    adapter = _make_adapter(handler)
    list(adapter.interview_chat_stream([], role_context="Some role."))


def test_interview_chat_stream_404_translates_to_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="not available locally"):
        list(adapter.interview_chat_stream([ChatMessage(role="user", content="hi")]))


def test_interview_chat_stream_error_line_translates_to_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_ndjson_stream({"error": "context length exceeded"}))

    adapter = _make_adapter(handler)
    with pytest.raises(LLMResponseError, match="context length"):
        list(adapter.interview_chat_stream([ChatMessage(role="user", content="hi")]))
