# ADR-0008: Phase 7 Frontend Redesign — Design Source, Tokens, Component Mapping

## Status: Accepted

## Context

v0.1.1 worked end-to-end but looked like a wireframe. Phase 7 is a pure frontend redesign to a warm off-white / deep-ink / muted-green visual language, shipped as v0.2.0. A design package (static HTML + JSX preview, `design/Hred.v2/`) and a handoff (`design/HANDOFF_PHASE_7_FRONTEND_REDESIGN.md`) defined the target; the handoff's §4/§17/§18 are the settled scope. The constraint was absolute: **no backend or business-logic change** — the LLM provider abstraction, API, and SQLite layer stay untouched.

The design is a *reference*, not a contract. It assumes data the backend doesn't produce (per-job `scoreReasons`, application scores, an autonomous daily agent) and includes features mapped to later phases (chat coach → Phase 8, feedback up/down → Phase 9). The redesign had to adopt the language without importing features that would be dead UI.

## Decision

1. **Design tokens as the single source of truth, dual-namespaced.** Raw design tokens (`--bg`, `--ink`, `--accent`, …) and the shadcn semantic HSL tokens (`--background`, `--primary`, …) both live under one `html[data-theme]` switch; shadcn's `--accent` was rebound to `--accent-ui` to avoid colliding with the design's brand green. shadcn/ui stays the component foundation (handoff §7) — reskinned via tokens, not ripped out.
2. **Self-hosted fonts.** Inter Tight / JetBrains Mono / Fraunces / Archivo ship as local `woff2` (latin subset). No runtime web-font CDN — consistent with local-first and dodging the packaged-build CSP risk (handoff §10).
3. **Sliced into 8 PRs (A–H)** off `main`, merge-commit never squash. A: tokens/fonts/theme/brand. B: shell + sidebar. C: onboarding. D: feed + JobCard. E: GeneratePage + ApplicationDetail merged into one `MaterialsScreen`. F: dashboard → 5-column Kanban. G: interview prep + settings restyle. H: polish + release.
4. **Honest UI over design fidelity where data doesn't exist.** `MatchRing` is omitted on Materials/Kanban (applications carry no score); the sidebar agent-status card, ⌘K, "scans every morning" copy, and design emoji were cut; `RejectionAnalysis` and tone buttons were dropped. No visual stubs (handoff §17, `PHASE_10_VISION.md`).
5. **Test discipline.** Where a real structural change moved the DOM (Materials merge, Kanban) tests were rewritten with every prior behaviour re-asserted and called out; where it didn't (`InterviewPrep.test`, `SettingsScreen.test`) they stayed byte-identical. A pre-existing `SettingsScreen.test` race was fixed first (`waitFor` on loaded content, not the container).
6. **`dragDropEnabled: false` in `tauri.conf.json`.** Tauri v2 defaults it true; the native OS file-drop handler swallowed the Kanban's HTML5 DnD. jsdom couldn't catch it — the lesson recorded for future native-API work.

## Why this shape

- **Dual token namespace** keeps the design files portable verbatim while letting existing shadcn primitives reskin with zero component edits.
- **Slices, not a mega-PR**, kept each change reviewable and CI-bisectable across a redesign that touched every screen.
- **One `MaterialsScreen`** (two thin route adapters) removed the GeneratePage/ApplicationDetail duplication the design implied without changing routes or the `/apply` contract.
- **Omission over fabrication** matches the user's "tools, not toys" bar; a `MatchRing` fed by a fake score teaches users the number is meaningless.

## Consequences

- ✅ Light + dark both ship in v0.2.0 from one attribute switch; brand assets (`HiredMark`/`Wordmark`/`Lockup`/`Stacked`) and shared `MatchRing`/`CompanyMark` are reused across screens.
- ✅ Backend/business logic provably untouched — every slice is frontend-only (plus the one Tauri webview-config line).
- ✅ The redesign exposed real backlog: structured `cv_suggestions` rendering, regenerate/save feedback (shipped in PR H), and backend gaps (unreliable company parser, no score on `ApplicationSummary`) deferred to a separate backend PR / Phase 10 (`PHASE_10_VISION.md`).
- ❌ Materials/Kanban show no match score until the backend joins it onto `ApplicationSummary` (Phase 10).
- ❌ Headless CI cannot drive the Tauri GUI; a consolidated manual Tauri/installer smoke on the v0.2.0 RC remains a human gate (handoff §9-q4/§16).

## Alternatives considered

- **One mega-PR.** Rejected (handoff §5): unreviewable across every screen, no safe rollback.
- **Rip out shadcn for the design's bespoke components.** Rejected (handoff §7): the design components are inline-styled previews, not a library; reskinning shadcn via tokens is less code and keeps a11y/primitives.
- **Migrate Kanban to `@dnd-kit`** when DnD failed in Tauri. Rejected: root cause was a one-line config default, not the HTML5 DnD code; a dependency would have masked a config bug.
- **Keep Google Fonts CDN.** Rejected: violates local-first and risks packaged-build font CSP (handoff §10).

## See also

- `design/HANDOFF_PHASE_7_FRONTEND_REDESIGN.md` — settled scope (§4/§17/§18).
- `docs/PHASE_7_AUTONOMOUS_COMPLETION.md` — autonomous completion spec.
- `docs/PHASE_10_VISION.md` — deferred full-automation vision + backend backlog.
- ADR-0001 — local-first architecture (why self-hosted fonts).
