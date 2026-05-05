---
description: Verify the current phase is truly complete before merging
---

You are doing a final verification before declaring a phase complete.

**Step 1:** Read the active phase's spec from `.claude/specs/`.

**Step 2:** For EACH acceptance criterion in the spec:
- Run the test or check that proves it
- Report ✅ pass or ❌ fail with details
- Do NOT trust prior runs — re-verify now

**Step 3:** Run the full test suite:
```bash
cd backend && uv run pytest --cov
cd frontend && pnpm test
```

Report coverage numbers explicitly. If below the spec's threshold, surface this.

**Step 4:** Check for skipped tests:
```bash
grep -rn "@pytest.mark.skip\|xit(\|test.skip" backend/ frontend/src/
```

Any skipped tests need a justifying comment with an issue link. If not, fail the verification.

**Step 5:** Run linters:
```bash
cd backend && uv run ruff check && uv run mypy .
cd frontend && pnpm lint && pnpm typecheck
```

**Step 6:** Smoke test the app manually (describe what you'd test if you could; you cannot click the UI yourself, so describe the user flow and what each step should produce).

**Step 7:** Final report:
- ✅ All acceptance criteria met
- ⚠️ Items I cannot verify without human action (list them)
- ❌ Things that don't pass (with exact failure)

If any ❌ exists, do NOT mark the phase complete. Fix or escalate.

If all ✅ and ⚠️ items are acceptable to the human, propose updating `docs/CURRENT_PHASE.md` to "Phase X complete; Phase Y starting".
