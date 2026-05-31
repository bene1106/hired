# Changelog

All notable user-visible changes to Hired. are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.7] - 2026-05-31

### Fixed

- Company research now uses **real web search** instead of relying on the
  model's memory, so briefs for small or newly founded companies are grounded
  in current sources rather than fabricated. The Anthropic API provider
  activates the stable web-search tool and lists the actual URLs it retrieved;
  the Claude Code and OpenAI Codex providers enable their respective web-search
  tools for the research call. Ollama (no web access) keeps its training-data
  disclaimer and never invents sources.

- Settings → Cost now shows a billing note that matches the active provider
  (Claude Code → Claude.ai plan, OpenAI Codex → ChatGPT plan / OpenAI key,
  Ollama → local, Anthropic API → per token) instead of always claiming Claude
  Code billing.
- Switching the provider from Settings now returns you to Settings after the
  change instead of dropping an already-onboarded user back into the full
  CV → Review → Done onboarding wizard.
- The onboarding CV dropzone now highlights while a PDF is dragged over it
  (dragenter/dragover/dragleave) and resets on drop or leave.

## [0.3.6] - 2026-05-31

### Added
- **OpenAI Codex CLI provider.** A new `CodexCLIAdapter` lets users who run
  the local `codex` CLI (authenticated against a ChatGPT plan or
  `OPENAI_API_KEY`) route Hired.'s LLM calls through it — the OpenAI-side
  counterpart to the existing Claude Code provider. It implements the full
  `LLMProvider` interface by shelling out to `codex exec --json` in a
  read-only sandbox, with token usage recorded the same way as every other
  adapter.
  - Onboarding and Settings list it as a first-class, provider-agnostic
    option with an "Experimental" badge. Detection distinguishes
    "not installed" / "installed but not logged in" / "ready", and the
    Test CLI button verifies `codex login` status.
  - Cost panel shows `$0.00 (subscription)` — usage is billed via the
    user's ChatGPT plan / OpenAI key, so no per-call price is fabricated.
  - See ADR-0010 for the design (CLI invocation, event-stream error
    handling because `codex exec` exits 0 even on failure, and why no
    model is pinned by the factory).

## [0.3.5] - 2026-05-21

Five fixes addressing two failure classes the v0.3.4 RC smoke surfaced:
(1) re-pasting a known job URL after re-onboarding left the Feed
empty because the crawler skipped re-scoring on dedup, (2) a
disappearing keychain credential produced a 500 generic wall instead
of an actionable "re-enter your key" path.

### Added
- **Crawler auto-rescore.** ``crawler/service.crawl()`` now reports
  ``rescore_job_ids`` for existing rows whose ``JobScore`` is at a
  stale ``profile_version``. The crawl pipeline scores ``new_job_ids
  + rescore_job_ids`` so a re-paste-known-URL flow doesn't leave
  the user with an empty Feed.
- **``GET /api/jobs/scoring-status``** — returns
  ``{jobs_total, jobs_with_current_score, rescore_candidate_count,
  profile_version}``. Drives the Feed empty-state conditional
  ("Re-score existing jobs" button only when ``jobs_total > 0``
  AND ``visible == 0``).
- **``POST /api/jobs/rescore``** — re-scores every job missing a
  ``JobScore`` at the current ``profile_version``. Synchronous,
  capped at 50 per call. Response: ``{rescored, total_candidates,
  capped}``.
- **``LLMAuthError`` → HTTP 401** with structured JSON body
  ``{detail, error_kind: "missing_api_key"}``. Replaces the
  generic 500 plaintext that v0.3.4's middleware was emitting when
  the Anthropic keychain entry was missing.
- **``/api/stats/provider`` active probe.** The Settings panel now
  surfaces ``construct_ok`` + ``construct_error`` so a dead provider
  shows up as "Disconnected" in real time instead of the historical
  call-log staying green forever.
- **Frontend: global 401 banner** at the top of AppShell with a
  direct "Re-enter key" link to ``/onboarding/provider``. Triggered
  by any ``error_kind=missing_api_key`` response anywhere in the app.
- **Frontend: Feed empty-state CTA.** When jobs exist in the DB but
  none are visible (you re-onboarded), the empty state shows a
  "Re-score existing jobs" button with the literal count
  ("You have 3 jobs in the DB that haven't been scored…"). On a
  fresh install (``jobs_total = 0``) the copy stays at the default
  Crawl invitation. Toast on completion names the actual numbers
  ("Rescored 3 jobs"; capped: "Rescored 50 jobs · 10 more queued —
  run again.").

### Tests
- ``test_crawler.py`` — 2 new cases: dedup + stale score adds to
  ``rescore_job_ids``; dedup + current score skips it.
- ``test_jobs_endpoints.py`` — 4 new cases: scoring-status (empty /
  with stale), rescore (catches up / caps at 50).
- ``test_error_middleware.py`` — 3 new cases: ``LLMAuthError`` →
  401 with ``error_kind``, ``/api/stats/provider`` reports
  ``construct_ok=true`` and ``=false`` paths.
- ``FeedScreen.test.tsx`` — 3 new cases: fresh-install copy,
  conditional rescore button + happy-path toast, capped toast.
- ``AppShell.test.tsx`` — 1 new case: 401 banner appears + link
  points to ``/onboarding/provider``.

### Notes for installers
- v0.3.5 is backend + frontend. Re-installing over v0.3.4 keeps
  your DB; if your Feed was empty after v0.3.4, the
  empty-state's new "Re-score existing jobs" button will catch up
  your jobs in one click.
- The "Switch provider" flow still resets the full onboarding —
  Bene flagged this for v0.3.6+ standalone Settings route.

## [0.3.4] - 2026-05-21

Hotfix on v0.3.3. The v0.3.3 RC smoke surfaced a "Failed to fetch" on
the Practice tab — curl reproduced an HTTP 500 in 0.2s on
\`GET /api/applications/{id}/interview/questions\`. A local TestClient
+ uvicorn re-run against a bit-identical DB snapshot returned 200 on
the same code. The bundled binary's stderr capture in Tauri's shell
plugin was producing zero new bytes around the failing request, so
the actual traceback was untraceable from logs in the field.

v0.3.4 fixes that observability gap and adds a defensive drop on the
Practice tab so a single bad cached row can't 500 the whole endpoint.
No behavioural change for healthy data paths.

### Added
- ``api/main.py``: new ``log_unhandled_exceptions`` middleware that
  catches anything escaping a sync handler, logs the full traceback
  through ``hired.api`` (which sidecar.py routes to
  ``~/.hired/logs/sidecar.log`` AND stdout), and returns
  ``"Internal Server Error (<ExceptionType>)"`` so a curl smoke can
  identify the exception type without grepping logs.
- ``sidecar.py``: ``_setup_logging`` now attaches handlers to the
  ``hired`` logger namespace with ``propagate=False`` in addition to
  the root logger. Before, uvicorn's startup dictConfig replaced the
  root handlers and ``hired.api`` log records (request errors,
  middleware diagnostics) stopped reaching the file once requests
  started flowing. Namespace-scoped handlers survive that.

### Fixed
- ``GET /api/applications/{id}/interview/questions``: cached rows are
  now validated row-by-row via ``InterviewQuestionResponse.model_validate``;
  any row that fails (missing required field, wrong category enum,
  schema drift after a prompt change) is **dropped from the response
  and logged** rather than escalating to a 500. The user sees a
  Practice tab with the still-valid questions (or empty + the same
  ``role_context``); the bad row's idx + payload keys land in
  sidecar.log for diagnosis. Three new backend tests
  (``test_error_middleware.py``) cover the middleware contract and
  both partial-drop and all-drop paths.

### Notes for installers
- v0.3.4 is a pure backend hotfix. Frontend is byte-identical to
  v0.3.3. If you saw "Failed to fetch" on Practice in v0.3.3, install
  v0.3.4 over it (DB carries over, no re-onboarding). Then re-open
  the Practice tab — if any row is still bad, the endpoint serves the
  others and logs the offender to ``~/.hired/logs/sidecar.log``.

## [0.3.3] - 2026-05-21

Hotfix on v0.3.2. **Cold-start regression.** Backend was healthy on
Bene's v0.3.2 RC smoke (verified via curl: HTTP 200 + correct CORS
headers for `http://tauri.localhost`), but the sidecar took ~30–60s
to bind after a fresh reinstall — PyInstaller bundle extraction +
Windows Defender scan + first-time imports of anthropic/pydantic from
cold disk. AppGate's retry window was 8 attempts on linear backoff
(~14s total, last shipped in v0.1.1), so it gave up before the
sidecar finished booting and showed "Backend not reachable: Failed
to fetch."

### Fixed
- `AppGate.tsx` polls every 1s for up to 60 attempts (~60s total),
  replacing the 8-attempt / linear-backoff scheme. Progress copy now
  shows elapsed seconds ("Connecting to backend… (3s)") rather than
  "attempt 3/8" so the user can see it's working through a cold
  start. Error state names the timeout explicitly: "Backend not
  reachable after 60s: …". Two new regression tests in
  `AppGate.test.tsx`: the progress copy uses the new format, and
  AppGate keeps polling past the old 8-attempt budget until the
  sidecar comes up at simulated attempt 12.

### Notes for installers
- **If you saw "Failed to fetch" on v0.3.2**, you can recover without
  reinstalling — just hit Ctrl+R or F5 in the Tauri window after the
  app has been open for ~30s. The sidecar is already running by then
  (`%LOCALAPPDATA%\dev.hired.desktop\logs\Hired.log` shows it bound
  port 8765 within seconds); the new poll budget in v0.3.3 just gives
  it long enough to be discovered on the first try.
- No backend or schema change; no re-onboarding.

## [0.3.2] - 2026-05-21

Hotfix on top of v0.3.1 — three InterviewChat UI bugs surfaced in the
v0.3.1 Tauri smoke. No backend changes. Coach streaming itself
**worked** in real WebView2 (the chunk transport, the multi-turn flow,
the language-awareness, the session lifecycle) — the bugs were
visual-layer only.

### Fixed
- **User-message bubble was invisible (HIGH, release-blocker).** The
  bubble was styled `bg-ink text-bg`, but `bg` is not a Tailwind colour
  token in this project (it's a CSS variable; the design token's
  Tailwind name is `paper`). The text fell back to inherited dark-on-
  dark and disappeared. Fixed to `bg-ink text-paper` and added a
  `data-testid="user-bubble"` plus a regression test that asserts both
  class names live on the rendered bubble.
- **Session-title overflow in the sidebar.** Long previews like "Frag
  mich eine Verhaltensfrage zu…" spilled out of the card into the
  chat pane because the flex item lacked `min-w-0`, so the `truncate`
  on the inner span couldn't engage. Added `min-w-0` to the session
  `<li>` and the resume-button, `flex-shrink-0` to the delete button,
  and a regression test that asserts both `truncate` on the title and
  `min-w-0` on its containing button.
- **Confidence slider read as a passive display, not an input.** Label
  was 10-px mono caption ("CONFIDENCE") — easy to miss — and segments
  looked like progress bars. Promoted to a real form prompt ("How
  confident do you feel after this round?"), made each segment a
  numbered button with hover state + border, added an honest helper
  line — "Click a number — your own gut-check, not graded. Resets when
  you switch sessions." — which is the truthful description of the
  state model from ADR-0009 D6 (UI-only, per-session). Regression test
  asserts the visible prompt, the helper copy, and that clicking a
  segment moves the active selection.

### Notes for installers
- v0.3.2 is the first build with a usable coach UX. **Recommend
  installing this over v0.3.0 / v0.3.1** before any public flip — the
  Bug-1 invisibility broke multi-turn conversations on the v0.3.1 RC.
- No backend or schema change: a fresh `~/.hired/data.db` from
  v0.3.0/0.3.1 carries over without re-onboarding.

## [0.3.1] - 2026-05-21

Hotfix on top of v0.3.0. No feature changes — adds a guard against the
class of operational mistake that destroyed real user data during Phase
8 PR-B smoke testing. The v0.3.0 production build itself was already
clean (no shipped fixtures, migrations only DDL + `app_config` seed);
this release just makes future mistakes loud.

### Added
- `db/session.resolve_db_url()` now emits a one-time stderr warning
  when the default `~/.hired/data.db` path is opened from outside the
  PyInstaller bundle and without `HIRED_DB_URL` set. Five new tests
  (`test_db_session_guard.py`) cover the trigger conditions: default-
  path-fires, override-silent, bundle-silent, quiet-env-silent, fires-
  exactly-once. Set `HIRED_PROD_DB_QUIET=1` only when the production
  path is genuinely the intended target.
- `CLAUDE.md` "Never Do" gains an explicit rule against writing to
  `~/.hired/data.db` from one-off scripts, citing the v0.3.1 trigger.

### Notes for installers
- v0.3.0 and v0.3.1 produce **identical user-facing behaviour**. If you
  installed v0.3.0 and reached a fresh-state onboarding (i.e. you
  weren't a victim of the PR-B smoke-fixture incident), there is no
  reason to reinstall — v0.3.1 only hardens dev tooling.
- If you DID see "Smoke Tester" / "SmokeCo" fixtures in v0.3.0, the
  fix on the user side is simply: stop the app, delete `~/.hired/
  data.db`, relaunch. v0.3.1 is the same build with the dev guard.

## [0.3.0] - 2026-05-21

Phase 8 — the interactive interview coach lands as a streaming chat
that coexists with the Phase 5 Question Bank inside the Interview Prep
tab. Plus an in-place editable Preferences card in Settings, so users
can sharpen targeting without re-running the onboarding wizard. The
`LLMProvider` interface gets its first new method since Phase 6
(`interview_chat_stream`) — all four adapters now stream.

### Added
- Phase 8 (PR E — polish + v0.3.0): ADR-0009 records the streaming
  Protocol extension, the SSE-over-fetch transport choice, the
  Practice/Coach coexistence policy, and the honest omissions
  (streak / answered-today / slider persistence). Versions bumped to
  0.3.0 across `frontend/package.json`, `src-tauri/Cargo.toml`,
  `Cargo.lock`, and `tauri.conf.json`.
- Phase 8 (PR D — editable Preferences): new "Preferences" card in
  Settings between Profile and Provider. Chip inputs for target_roles
  and target_locations (Enter or comma to add, × to remove, Backspace
  on empty input pops the last chip), number input for minimum salary
  (empty → null), textarea for priorities (one per line, blank lines
  trimmed). Save button shows a "Saving…" spinner and surfaces a
  toast on success. Backend: zero changes — Profile already has the
  fields and `PUT /api/profile` accepts them.
- Phase 8 (PR C — chat UI + SSE consumer): new `InterviewChat`
  component, 2-column layout with a session sidebar (newest-first
  list, preview + turn count, delete per row) and the chat panel.
  Streaming consumer uses `fetch()` + `ReadableStream` (not
  `EventSource` — it can't send a POST body and is quirky in
  WebView2); each SSE chunk lands in the same assistant bubble.
  Confidence slider per session (UI-only state, drops on session
  switch). New `InterviewPanel` wraps a Practice ↔ Coach segmented
  toggle, default Practice — every Phase 7 PR G test for
  `InterviewPrep` passes unchanged. Half-write-safe: on mid-stream
  error the user turn stays in the transcript, the empty assistant
  placeholder is dropped, and the error surfaces via `role="alert"`.
  Also: fixed a recurrence of the PR #11 `SettingsScreen` cost-panel
  flake (same sync-toHaveTextContent race the provider-panel fix
  patched in PR #11; the em-dash test was missed).
- Phase 8 (PR B — chat endpoint + sessions API): five new endpoints
  under `/api/applications/{id}/interview/sessions/*` — create, list
  (newest first, with preview + turn_count), get full transcript,
  delete, and the SSE-streaming POST messages. Uses the existing
  `InterviewSession` model (transcript_json) — no DB migration. SSE
  frames: `data: {"chunk": "<text>"}\n\n` per chunk, terminator
  `data: {"done": true, "session_id": N}\n\n`, or
  `data: {"error": "..."}\n\n` on mid-stream failure. User turn is
  persisted synchronously before streaming; assistant turn only on
  clean completion. The Phase 5 endpoints (`/questions`, `/practice`,
  `/attempts`) are untouched and coexist with the chat.
- Phase 8 (PR A — provider streaming): `LLMProvider` gains
  `interview_chat_stream(messages, role_context) -> Iterator[str]`.
  New `ChatMessage` / `ChatRole` types (`user` / `assistant`, same
  shape as the DB transcript and the frontend so no translation
  layer). New `backend/prompts/interview_coach.md` — multi-turn
  CRITIQUE-AND-FOLLOWUP shape, honest tone, no JSON / no emojis, two
  few-shot examples, `{{role_context}}` substitution. `MockProvider`
  yields deterministic chunks; `AnthropicAPIAdapter` uses
  `messages.stream()`; `OllamaAdapter` consumes `stream=true` NDJSON;
  `ClaudeCodeAdapter` parses `--output-format stream-json
  --include-partial-messages` events with graceful fallback to single
  `assistant`-event chunk on older CLI versions. `RecordingProvider`
  wraps the iterator so latency is measured at drain and one
  `provider_call_log` row is written per stream (success or error).
- The prompt loader (`PromptTemplate.render`) now substitutes
  `{{}}` placeholders in both `system` and `user` blocks (was
  user-only). Verified safe: every pre-Phase-8 prompt uses
  placeholders only in user blocks.

### Notes for installer testing
- The `v0.3.0` tag triggers `release.yml` and builds a 3-OS draft
  release. The Tauri smoke for chat coexists with the Phase-7-RC
  pattern: install the build, run a chat session in real WebView2,
  verify chunks arrive progressively (`X-Accel-Buffering: no` is set
  on the SSE response to avoid webview-level buffering). Real
  WebView2 SSE risk is the only deferred verification.

## [0.2.0] - 2026-05-19

Phase 7 — frontend redesign. The app now uses the new warm
off-white / deep-ink / muted-green design language across every
screen, with light + dark mode. Backend and business logic
untouched.

### Added
- Phase 7 (PR H — polish + v0.2.0): a brand-green `Toast` (fires on
  cover-letter save — the carried-over PR D feedback gap), a
  structured `SuggestionRenderer` for the CV tab (one card per
  suggestion with a typed eyebrow; falls back to markdown for
  legacy/plain content), a Regenerate loading state (disabled +
  spinner + "Regenerating…"), and a Fraunces preload to kill the
  onboarding hero FOUT. Accessibility re-audit: the provider tiles
  (`role="radio"`) are now keyboard-operable (`tabIndex` +
  Enter/Space); Feed and Applications get shimmer skeletons with
  `aria-busy`/`sr-only` while loading. Dark-mode audit passed (all
  raw colours are intentional/dark-stable). ADR-0008 records the
  redesign. Version bumped to 0.2.0 across the frontend, the Tauri
  shell, and the lockfile.
- Phase 7 (PR G — interview prep + settings restyle): both screens
  adopt the new visual language with zero behaviour change. Interview
  Prep keeps the question bank (4 categories, practice mode via
  `evaluate_answer`) and gets token-styled cards, a green accent-tint
  feedback bubble, and chip-styled "✓ Practiced" markers — no chat
  coach (that stays Phase 8). Settings restyles the Profile / Provider
  / Cost / Delete-everything cards, drops the redundant in-screen
  "Back to app" button (sidebar owns global nav, consistent with PR
  D/F), and keeps the provider-panel loading→loaded contract intact.
  No backend changes; `InterviewPrep.test` and `SettingsScreen.test`
  pass unmodified.
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
