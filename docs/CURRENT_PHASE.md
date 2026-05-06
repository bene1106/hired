# Current Phase

Phase 2 merged (PR #2, commit `35fff0c`). **Phase 3 — Profile setup, CV
upload + parse, onboarding wizard — in progress.**

Spec: `.claude/specs/PHASE_3_profile.md`

## Phase 3 — kickoff decisions (locked in 2026-05-06)

- **Profile schema:** plural reshape now. Migration 0003 drops the singular
  `target_role`/`target_location` columns and adds `target_roles_json`,
  `target_locations_json`, `priorities_json` (JSON columns). Profile table
  is empty so the drop is cheap.
- **Provider observability:** `provider_call_log` table populated by a thin
  recorder around `LLMProvider`. Schema: `id, provider, method, latency_ms,
  success, tokens_in, tokens_out, error_type, created_at`. Settings UI
  reads it for "last call latency / calls today".
- **`DELETE /api/data/all` scope:** wipes every user-owned table **and**
  `app_config`, **and** clears the keychain entry via
  `credentials.delete_credential(...)`. The wizard runs from scratch on
  next launch with no secrets left behind.
- **Routing:** React Router v6.
- **CV parsing output:** the existing `parse_cv` prompt already returns
  `summary`, `education`, `languages`, `certifications` alongside the
  Profile-typed fields. Persist the full dict as `profile.cv_parsed_json`;
  the typed `Profile` consumes the subset business logic needs.
- **Test deps:** add `msw` to the frontend for API mocking in Vitest.

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
