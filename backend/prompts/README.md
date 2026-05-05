# Prompt Library

This folder contains all LLM prompts used by Hired., versioned as plain text files.

## Why This Folder Exists

Prompts are **code**. They:

- Need version control (a bad prompt change can silently break the app)
- Need testing (changes evaluated against the goldset before merging)
- Need review (your prompt reviewer sees the diff alongside business logic)
- Need to live next to the code that uses them, not in a separate doc

Putting them in `.md` files (instead of inline Python strings) makes diffs readable and lets non-coders edit them without touching Python.

## File Format

Every prompt file follows this structure:

```markdown
# <Task Name>

**Purpose:** <one line>
**Used by:** `LLMProvider.<method>`
**Last reviewed:** YYYY-MM-DD
**Owner:** <team member>

## Provider Notes
<Any provider-specific tweaks: e.g., "Ollama needs more explicit JSON instructions">

## System Prompt
\`\`\`
<system prompt text>
\`\`\`

## User Prompt Template
\`\`\`
<user prompt with {{placeholders}}>
\`\`\`

## Output Schema
\`\`\`json
{...JSON Schema for structured output...}
\`\`\`

## Few-Shot Examples
### Example 1: <short label>
**Input:** ...
**Output:** ...

## Evaluation Notes
<How this prompt is evaluated: which goldset entries, what metrics>
```

## Loading Prompts in Code

`backend/llm/prompts.py` provides a single helper:

```python
from backend.llm.prompts import load_prompt

prompt = load_prompt("score_job", profile=profile, job=job)
# Returns a structured object: { system: str, user: str, schema: dict, examples: list }
```

## Updating Prompts

When you change a prompt:

1. Increment a tiny version footer in the file: `**Version:** 3 → 4`
2. Run `make eval` to check it didn't regress on the goldset
3. Mention the eval delta in your PR description (e.g., "precision@5: 0.78 → 0.82")
4. Update `**Last reviewed:**`

## Files in This Folder

- `parse_cv.md` — Extract structured data from a raw CV
- `score_job.md` — Score a job 0–100 against a profile
- `research_company.md` — One-page company brief with sources
- `tailor_cv.md` — Suggest CV emphasis changes for a specific job
- `generate_cover_letter.md` — Generate a tailored cover letter
- `generate_interview_questions.md` — Likely interview questions for a role
- `evaluate_answer.md` — Feedback on a user's interview answer
