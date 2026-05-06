"""Tests for the Phase 2 LLM provider layer.

Always-run tests cover MockProvider, the provider factory, Pydantic
validation of typed outputs, and the credentials helper (with keyring
monkeypatched). Integration tests behind ``@pytest.mark.integration``
exercise the real Anthropic API and are skipped by default.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import update

from db.migrations import run_migrations
from db.models import AppConfig
from db.session import get_session
from llm import (
    LLMError,
    MockProvider,
    get_provider,
    reset_provider_cache,
)
from llm.anthropic_api import (
    ANTHROPIC_API_KEY_NAME,
    AnthropicAPIAdapter,
    _extract_markdown_sources,
    _extract_text,
    _parse_json_object,
    _parse_pydantic,
)
from llm.credentials import (
    SERVICE_NAME,
    delete_credential,
    get_credential,
    set_credential,
)
from llm.errors import LLMResponseError
from llm.types import (
    AnswerFeedback,
    CompanyBrief,
    CoverLetter,
    ImprovementNote,
    InterviewQuestion,
    Job,
    Profile,
    ScoreResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_provider_between_tests() -> None:
    reset_provider_cache()


@pytest.fixture
def sample_profile() -> Profile:
    return Profile(
        name="Alex K.",
        target_role="Backend Developer",
        target_locations=["Berlin", "Remote EU"],
        target_salary_min=55000,
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
    )


@pytest.fixture
def sample_job() -> Job:
    return Job(
        title="Junior Backend Engineer",
        company="HealthTech GmbH",
        location="Berlin (hybrid)",
        remote_policy="hybrid",
        salary_range="55000-65000 EUR",
        description="Junior backend role; Python, FastAPI, PostgreSQL.",
    )


# ---------------------------------------------------------------------------
# MockProvider — deterministic stubs for every method
# ---------------------------------------------------------------------------


class TestMockProvider:
    def test_parse_cv_returns_dict(self) -> None:
        provider = MockProvider()
        result = provider.parse_cv("any cv text")
        assert isinstance(result, dict)
        assert "skills" in result and isinstance(result["skills"], list)

    def test_score_job_returns_valid_score_result(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        provider = MockProvider()
        result = provider.score_job(sample_profile, sample_job)
        assert isinstance(result, ScoreResult)
        assert 0 <= result.score <= 100
        assert isinstance(result.rationale, str) and result.rationale

    def test_research_company_returns_company_brief(self) -> None:
        provider = MockProvider()
        brief = provider.research_company("Acme Corp")
        assert isinstance(brief, CompanyBrief)
        assert brief.company == "Acme Corp"
        assert brief.markdown.startswith("# Acme Corp")

    def test_tailor_cv_returns_markdown_string(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        provider = MockProvider()
        result = provider.tailor_cv(sample_profile, sample_job)
        assert isinstance(result, str)
        assert "Emphasize" in result

    def test_generate_cover_letter_returns_cover_letter(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        provider = MockProvider()
        brief = provider.research_company("HealthTech GmbH")
        letter = provider.generate_cover_letter(sample_profile, sample_job, brief)
        assert isinstance(letter, CoverLetter)
        assert letter.body
        assert letter.word_count and letter.word_count > 0

    def test_generate_interview_questions_returns_typed_list(
        self, sample_job: Job
    ) -> None:
        provider = MockProvider()
        questions = provider.generate_interview_questions(sample_job)
        assert isinstance(questions, list)
        assert len(questions) >= 1
        for q in questions:
            assert isinstance(q, InterviewQuestion)
            assert q.category in {
                "technical",
                "behavioral",
                "role_specific",
                "company_fit",
            }

    def test_evaluate_answer_returns_feedback(self) -> None:
        provider = MockProvider()
        feedback = provider.evaluate_answer(
            question="Tell me about yourself.",
            answer="I'm a backend engineer who likes building things.",
        )
        assert isinstance(feedback, AnswerFeedback)
        assert feedback.what_to_improve  # min_length=1 enforced by the model

    def test_set_response_overrides_method(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        provider = MockProvider()
        custom = ScoreResult(score=42, rationale="Test override.")
        provider.set_response("score_job", custom)
        assert provider.score_job(sample_profile, sample_job) is custom

    def test_set_response_can_be_cleared(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        provider = MockProvider()
        provider.set_response("score_job", ScoreResult(score=1, rationale="x"))
        provider.set_response("score_job", None)
        result = provider.score_job(sample_profile, sample_job)
        assert result.score == 75  # back to the default stub

    def test_set_response_rejects_unknown_method(self) -> None:
        provider = MockProvider()
        with pytest.raises(ValueError, match="Unknown method"):
            provider.set_response("not_a_method", "x")


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


class TestProviderFactory:
    def test_factory_returns_mock_provider_by_default(self) -> None:
        run_migrations()
        provider = get_provider()
        assert isinstance(provider, MockProvider)

    def test_factory_caches_provider(self) -> None:
        run_migrations()
        first = get_provider()
        second = get_provider()
        assert first is second

    def test_reset_provider_cache_clears_cache(self) -> None:
        run_migrations()
        first = get_provider()
        reset_provider_cache()
        second = get_provider()
        assert first is not second

    def test_factory_raises_for_unknown_provider(self) -> None:
        run_migrations()
        with get_session() as session:
            session.execute(
                update(AppConfig)
                .where(AppConfig.key == "provider")
                .values(value="not_a_real_provider")
            )
            session.commit()
        with pytest.raises(LLMError, match="Unknown provider"):
            get_provider()

    def test_factory_builds_anthropic_adapter_when_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_migrations()
        with get_session() as session:
            session.execute(
                update(AppConfig)
                .where(AppConfig.key == "provider")
                .values(value="anthropic_api")
            )
            session.commit()

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        # Don't read from the user's keychain during tests.
        monkeypatch.setattr(
            "llm.anthropic_api.get_credential", lambda _name: None
        )

        provider = get_provider()
        assert isinstance(provider, AnthropicAPIAdapter)
        assert provider.model == "claude-opus-4-7"


# ---------------------------------------------------------------------------
# Typed-output Pydantic validation
# ---------------------------------------------------------------------------


class TestPydanticValidation:
    def test_score_result_rejects_out_of_range_score(self) -> None:
        with pytest.raises(ValidationError):
            ScoreResult(score=150, rationale="too high")
        with pytest.raises(ValidationError):
            ScoreResult(score=-1, rationale="too low")

    def test_answer_feedback_requires_at_least_one_improvement(self) -> None:
        with pytest.raises(ValidationError):
            AnswerFeedback(
                what_worked=["nice tone"],
                what_to_improve=[],
                sample_stronger_answer="…",
            )

    def test_interview_question_rejects_unknown_category(self) -> None:
        with pytest.raises(ValidationError):
            InterviewQuestion(category="not_a_category", question="q")  # type: ignore[arg-type]

    def test_profile_ignores_extra_fields(self) -> None:
        # extra="ignore" — surplus keys (e.g., from a richer DB row) shouldn't break us.
        profile = Profile.model_validate(
            {"name": "Alex", "stray_field_from_db": "ignored"}
        )
        assert profile.name == "Alex"


# ---------------------------------------------------------------------------
# Credentials helper (with monkeypatched keyring backend)
# ---------------------------------------------------------------------------


class TestCredentials:
    def test_round_trip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store: dict[tuple[str, str], str] = {}

        def fake_set(service: str, name: str, value: str) -> None:
            store[(service, name)] = value

        def fake_get(service: str, name: str) -> str | None:
            return store.get((service, name))

        def fake_delete(service: str, name: str) -> None:
            store.pop((service, name), None)

        monkeypatch.setattr("llm.credentials.keyring.set_password", fake_set)
        monkeypatch.setattr("llm.credentials.keyring.get_password", fake_get)
        monkeypatch.setattr("llm.credentials.keyring.delete_password", fake_delete)

        assert get_credential("test_key") is None
        set_credential("test_key", "secret-value")
        assert get_credential("test_key") == "secret-value"
        assert (SERVICE_NAME, "test_key") in store
        delete_credential("test_key")
        assert get_credential("test_key") is None

    def test_get_returns_none_on_keyring_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from keyring.errors import KeyringError

        def fake_get(service: str, name: str) -> str | None:
            raise KeyringError("backend missing")

        monkeypatch.setattr("llm.credentials.keyring.get_password", fake_get)
        assert get_credential("missing_backend") is None

    def test_delete_swallows_password_delete_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from keyring.errors import PasswordDeleteError

        def fake_delete(service: str, name: str) -> None:
            raise PasswordDeleteError("not found")

        monkeypatch.setattr("llm.credentials.keyring.delete_password", fake_delete)
        delete_credential("nope")  # should NOT raise


# ---------------------------------------------------------------------------
# AnthropicAPIAdapter — exercised via a stubbed client so we don't hit the API
# ---------------------------------------------------------------------------


class _FakeContentBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeContentBlock(text)]


class _FakeMessages:
    def __init__(
        self,
        *,
        response_text: str | None = None,
        raise_with: Exception | None = None,
    ) -> None:
        self._response_text = response_text
        self._raise_with = raise_with
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> _FakeResponse:
        self.last_kwargs = kwargs
        if self._raise_with is not None:
            raise self._raise_with
        assert self._response_text is not None
        return _FakeResponse(self._response_text)


class _FakeAnthropic:
    def __init__(
        self, *, response_text: str | None = None, raise_with: Exception | None = None
    ) -> None:
        self.messages = _FakeMessages(response_text=response_text, raise_with=raise_with)


def _make_adapter(
    *, response_text: str | None = None, raise_with: Exception | None = None
) -> AnthropicAPIAdapter:
    fake = _FakeAnthropic(response_text=response_text, raise_with=raise_with)
    return AnthropicAPIAdapter(client=fake)  # type: ignore[arg-type]


class TestAnthropicAPIAdapter:
    def test_init_raises_auth_error_when_no_key_anywhere(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr("llm.anthropic_api.get_credential", lambda _name: None)
        from llm.errors import LLMAuthError

        with pytest.raises(LLMAuthError):
            AnthropicAPIAdapter()

    def test_init_uses_explicit_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Hard-pin the keychain lookup to None so this test doesn't depend on
        # whatever the developer happens to have stored locally.
        monkeypatch.setattr("llm.anthropic_api.get_credential", lambda _name: None)
        adapter = AnthropicAPIAdapter(api_key="sk-ant-explicit")
        assert adapter.model == "claude-opus-4-7"

    def test_score_job_round_trip(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        payload = (
            '{"score": 82, "rationale": "Strong match.", '
            '"matched_skills": ["Python"], "missing_skills": [], "red_flags": []}'
        )
        adapter = _make_adapter(response_text=payload)
        result = adapter.score_job(sample_profile, sample_job)
        assert isinstance(result, ScoreResult)
        assert result.score == 82

    def test_research_company_returns_brief_with_sources(self) -> None:
        markdown = (
            "# Acme\n## What they do\nThings.\n## Sources\n"
            "- https://acme.example/about\n- https://news.example/acme-funding\n"
        )
        adapter = _make_adapter(response_text=markdown)
        brief = adapter.research_company("Acme")
        assert brief.company == "Acme"
        assert len(brief.sources) == 2

    def test_generate_interview_questions_round_trip(self, sample_job: Job) -> None:
        payload = (
            '{"questions": ['
            '{"category": "technical", "question": "Idempotency?", '
            '"what_theyre_assessing": null, "difficulty": "standard"}'
            ']}'
        )
        adapter = _make_adapter(response_text=payload)
        questions = adapter.generate_interview_questions(sample_job)
        assert len(questions) == 1
        assert questions[0].category == "technical"

    def test_generate_interview_questions_rejects_non_list(
        self, sample_job: Job
    ) -> None:
        adapter = _make_adapter(response_text='{"questions": "oops"}')
        with pytest.raises(LLMResponseError, match="expected 'questions' list"):
            adapter.generate_interview_questions(sample_job)

    def test_generate_cover_letter_wraps_text(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        adapter = _make_adapter(response_text="Dear team,\n\nI am applying.\n")
        brief = CompanyBrief(company="Acme", markdown="# Acme")
        letter = adapter.generate_cover_letter(sample_profile, sample_job, brief)
        assert letter.body.startswith("Dear team")
        # "Dear" "team," "I" "am" "applying." → 5 words
        assert letter.word_count == 5

    def test_evaluate_answer_round_trip(self) -> None:
        payload = (
            '{"what_worked": ["Concrete"], '
            '"what_to_improve": [{"issue": "no metric", "fix": "add one"}], '
            '"sample_stronger_answer": "X.", "off_topic": false}'
        )
        adapter = _make_adapter(response_text=payload)
        feedback = adapter.evaluate_answer("Q?", "A.")
        assert isinstance(feedback, AnswerFeedback)
        assert feedback.what_to_improve[0].issue == "no metric"

    def test_tailor_cv_returns_text(self, sample_profile: Profile, sample_job: Job) -> None:
        adapter = _make_adapter(response_text="**Emphasize** Python.\n")
        result = adapter.tailor_cv(sample_profile, sample_job)
        assert "Emphasize" in result

    def test_parse_cv_returns_dict(self) -> None:
        adapter = _make_adapter(response_text='{"name": "Alex", "skills": []}')
        result = adapter.parse_cv("...")
        assert result["name"] == "Alex"

    def test_translates_authentication_error(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        from anthropic import AuthenticationError

        from llm.errors import LLMAuthError

        # SDK error classes need a request object; build a minimal stand-in.
        err = AuthenticationError.__new__(AuthenticationError)
        adapter = _make_adapter(raise_with=err)
        with pytest.raises(LLMAuthError):
            adapter.score_job(sample_profile, sample_job)

    def test_translates_rate_limit_error(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        from anthropic import RateLimitError

        from llm.errors import LLMRateLimitError

        err = RateLimitError.__new__(RateLimitError)
        adapter = _make_adapter(raise_with=err)
        with pytest.raises(LLMRateLimitError):
            adapter.score_job(sample_profile, sample_job)

    def test_translates_connection_error(
        self, sample_profile: Profile, sample_job: Job
    ) -> None:
        from anthropic import APIConnectionError

        from llm.errors import LLMNetworkError

        err = APIConnectionError.__new__(APIConnectionError)
        adapter = _make_adapter(raise_with=err)
        with pytest.raises(LLMNetworkError):
            adapter.score_job(sample_profile, sample_job)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestParserHelpers:
    def test_parse_json_object_strips_fenced_block(self) -> None:
        text = '```json\n{"a": 1}\n```'
        assert _parse_json_object(text) == {"a": 1}

    def test_parse_json_object_strips_unlabeled_fence(self) -> None:
        text = '```\n{"a": 1}\n```'
        assert _parse_json_object(text) == {"a": 1}

    def test_parse_json_object_rejects_non_object(self) -> None:
        with pytest.raises(LLMResponseError, match="Expected JSON object"):
            _parse_json_object('["not", "an", "object"]')

    def test_parse_json_object_rejects_invalid_json(self) -> None:
        with pytest.raises(LLMResponseError, match="not valid JSON"):
            _parse_json_object("definitely not json")

    def test_parse_pydantic_validation_error(self) -> None:
        with pytest.raises(LLMResponseError, match="ScoreResult validation"):
            _parse_pydantic('{"score": "bad", "rationale": "x"}', ScoreResult)

    def test_extract_text_handles_multi_block(self) -> None:
        class FakeBlock:
            def __init__(self, text: str) -> None:
                self.text = text

        class FakeResponse:
            content = [FakeBlock("one "), FakeBlock("two")]

        assert _extract_text(FakeResponse()) == "one two"

    def test_extract_text_raises_when_empty(self) -> None:
        class FakeResponse:
            content: list[Any] = []

        with pytest.raises(LLMResponseError, match="no text content"):
            _extract_text(FakeResponse())

    def test_extract_markdown_sources_no_section(self) -> None:
        assert _extract_markdown_sources("# heading\nno sources here") == []

    def test_extract_markdown_sources_with_bullets(self) -> None:
        text = "## Sources\n- https://one\n- https://two\n## Next"
        assert _extract_markdown_sources(text) == ["https://one", "https://two"]


# ---------------------------------------------------------------------------
# Integration test — only runs with `pytest -m integration` and a real API key
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_anthropic_adapter_score_job_integration(
    sample_profile: Profile, sample_job: Job
) -> None:
    if not (
        os.getenv("ANTHROPIC_API_KEY")
        or get_credential(ANTHROPIC_API_KEY_NAME)
    ):
        pytest.skip("ANTHROPIC_API_KEY not set; skipping integration test")

    adapter = AnthropicAPIAdapter()
    result = adapter.score_job(sample_profile, sample_job)
    assert isinstance(result, ScoreResult)
    assert 0 <= result.score <= 100
    assert isinstance(result.rationale, str) and result.rationale


def test_imports_imported() -> None:
    """Sanity: ImprovementNote is exported from `llm`."""
    from llm import ImprovementNote as Exposed

    assert Exposed is ImprovementNote
