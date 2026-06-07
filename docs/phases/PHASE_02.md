# Phase 2 — LLM Provider Layer — MVP (shipped in v0.1.1)

**Status:** ✅ DONE

## Scope

Die `LLMProvider`-Abstraktion als Herz der App: ein Protocol, ein
deterministischer `MockProvider` für Tests und der erste echte Adapter
gegen die Anthropic-API. Business-Logik sieht ausschließlich das Interface.

Spec: `.claude/specs/PHASE_2_llm_layer.md`

## Real erledigt

- `LLMProvider`-Protocol (`backend/llm/base.py`) mit sieben Methoden:
  `parse_cv`, `score_job`, `research_company`, `tailor_cv`,
  `generate_cover_letter`, `generate_interview_questions`, `evaluate_answer`.
- Pydantic-Typen (`backend/llm/types.py`): Profile, Job, ScoreResult,
  CompanyBrief, CoverLetter, InterviewQuestion, AnswerFeedback (+ Helfer).
- `MockProvider` (`backend/llm/mock.py`) — deterministische Stubs, keine
  Netzwerkaufrufe, `set_response(method, value)` für Tests.
- `AnthropicAPIAdapter` (`backend/llm/anthropic_api.py`) über das offizielle
  `anthropic`-SDK. API-Key aus OS-Keychain oder `ANTHROPIC_API_KEY`.
  Default-Modell `claude-opus-4-7` für jede Aufgabe (Per-Task-Split → Phase 6).
- OS-Keychain-Helfer (`backend/llm/credentials.py`) via `keyring`,
  Service-Name `dev.hired.app`. Loggt nie Werte.
- Provider-Factory in `backend/llm/__init__.py`, liest `provider`/`model`
  aus `app_config`, cached den Provider, `reset_provider_cache()` für Wechsel.
- Migration `0002_seed_default_model.py` (Default-Modell-Row in `app_config`).
- Pytest-Marker `integration` registriert; CI-Default überspringt den
  Integrationstest. `eval/goldset.json` mit 3 Start-Beispielen.

PR: #2 (`feat/phase-2-llm-layer`) · ADR: `docs/adr/0005-api-first-llm-provider.md`

## Offen

Keine — Phase abgeschlossen.

## Out-of-scope / Deferrals

- **Kleineres Modell** für klassifikationsartige Tasks (`score_job`,
  `evaluate_answer`) → Phase 6 Kostenoptimierung.
- **ClaudeCodeAdapter / OllamaAdapter** → Phase 6 (ADR-0005).
- Volle Goldset-Erweiterung → Phase 4.
