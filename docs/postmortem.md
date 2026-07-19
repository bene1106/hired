# Hired. — Postmortem

**Project:** Hired., a local-first AI career agent (Tauri + React + FastAPI).
**Window:** 6 phases over the project, last commit 2026-05-10.
**Authoring agent:** Claude (Opus 4.7 1M-context) collaborating with the human owner via the Claude Code CLI; this postmortem is written from the agent's working perspective, with the human owner's framing decisions noted where they shaped the outcome.

This document closes Phase 6. It's not a marketing recap — it's the honest "if I were doing it again" log, scoped to choices that mattered.

## How we worked

Hired. is a four-person project built with heavy agent assistance. Work was
split by ownership area rather than by file: architecture and the LLM provider
layer (Anna, Bene), frontend and the design system (Eren), backend, data
ingestion, packaging and the AI integration prompts (Kaleem). Everyone worked
against one shared codebase, reviewed each other's PRs, and synced weekly.

Two consequences worth naming, because they shape what this postmortem can and
cannot tell you:

- **The retrospective below is written from the agent's perspective on the
  implementation workstream through Phase 6.** It is deliberately narrow. The
  Phase 7 design system, the decks, and the demo videos are substantial team
  output that this document does not cover, and that `git log` does not show
  either — commit counts are a poor proxy for contribution on this project.
- **Agent-assisted development changed the shape of the work more than the
  split of it.** The phase-spec contracts described below existed so that
  several people plus an agent could work against the same repository without
  re-litigating scope every session.

## What worked

### Phase-spec contracts

Every phase had its own `.claude/specs/PHASE_<N>_*.md` with explicit acceptance criteria and an out-of-scope list. The shape stopped scope creep cold: when a chunk of work didn't fit the current phase's contract, it became "deferred to Phase N+1" with an inline note rather than silently growing the diff. Three deferrals (Phase 1 → 6 sidecar bundling, Phase 3 → 4/6 token usage, Phase 5 → 6 `summarize_role`) were caught and tracked exactly because the contract was tight.

### `LLMProvider` Protocol as the load-bearing seam

Designed in Phase 2, the seven-method `Protocol` survived four more phases and the addition of two adapters in Phase 6 with one signature addition (`summarize_role`). The decision to gate it behind `RecordingProvider` from day one paid off twice: once when Phase 5 wired token usage through a contextvar without touching the business layer, and again when Phase 6's cost panel could just look up the active provider's label without knowing what kind of adapter sat behind it.

### MockProvider as the default in tests

Backend tests grew from 3 (Phase 1) to 206 (Phase 6) with zero LLM-call latency in CI. The shape — deterministic stubs per method, with `set_response` overrides — meant tests stayed fast even as features piled on. Anyone building a similar agent in this style: write the mock first, then the real adapter.

### Migrations as a forcing function

Five migrations, each landing the schema for that phase's data. When `profile_version` rolled out in Phase 4, the same column landed on `application_materials` in Phase 5 to invalidate cached generations on profile edits. Both consumed the same field through the same lookup. Without the discipline of "one migration per phase" we would have shadowed a JSON blob and regretted it.

### Versioned `.md` prompts with Provider Notes

Prompts as files, loaded by name, with a "Provider Notes" section that calls out adapter-specific caveats next to the prompt itself. Phase 6's Ollama adapter lit up when this paid off: smaller models drifting on JSON shape was already documented in the `score_job.md` Provider Notes section. The fix — drop a few-shot example — is now a per-prompt knob waiting to be wired.

## What didn't work (or worked less well than hoped)

### Format-only CI failures

Two phases (3 and 4) burned cycles on `ruff format --check` failing in CI after `ruff check` passed locally. The fix — adding `format --check` to the documented pre-push contract in `CLAUDE.md` — should have happened earlier. Cost: maybe 30 min total over both incidents, but more importantly the cognitive overhead of "why did CI fail when my pre-commit hook ran clean."

### The crawler is the weak link

Phase 4's LinkedIn scraper was always going to be fragile (ADR-0006 makes that explicit). It works against today's DOM and will break the day LinkedIn ships a layout change. The fallback — paste-URL crawling — is the actually-reliable path. If we'd known we'd ship as a desktop app first, the crawler might have been deferred entirely in favour of a browser extension or a "save this job" bookmarklet. Lesson: when a path is fragile by design, ship the fallback as the primary affordance, not the secondary.

### PyInstaller bundling deferred too long

Decision in Phase 1 to defer sidecar bundling to Phase 6 was right *for that phase* — it would have eaten Phase 1's budget and we had no real product to ship yet. But it left the dev experience permanently asymmetric: every contributor had to remember to start `uv run uvicorn` separately. By Phase 4 we'd built up enough muscle memory that `pnpm tauri dev` felt complete, which made the eventual "the prod build needs a different launch path" landing in Phase 6 jarring. If I were doing it again I'd land a minimal PyInstaller spec in Phase 1 — even if it only worked on one platform — to pin the constraint into every adapter from day one.

### Generation progress in an in-process dict

Both `services/crawl_progress.py` and `services/generation_progress.py` keep their state in a process-local dict. Restart the backend, lose your in-flight task. We documented the constraint and shipped anyway, but if a real user reports lost progress mid-generation the fix involves promoting both to a small SQLite table, refactoring the polling endpoints, and deciding what "task lost" looks like in the UI. Cheap to fix once, expensive to put off forever.

### `summarize_role` deferral was the right call but only barely

Phase 5 deferred the synthesised role explanation because adding a method to `LLMProvider` mid-phase would have rippled into every existing adapter. Phase 6 picked it up cleanly because it was already touching every adapter for the new ones. **But** the deferral note in `CURRENT_PHASE.md` had to be re-read carefully when Phase 6 started — it was easy to miss. If we'd had a `docs/deferrals.md` that tracked Phase-N → Phase-N+1 carryover in one place, the handoff would have been cleaner.

## What we'd do differently

1. **Land a CI-mirror script.** A single `make ci-local` (or `pnpm ci-mirror`) that runs the exact backend + frontend checks CI runs would have prevented both format-only failures and saved real time on every push. The bullets in `CLAUDE.md` are documentation; a script would be enforcement.
2. **Ship a `tools/devtest` that tests provider switching round-trip.** Phase 6 spent meaningful time validating that switching from `mock` → `anthropic_api` → `claude_code` → `ollama` and back works without restart. Most of that validation is now scattered across unit tests; a single end-to-end "switch every provider in sequence" test would catch interface drift faster than per-adapter unit tests.
3. **Bundle observability earlier.** `RecordingProvider` landed Phase 3, token usage landed Phase 5, the Settings stats panel only got real data Phase 6. If we'd wired the panel against fake stats in Phase 3 we'd have caught the columns-but-no-data state earlier and shipped meaningful telemetry by Phase 4.
4. **Treat the eval harness as load-bearing, not a nice-to-have.** Phase 4's goldset (20 entries) is the right size for a single reviewer to label by hand; running it against the mock provider is structurally meaningful but the numbers aren't real. We never integrated `make eval` into a recurring schedule. If this project continues, a weekly scheduled run against the real API plus a PR comment with eval deltas would close the loop.
5. **Pin Tauri sidecar binaries to a target-triple suffix from day one.** The Phase 6 release workflow had to rename the PyInstaller output for each platform; this is convention, not Tauri's fault, but it would have been cheaper to bake the convention into a pre-build hook in `tauri.conf.json` from the start.

## Lessons for the next project

- **Local-first is a discipline, not a feature.** Every "could we just call out to a service" temptation has to be answered "no" the first time it comes up; once one cloud dependency lands, the architecture rationalisation gets easier each time. We held the line; if we'd let one slip we'd have ended up with three.
- **Adapters should publish through context, not return value.** The `llm.usage` contextvar pattern (Phase 5) was the cleanest way to ship token counts through `RecordingProvider` without changing every adapter's return shape. Adopt the same pattern for any other "metadata about the call" that doesn't belong in the typed result.
- **Subagents earn their keep on independent searches, not on multi-step plans.** During this project, single Claude conversations with tight prompts and small tool budgets consistently outperformed delegating to subagents for complex tasks — but parallel `Explore` subagents were great for "where is X used across the repo?" questions. The lesson isn't that subagents are bad; it's that they're a tool for breadth, not depth.
- **Postmortems land best with concrete examples.** This document is more useful than "things went well, things went poorly" because every claim has a phase, a file, or a commit behind it. The next project should write its postmortem in real-time, one bullet per phase, instead of trying to remember everything at the end.

## Closing

We shipped the MVP we set out to ship. Six phases, a four-person team, and one persistent agent. The product runs end-to-end against four providers on three operating systems, with type-safe code on both sides, a real eval harness, and an accessibility audit that's honest about what it didn't do.

The strong-final-touch advice from the Phase 6 spec — "this is for the documentation grade" — undersells what postmortems are for. The grade is incidental; the value is the next project starting with a sharper picture of what to do differently. That's what's above.
