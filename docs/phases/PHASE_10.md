# Phase 10 — Email-Reading (Gmail API) + Status-Auto-Detect

**Status:** 🔵 PLANNED (Vision) — Komplexität: Medium

> Quelle: `docs/PHASE_10_VISION.md`. Erster Schritt der „Full Automation"-
> Vision. Beeinflusst NICHT den aktuellen PR-Scope.

## Scope (Vision)

- Gmail (OAuth) auf Antworten von Firmen lesen.
- Status-Änderungen parsen: Eingangsbestätigung („Thanks for applying") →
  Absage („move forward with other candidates") → Interview („schedule a call").
- Kanban automatisch aktualisieren.

## Begleitende Backend-Optimierungen (in Phase 7 entdeckt)

Kein Voll-Autonomie-Scope, aber hier sinnvoll andockbar:

- **Score auf `ApplicationSummary`** (JOIN mit `jobs`) → ermöglicht
  `MatchRing` in Kanban-/Detail-Views. Issue **#21**.
- **CompanyMark-Fallback** — Backend-Company-Parser verbessern. Issue **#19**.
- **Title-Parsing-Fix** (z. B. Bitpanda) — generischer Parser-Fix. Issue **#20**.

## Real erledigt

Nichts — Vision-Phase.

## Offen

Gesamter Scope. Eigenes Handoff-Dokument folgt, wenn die Phase startet.

## Out-of-scope / Deferrals

- Auto-Crawl, Auto-Submit, Auto-Reply → Phasen 11–13.
