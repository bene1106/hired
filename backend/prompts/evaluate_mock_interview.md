# Evaluate Mock Interview

**Purpose:** Score a completed mock interview as a whole — per-question ratings, an overall correctness percentage, and strengths/weaknesses.
**Used by:** `LLMProvider.evaluate_mock_interview`
**Last reviewed:** 2026-06-24
**Owner:** AI Engineer
**Version:** 1

## Provider Notes

- Temperature: 0.2 — scoring should be stable and defensible.
- One call scores the whole transcript so ratings are calibrated against each other.

## System Prompt

```
You evaluate a candidate's answers to a mock interview. You are given the
interview type, the job, and the full list of question/answer pairs (answers are
transcribed from speech or typed, so tolerate minor disfluencies).

For each question, give a "rating" from 0 to 100 reflecting how well the answer
addresses what the question is really probing, and a short "comment" (one or two
sentences) that is specific and actionable.

Then give:
- "overall_percentage" (0–100): the candidate's overall performance.
- "strengths": 2–4 short bullet phrases the candidate did well.
- "weaknesses": 2–4 short bullet phrases to improve.

Be fair but honest. An empty or off-topic answer scores low. Reward concrete
examples and quantified outcomes. Return JSON only.
```

## User Prompt Template

```
Evaluate this mock interview.

<INTERVIEW>
Round: {{context.round_number}}
Type: {{context.interview_type}}
</INTERVIEW>

<JOB>
Title: {{job.title}}
Company: {{job.company}}
</JOB>

<TRANSCRIPT>
{{qa_json}}
</TRANSCRIPT>

Return JSON with per_question ratings, overall_percentage, strengths, weaknesses.
```

## Output Schema

```json
{
  "type": "object",
  "required": ["per_question", "overall_percentage", "strengths", "weaknesses"],
  "properties": {
    "per_question": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["question", "rating", "comment"],
        "properties": {
          "question": { "type": "string" },
          "rating": { "type": "integer" },
          "comment": { "type": "string" }
        }
      }
    },
    "overall_percentage": { "type": "integer" },
    "strengths": { "type": "array", "items": { "type": "string" } },
    "weaknesses": { "type": "array", "items": { "type": "string" } }
  }
}
```

## Few-Shot Example

### Example: One strong, one weak answer

**Input — Transcript:**
```
[
  {"question": "Tell me about yourself.", "answer": "I'm a backend engineer with four years on Python APIs; at my last role I cut p95 latency from 800ms to 220ms."},
  {"question": "How do you debug a slow query?", "answer": "Um, I guess I'd look at it."}
]
```

**Output:**
```json
{
  "per_question": [
    {
      "question": "Tell me about yourself.",
      "rating": 85,
      "comment": "Strong: concrete experience and a quantified result. Could tie it more directly to this role."
    },
    {
      "question": "How do you debug a slow query?",
      "rating": 20,
      "comment": "Far too vague — no mention of EXPLAIN, indexes, or monitoring. Walk through a concrete process."
    }
  ],
  "overall_percentage": 52,
  "strengths": ["Quantifies impact", "Clear background"],
  "weaknesses": ["Vague on technical process", "Needs concrete debugging steps"]
}
```

## Known Failure Modes

- **Grade inflation**: model rates empty answers too kindly. Mitigated by the
  explicit "empty or off-topic scores low" instruction.
- **Overall out of step with per-question ratings**: mitigated by scoring the
  whole transcript in one call so ratings are mutually calibrated.
