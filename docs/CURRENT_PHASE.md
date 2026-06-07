# Current Phase — Übersicht

> **Single Source of Truth** für den Phasen-Stand. Detail-Checklisten je
> Phase liegen in `docs/phases/PHASE_NN.md` — diese Datei bleibt schlank.

## Aktueller Stand (verifiziert)

- **Code-Stand (HEAD):** `v0.3.7` — konsistent in `frontend/package.json`,
  `src-tauri/tauri.conf.json` und `src-tauri/Cargo.toml`.
- **Öffentliches Release („Latest"):** **`v0.3.6`**.
- **`v0.3.7` ist aktuell nur ein Draft-Release** (noch nicht publiziert);
  zusätzlich existiert ein `v0.3-stable`-Pre-Release.
- **Letzte abgeschlossene Phase:** **Phase 8** (Interactive Coach), danach
  zwei Post-Phase-8-Point-Releases (v0.3.6 Codex-Provider, v0.3.7
  Web-Search-Company-Research + UX-Fixes).
- **Nächste Phase:** **Phase 9 — Feedback Loop** (geplant, noch nicht im Code).

## Phasen-Tabelle

| Phase | Fokus | Versionsziel | Status | Doc |
|-------|-------|--------------|--------|-----|
| 1 | Foundation (Tauri+FastAPI, Schema, CI) | MVP → v0.1.1 | ✅ DONE | [PHASE_01](phases/PHASE_01.md) |
| 2 | LLM-Provider-Layer + MockProvider + Anthropic-Adapter | MVP → v0.1.1 | ✅ DONE | [PHASE_02](phases/PHASE_02.md) |
| 3 | Profile-Setup + Onboarding-Wizard | MVP → v0.1.1 | ✅ DONE | [PHASE_03](phases/PHASE_03.md) |
| 4 | Job-Ingestion + Scoring + Feed | MVP → v0.1.1 | ✅ DONE | [PHASE_04](phases/PHASE_04.md) |
| 5 | Application-Materials + Dashboard + Interview-Prep | MVP → v0.1.1 | ✅ DONE | [PHASE_05](phases/PHASE_05.md) |
| 6 | Multi-Provider + Packaging + Polish | v0.1.1 | ✅ DONE | [PHASE_06](phases/PHASE_06.md) |
| 7 | Frontend-Redesign (Design-System, Kanban) | v0.2.0 | ✅ DONE | [PHASE_07](phases/PHASE_07.md) |
| 8 | Interactive Coach + editierbare Preferences | v0.3.0 (→ v0.3.5) | ✅ DONE | [PHASE_08](phases/PHASE_08.md) |
| — | Point-Releases: Codex-CLI-Provider; Web-Search-Research + UX-Fixes | v0.3.6 – v0.3.7 | ✅ DONE | [PHASE_08](phases/PHASE_08.md) |
| **9** | **Feedback Loop (thumbs up/down, `job_feedback`, Score-Rework, Unread-Badges)** | **v0.4.0** | 🟡 **PLANNED** | [**PHASE_09**](phases/PHASE_09.md) **← WIR SIND HIER (nächste Phase)** |
| 10 | Email-Reading (Gmail) + Status-Auto-Detect | — | 🔵 PLANNED (Vision) | [PHASE_10](phases/PHASE_10.md) |
| 11 | Auto-Crawl (Newsletter, RSS, LinkedIn-Alerts) | — | 🔵 PLANNED (Vision) | [PHASE_11](phases/PHASE_11.md) |
| 12 | Auto-Submission (Easy Apply + Form-Automation) | — | 🔵 PLANNED (Vision) | [PHASE_12](phases/PHASE_12.md) |
| 13 | Auto-Reply (Recruiter-Kommunikation) | — | 🔵 PLANNED (Vision) | [PHASE_13](phases/PHASE_13.md) |

Legende: ✅ DONE · 🟡 PLANNED (konkret, nächster Schritt) · 🔵 PLANNED (Vision, eigenes Handoff folgt)

## Offene Punkte am aktuellen Stand

- **Release:** `v0.3.7`-Draft publizieren bzw. Public-Flip entscheiden
  (öffentliches Latest ist noch v0.3.6). Tauri-/Installer-Smoke auf dem RC
  (WebView2-SSE ist die einzige nicht headless verifizierbare Risikofläche).
- **Offene Issues:** #32 (Interview-Prep-Tab versteckt bis `applied`),
  #21 (Score auf ApplicationSummary → MatchRing), #20 (Title-Parsing),
  #19 (Company-Parser → CompanyMark „?").
- **Phase 9** vor Start: Spec `.claude/specs/PHASE_9_feedback.md` schreiben.

## Versionsverlauf (Phasen → Releases)

| Release | Datum | Inhalt |
|---------|-------|--------|
| v0.1.1 | 2026-05-17 | MVP feature-complete (Phasen 1–6) + CORS/Sidecar-Hotfix |
| v0.2.0 | 2026-05-19 | Phase 7 — Frontend-Redesign |
| v0.3.0 | 2026-05-21 | Phase 8 — Interactive Coach + Preferences |
| v0.3.1–v0.3.5 | 2026-05-21 | Phase-8-RC-Smoke-Hotfixes |
| v0.3.6 | 2026-05-31 | Codex-CLI-Provider (ADR-0010) — **aktuelles Public Latest** |
| v0.3.7 | 2026-05-31 | Web-Search-Company-Research + UX-Fixes — **Draft** |

> Hinweis: Die Phase-6-Spec sprach historisch von `v1.0.0`; real ausgeliefert
> wurde die MVP-Komplettierung als `v0.1.1`. Es gibt keinen `v1.0.0`-Tag.

## Verwandte Dokumente

- Vision (Phasen 10–13): `docs/PHASE_10_VISION.md`
- Phase-7-Autonomous-Completion-Spec: `docs/PHASE_7_AUTONOMOUS_COMPLETION.md`
- Architektur: `docs/architecture.md` · API: `docs/api.md`
- Changelog: `docs/CHANGELOG.md`
