# ADR-0009: Phase 8 — Interactive Interview Coach (Streaming) + Editable Preferences

**Status:** accepted
**Date:** 2026-05-21
**Supersedes:** —
**Builds on:** ADR-0005 (API-first LLM provider), ADR-0007 (multi-provider rollout), ADR-0008 (Phase 7 frontend redesign)

## Context

Phase 7 shipped v0.2.0 — the warm off-white / deep-ink / muted-green design language across every screen, no backend changes. The handoff (§17) explicitly deferred two pieces to Phase 8:

1. **Chat-style interview coach** — replace (or sit alongside) the Phase 5 static question bank with a streaming coach that critiques candidate answers in real time.
2. **Editable Preferences / Priorities** — the design's onboarding-step idea, re-homed to a Settings sub-page.

Phase 8 (v0.3.0) shipped both, plus the first extension to the `LLMProvider` interface since Phase 6.

## Decisions

### D1. Coexist, do not replace, the question bank

Handoff §17 wording was *"replace the static question-bank UI with a chat-style coach"*. We chose **coexistence** instead:

- `InterviewPanel` owns a `Practice` ↔ `Coach` segmented toggle.
- **Default mode is `Practice`** — returning users see the same Phase 5/7 surface.
- The Phase 5 endpoints (`/interview/questions`, `/interview/practice`, `/interview/attempts`) and their tests (`InterviewPrep.test.tsx`, 4 cases) are **unchanged**.

**Why diverge from the handoff:**

- §17 was written before Phase 7 PR G modernised the question bank into the new design language. Today's question bank is a polished, tested artifact — tearing it out would be a regression.
- The question bank has its own value (slow, deliberate, written self-review) distinct from the chat coach (live conversation).
- Tear-out would destroy the `practice_attempts` history users may have accumulated.
- Honest-omission policy: shipping both is honest about what works.

The split is mode-level (toggle), not screen-level (tab), so the user model is "two modes of preparing for one interview" rather than "two unrelated tools."

### D2. Streaming transport: SSE over `fetch` + `ReadableStream`, not `EventSource` or WebSocket

The chat endpoint is `POST /api/applications/{id}/interview/sessions/{sid}/messages`. The reply streams back. The frontend needs progressive token rendering.

Options considered:

- **`EventSource`** — read-only (can't send a POST body), historically quirky in Tauri WebView2.
- **WebSocket** — bi-directional, overkill for one-way streaming, more moving parts (lifecycle, reconnect, framing).
- **HTTP chunked + `fetch` + `ReadableStream`** — what we shipped. Single POST request, response body is a stream, `getReader()` + `TextDecoder` + frame-parsing.

The frame format is SSE-style (`data: {...}\n\n` separators) for ergonomics, but transported over a normal `text/event-stream` chunked HTTP response — not the browser's `EventSource` API. This works in WebView2 without Tauri-config tweaks (verified in jsdom across 4 tests; real WebView2 smoke deferred to v0.3.0 RC).

`X-Accel-Buffering: no` is set on the response to prevent reverse-proxy or webview buffering.

### D3. `LLMProvider` Protocol extension: streaming as a 9th method

`LLMProvider` gained `interview_chat_stream(messages, role_context) -> Iterator[str]`. All four adapters implement it:

- **MockProvider** — yields deterministic chunks driven by the last user turn; `set_response("interview_chat_stream", […])` for tests.
- **AnthropicAPIAdapter** — SDK `messages.stream()` with `text_stream` + `get_final_message()` for usage.
- **OllamaAdapter** — `POST /api/chat` with `stream=true`, parses NDJSON lines, captures usage from the final `done` line.
- **ClaudeCodeAdapter** — `Popen` with `--output-format stream-json --include-partial-messages`, parses `content_block_delta` events. Gracefully falls back to a single `assistant`-event chunk if the installed CLI version doesn't emit partial messages.

`RecordingProvider` gained a `_record_stream` wrapper: measures latency at iterator drain, captures usage after the stream completes (every adapter publishes usage on the final event), writes one `provider_call_log` row per stream — success or mid-stream error.

### D4. Half-write-safe transcript persistence

User turn → persisted **before** the stream starts. Assistant turn → persisted only on clean completion.

A disconnected client never poisons the transcript with a partial reply; the user can retry their question without retyping. The frontend mirrors this contract: on mid-stream error, the empty assistant bubble is dropped, the error surfaces via `role="alert"`, and the user turn stays.

### D5. Multi-session, not one-rolling-session-per-application

The `InterviewSession` table (allocated in Phase 5, unused until now) carries `application_id` + `transcript_json` + `created_at`. Each "New session" button click creates a fresh row. The session sidebar lists them newest-first with a preview (last user message) and turn count. Resume by clicking. Delete via the per-row × button.

This matches the design's "New session" affordance and the mental model "I'll practice three times this week and see my history."

### D6. Confidence slider: UI-only state, no backend persistence

The design's right-side panel had:

- Confidence slider (1–5)
- "Answered today" list
- 14-day streak

The first ships as local React state, reset on session switch. The other two are **deliberately omitted** — there's no backend daily aggregation, and shipping them as static stubs would violate the honest-omission policy established in Phase 7 (MatchRing on Kanban).

If we want confidence persisted later, the path is straightforward: extend `transcript_json.meta`. Out of scope for Phase 8.

### D7. Editable Preferences as a Settings card, not a tab

Flag 3 from the planning conversation: tabs vs. inline card. The current Settings is card-stacked, not tabbed. Restructuring to tabs would churn `SettingsScreen.test.tsx` for no functional gain. The Preferences panel slots in as another Card between Profile and Provider.

Backend: zero changes. Profile already has `target_roles_json`, `target_locations_json`, `target_salary_min`, `priorities_json` since Phase 3, and `PUT /api/profile` accepts those keys.

### D8. Prompt loader now substitutes both system AND user

Pre-Phase-8 prompts (`evaluate_answer.md`, `score_job.md`, etc.) only used `{{}}` placeholders in their user templates. The coach prompt needs `{{role_context}}` substituted into the *system* prompt so it persists across turns.

`PromptTemplate.render()` now interpolates both `system` and `user`. Grepped all 9 prompt files — none use `{{}}` in their system blocks, so the change is a no-op for legacy prompts and a feature for the coach prompt. Behaviour-preserving extension, not a breaking change.

## Consequences

**Good:**
- The Protocol stays the contract every business module talks to. Streaming added without breaking any caller.
- Question bank + chat coach coexist; no data loss, no regression for users who liked the deliberate-prep flow.
- Half-write safety means clients can disconnect mid-stream without poisoning state.
- Preferences are now in-app editable; no need to re-run the onboarding wizard to retune targeting.

**Acceptable trade-offs:**
- `ClaudeCodeAdapter`'s streaming implementation depends on CLI flags (`--include-partial-messages`) that may evolve. We have a graceful fallback path. Spot-check on new CLI versions.
- Confidence slider state is per-session-render only. If a user closes and reopens the chat, the slider resets to 3. Acceptable for v0.3.0; can be persisted in `transcript_json.meta` if a real user complains.
- Real WebView2 SSE smoke is deferred to the v0.3.0 RC. The risk is HTTP response buffering inside the webview; if chunks don't arrive progressively, the fix is likely a Tauri-config tweak, not architectural.

**Honest omissions:**
- Streak / answered-today panel (no backend data).
- Slider persistence (no urgent need).
- Drag-reorderable priorities (textarea-per-line ships value; sortable list is a polish-pass enhancement).
