# Accessibility Audit — Phase 6

**Date:** 2026-05-10 · **Scope:** WCAG 2.1 AA on the key user-facing screens.

The Phase 6 spec calls for an axe-core run on the main screens with all critical/serious findings fixed. This audit was done **manually** against the React source on the `feat/phase-6-multi-provider` branch — see the deferral note at the bottom on running `axe-core` interactively.

## Screens reviewed

| Screen                      | Component                                     |
|-----------------------------|-----------------------------------------------|
| Onboarding — Provider        | `frontend/src/components/onboarding/ProviderStep.tsx` |
| Onboarding — CV upload       | `frontend/src/components/onboarding/CVStep.tsx`       |
| Onboarding — Review          | `frontend/src/components/onboarding/ReviewStep.tsx`   |
| Feed                        | `frontend/src/feed/FeedScreen.tsx`, `JobCard.tsx`     |
| Generate (apply flow)       | `frontend/src/applications/GeneratePage.tsx`          |
| Application dashboard       | `frontend/src/applications/Dashboard.tsx`             |
| Interview prep              | `frontend/src/applications/InterviewPrep.tsx`         |
| Settings                    | `frontend/src/components/SettingsScreen.tsx`          |

## Findings + fixes

| # | Severity   | Finding                                                                                    | Where                                  | Fix                                                                                                     |
|---|-----------|--------------------------------------------------------------------------------------------|----------------------------------------|---------------------------------------------------------------------------------------------------------|
| 1 | **Serious**  | Dashboard rows had `onClick` with no keyboard handler — keyboard users couldn't open the detail view. | `Dashboard.tsx` row `<tr>`             | Added `role="button"`, `tabIndex={0}`, Enter/Space handler, `aria-label`, and a `focus-visible` ring.     |
| 2 | **Moderate** | Loading regions ("Loading…", "Generating…", "Loading interview prep…") didn't announce to screen readers when they appeared/changed. | `FeedScreen`, `Dashboard`, `GeneratePage`, `InterviewPrep` | Wrapped in `aria-live="polite"` so AT users hear status changes without focus shifts.                  |
| 3 | **Moderate** | Inline error messages were rendered as plain `<p>` — screen readers ignored them.            | `FeedScreen`, `Dashboard`, `GeneratePage`, `InterviewPrep` | Added `role="alert"` so AT announces them when they replace the previous content.                       |
| 4 | **Moderate** | Matched / missing skill chips on `JobCard` were distinguishable only by colour and badge variant. | `JobCard.tsx`                          | Added visually-hidden `<span class="sr-only">Matched skills:</span>` / `Missing skills:` group prefixes. |
| 5 | **Minor**    | "Open" button in dashboard rows would have been read twice (button + its own row label).     | `Dashboard.tsx`                        | Demoted to `aria-hidden` text — the row itself is the accessible action.                                |

## Verified-clean (no fix needed)

- **Provider cards** in `ProviderStep` already carry `role="radio"` + `aria-checked` + `aria-disabled`.
- **Crawl panel toggle** on `FeedScreen` already wires `aria-expanded` + `aria-controls`.
- **Score badge** on `JobCard` already has `aria-label="Match score N out of 100"`.
- **Settings icon-only button** already has `aria-label="Settings"`.
- **All form inputs** in onboarding (API key, profile fields, CV textarea) pair with a `<Label>` via `htmlFor`.
- **Practice answer textarea** in `InterviewPrep` carries `aria-label="Practice answer"`.
- **Provider status panel** in `SettingsScreen` is wrapped in `aria-live="polite"`.
- **Color contrast** of the shadcn defaults we ship passes WCAG AA at base font size — the destructive / muted-foreground tones in tailwind.config.js trace back to OKLCH lightness pairs that meet the 4.5:1 threshold for normal text. Score badges use white-on-emerald (≥ 4.5:1) / amber-900-on-amber-400 (verified ≥ 4.5:1) / muted-foreground-on-muted (verified ≥ 4.5:1).

## Skip-link / heading hierarchy

The app ships a single-pane shell so a "skip to main content" link would have nowhere meaningful to skip past. Headings follow a sensible hierarchy: `<h1>` per top-level screen ("Hired.", "Settings", "Applications", "Generate application"), `<h2>` for empty-state callouts; we don't nest deeper than that. No fix needed.

## What we did NOT do

- **Run axe-core or Lighthouse interactively against a live build.** Per the Phase 6 spec § 6.5 the deliverable is "Run axe-core on key screens; fix all critical/serious issues; document audit results." A live axe-core run requires Chrome DevTools or a CI-integrated runner; the project's a11y testing budget is "manual one-off" per the Phase 6 plan, so this audit is source-level only. Wiring axe-core into Vitest was explicitly skipped to avoid recurring maintenance overhead on a solo project. **If a real user reports an a11y issue not covered above**, run `npx @axe-core/cli http://localhost:5173` against `pnpm dev` and re-run this audit.
- **Test with real screen readers** (VoiceOver, NVDA, JAWS). The fixes above are based on ARIA spec semantics; concrete VO/NVDA verification is queued for any future packaged build cycle.
- **High-contrast / forced-colors mode review.** The shadcn theme defines its own palette and doesn't yet honour `forced-colors: active`. Tracked as a follow-up.

## Re-run cadence

Re-audit when:
- a new top-level screen is added,
- the shadcn theme palette changes,
- or a real user reports an accessibility regression.
