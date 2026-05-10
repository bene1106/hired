# Current Phase

**Phase 6 complete; v1.0.0 release pipeline live.**

The MVP is feature-complete across all six phases. Track A
(multi-provider), Track B (packaging), and Track C (polish) all
landed on `feat/phase-6-multi-provider`. The first `v*` tag push
exercises `.github/workflows/release.yml`, which builds installers
for macOS / Linux / Windows via PyInstaller + tauri-action and
uploads them to a draft GitHub release.

Branch: `feat/phase-6-multi-provider` (merged → main after PR)
Spec: `.claude/specs/PHASE_6_polish.md`

## Phase 6 — completed checklist

- [x] `llm/claude_code.py` — subprocess wrapper around the local
  `claude` CLI (`-p --output-format json --append-system-prompt`),
  120s timeout, stdin-piped user prompt to dodge CLI length limits,
  flattened few-shot examples for single-turn mode.
- [x] `llm/ollama.py` — HTTP client to `localhost:11434/api/chat`,
  default `qwen2.5:14b` (fallback `llama3.2:3b`), 180s timeout, token
  usage from `prompt_eval_count` / `eval_count`.
- [x] `llm/base.py` extended with `summarize_role`; new prompt template
  `prompts/summarize_role.md` (two-paragraph plain text). Cached on
  the latest `interview_questions` material's `source_meta_json` so a
  profile bump or `refresh=true` regenerates both questions and
  summary together. Falls back to the raw job description when the
  call fails.
- [x] Factory in `llm/__init__.py` builds the new adapters; the
  Phase-3 selectability guard in `services/provider_setup.py` and
  `api/routes/setup.py` is removed.
- [x] `GET /api/setup/providers` exposes UI metadata (label,
  `is_experimental`, `requires_api_key`, `default_model`) so the
  onboarding wizard renders the "Experimental" badge for Claude Code
  without hardcoding the list. `/select-provider` now persists model
  alongside provider.
- [x] Frontend onboarding `ProviderStep` enables Claude Code (when
  the CLI is detected) and Ollama (when reachable) selection, with a
  destructive "Experimental" badge + ToS notice on the Claude Code
  card per ADR-0007 R-01, and a model dropdown populated from
  `/api/tags` for Ollama.
- [x] `SettingsScreen` shows live provider status sourced from
  `/api/stats/provider` ("Currently using: X · ✓ Healthy · 187 ms
  latency · 12 calls today"), with the Experimental badge surfaced on
  Claude Code there too.
- [x] `backend/sidecar.py` + `backend/hired-sidecar.spec` PyInstaller-
  bundle the FastAPI sidecar. `db/migrations.py` and `llm/prompts.py`
  resolve resource paths through `sys._MEIPASS` when frozen.
- [x] Tauri sidecar wiring: `tauri.conf.json` declares
  `bundle.externalBin: ["binaries/hired-sidecar"]`, `Cargo.toml`
  picks up `tauri-plugin-shell`, `lib.rs` spawns the binary on app
  start and drains stdout/stderr into the log plugin (skipped in
  `pnpm tauri dev` so the existing `uvicorn` workflow stays).
- [x] `.github/workflows/release.yml` — matrix build mac/linux/win on
  `v*` tag pushes; PyInstaller-builds the sidecar, renames with the
  Tauri target-triple suffix into `src-tauri/binaries/`, then
  `tauri-action` ships installers to a draft GitHub release.
- [x] `docs/install/{macos,windows,linux}.md` — first-launch
  workarounds for unsigned builds (Gatekeeper right-click → Open,
  SmartScreen More info → Run anyway, AppImage `chmod +x` +
  `libfuse2`), data paths, uninstall steps.
- [x] `README.md` rewritten with elevator pitch, OS-by-OS install
  table, source build steps, architecture sketch + tech stack.
- [x] `docs/architecture.md` — one-page diagram + invariants +
  per-layer responsibility table.
- [x] `docs/api.md` + committed `docs/api.openapi.json` — full REST
  reference grouped by area.
- [x] Accessibility pass: keyboard-activatable dashboard rows
  (`role=button` + Enter/Space), `aria-live=polite` on loading
  regions across screens, `role=alert` on inline errors, screen-
  reader-only "Matched/Missing skills:" group prefixes on `JobCard`.
  Findings + fixes logged in `docs/accessibility-audit.md`.
- [x] ADR-0007 records the multi-provider rollout shape and ties it
  back to ADR-0005 + Risk R-01.
- [x] `docs/postmortem.md` — what worked, what didn't, lessons.
- [x] Backend: 206 tests passing + 1 integration skipped (38 new for
  Phase 6: 13 ClaudeCodeAdapter, 13 OllamaAdapter, 6 new
  test-/select-provider cases, 2 new factory cases, 4 across the
  summarize_role wiring). Frontend: 37 tests passing including 5 new
  for ProviderStep + Settings.
- [x] CHANGELOG updated.

## Phase 6 — scope notes / deferrals logged

- **Demo video, final bug bash** — explicitly skipped per the human
  owner's call. The per-phase manual tests are the QA gate; a real
  user reporting a regression is the trigger for fix work.
- **Code signing** — unsigned builds. Apple Developer ID + Windows EV
  cert wiring is documentation-only at this point; the install docs
  cover the Gatekeeper / SmartScreen workarounds.
- **Stretch goals** (mock interview chatbot, salary benchmark,
  rejection pattern analysis, multi-language) — all deferred. They
  may return as standalone issues post-MVP.
- **Per-prompt few-shot drop knob for smaller Ollama models** —
  documented in `OllamaAdapter` docstring as a follow-up if a real
  user reports tight-context drift.
- **First 1-2 release-workflow CI runs** are expected to surface
  platform-specific PyInstaller hidden-import gaps; the spec gets
  iterated as those land.
- **Cold-start latency** for `claude` CLI invocations isn't
  optimised. Long-lived stdin pipe was considered and rejected in
  ADR-0007. Revisit if the bottleneck shows up.

PR for Phase 5 (kept here for context): https://github.com/bene1106/hired/pull/6
Spec for Phase 5: `.claude/specs/PHASE_5_applications.md`

## Phase 5 — completed checklist (kept for reference)

- [x] Migration `0005_phase5_application_materials.py` adds
  `source_meta_json` and `profile_version` to `application_materials`,
  creates the `company_briefs` cache table (case-insensitive unique
  `company_lower`), and the `practice_attempts` history table.
- [x] `services/application_service.py` orchestrates the three-step
  apply pipeline (research → tailor CV → cover letter) with two
  layered caches: company briefs keyed by `lower(company)` (three
  jobs at the same company → one research call) and CV tailoring +
  cover letters keyed by `(application_id, type, profile_version)`
  so a profile bump forces re-generation.
- [x] `services/generation_progress.py` mirrors `crawl_progress` —
  per-task in-process state, sequentially marking each step
  `running` → `done | cached | error`.
- [x] `api/routes/applications.py` exposes 11 endpoints powering the
  apply / dashboard / interview-prep flows; status accepts the union
  `saved | applied | skipped | interview | offer | rejected`.
- [x] `llm/usage.py` adds a contextvar seam; `AnthropicAPIAdapter`
  publishes `response.usage` and `RecordingProvider` persists
  `tokens_in` / `tokens_out` to `provider_call_log`.
- [x] `services/pricing.py` carries per-model USD/Mtok rates and
  returns `None` for unknown models so the UI shows "—".
- [x] `services/cost_service.py` rolls up today + this-week totals
  with explicit labels (`priced` / `subscription` / `local` /
  `unknown`).
- [x] `GET /api/stats/cost` and `/api/stats/provider` expose the
  rollups; the cost endpoint substitutes the right label so the
  frontend doesn't need per-provider semantics.
- [x] Frontend `applications/GeneratePage.tsx` triggers generation,
  polls progress, reveals each section as it lands, and supports
  inline cover-letter editing with a side-by-side textarea +
  react-markdown preview. "Mark applied" flips status and lands on
  the dashboard.
- [x] `applications/Dashboard.tsx` renders a filterable, sortable
  table with status pills.
- [x] `applications/ApplicationDetail.tsx` composes materials view +
  status transitions + an interview-prep tab.
- [x] `applications/InterviewPrep.tsx` groups the cached question
  bank by category, runs practice mode against
  `LLMProvider.evaluate_answer`, and marks practiced questions.
- [x] Settings gains a Cost panel handling every provider label
  with the right copy.
- [x] FeedScreen `Apply` now navigates to `/app/apply/:jobId`; status
  transitions live in the generation flow / dashboard.
- [x] msw handlers cover every Phase 5 endpoint.
- [x] Backend tests: 168 passing + 1 integration skipped (43 new for
  Phase 5: 13 application-service, 17 application endpoints, 13
  cost tracking). Frontend tests: 32 passing including 14 new for
  Phase 5 screens.
- [x] CHANGELOG updated.

## Phase 5 — scope notes / deferrals logged

- **Synthesised role explanation** (§5.6, "2 paragraphs synthesized
  from job description, one LLM call, cached") deferred to Phase 6.
  Adding `LLMProvider.summarize_role` would force every adapter to
  grow a method mid-phase; the interview view renders the existing
  job description as the role context instead. Documented inline in
  `api/routes/applications.py`.
- **Pricing rates** in `services/pricing.py` are placeholders for
  Anthropic's published rates as of Jan 2026; update the dict when
  rates change. Unknown models return `None` so the UI safely shows
  an em-dash.
- **End-to-end `pnpm tauri dev`** smoke test is left to the human
  reviewer; backend + frontend tests are green and the in-process
  TestClient round-trip exercises the full Apply → Generate →
  Edit → Mark applied → Dashboard → Interview-prep flow.
- **Generation progress** lives in the same kind of in-process dict
  as crawl progress and resets on backend restart. Acceptable for
  MVP; promote to a persisted table if a real user reports lost
  progress mid-generation.

PR for Phase 4 (kept here for context): https://github.com/bene1106/hired/pull/5
Spec for Phase 4: `.claude/specs/PHASE_4_jobs.md`
ADR: `docs/adr/0006-crawler-fragility.md` (manual URL paste = primary path)

## Phase 4 — completed checklist

- [x] Migration `0004_phase4_jobs_scoring.py` adds `remote_policy`,
  `salary_min`, `salary_max`, `currency` to `jobs`, and a
  `profile_version` integer to `profile` (mirrored on `job_scores`)
  so cached scores invalidate automatically when the profile is edited.
- [x] `backend/crawler/`: `JobSource` ABC + `RawJob` shape; primary
  `ManualURLSource` (httpx + BeautifulSoup, JSON-LD `JobPosting` first
  with Open Graph fallback); experimental `LinkedInSource` (Playwright,
  raises `LinkedInUnavailable` so callers fall back); `service.crawl()`
  orchestrator handles dedup on `(source, source_id)` and persistence.
- [x] `services/profile_mapper.py` converts DB rows to `llm.types`
  shapes (Profile, Job) so the scoring/eval/feed paths share one
  conversion.
- [x] `services/scoring_service.py` reads cached scores at the current
  `profile_version`, scores misses through a 5-thread pool, and persists
  one row per (profile_version, job_id). Profile updates and CV
  re-uploads bump `profile_version`.
- [x] `services/crawl_progress.py` — bounded in-process registry; the
  status endpoint reads from it. Resets on backend restart (documented
  constraint, MVP-acceptable).
- [x] `POST /api/jobs/crawl` (BackgroundTasks), `GET /api/jobs/crawl/
  status/{job_id}`, `GET /api/jobs/feed` (filter + min-score + exclude
  status), `POST /api/jobs/{id}/action` (apply/save/skip → upsert
  Application row).
- [x] Frontend: `frontend/src/feed/{FeedScreen,JobCard}.tsx` replaces
  the Phase 3 "no jobs yet" main shell. Inline crawl panel with a
  multiline URL paste box and a clear "LinkedIn scraping is unreliable"
  notice; status polls every 1.5s until done; filter row toggles
  All/Saved/Applied/Skipped; cards render score badges (green ≥75 /
  yellow ≥50 / gray) plus skill chips and action buttons.
- [x] `eval/goldset.json` expanded from 3 → 20 entries (4 SWE, 3 data,
  3 design, 3 PM, 3 marketing+sales, 4 borderline — location, salary,
  partial skill, visa).
- [x] `eval/run_eval.py` reports in-range rate, MAE, precision@5, and
  must-mention coverage; `eval/bias_audit.py` swaps each candidate's
  name to a paired alternative and flags any pair with >10pt variance.
  Both default to the `app_config` provider with `--provider` override.
- [x] `Makefile` at repo root with `eval`, `bias-audit`, `backend-test`,
  `frontend-test`, and `test` targets (PROVIDER=mock|anthropic_api).
- [x] Backend tests: 122 passing + 1 integration skipped. Frontend
  tests: 18 passing including five new FeedScreen/JobCard tests.
- [x] CHANGELOG updated.
- [x] ADR-0006 records the manual-URL-first decision.

## Phase 4 — scope notes / deferrals logged

- **Live LinkedIn scraping** works against today's DOM but is fragile
  by design. The UI calls it out explicitly. The default crawl source
  is `manual_url`; LinkedIn is a `?source=linkedin` opt-in.
- **Background-task progress** lives in an in-process dict that resets
  on backend restart. We intentionally did not persist it. If a real
  user reports lost progress, persistence is a small change in
  `services/crawl_progress.py`.
- **Scoring concurrency** is a 5-worker thread pool, well below any
  Anthropic rate limit at the 20-job MVP scale. Phase 6 may revisit if
  we add larger crawls.
- **Eval against `MockProvider`** is structurally meaningful (the
  harness runs and computes metrics) but the numbers are not — the mock
  returns 75 for everything. Real evaluation runs require
  `make eval PROVIDER=anthropic_api` with a configured API key.
- **End-to-end `pnpm tauri dev`** smoke test is left to the human
  reviewer; backend + frontend tests are green and the in-process
  TestClient round-trip exercises the full Crawl → Score → Feed →
  Action flow against a fresh SQLite per test.

PR for Phase 3 (kept here for context): https://github.com/bene1106/hired/pull/3
Spec for Phase 3: `.claude/specs/PHASE_3_profile.md`

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
