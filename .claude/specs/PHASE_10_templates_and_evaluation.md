# Phase 10 — CV Templates, Gap Detection & Evaluation

**Duration:** Planned (next phase)
**Depends on:** Phases 1–9 complete; v0.5.0 released
**Version target:** v0.6.0

## Goal

Close the four gaps recorded in `docs/PROJECT_DOC.md` §2.3 Future Work. Three
of them are small; one (CV template export) is the first genuinely new user-
facing capability since voice.

This phase replaces the previously planned Phase 10 (Gmail reading + status
auto-detect), which is deferred — see "Why not email reading" below.

## Scope

### 1. CV template export

Hired. tailors a CV today but never produces a formatted document. The parsed CV
is already structured (`profile.cv_parsed_json`), and PDF export already exists
(`frontend/src/lib/pdf.ts`), so this renders existing data rather than building
new machinery.

**Decision to make first (ADR-0011):** we emit LaTeX *source* and do not bundle a
compiler. TeX Live is several gigabytes; bundling it contradicts the lean local
install, and requiring a separate install breaks the download-and-it-works
property. Users compile locally or in Overleaf.

- Backend: a renderer that maps `cv_parsed_json` onto a `.tex` template for one
  known class (`moderncv`), exposed as an endpoint. Escaping is the sharp edge —
  `&`, `%`, `_`, `#`, and `\` in user data must be escaped or the output will not
  compile.
- Frontend: template picker on the materials screen, with download.
- Follow-on (optional this phase): HTML/CSS templates rendered through the
  WebView's own print-to-PDF, for users who do not write LaTeX.

### 2. Missing-information detection

Parsing already refuses to invent (`parse_cv.md` returns `null` for absent
fields), but nothing tells the user what is missing. A CV with no skills section
scores every job low and the feed looks broken for an invisible reason.

- Backend: a completeness check after parsing — which of `skills`,
  `work_experience`, `education` came back empty — returned with the parse result.
- Frontend: surfaced on the onboarding review step and in Settings, with inline
  fields to fill the gap. Wording should explain the consequence, not just the
  gap: "match scores will be unreliable until you add this".

### 3. Evaluation against a live provider

`eval/run_eval.py` and `eval/bias_audit.py` work but have only run against
`MockProvider`, so three metrics in PROJECT_DOC §12 read "not measured".

- Run both against `anthropic_api` over the existing 20-entry goldset.
- Commit `docs/eval-results.md`: date, provider, model, precision@5, MAE,
  in-range rate, per-name bias deltas, token cost, and an honest reading of
  where the scorer underperforms.
- Update §12 to cite the results file.

### 4. Installer size reduction

Bundling the speech runtimes in v0.5.0 grew installers three- to fourfold. The
models are still downloaded on first use, so the growth is runtime libraries.

- Measure what `onnxruntime`, `ctranslate2`, and PyAV actually contribute.
- Exclude GPU execution providers, which are dead weight for CPU inference.
- Verify all three platforms still build **and that a packaged build still
  reports `deps_available: true`** — the check that proved the bundling worked.

## Out of scope

- Gmail / email reading and status auto-detection (deferred).
- Auto-submission to ATS portals (Phase 12 vision).
- Recruiter reply automation (Phase 13 vision).
- Bundling a TeX compiler — explicitly rejected, see ADR-0011.

## Suggested PR breakdown

Seven PRs; nine if both template engines land. Tracks 2–5 are independent.

| # | PR | Track | Effort |
|---|---|---|---|
| 1 | `docs: ADR-0011 CV template export strategy` | A | 1h |
| 2 | `feat: render parsed CV to .tex (moderncv)` | A | ~1 day |
| 3 | `feat: template picker + download` | A | ~0.5 day |
| 4 | `feat: flag missing CV sections after parsing` | B | ~0.5 day |
| 5 | `docs: eval results against the Anthropic API` | C | ~2h |
| 6 | `perf: exclude GPU execution providers from the bundle` | D | ~0.5 day |
| 7 | `chore: release v0.6.0` | — | 1h |

PR 6 may need a second round if excluding providers breaks the macOS or Linux
build. PR 4 can split into backend and frontend if you want them reviewed
separately.

## Acceptance criteria

- [ ] ADR-0011 records the emit-source-don't-compile decision and its rejected
      alternative.
- [ ] A parsed CV exports to `.tex` that compiles cleanly under `moderncv`,
      including CVs containing LaTeX special characters.
- [ ] The template picker is reachable from the materials screen and downloads
      the chosen output.
- [ ] Uploading a CV with no skills section produces a visible warning that
      explains the consequence for match scores.
- [ ] `docs/eval-results.md` exists with real numbers from a live provider, and
      PROJECT_DOC §12 cites it instead of reading "not measured".
- [ ] Installer size is measured before and after; the reduction (or the finding
      that it is irreducible) is recorded in the changelog.
- [ ] All three platforms build, and a packaged build still reports voice
      available.
- [ ] `docs/PROJECT_DOC.md` §2.3 is updated to move completed items out of
      Future Work.

## Why not email reading

The previous Phase 10 plan was Gmail reading with status auto-detection. It is
deferred rather than dropped, for three reasons:

1. **It breaks the privacy story.** Every other feature runs locally or sends a
   single prompt the user triggered. Gmail OAuth means a persistent token with
   read access to the user's whole inbox — a categorically larger ask than
   anything the app does today, and hard to reconcile with §7.
2. **It is the largest remaining item, not the smallest.** OAuth flow, token
   refresh, message parsing, and status classification is a phase on its own.
   The four items above are collectively smaller and each closes a gap that is
   already documented.
3. **Nothing depends on it.** The Kanban board works with manual status updates.

If it returns, it should come back as its own phase with its own ADR covering
the privacy trade-off, not folded into a polish phase.
