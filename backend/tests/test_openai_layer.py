"""OpenAIAPIAdapter tests — exercised via a stubbed client so no network is hit."""

from __future__ import annotations

from typing import Any

import pytest

from llm.errors import LLMAuthError, LLMResponseError
from llm.openai_api import DEFAULT_MODEL, OpenAIAPIAdapter
from llm.types import Job, MockInterviewContext, MockInterviewPlan, Profile, ScoreResult

# ---------------------------------------------------------------------------
# Fake OpenAI client (mirrors the `chat.completions.create` shape)
# ---------------------------------------------------------------------------


class _Usage:
    def __init__(self, prompt: int, completion: int) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class _Message:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str | None) -> None:
        self.message = _Message(content)


class _Response:
    def __init__(self, text: str | None, usage: _Usage | None) -> None:
        self.choices = [_Choice(text)] if text is not None else []
        self.usage = usage


class _Delta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _StreamChoice:
    def __init__(self, content: str | None) -> None:
        self.delta = _Delta(content)


class _Chunk:
    def __init__(self, content: str | None = None, usage: _Usage | None = None) -> None:
        self.choices = [_StreamChoice(content)] if content is not None else []
        self.usage = usage


class _Completions:
    def __init__(
        self,
        *,
        text: str | None = None,
        usage: _Usage | None = None,
        chunks: list[_Chunk] | None = None,
        raise_with: Exception | None = None,
    ) -> None:
        self._text = text
        self._usage = usage
        self._chunks = chunks
        self._raise = raise_with
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        if self._raise is not None:
            raise self._raise
        if kwargs.get("stream"):
            return iter(self._chunks or [])
        return _Response(self._text, self._usage)


class _FakeOpenAI:
    def __init__(self, completions: _Completions) -> None:
        self.chat = type("_Chat", (), {"completions": completions})()


def _adapter(**kwargs: Any) -> OpenAIAPIAdapter:
    return OpenAIAPIAdapter(client=_FakeOpenAI(_Completions(**kwargs)))  # type: ignore[arg-type]


@pytest.fixture
def profile() -> Profile:
    return Profile(name="Alex", target_role="Backend Engineer", skills=["Python"])


@pytest.fixture
def job() -> Job:
    return Job(title="Backend Engineer", company="Acme", description="Build APIs.")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_init_raises_auth_error_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("llm.openai_api.get_credential", lambda _name: None)
    with pytest.raises(LLMAuthError):
        OpenAIAPIAdapter()


def test_init_uses_explicit_key_and_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm.openai_api.get_credential", lambda _name: None)
    adapter = OpenAIAPIAdapter(api_key="sk-test")
    assert adapter.model == DEFAULT_MODEL == "gpt-4o"


def test_score_job_round_trip(profile: Profile, job: Job) -> None:
    payload = (
        '{"score": 82, "rationale": "Strong match.", '
        '"matched_skills": ["Python"], "missing_skills": [], "red_flags": []}'
    )
    adapter = _adapter(text=payload, usage=_Usage(10, 5))
    result = adapter.score_job(profile, job)
    assert isinstance(result, ScoreResult)
    assert result.score == 82


def test_parse_cv_round_trip() -> None:
    adapter = _adapter(text='{"name": "Alex", "skills": ["Python"]}')
    result = adapter.parse_cv("Alex — Python dev")
    assert result["name"] == "Alex"


def test_invalid_json_raises_response_error(profile: Profile, job: Job) -> None:
    adapter = _adapter(text="not json at all")
    with pytest.raises(LLMResponseError):
        adapter.score_job(profile, job)


def test_no_choices_raises_response_error() -> None:
    adapter = _adapter(text=None)  # → empty choices
    with pytest.raises(LLMResponseError):
        adapter.parse_cv("x")


def test_generate_mock_interview_questions(profile: Profile, job: Job) -> None:
    payload = (
        '{"questions": [{"category": "behavioral", "question": "Tell me about yourself.", '
        '"rephrasing": "Walk me through your background.", "time_limit_seconds": 300, '
        '"is_intro": true}]}'
    )
    adapter = _adapter(text=payload)
    ctx = MockInterviewContext(
        round_number=1, interview_type="technical", duration_minutes=30, num_questions=1
    )
    plan = adapter.generate_mock_interview_questions(job, profile, ctx)
    assert isinstance(plan, MockInterviewPlan)
    assert plan.questions[0].is_intro is True


def test_interview_chat_stream_yields_chunks() -> None:
    chunks = [_Chunk("Hello "), _Chunk("there"), _Chunk(usage=_Usage(3, 2))]
    adapter = _adapter(chunks=chunks)
    out = list(adapter.interview_chat_stream([], role_context="Backend role"))
    assert out == ["Hello ", "there"]
