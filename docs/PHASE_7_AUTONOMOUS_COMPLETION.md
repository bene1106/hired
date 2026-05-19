# Phase 7 Autonomous Completion Spec

## Context

Bene has shifted from "review-each-PR-with-second-opinion-AI" to autonomous completion.
Claude Code now owns the remaining Phase 7 slices end-to-end:
- Plan
- Implement
- Test (CI + lokal smoke-test in Tauri, not just pnpm dev)
- Verify (read own diff for plan adherence)
- Merge
- Move to next slice

No external review between slices. Bene only intervenes if Claude Code surfaces a 
genuine decision (settled-decision conflict, new flag with no precedent).

## Source of Truth

The original Phase 7 plan and all settled decisions live in the repo's original 
phase-7 handoff document (find it under docs/). All §-references in this spec 
point to that document. If anything in this spec contradicts the handoff, the 
handoff wins — unless Bene explicitly says otherwise.

## Completion State at Start of Autonomous Mode

Merged: PR A · #11 flake-fix · PR B · PR C · PR D · PR E · PR F
Remaining: PR G, PR H, v0.2.0 release

## PR F DnD Fix (Historical Note)

PR F was initially merged with a Tauri v2 DnD issue: `dragDropEnabled` 
defaults to `true`, the webview's native OS file-drop handler swallowed 
HTML5 DnD before it could begin. CI was green because jsdom doesn't 
drive the native Tauri lifecycle — classic test-discipline gap.

Fix: `app.windows[].dragDropEnabled: false` in `tauri.conf.json`. 
One-line config. Defensive unit tests added: `draggable="true"` 
assertion (shadcn Card prop-forwarding) + `preventDefault` on dragover 
assertion. AppCard has a code comment documenting the dependency.

Side-effect: the PR C onboarding CV drop-zone, which had the same 
latent interception, now also works in Tauri.

Lesson for future slices: Tauri smoke-test (not just `pnpm dev`) is 
non-negotiable for any feature involving native browser APIs (DnD, 
clipboard, file system, etc.). This is now enforced in the per-slice 
workflow below.

## Remaining Slices

### PR G — Interview Prep + Settings Restyle

**Scope** (§4 settled + §18):
- Pure visual restyle of existing screens
- No behavior change
- No new capability
- No backend touch

**Interview Prep:**
- Keep existing Question Bank: 4 categories (technical / behavioral / role_specific / company_fit)
- Keep curated questions + practice mode via `evaluate_answer`
- Apply new visual language (tokens from PR A, Icon component, chip system if relevant)
- Reuse design pieces from `interview.jsx` that fit WITHOUT the chat (category tabs, layout)
- The design's chat-style coach UI stays **idle** — revived in Phase 8

**Settings:**
- Restyle existing SettingsScreen
- Provider switcher / Profile / Cost panel / two-step "Delete everything" wipe all preserved
- No new capability

**Phase 8 gating stays explicit:**
- ❌ Chat-style interview coach → Phase 8 (v0.3.0)
- ❌ Editable Preferences / Priorities → Phase 8 as Settings sub-page
- PR G does NOT add either

**Test discipline (hard targets):**
- `InterviewPrep.test.tsx` stays UNTOUCHED. The restyle keeps every testid/role/label/
  button name. If a deliberate DOM change forces an edit, flag it with preserved-
  assertion list (PR E discipline), but goal = zero changes to InterviewPrep.test.
- `SettingsScreen.test.tsx` (#11 flake fix) must keep passing. Provider-panel 
  loading→loaded contract and `waitFor` fix intact.

### PR H — Polish + v0.2.0 Release

**Backlog items collected during Phases A–F:**

1. **Save-button feedback** (carry-over PR D Flag 6)
   - Currently: click "Save" on edited cover letter → no visible feedback
   - Backend works, persistence works
   - Fix: Toast system. The subtle-bounce animation already exists in 
     `tailwind.config`. Add a `<Toast>` component, fire on successful save mutation.

2. **CV-Tab raw JSON rendering** (pre-existing, surfaced in PR E)
   - Backend returns structured JSON for `cv_suggestions`:
```
     { 
       "overall_fit": "...", 
       "suggestions": [
         { "type", "current", "suggestion", "rationale" }
       ] 
     }
```
   - Frontend renders via `MarkdownView` → user sees raw stringified JSON
   - Fix: dedicated `SuggestionRenderer` component
   - One card per suggestion, `type` as eyebrow ("Reality check" / "Emphasize" / 
     "Add" / "Reword" / "Deemphasize" → match Tailwind chip colors used in PR D)
   - Layout: `current` → `suggestion` → `rationale` in clear sections

3. **Regenerate loading state** (PR E)
   - Click "Regenerate" → ~30s blank period → new content suddenly appears
   - Backend works, no error
   - Fix: button disabled + "Regenerating..." label + spinner during mutation pending

4. **Fraunces FOUT** (PR C, low priority)
   - Welcome screen hero uses Fraunces but only Inter Tight is preloaded
   - Fix: add Fraunces preload link in `index.html`

5. **Version bump to 0.2.0**
   - `frontend/package.json` version → 0.2.0
   - `src-tauri/Cargo.toml` package.version → 0.2.0
   - `src-tauri/tauri.conf.json` version → 0.2.0
   - `docs/CHANGELOG.md`: convert `## [Unreleased]` to `## [0.2.0] — YYYY-MM-DD`
   - Git tag `v0.2.0` after merge

**NOT in PR H scope:**
- CompanyMark "?" fallback — backend company parser issue, separate backend PR
- Bitpanda title parsing — backend parser issue, separate backend PR
- Score on ApplicationSummary (would enable MatchRing in Kanban/Detail) — 
  legitimate backend optimization, but Phase 10+ scope per Bene's vision deferral

## Working Mode

### Subagent Strategy

Claude Code MAY parallelize work across subagents where independent. Suggested splits:

**PR G:**
- Subagent 1: Interview Prep restyle (InterviewPrep.tsx + new visual language)
- Subagent 2: Settings restyle (SettingsScreen.tsx + ProviderPanel + ProfilePanel + 
  CostPanel)

Both can work in parallel since they touch different files. Single agent reconciles 
in shared concerns (Icon union widening, CHANGELOG entry).

**PR H:**
- Subagent 1: Toast system (new component + wire into save mutations across the app)
- Subagent 2: CV SuggestionRenderer (new component + replace MarkdownView call in 
  MaterialsScreen CV tab)
- Subagent 3: Regenerate loading state + Fraunces preload (small, can batch)

All three can work in parallel. Single agent reconciles + version bump + CHANGELOG.

### Per-Slice Workflow

For each slice (PR G, PR H, release):

1. **Plan** (internal): Write the plan as a comment in the slice's branch or in a 
   scratch file. No need for Bene approval unless a genuine flag surfaces.
2. **Implement**: Code, with subagents in parallel where applicable.
3. **Local verification**:
   - `pnpm typecheck` — must pass
   - `pnpm lint` — must pass (0 errors)
   - `pnpm exec prettier --check .` — must pass
   - `pnpm test` — all green
   - `pnpm build` — must pass
4. **Tauri smoke-test**: `pnpm tauri dev` — boot the app, test the actual behavior 
   added in the slice. Take screenshots if behavior is visual. THIS IS THE STEP 
   THAT WAS MISSING FOR PR F.
5. **Plan adherence self-review**: Read own diff against the slice's plan + this 
   spec. Verify:
   - No backend touch (unless slice explicitly allows)
   - Settled decisions honored
   - Test discipline (which tests modified, which preserved — with reasons)
6. **Push + PR + wait for CI green**.
7. **Merge** via merge-commit (never squash, per established convention).
8. **Pull main + delete branch + move to next slice**.

### When to Pause and Ask Bene

Claude Code SHOULD pause and ask Bene only if:
- A settled decision (any §-reference in the original phase-7 handoff) appears to 
  conflict with what the slice needs to do
- A new flag surfaces with no precedent in the handoff or this spec (e.g., a 
  data model contradiction like the MatchRing-Score situation from PR E and PR F)
- Local Tauri smoke-test fails and root-cause isn't obvious within ~30 minutes 
  of investigation
- Something breaks that affects already-merged slices

Claude Code SHOULD NOT pause and ask Bene for:
- Routine plan adherence questions (just check this spec)
- Test rewrites necessitated by DOM changes (handoff §6 allows)
- Subagent task division (Claude Code's call)
- Minor visual decisions within the established design system

### Context Window Management

Phase 7 has been long. To avoid bloating the main chat context:

- Use subagents for **independent file modifications**. Each subagent gets only the 
  files it needs.
- After each merged slice, drop intermediate planning notes from working memory. 
  Keep only: this spec, the handoff doc, and the current branch state.
- Reference (don't re-quote) prior PR conversations. The git history and this spec 
  are the source of truth.

### Reporting Cadence

After each merged slice, post a brief summary to Bene's chat:
- What was done
- Test results (typecheck/lint/test/build/tauri smoke counts)
- Any flags or interesting findings
- What's next

No need for full plan-before-code dialogs anymore. Just: "Working on PR G now. 
Will report when done."

## Definition of Done

Phase 7 is complete when:
- [x] PR A through F merged with green CI
- [ ] PR G merged with green CI + Tauri smoke
- [ ] PR H merged with green CI + Tauri smoke + all 5 backlog items addressed
- [ ] Version bumped to 0.2.0 across all 3 manifest files
- [ ] CHANGELOG.md has a complete `[0.2.0]` section
- [ ] `v0.2.0` git tag pushed to GitHub
- [ ] Bene notified: "Phase 7 complete, v0.2.0 tagged. Ready for Phase 8 handoff 
  whenever you are."

## Out of Scope for Phase 7

Per docs/PHASE_10_VISION.md (separate file):
- Auto-detection of application status from email
- Auto-crawling of job sources
- Auto-submission of applications
- AI-driven recruiter email communication

These belong in Phase 10+ and will get their own handoff document then.
