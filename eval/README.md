# Evaluation Goldset

`goldset.json` is the source of truth for prompt regression tests. Each entry
is a `(profile, job, expected)` triple the harness can replay against any
`LLMProvider` implementation.

Phase 2 ships **3 starter examples** to lock the structure in. The full set
(20+) lands in Phase 4 alongside the scorer and ranking pipeline.

## Schema (per entry)

| field                       | type           | meaning                                                            |
| --------------------------- | -------------- | ------------------------------------------------------------------ |
| `id`                        | string         | Stable identifier; never reuse after deletion.                     |
| `description`               | string         | One-line human description so reviewers know what's being tested.  |
| `profile`                   | object         | A `Profile`-shaped payload (see `backend/llm/types.py::Profile`).  |
| `job`                       | object         | A `Job`-shaped payload (see `backend/llm/types.py::Job`).          |
| `expected_score_range`      | `[int, int]`   | Inclusive range of acceptable `score_job.score`.                   |
| `must_mention_in_rationale` | list of string | Substrings that should appear in `score_job.rationale`.            |

## Adding examples

1. Pick an unused `id`.
2. Fill in `profile` + `job` using realistic data — no real PII.
3. Set `expected_score_range` from human judgment of the match strength.
4. Note any keywords reviewers should expect in the rationale.
5. Run the eval harness (Phase 4) before merging.
