# Current Phase

**Phase 3 — Profile setup, CV upload + parse, onboarding wizard —
implementation complete; PR #3 open.**

PR: https://github.com/bene1106/hired/pull/3
Spec: `.claude/specs/PHASE_3_profile.md`

## Phase 3 — completed checklist

- [x] Migration `0003_phase3_profile_and_call_log.py` reshapes `profile`
  to plural JSON columns (`target_roles_json`, `target_locations_json`,
  `priorities_json`) and adds the `provider_call_log` table.
- [x] `RecordingProvider` wraps every `LLMProvider` built by
  `get_provider()`; one row per call written to `provider_call_log`,
  best-effort write so observability never breaks the user flow.
- [x] `services/provider_detection.py` + `POST /api/setup/detect-providers`
  (env + keychain for Anthropic, `shutil.which` + `--version` for Claude
  Code, `/api/tags` for Ollama; defensive — failures = `detected: false`).
- [x] `services/provider_setup.py` + `POST /api/setup/test-provider`
  (1-token round trip for Anthropic, trivial pass for Mock, classified
  errors so the UI can render friendly messages).
- [x] `POST /api/setup/select-provider` commits the wizard's choice to
  `app_config`, stores the API key in the OS keychain, resets the cached
  LLM provider.
- [x] `services/cv_service.py` — pypdf extraction, 5 MB upload guard,
  30 KB pre-LLM truncation, upsert that preserves user-edited
  `name`/`email`. `POST /api/profile/cv` (text) and
  `POST /api/profile/cv/upload` (multipart PDF).
- [x] `GET /api/profile` (404 when empty), `POST /api/profile` (partial
  upsert; missing fields are left untouched).
- [x] `DELETE /api/data/all` truncates every user-owned table, re-seeds
  `app_config`, deletes the Anthropic API key from the keychain, and
  resets the provider cache. Idempotent.
- [x] Frontend foundation: React Router v6, typed API client
  (`src/lib/api.ts`), msw test server, shadcn primitives (Card, Input,
  Label, Textarea, Select, Badge, Button).
- [x] Onboarding wizard — Welcome, Provider, CV, Review, Done — with a
  stepper and shared `OnboardingProvider` context.
- [x] Main app shell + Settings (active provider, edit profile, switch
  provider, two-step "Delete everything").
- [x] Backend tests: 88 passing + 1 integration skipped. Frontend tests:
  13 passing across App routing, all four wizard steps, and Settings.
- [x] CHANGELOG updated.

## Phase 3 — scope notes / deferrals logged

- **ClaudeCodeAdapter and OllamaAdapter** are still Phase 6. Detection
  works for both (informational), but `select-provider` returns 400 if
  the user picks one. The UI marks those cards `aria-disabled`.
- **Provider stats panel in Settings** is wired in the backend
  (`services/provider_stats.py`) but the Settings UI shows only the
  basic profile/provider buttons in Phase 3. The latency + call-count
  display lands in Phase 4 once we have meaningful traffic.
- **Tokens in/out** in `provider_call_log` are populated as `NULL` —
  the column exists but threading `response.usage` through
  `AnthropicAPIAdapter` is a Phase 4/6 concern.
- **End-to-end `pnpm tauri dev`** smoke test is left to the human
  reviewer; we did a backend-only HTTP round-trip across every Phase 3
  route (wizard → CV parse → profile save → wipe → 404) and confirmed
  it works against a real SQLite + the Anthropic detection on this
  machine even picked up the locally-installed `claude.CMD`.

## Phase 2 — completed checklist

- [x] `LLMProvider` Protocol (`backend/llm/base.py`) with seven methods.
- [x] Pydantic types (`backend/llm/types.py`): Profile, Job, ScoreResult,
  CompanyBrief, CoverLetter, InterviewQuestion, AnswerFeedback, plus
  small helper types (WorkExperience, ImprovementNote).
- [x] `MockProvider` (`backend/llm/mock.py`) returning deterministic
  stubs for every method, with `set_response(method, value)` override
  for tests. Zero network calls.
- [x] `AnthropicAPIAdapter` (`backend/llm/anthropic_api.py`) using the
  official `anthropic` SDK. Reads the API key from the OS keychain
  (or `ANTHROPIC_API_KEY` env var). Defaults to `claude-opus-4-7`
  for every task; per-task model split deferred to Phase 6.
- [x] OS-keychain credentials helper (`backend/llm/credentials.py`)
  backed by `keyring`, service name `dev.hired.app`. Never logs values.
- [x] Provider factory in `backend/llm/__init__.py` reading `provider`
  and `model` from `app_config`, caching the built provider, with
  `reset_provider_cache()` for config changes.
- [x] Migration `0002_seed_default_model.py` adds the `model` row to
  `app_config` (default `claude-opus-4-7`). `app_config` stays a
  key/value table; no schema change.
- [x] Pytest marker `integration` registered in `pyproject.toml`. CI
  default `pytest` skips the integration test by design (run locally
  with `pytest -m integration` and an API key).
- [x] 45 always-run unit tests + 1 integration test. Coverage on
  `backend/llm/` is 95% (target was 85%).
- [x] `eval/goldset.json` bootstrapped with 3 starter examples + schema
  doc. Full goldset arrives in Phase 4.
- [x] ADR-0005 records the API-first decision.
- [x] CHANGELOG updated.

## Scope notes / deferrals logged

- **Smaller-model split** for classification-shaped tasks (`score_job`,
  `evaluate_answer`) deferred to Phase 6 cost-optimization work. TODO
  documented inline in `backend/llm/anthropic_api.py`.
- **Scheduled CI integration test runs** deferred to Phase 6. Local
  `pytest -m integration` with a real API key is the verification path
  for now.
- **ClaudeCodeAdapter and OllamaAdapter** remain Phase 6 per ADR-0005.

## Phase 1 — completed checklist (kept for reference)

- [x] Repo bootstrap: `.gitignore`, `.gitattributes`, `LICENSE` (MIT, Benedict
  Herrnleben), project `README.md`, `docs/CHANGELOG.md`, ADR-0001.
- [x] Tauri 2.x shell at `src-tauri/` (identifier `dev.hired.app`, window
  1280x800, min 800x600). `cargo check` + `cargo clippy -D warnings` clean.
- [x] React + TS strict + Vite + Tailwind + shadcn init at `frontend/`.
  Single page renders the title and the "Run health check" button. ESLint
  flat config, Prettier, Vitest — 1 test passes.
- [x] FastAPI sidecar at `backend/` with `GET /health` returning the
  spec-mandated JSON after a real DB query. ruff + pytest — 3 tests pass.
- [x] Initial Alembic migration creates the 7 tables and seeds
  `app_config` with `provider=mock`. Migrations auto-run on FastAPI
  startup via lifespan handler.
- [x] CI workflow at `.github/workflows/ci.yml`: backend + frontend checks
  on every push; full Tauri build matrix (ubuntu/macos/windows) gated to
  PRs targeting main and tag pushes (per the cost decision).
- [x] Cross-platform `scripts/bootstrap.{sh,ps1}` — verified end-to-end
  on this Windows machine.

## Scope reductions logged during Phase 1

- **Sidecar bundling deferred to Phase 6.** PyInstaller-bundling the
  FastAPI sidecar into the Tauri build proved to be a big cross-platform
  CI lift; we deferred it. In Phase 1 the user runs `uvicorn` separately
  during dev; the frontend hits `http://localhost:8765` either way. See
  the strikethrough note in `.claude/specs/PHASE_1_foundation.md` task 1.2.
