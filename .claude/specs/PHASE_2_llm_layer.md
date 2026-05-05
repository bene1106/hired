# Phase 2 — LLM Provider Layer

**Duration:** Week 2
**Owner suggestion:** AI Engineer
**Depends on:** Phase 1 complete

## Goal

Build the LLM abstraction that the rest of the app will use. By the end of this phase, the app can do real AI work via the Anthropic API, and tests run fast against a deterministic mock.

**Critically: this phase determines the quality of every later phase.** Get it right.

## Acceptance Criteria

A reviewer can:

```python
from backend.llm import get_provider
from backend.llm.types import Profile, Job

provider = get_provider()  # reads config, returns configured adapter
result = provider.score_job(profile, job)
assert 0 <= result.score <= 100
assert isinstance(result.rationale, str)
```

…and this works for both `provider=mock` (default in tests) and `provider=anthropic_api` (with a real key).

## Tasks

### 2.1 Define the Provider Interface

In `backend/llm/base.py`, define:

```python
from typing import Protocol, runtime_checkable
from .types import Profile, Job, ScoreResult, CoverLetter, CompanyBrief, InterviewQuestion, AnswerFeedback

@runtime_checkable
class LLMProvider(Protocol):
    def parse_cv(self, cv_text: str) -> dict: ...
    def score_job(self, profile: Profile, job: Job) -> ScoreResult: ...
    def research_company(self, company: str) -> CompanyBrief: ...
    def tailor_cv(self, profile: Profile, job: Job) -> str: ...
    def generate_cover_letter(self, profile: Profile, job: Job, brief: CompanyBrief) -> CoverLetter: ...
    def generate_interview_questions(self, job: Job) -> list[InterviewQuestion]: ...
    def evaluate_answer(self, question: str, answer: str) -> AnswerFeedback: ...
```

In `backend/llm/types.py`, define typed Pydantic models for each input/output (Profile, Job, ScoreResult, etc.). All outputs are Pydantic models so consumers get validated structured data.

### 2.2 Implement MockProvider

In `backend/llm/mock.py`:

- Returns deterministic stub data for every method
- Stubs are realistic enough to drive UI tests (e.g., `score_job` returns score=75, rationale="Strong match on Python and React")
- Has a `set_response(method, value)` helper for tests that need specific responses
- **Zero network calls, zero token usage**

This is what every later phase tests against. Make it pleasant to use.

### 2.3 Implement AnthropicAPIAdapter

In `backend/llm/anthropic_api.py`:

- Uses the official `anthropic` Python SDK (latest version)
- Reads API key from OS keychain via `backend.llm.credentials` (next task)
- Default model: `claude-opus-4-7` for generation, smaller model for classification tasks
- Implements all `LLMProvider` methods
- Handles errors: rate limits, auth errors, network errors → raises typed exceptions from `backend.llm.errors`
- Uses structured outputs via JSON Schema where applicable (scoring, interview questions)

For each method:
- Loads the prompt template from `backend/prompts/<method>.md`
- Substitutes inputs into the template
- Calls API with appropriate `max_tokens` for the task
- Parses the response into the typed Pydantic model

### 2.4 Credentials Helper

In `backend/llm/credentials.py`:

- `get_credential(name: str) -> str | None`
- `set_credential(name: str, value: str) -> None`
- Uses `keyring` Python package (works on macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Service name: `dev.hired.app`
- **Never** logs credential values

### 2.5 Provider Factory

In `backend/llm/__init__.py`:

```python
def get_provider() -> LLMProvider:
    """
    Returns the configured provider based on app_config.provider in DB.
    Cached after first call (provider state lives for app lifetime).
    """
```

Reads from `app_config` table, builds the appropriate adapter, caches it. If config changes (user switches providers), call `reset_provider_cache()`.

FastAPI dependency: `Depends(get_provider)` for routes.

### 2.6 Prompt Templates

Create `backend/prompts/` with one `.md` file per task. Each file has:
- A `SYSTEM:` section
- A `USER:` section with `{{placeholder}}` for inputs
- Optional `EXAMPLES:` section with few-shot examples (especially for `score_job`)

Required prompts:
- `parse_cv.md`
- `score_job.md`
- `research_company.md`
- `tailor_cv.md`
- `generate_cover_letter.md`
- `generate_interview_questions.md`
- `evaluate_answer.md`

Keep prompts concise. Include explicit JSON schema for structured outputs.

### 2.7 Tests

In `backend/tests/test_llm_layer.py`:

**Always-run tests** (no API key needed, must pass in CI):
- MockProvider returns expected stubs for each method
- Provider factory returns MockProvider when `provider=mock`
- Pydantic validation rejects malformed responses
- Credentials helper round-trips a value (with monkeypatched keyring)

**Optional integration tests** (skipped if no API key):
- AnthropicAPIAdapter `score_job` returns valid `ScoreResult` for a sample input
- Marked with `@pytest.mark.integration`
- Run via `pytest -m integration` (CI skips by default)

### 2.8 Update app_config Schema

Add a `model` field to `app_config` so users can override the default model per provider. Default to `claude-opus-4-7` for `anthropic_api`.

### 2.9 Goldset Bootstrap

In `eval/goldset.json`, create a starter set of **3 examples** (full set comes in Phase 4):

```json
[
  {
    "id": "ex-001",
    "profile": {...},
    "job": {...},
    "expected_score_range": [70, 90],
    "must_mention_in_rationale": ["Python", "FastAPI"]
  }
]
```

This is just structure. Real evaluation comes later.

## Verification Steps

1. `pytest backend/tests/test_llm_layer.py` passes (without API key)
2. `pytest -m integration backend/tests/test_llm_layer.py` passes (with API key in env)
3. Manual smoke test:
   ```python
   from backend.llm import get_provider
   from backend.llm.credentials import set_credential
   set_credential("anthropic_api_key", "sk-ant-...")
   # Set provider=anthropic_api in DB
   p = get_provider()
   result = p.score_job(sample_profile, sample_job)
   print(result)  # Should print real Claude response
   ```
4. Code coverage on `backend/llm/` ≥ 85%
5. `docs/CURRENT_PHASE.md` updated; PR merged

## Out of Scope for Phase 2

- ClaudeCodeAdapter and OllamaAdapter — they come in Phase 6 (after MVP works with API)
- UI for provider selection — Phase 3 onboarding
- Caching of LLM responses — Phase 4 when we have real load
- Cost tracking UI — Phase 6

## Why API-First, Not Claude-Code-First?

We deliberately implement the API adapter before Claude Code:
- API is officially supported and stable
- Easier to debug (clear error messages, predictable latency)
- ToS-clean — no gray-area concerns during early dev
- Once the interface is proven against API, swapping in Claude Code is straightforward

This is documented in ADR-0005 (write it as part of this phase).
