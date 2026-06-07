# Phase 5 — Application Materials, Dashboard & Interview Prep — MVP (shipped in v0.1.1)

**Status:** ✅ DONE

## Scope

Aus einem Feed-Job Bewerbungsmaterialien generieren (Company-Research →
CV-Tailoring → Anschreiben), ein Dashboard über alle Bewerbungen und ein
Interview-Prep-Panel mit Fragenbank + Practice-Modus.

Spec: `.claude/specs/PHASE_5_applications.md`

## Real erledigt

- Migration `0005_phase5_application_materials.py`: `source_meta_json` +
  `profile_version` auf `application_materials`, Tabelle `company_briefs`
  (case-insensitive unique `company_lower`), Tabelle `practice_attempts`.
- `services/application_service.py` — Apply-Pipeline (research → tailor CV →
  cover letter) mit zwei Cache-Schichten: Company-Briefs nach
  `lower(company)`, CV/Anschreiben nach `(application_id, type, profile_version)`.
- `services/generation_progress.py` (spiegelt `crawl_progress`).
- `api/routes/applications.py` — 11 Endpoints für Apply/Dashboard/Interview;
  Status-Union `saved | applied | skipped | interview | offer | rejected`.
- Kostentracking: `llm/usage.py` (contextvar), `AnthropicAPIAdapter`
  publiziert `response.usage`, `RecordingProvider` persistiert tokens_in/out;
  `services/pricing.py` + `services/cost_service.py`; `GET /api/stats/cost`
  und `/api/stats/provider`.
- Frontend: `applications/GeneratePage.tsx` (Generierung + Inline-Edit des
  Anschreibens), `Dashboard.tsx` (filter-/sortierbare Tabelle),
  `ApplicationDetail.tsx`, `InterviewPrep.tsx` (Fragenbank + Practice gegen
  `evaluate_answer`). Settings bekommt ein Cost-Panel.

PR: #6 (`feat/phase-5-applications`)

## Offen

- **Interview-Prep-Discoverability** (Issue #32, offen): der Interview-Prep-Tab
  ist bis `status='applied'` versteckt — Bruch in der Auffindbarkeit.

## Out-of-scope / Deferrals

- **Synthetisierte Rollen-Erklärung** (§5.6) → Phase 6 (würde sonst alle
  Adapter mitten in der Phase um eine Methode erweitern).
- **Pricing-Raten** in `services/pricing.py` sind Platzhalter (Stand Jan 2026).
- **Generation-Progress** in in-process Dict (resettet bei Neustart).
