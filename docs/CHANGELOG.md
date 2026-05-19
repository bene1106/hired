# Changelog

All notable user-visible changes to Hired. are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 7 (PR F — dashboard → Kanban): the applications table is
  replaced by a 5-column drag-and-drop board (Saved → Applied →
  Interview → Offer → Rejected). `skipped` has no column (Skip is the
  archive action). One `listApplications()` fetch grouped client-side;
  per-column counts + a stats strip are real. Dragging a card does an
  optimistic move + `updateApplicationStatus` + refetch (intra-column
  order isn't persisted — no backend for it); cards are also
  keyboard-activatable and open the PR E detail screen (the accessible
  status-change path). `CompanyMark` reused; `MatchRing` omitted
  (applications carry no score — honest, like PR E). The design's
  `RejectionAnalysis` card and Filter/Sort/Add buttons are cut (no
  backend / redundant on a board), in-screen nav removed (sidebar owns
  it), and the empty-column copy is rewritten emoji-free with no
  autonomous-agent claims. Statuses stay manual; no backend changes.
  `Dashboard.test` was rewritten for the board with every prior
  behaviour re-asserted plus a drag-persist test.
- Phase 7 (PR F fix — Kanban drag-and-drop in Tauri): set
  `app.windows[].dragDropEnabled = false` in `tauri.conf.json`. Tauri
  v2 defaults it to `true`, which registers a native OS file-drop
  handler that swallowed the drag gesture before the webview's HTML5
  DnD could start — board cards couldn't be picked up in the packaged
  app even though jsdom tests passed. No code change to the DnD
  itself; the test now also asserts the card is `draggable` and the
  drop target preventDefaults on dragover. (This also lets the
  onboarding CV drop-zone's in-page file drop work in Tauri.)
- Phase 7 (PR E — job detail + materials merge): `GeneratePage` and
  `ApplicationDetail` are unified into one `MaterialsScreen` (both
  routes kept via thin adapters). One screen handles generation
  (progress ring + staged checklist from the existing pipeline
  polling) and post-generation editing: a two-column layout with the
  job post + a collapsible "Company research" disclosure (the real
  `company_brief` material, kept as secondary context, not a tab) on
  the left, and a Cover letter / CV tab panel on the right. Cover
  letter stays editable with the edit-count line; **Regenerate is the
  only action over generated content** (no tone buttons). Status
  switcher + rejection notes (detail mode) and Mark applied (generate
  mode) are preserved; Interview Prep stays reachable (restyle is
  PR G). No `/apply` or any backend changes. `GeneratePage.test` and
  `Dashboard.test` were updated for the new tabbed DOM with every
  prior behaviour re-asserted; `InterviewPrep.test` untouched.
- Phase 7 (PR D — feed + job card): the job feed and cards are
  restyled in the new visual language. A new shared `MatchRing`
  (animated arc, score shown final-immediately for screen-reader and
  test stability) replaces the score bubble, and a shared
  `CompanyMark` (deterministic initial) anchors each card. Matched /
  missing / red-flag chips carry the real `FeedItem` data (richer than
  the design's generic tags; `sr-only` labels kept for a11y). The
  feed's redundant in-screen global nav is removed now that the
  sidebar owns it (Crawl stays — it's feed-specific). No up/down
  feedback (Phase 9) and no Save toast (PR H). Scoring, feed, crawl,
  and action APIs are untouched; no backend changes.
- Phase 7 (PR C — onboarding redesign): the 5-step wizard (Welcome →
  Provider → Upload CV → Review → Done) is restyled in the new visual
  language — a `HiredStacked` hero with a Fraunces headline, a
  display-only numbered stepper (guard-railed: no step-jumping), and
  the design's card/drop-zone/parsing-ring patterns. The Provider
  screen is designed from first principles (the design package has no
  equivalent); Welcome and Done are built from scratch with Done
  lifting the design's "your agent is ready" success block. Routes,
  wizard state, every API contract, and all guard-rails are unchanged;
  the CV paste path is kept alongside the drop-zone. Copy is honest
  (no autonomous-agent claims) and emoji-free. No backend changes.
- Phase 7 (PR B — app shell + sidebar): the main app now renders inside
  a two-column shell — a fixed 244px sidebar plus the existing screens
  in the flexible main column. The sidebar carries the brand lockup,
  data-driven navigation (Job Feed, Applications, Settings — the routes
  that exist today; it grows as later PRs land their screens), a
  profile footer sourced from the saved profile, and a theme toggle
  wired to the PR A `useTheme` hook. A strict-union `Icon` set
  (ported from the design package, extended per-PR) backs the nav.
  Onboarding and the boot gate stay outside the shell. No screen or
  backend changes — existing screens render unchanged; their
  redundant in-screen headers are stripped when each is restyled in
  PRs C–G.
- Phase 7 (PR A — design foundation): the visual token system from the
  Phase 7 redesign package now backs the app. Tailwind and the global
  stylesheet carry the warm off-white / deep-ink / muted-green palette,
  the Inter Tight · JetBrains Mono · Fraunces · Archivo type stack
  (self-hosted woff2 — no runtime web-font CDN, keeping the app
  local-first and offline-clean), the warm shadow + radius scale, and
  the design's keyframes (fade-up, shimmer, pulse-dot, subtle-bounce).
  A single `data-theme` attribute on `<html>` drives both light and
  dark mode for the design tokens **and** the shadcn primitives, which
  were remapped onto the new palette so they restyle without edits; an
  inline boot script applies the saved theme before first paint to
  avoid a flash. New `useTheme` hook (localStorage-persisted) and the
  reusable brand assets — `HiredMark`, `HiredWordmark`, `HiredLockup`,
  `HiredStacked` — with dark-mode mark inversion handled at the token
  layer. No screen or behaviour changes yet: every existing screen
  renders unchanged inside the new foundation.

## [0.1.1] - 2026-05-17

### Fixed
- **Packaged app could not reach its own backend ("Backend not
  reachable: Failed to fetch").** The bundled Windows build loads the
  webview from the `http://tauri.localhost` origin (WebView2), which
  was not in the FastAPI CORS allowlist — so every in-app request was
  blocked by the browser even though the sidecar was running and
  answering on `127.0.0.1:8765` (curl/browser worked, the app didn't).
  The CORS origin allowlist now also permits `http(s)://tauri.localhost`
  alongside the existing `tauri://localhost`, loopback, and dev
  origins. This was invisible in `pnpm tauri dev` because dev serves
  from `http://localhost:5173`, which was already allowed.
- **Stale sidecar processes.** The Tauri shell never reaped the spawned
  sidecar on app exit, so a closed app left `hired-sidecar` (and its
  PyInstaller child) holding port 8765; the next launch's sidecar then
  lost the bind race. The shell now kills the sidecar process tree on
  exit, and a new single-instance guard stops a second launch from
  spawning a competing sidecar.

### Added (diagnostics)
- Logging now works in **release** builds, not just `cargo` debug: the
  Tauri log plugin writes to a file in the OS log dir, the sidecar
  writes a rotating `~/.hired/logs/sidecar.log` (PID, migration, bind
  result, and a loud error if it can't bind 8765), the backend logs the
  inbound `Origin` of every request, and a failed frontend fetch now
  reports the live webview origin and target URL in its error message.

### Changed
- Version bumped to `0.1.1` across the Tauri shell, sidecar `/health`,
  and frontend.

### Added
- Phase 6 — Multi-provider, packaging & polish: the `claude_code` and
  `ollama` adapters now ship as first-class options. Onboarding lets
  the user pick between Anthropic API, **Claude Code** (the local CLI;
  yellow "Experimental" badge per ADR-0007 + Risk R-01), **Ollama**
  (with a model dropdown sourced from `/api/tags`), and Mock. Each
  carries its own end-to-end Test step — `claude --version` for the
  CLI, `/api/tags` for Ollama (which also confirms the requested model
  is pulled, with an `ollama pull <name>` hint when it's not). The
  factory in `backend/llm/__init__.py` builds the right adapter on
  `app_config` change and `reset_provider_cache()` reroutes the next
  call without an app restart. Settings gains a live provider status
  panel ("Currently using: X · ✓ Healthy · 187 ms latency · 12 calls
  today") sourced from the existing `/api/stats/provider`. The Phase 5
  deferral lands too: a new `LLMProvider.summarize_role` synthesises a
  two-paragraph role explanation that the Interview Prep view shows
  under "Role description"; the summary is cached alongside the
  question bank in `interview_questions.source_meta_json` and falls
  back to the raw job description if the call fails. Distribution
  flips from "run uvicorn yourself" to a single bundled installer per
  OS: `backend/hired-sidecar.spec` PyInstaller-packs the FastAPI
  sidecar, and a new `.github/workflows/release.yml` builds installers
  for macOS / Windows / Linux on `v*` tag pushes via `tauri-action`.
  Builds are unsigned — see `docs/install/{macos,windows,linux}.md`
  for the right-click-Open / SmartScreen / AppImage workarounds. The
  README is rewritten with download links and an architecture sketch;
  `docs/architecture.md` and `docs/api.md` join `api.openapi.json` for
  the doc grade. An accessibility pass adds keyboard activation to
  dashboard rows, `aria-live="polite"` on loading regions, and
  `role="alert"` on inline errors — full audit + findings in
  `docs/accessibility-audit.md`.
- Phase 5 — Application materials, dashboard & interview prep: clicking
  **Apply** on a feed job now opens a dedicated generation page that
  triggers a background pipeline producing three artefacts in sequence
  (company brief → CV tailoring → cover letter). A side-by-side
  textarea + react-markdown preview lets the user edit the cover
  letter inline; every save appends a new `application_materials` row
  and the visible edit count tracks revisions since generation. **Mark
  applied** flips the application to `applied` and lands on the new
  Dashboard, a filterable/sortable table over the full status union
  (`saved | applied | skipped | interview | offer | rejected`). The
  detail view exposes status transitions (with optional rejection
  notes) and a tabbed Interview Prep panel with a categorised question
  bank (technical / behavioural / role-specific / company-fit), a
  practice mode that calls `LLMProvider.evaluate_answer`, and a
  "✓ Practiced" indicator backed by the new `practice_attempts` table.
  Two layered caches keep generation cheap: company briefs are keyed
  by `lower(company)` (three jobs at the same company → one research
  call) and CV tailoring + cover letters fall out of cache when
  `profile_version` bumps. Settings gains a Cost panel that handles
  every provider label — real cents for `anthropic_api`,
  `$0.00 (subscription)` for the upcoming Claude Code adapter,
  `$0.00 (local)` for Ollama, and an em-dash for `mock`. To support
  this, `AnthropicAPIAdapter` now publishes `response.usage` through a
  new `llm.usage` contextvar so `RecordingProvider` can persist
  `tokens_in` / `tokens_out` per call. Migration `0005` adds
  `source_meta_json` and `profile_version` to `application_materials`,
  the `company_briefs` cache table, and the `practice_attempts`
  history table. The synthesised "role explanation" from spec §5.6 is
  deferred to Phase 6; the interview view renders the existing job
  description as the role context to keep the `LLMProvider` Protocol
  stable.
- Phase 4 — Job ingestion & ranked feed: clicking **Crawl** opens an
  inline panel where the user pastes job URLs (one per line); the
  backend fetches each URL, extracts metadata via JSON-LD (`JobPosting`
  schema) with Open Graph fallback, persists deduplicated rows on
  `(source, source_id)`, and scores them against the saved profile via
  `LLMProvider.score_job`. Scores are cached on `(profile_version,
  job_id)` and invalidate automatically when the profile is edited. The
  feed renders ranked job cards with a color-coded score badge, a
  2-sentence rationale, matched/missing skill chips, and Apply / Save /
  Skip buttons; a top-of-page filter row switches between All / Saved /
  Applied / Skipped. A best-effort experimental LinkedIn scraper exists
  but is clearly labeled as unreliable in the UI (see ADR-0006).
  Migration `0004` adds `remote_policy`, `salary_min`, `salary_max`,
  `currency` to `jobs` and `profile_version` to `profile` and
  `job_scores`. The eval harness was rebuilt: `eval/goldset.json` now has
  20 manually-labeled CV/job pairs covering SWE, data, design, PM,
  marketing+sales, and four borderline edge cases; `make eval` reports
  precision@5 and MAE; `make bias-audit` swaps candidate names against a
  fixed pair list and flags any pair with >10pt score variance.
- Phase 3 — Profile setup & onboarding: a five-step wizard (welcome →
  pick provider → upload CV → review profile → done) is now the entry
  point for first-time users; the main app shell and Settings screen
  exist behind it. PDF or pasted CVs are extracted with `pypdf`, parsed
  via `LLMProvider.parse_cv`, and persisted alongside structured
  profile fields. Settings lets users switch providers, edit their
  profile, and "Delete everything" — a two-step destructive action that
  truncates the DB **and** clears the keychain entry so no secrets are
  left behind. Migration `0003` reshapes the profile schema for plural
  preferences (`target_roles_json`, `target_locations_json`,
  `priorities_json`) and adds `provider_call_log` for the Settings UI.
- Phase 2 — LLM provider layer: `LLMProvider` Protocol with seven
  methods (`parse_cv`, `score_job`, `research_company`, `tailor_cv`,
  `generate_cover_letter`, `generate_interview_questions`,
  `evaluate_answer`); `MockProvider` for tests and offline use;
  `AnthropicAPIAdapter` against the public Anthropic API; OS-keychain
  credentials helper; provider factory keyed on `app_config.provider`
  with `model` configurable per provider. ADR-0005 records why we
  shipped the API adapter first. Goldset bootstrapped with 3 examples
  in `eval/goldset.json`.
- Phase 1 — Foundation: Tauri 2.x shell + React/TS/Tailwind frontend +
  FastAPI sidecar with `/health` endpoint + SQLite + Alembic migrations
  for the initial 7-table schema. CI runs backend + frontend checks on
  every push and the Tauri build matrix on PRs to main and tag pushes.
  Cross-platform bootstrap scripts (`scripts/bootstrap.{sh,ps1}`).
