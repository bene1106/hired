# Phase 3 — Profile Setup & Onboarding — MVP (shipped in v0.1.1)

**Status:** ✅ DONE

## Scope

Erster Einstiegspunkt für neue Nutzer: ein fünfstufiger Onboarding-Wizard
(Welcome → Provider → CV-Upload → Review → Done), CV-Parsing und der
Settings-Screen hinter dem Wizard.

Spec: `.claude/specs/PHASE_3_profile.md`

## Real erledigt

- Migration `0003_phase3_profile_and_call_log.py`: `profile` auf plurale
  JSON-Spalten umgebaut (`target_roles_json`, `target_locations_json`,
  `priorities_json`) + neue Tabelle `provider_call_log`.
- `RecordingProvider` umhüllt jeden `LLMProvider` aus `get_provider()`; eine
  Zeile pro Aufruf in `provider_call_log` (best-effort).
- Provider-Detection (`services/provider_detection.py` +
  `POST /api/setup/detect-providers`): env + Keychain für Anthropic,
  `shutil.which` für Claude Code, `/api/tags` für Ollama.
- Provider-Test (`services/provider_setup.py` + `POST /api/setup/test-provider`)
  und `POST /api/setup/select-provider` (committet Wahl, speichert Key im
  Keychain, resettet Provider-Cache).
- `services/cv_service.py` — pypdf-Extraktion, 5 MB Upload-Guard, 30 KB
  Pre-LLM-Truncation, Upsert. `POST /api/profile/cv` (Text) und
  `/api/profile/cv/upload` (PDF). `GET`/`POST /api/profile` (partielles Upsert).
- `DELETE /api/data/all` — truncatet alle User-Tabellen, re-seedet
  `app_config`, löscht den Anthropic-Key aus dem Keychain. Idempotent.
- Frontend-Fundament: React Router v6, typed API-Client (`src/lib/api.ts`),
  msw-Testserver, shadcn-Primitives. Onboarding-Wizard + App-Shell + Settings.

PR: #3 (`feat/phase-3-profile`)

## Offen

Keine — Phase abgeschlossen.

## Out-of-scope / Deferrals

- **ClaudeCodeAdapter / OllamaAdapter** auswählbar → Phase 6 (Detection ist
  informativ vorhanden, `select-provider` gibt für diese 400 zurück).
- **Provider-Stats-Panel** (Latenz/Call-Count) in Settings → Phase 4.
- **tokens_in/out** in `provider_call_log` bleiben NULL → Phase 4/6.
