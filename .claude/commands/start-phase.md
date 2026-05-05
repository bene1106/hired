---
description: Start work on a Hired. project phase
---

You are starting work on a phase of the Hired. project.

**Step 1:** Read `docs/CURRENT_PHASE.md` to confirm which phase is active.

**Step 2:** Read the spec file `.claude/specs/PHASE_<N>_<name>.md` for the active phase. This is your contract — the acceptance criteria there are non-negotiable.

**Step 3:** Read `CLAUDE.md` for project conventions (you may have read it already this session, but re-skim).

**Step 4:** Before writing any code, summarize back to me:
- What this phase delivers
- What the acceptance criteria are
- What you plan to build first, second, third (high-level task order)
- What's risky or unclear (questions for the human)

**Step 5:** Wait for confirmation before starting implementation. Do not assume — ask if a task is ambiguous.

**Step 6:** After confirmation, work in small commits. After each meaningful unit of work:
- Run the relevant tests
- If tests pass, commit with a conventional commit message
- If tests fail, fix before moving on

**Step 7:** When you believe the phase is complete, run the full verification steps from the spec and report back.

Argument: $ARGUMENTS (optional — phase number to switch to)
