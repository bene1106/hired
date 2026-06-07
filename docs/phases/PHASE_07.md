# Phase 7 — Frontend Redesign — v0.2.0

**Status:** ✅ DONE — getaggt `v0.2.0` (2026-05-19)

## Scope

Reiner Frontend-Redesign auf die neue warme Off-White / Deep-Ink /
Muted-Green-Designsprache, inkl. Light- + Dark-Mode. Backend und
Business-Logik bleiben unangetastet. Umgesetzt in den Slices PR A–H.

Spec: `docs/PHASE_7_AUTONOMOUS_COMPLETION.md` (+ originales Phase-7-Handoff)

## Real erledigt (PR-Slices)

- **PR A** (#10) — Design-Foundation: Token-System, Type-Stack (Inter Tight ·
  JetBrains Mono · Fraunces · Archivo, self-hosted woff2), `useTheme`-Hook,
  Brand-Assets, `data-theme` treibt Tokens + shadcn.
- **PR B** (#12) — App-Shell + Sidebar (fixed 244px, datengetriebene Nav).
- **PR C** (#13) — Onboarding-Redesign (5-Step-Wizard restyled, ehrliche Copy).
- **PR D** (#14) — Feed + Job-Card: `MatchRing` + `CompanyMark`, Skill-Chips.
- **PR E** (#15) — Job-Detail + Materials zu einem `MaterialsScreen` vereint.
- **PR F** (#16) — Dashboard → 5-Spalten-Kanban (Saved → Applied → Interview
  → Offer → Rejected) mit Drag-and-Drop; inkl. Tauri-DnD-Fix
  (`dragDropEnabled: false`).
- **PR G** (#17) — Interview-Prep + Settings restyle (kein Verhalten geändert).
- **PR H** (#18) — Politur + Release: `Toast` (Save-Feedback),
  `SuggestionRenderer` (CV-Tab), Regenerate-Loading-State, Fraunces-Preload;
  Version-Bump auf 0.2.0, CHANGELOG, Tag `v0.2.0`.
- Zwischendrin: #9 (Design-Reference), #11 (Flaky-Settings-Test-Fix).

ADR: `docs/adr/0008-phase-7-frontend-redesign.md`

## Offen

Keine — Phase abgeschlossen.

## Out-of-scope / Deferrals

- **Up/Down-Feedback** am Job-Card → Phase 9 (Feedback Loop).
- **Chat-Coach** in Interview-Prep → Phase 8.
- **Editierbare Preferences** → Phase 8.
- **Score auf ApplicationSummary** (würde MatchRing in Kanban/Detail
  ermöglichen) → bewusst weggelassen (Honesty), Issue #21, Phase 10+.
- **Autonomie-Andeutungen** (Agent-Status-Card, „scans every morning")
  bewusst NICHT eingebaut (siehe `docs/PHASE_10_VISION.md`).
