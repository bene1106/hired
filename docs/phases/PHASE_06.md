# Phase 6 — Multi-Provider, Packaging & Polish — v0.1.1

**Status:** ✅ DONE

> Versionshinweis: Die Phase-6-Spec und das damalige `CURRENT_PHASE.md`
> sprachen von einem `v1.0.0`-Releaseziel. Real ausgeliefert wurde die
> MVP-Komplettierung als **`v0.1.1`** (2026-05-17, erster öffentlicher Tag).
> Es gibt keinen `v1.0.0`-Tag. Der Phase-6-Hotfix-PR hieß intern
> `hotfix/v1.0.1-sidecar-fetch` (PR #8), wurde aber als `v0.1.1` veröffentlicht.

## Scope

`ClaudeCodeAdapter` + `OllamaAdapter` als First-Class-Optionen,
PyInstaller-Packaging des Sidecars in den Tauri-Build, Release-Pipeline,
Doku- und Accessibility-Politur. Damit ist das MVP über alle sechs Phasen
feature-complete.

Spec: `.claude/specs/PHASE_6_polish.md`

## Real erledigt

- `llm/claude_code.py` — Subprocess-Wrapper um die lokale `claude`-CLI;
  `llm/ollama.py` — HTTP-Client gegen `localhost:11434/api/chat`
  (default `qwen2.5:14b`). Factory in `llm/__init__.py` baut beide; der
  Phase-3-Selektierbarkeits-Guard entfällt.
- `LLMProvider.summarize_role` + Prompt `prompts/summarize_role.md` (löst das
  Phase-5-Deferral; Cache auf `interview_questions.source_meta_json`).
- `GET /api/setup/providers` liefert UI-Metadaten (Label, `is_experimental`,
  `requires_api_key`, `default_model`); `/select-provider` persistiert Modell.
- Onboarding `ProviderStep` + `SettingsScreen` mit Live-Provider-Status
  (`/api/stats/provider`) und „Experimental"-Badge (ADR-0007 R-01).
- `backend/sidecar.py` + `hired-sidecar.spec` (PyInstaller); Tauri-Wiring
  (`externalBin`, `tauri-plugin-shell`, Spawn in `lib.rs`).
- `.github/workflows/release.yml` — Matrix-Build mac/linux/win auf `v*`-Tags,
  liefert Installer in ein Draft-Release.
- Doku: `docs/install/{macos,windows,linux}.md`, README-Rewrite,
  `docs/architecture.md`, `docs/api.md` + `api.openapi.json`,
  Accessibility-Pass (`docs/accessibility-audit.md`), `docs/postmortem.md`.

### v0.1.1-Hotfix (Teil dieser Phase)

- **CORS-Fix:** Packaged App erreichte ihr eigenes Backend nicht
  (`http://tauri.localhost`-Origin fehlte in der Allowlist).
- **Stale-Sidecar-Reaping** + Single-Instance-Guard; Release-Logging.

PR: #7 (`feat/phase-6-multi-provider`), #8 (Hotfix v0.1.1) ·
ADR: `docs/adr/0007-multi-provider-rollout.md`

## Offen

Keine — Phase abgeschlossen.

## Out-of-scope / Deferrals

- **Code-Signing** — Builds bleiben unsigniert; Install-Docs decken die
  Gatekeeper-/SmartScreen-Workarounds ab.
- **Demo-Video, finaler Bug-Bash** — bewusst übersprungen (Owner-Entscheid).
- **Stretch-Goals** (Salary-Benchmark, Rejection-Pattern-Analyse,
  Multi-Language) — verschoben, ggf. als Standalone-Issues.
