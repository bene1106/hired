# Phase 8 — Interactive Interview Coach + Editable Preferences — v0.3.0

**Status:** ✅ DONE — getaggt `v0.3.0` (2026-05-21), stabilisiert bis `v0.3.5`

## Scope

Ein interaktiver Interview-Coach als Streaming-Chat, der neben der
Phase-5-Fragenbank im Interview-Prep-Tab koexistiert (Practice ist Default),
plus eine in-place editierbare Preferences-Card in Settings. Das
`LLMProvider`-Interface bekommt seine erste neue Methode seit Phase 6:
`interview_chat_stream(messages, role_context) -> Iterator[str]`.

ADR: `docs/adr/0009-phase-8-interactive-coach.md`

## Real erledigt (PR-Slices)

- **PR A** (#22) — Provider-Streaming: `interview_chat_stream` über alle vier
  Adapter (Mock, AnthropicAPI, Ollama, ClaudeCode), `ChatMessage`/`ChatRole`,
  Prompt `prompts/interview_coach.md`, `RecordingProvider` umhüllt den Iterator.
- **PR B** (#23) — Chat-Endpoint + Sessions-API: fünf Endpoints unter
  `/api/applications/{id}/interview/sessions/*` (create/list/get/delete +
  SSE-streaming POST). Nutzt die bestehende `InterviewSession`-Tabelle —
  **keine DB-Migration**.
- **PR C** (#24) — Chat-UI + SSE-Consumer: `InterviewChat` (fetch +
  `ReadableStream`, nicht `EventSource`), Session-Sidebar, `InterviewPanel`
  mit Practice↔Coach-Toggle.
- **PR D** (#25) — editierbare Preferences in Settings (Backend unverändert).
- **PR E** (#26) — Politur + Release: ADR-0009, CHANGELOG, Version-Bump 0.3.0,
  Tag `v0.3.0`.

## RC-Smoke-Hotfixes (v0.3.1 – v0.3.5, Teil dieser Phase)

| Version | PR | Inhalt |
|---------|----|--------|
| v0.3.1 | #27 | Prod-DB-Guard (`resolve_db_url()` warnt bei Default-Pfad ohne `HIRED_DB_URL`); CLAUDE.md-Regel. Kein Feature-Change. |
| v0.3.2 | #28 | Drei InterviewChat-UI-Bugs (unsichtbare User-Bubble `bg-ink text-paper`, Session-Title-Overflow, Confidence-Slider als echtes Input). |
| v0.3.3 | #29 | Cold-Start-Regression: `AppGate` pollt 60× / 1s statt 8× linear. |
| v0.3.4 | #30 | Sidecar-Error-Visibility: `log_unhandled_exceptions`-Middleware + namespace-scoped Logging; Practice-Tab dropt einzelne kaputte Cached-Rows statt 500. |
| v0.3.5 | #31 | Crawler-Auto-Rescore (`rescore_job_ids`), `GET /api/jobs/scoring-status`, `POST /api/jobs/rescore`, `LLMAuthError`→401, Feed-Empty-State-CTA, globaler 401-Banner. |

## Post-Phase-8-Point-Releases (v0.3.6 – v0.3.7)

Diese Releases gehören zu **keiner** nummerierten Phase — es sind
Wartungs-/Punkt-Feature-Releases nach Phase 8 und vor dem geplanten Phase 9.

- **v0.3.6** (PR #34/#35) — **OpenAI Codex CLI Provider**: neuer
  `CodexCLIAdapter` (shellt zu `codex exec --json` im Read-only-Sandbox),
  als provider-agnostische „Experimental"-Option in Onboarding + Settings.
  ADR: `docs/adr/0010-codex-cli-provider.md`.
- **v0.3.7** (PR #36/#39/#40) — **Company-Research mit echter Web-Suche**
  (statt Modell-Gedächtnis; Anthropic-Web-Search-Tool, Codex/Claude-Code
  Web-Search; Ollama behält Disclaimer). Plus UX-Fixes: providergenaue
  Cost-Billing-Note, Provider-Switch landet zurück in Settings statt im
  vollen Onboarding, Onboarding-CV-Dropzone-Highlight beim Drag.

## Offen

- Konsolidierter Tauri-/Installer-Smoke auf einem aktuellen RC (WebView2-SSE-
  Consumer ist die einzige nicht headless verifizierbare Risikofläche).
- **Release-Status:** `v0.3.7` ist aktuell nur als **Draft**-Release vorhanden;
  öffentliches „Latest" ist **v0.3.6**. Vor einem Public-Flip ist der Draft zu
  publizieren.
- (Optional) Aktualisierte Screenshots nach `docs/screenshots/` für die README.

## Out-of-scope / Deferrals

- **Streak / answered-today / Slider-Persistenz** — bewusst weggelassen
  (ADR-0009; Slider ist UI-only, per-session).
