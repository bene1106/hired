---
description: Document an architecture decision as an ADR
---

The user wants to document a decision as an Architecture Decision Record.

**Step 1:** Look at `docs/adr/` to find the next available number (ADRs are numbered sequentially: 0001, 0002, …).

**Step 2:** Ask the user (if not already provided):
- The decision title (short, in present tense, e.g., "Use SQLite over Postgres")
- Context: what triggered this decision?
- Options considered
- Which option was chosen
- Why
- Consequences (good and bad)

**Step 3:** Create `docs/adr/<NNNN>-<kebab-case-title>.md` with this template:

```markdown
# ADR-<NNNN>: <Title>

## Status
Accepted (or: Proposed, Deprecated, Superseded by ADR-XXXX)

## Date
<YYYY-MM-DD>

## Context
<What's the situation? What problem are we solving?>

## Options Considered
1. <Option A> — <one-line summary>
2. <Option B> — <one-line summary>
3. <Option C> — <one-line summary>

## Decision
<Which option, in 1-2 sentences>

## Rationale
<Why this option, in detail. Reference Section X of project doc if relevant.>

## Consequences
### Positive
- <Good outcome 1>
- <Good outcome 2>

### Negative / Trade-offs
- <Cost or limitation 1>
- <Cost or limitation 2>

## Related
- Project Doc Section X
- ADR-YYYY (if related)
```

**Step 4:** After creating the file, remind the user to commit it with message `docs: add ADR-<NNNN> <title>`.

Argument: $ARGUMENTS (optional — short title for the ADR)
