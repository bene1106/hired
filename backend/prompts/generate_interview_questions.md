# Generate Interview Questions

**Purpose:** Produce a list of likely interview questions tailored to a specific job.
**Used by:** `LLMProvider.generate_interview_questions`
**Last reviewed:** 2026-04-23
**Owner:** AI Engineer
**Version:** 1

## Provider Notes

- Temperature: 0.5 — some variety helps cover different angles.
- Output is structured (categorized list), not a flat list.

## System Prompt

```
You generate likely interview questions for a specific job posting. The candidate 
will use these to prepare. Your goal is realistic preparation, not an exhaustive 
test bank.

Categories (produce questions in each):
- TECHNICAL: questions about specific skills, tools, or technologies in the job description
- BEHAVIORAL: STAR-format questions ("Tell me about a time when...") tied to the role's competencies
- ROLE_SPECIFIC: questions about the day-to-day work, decisions the candidate would face
- COMPANY_FIT: questions that probe motivation, values alignment, why this company

Quality bar:
- Specific to THIS job, not generic
- Real questions a real interviewer would ask, not academic trivia
- Avoid questions that are mostly testing memorization
- Mix of difficulties: some warm-up, some deep

Output: 8–12 questions total, distributed across the four categories.

Return JSON only.
```

## User Prompt Template

```
Generate likely interview questions for this role.

<JOB>
Title: {{job.title}}
Company: {{job.company}}
Description:
{{job.description}}
</JOB>

Optional company context:
<BRIEF>
{{company_brief}}
</BRIEF>

Return 8-12 questions in JSON.
```

## Output Schema

```json
{
  "type": "object",
  "required": ["questions"],
  "properties": {
    "questions": {
      "type": "array",
      "minItems": 8,
      "maxItems": 12,
      "items": {
        "type": "object",
        "required": ["category", "question"],
        "properties": {
          "category": {
            "type": "string",
            "enum": ["technical", "behavioral", "role_specific", "company_fit"]
          },
          "question": { "type": "string" },
          "what_theyre_assessing": {
            "type": ["string", "null"],
            "description": "Brief note on what the interviewer is looking for"
          },
          "difficulty": {
            "type": "string",
            "enum": ["warmup", "standard", "deep"]
          }
        }
      }
    }
  }
}
```

## Few-Shot Example

### Example: Backend Engineer role at a healthtech company

**Input — Job:**
```
Title: Backend Engineer · HealthTech GmbH
Description: Build patient-data APIs. Python/FastAPI, PostgreSQL. GDPR-first 
engineering. Async experience valued. Mid-level (2-4 years).
```

**Output:**
```json
{
  "questions": [
    {
      "category": "technical",
      "question": "Walk me through how you'd design an API endpoint that handles patient data, paying attention to GDPR concerns.",
      "what_theyre_assessing": "Whether you naturally think about data minimization, encryption, audit logs, and consent — not whether you can recite GDPR articles.",
      "difficulty": "deep"
    },
    {
      "category": "technical",
      "question": "Explain the difference between asyncio and threads in Python. When would you choose each?",
      "what_theyre_assessing": "Concurrency model fundamentals, not memorization.",
      "difficulty": "standard"
    },
    {
      "category": "technical",
      "question": "How would you handle a slow PostgreSQL query in production? Walk me through your investigation.",
      "what_theyre_assessing": "Practical debugging instincts: EXPLAIN, indexes, query patterns, monitoring.",
      "difficulty": "standard"
    },
    {
      "category": "behavioral",
      "question": "Tell me about a time you had to balance shipping speed against compliance or security concerns. How did you handle it?",
      "what_theyre_assessing": "Whether you can navigate this conflict pragmatically — central to healthtech.",
      "difficulty": "standard"
    },
    {
      "category": "behavioral",
      "question": "Describe a time you disagreed with a technical decision your team made. What did you do?",
      "what_theyre_assessing": "Disagree-and-commit; whether you push back without being obstructive.",
      "difficulty": "standard"
    },
    {
      "category": "role_specific",
      "question": "If a doctor reports their dashboard is showing stale data, how would you approach debugging it?",
      "what_theyre_assessing": "End-to-end thinking; do you check caching, replication lag, frontend state, or just look at the API?",
      "difficulty": "standard"
    },
    {
      "category": "role_specific",
      "question": "What's your view on test coverage? Where would you push for more, where would you accept less?",
      "what_theyre_assessing": "Pragmatic engineering taste; not a 'right answer' question.",
      "difficulty": "warmup"
    },
    {
      "category": "company_fit",
      "question": "Why healthcare specifically? It comes with extra compliance overhead — what makes that worth it for you?",
      "what_theyre_assessing": "Whether you have a real reason or are spray-applying.",
      "difficulty": "warmup"
    },
    {
      "category": "company_fit",
      "question": "What questions do you have about how engineering decisions get made here?",
      "what_theyre_assessing": "Whether you've thought about culture, not just tech stack.",
      "difficulty": "warmup"
    },
    {
      "category": "technical",
      "question": "We use FastAPI. How would you structure dependency injection for a service that needs both a database session and an audit-log writer?",
      "what_theyre_assessing": "Concrete framework knowledge — you should have an opinion.",
      "difficulty": "deep"
    }
  ]
}
```

## Evaluation Notes

- Manual review of 5 generated question sets per release
- Rate each set on:
  - Tailoring (questions feel specific to the job, not generic)
  - Realism (a real interviewer might ask this)
  - Range (mix of warmup/standard/deep, mix of categories)
- Target: average ≥4.0 on tailoring across reviewers

## Known Failure Modes

- **Generic technical trivia**: "What is the difference between a list and a tuple?" — tone-deaf for a senior role. Mitigated by "Avoid memorization questions" instruction.
- **Behavioral questions that are too vague**: "Tell me about your strengths". Mitigated by tying behaviorals to role competencies in the prompt.
- **Missing company-fit questions**: model focuses on technical and forgets fit. Schema enforces all four categories present.
