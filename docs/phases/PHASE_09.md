# Phase 9 — Feedback Loop — v0.4.0 (Ziel)

**Status:** 🟡 PLANNED — noch **nicht** im Code

> Verifiziert: Es existiert weder eine `job_feedback`-Tabelle noch ein
> `/api/jobs/{id}/feedback`-Endpoint im Backend (Stand HEAD = v0.3.7).
> Diese Phase ist Planung, kein ausgelieferter Code.

## Scope (geplant)

Ein Feedback-Loop, mit dem Nutzer das Job-Scoring durch direktes Signal
verbessern — der erste Schritt Richtung lernendes Ranking. Quelle des
Scopes: Phase-7-Deferrals (CHANGELOG „No up/down feedback (Phase 9)") und
Projekt-Memory.

- **Thumbs up/down** am Job-Card (explizites Relevanz-Signal pro Job).
- **`POST /api/jobs/{id}/feedback`** — nimmt das Signal entgegen.
- **`job_feedback`-Tabelle** — persistiert Feedback (neue Migration `0006`).
- **Score-Rework** — Feedback fließt in das Re-Scoring/Ranking ein.
- **Unread-Badges** — markieren neue/ungesehene Feed-Items.

## Real erledigt

Nichts — Phase noch nicht begonnen.

## Offen

Gesamter Scope (siehe oben). Vor dem Start: Phase-Spec unter
`.claude/specs/PHASE_9_feedback.md` schreiben (existiert noch nicht) und
Akzeptanzkriterien festlegen.

## Out-of-scope / Deferrals

- Voll-autonome Auto-Discovery / Auto-Submit — gehört in Phase 11–12
  (siehe `docs/PHASE_10_VISION.md`).
