# Generate Mock Interview Questions

**Purpose:** Prepare a full, ordered mock-interview question set for one specific upcoming interview, in a single call.
**Used by:** `LLMProvider.generate_mock_interview_questions`
**Last reviewed:** 2026-06-24
**Owner:** AI Engineer
**Version:** 1

## Provider Notes

- Temperature: 0.5 — some variety, but the set must stay realistic and ordered.
- One call produces the whole interview; each question carries a rephrasing so a
  timed runner can re-ask without another call.

## System Prompt

```
You are an interviewer preparing the question list for ONE specific interview a
candidate is about to sit. You will be told the round number, the interview type
(e.g. HR, technical, behavioral), the duration in minutes, and how many questions
to produce. The candidate's profile and the job are provided so questions are
tailored to both.

Rules:
- Produce EXACTLY the requested number of questions, in the order they will be asked.
- The FIRST question is always a warm-up "introduce yourself" question with
  "is_intro": true.
- Slant the remaining questions to the interview TYPE: an HR round leans
  behavioral/company_fit; a technical round leans technical/role_specific.
- Make questions specific to THIS job and THIS candidate, not generic trivia.
- For every question include a "rephrasing": a clearly reworded version asking the
  same thing, used if the candidate freezes.
- "time_limit_seconds" is the max answer window: 300 for the intro, 180 otherwise.
- Categories: technical, behavioral, role_specific, company_fit.

Return JSON only.
```

## User Prompt Template

```
Prepare the question set for this interview.

<INTERVIEW>
Round: {{context.round_number}}
Type: {{context.interview_type}}
Duration (minutes): {{context.duration_minutes}}
Number of questions to produce: {{target_count}}
</INTERVIEW>

<JOB>
Title: {{job.title}}
Company: {{job.company}}
Description:
{{job.description}}
</JOB>

<CANDIDATE>
{{profile_json}}
</CANDIDATE>

Return exactly {{target_count}} questions in JSON, intro first.
```

## Output Schema

```json
{
  "type": "object",
  "required": ["questions"],
  "properties": {
    "questions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["category", "question", "rephrasing", "time_limit_seconds"],
        "properties": {
          "category": {
            "type": "string",
            "enum": ["technical", "behavioral", "role_specific", "company_fit"]
          },
          "question": { "type": "string" },
          "rephrasing": { "type": "string" },
          "time_limit_seconds": { "type": "integer" },
          "is_intro": { "type": "boolean" }
        }
      }
    }
  }
}
```

## Few-Shot Example

### Example: Technical round, 30 minutes, Backend Engineer

**Input — Interview + Job:**
```
Round: 1
Type: technical
Duration (minutes): 30
Number of questions to produce: 5
Title: Backend Engineer · HealthTech GmbH
Description: Build patient-data APIs. Python/FastAPI, PostgreSQL. GDPR-first.
```

**Output:**
```json
{
  "questions": [
    {
      "category": "behavioral",
      "question": "To start, tell me a bit about yourself and your background.",
      "rephrasing": "Walk me through your career so far and what brought you here.",
      "time_limit_seconds": 300,
      "is_intro": true
    },
    {
      "category": "technical",
      "question": "How would you design a FastAPI endpoint that returns patient data while respecting GDPR?",
      "rephrasing": "What would you build into a patient-data API so it stays GDPR-compliant?",
      "time_limit_seconds": 180,
      "is_intro": false
    },
    {
      "category": "technical",
      "question": "A PostgreSQL query is slow in production. Walk me through your investigation.",
      "rephrasing": "How do you go about diagnosing a slow database query under load?",
      "time_limit_seconds": 180,
      "is_intro": false
    },
    {
      "category": "role_specific",
      "question": "A doctor reports stale data on their dashboard — how do you debug it end to end?",
      "rephrasing": "Stale data is showing up for a user. How do you trace where it went wrong?",
      "time_limit_seconds": 180,
      "is_intro": false
    },
    {
      "category": "technical",
      "question": "How would you structure dependency injection for a service needing a DB session and an audit-log writer?",
      "rephrasing": "How do you wire up shared dependencies like a DB session and an audit logger in FastAPI?",
      "time_limit_seconds": 180,
      "is_intro": false
    }
  ]
}
```

## Known Failure Modes

- **Wrong count**: model returns more/fewer than requested. The service clamps and
  trims, but the prompt states the exact count twice.
- **No intro first**: mitigated by the explicit `is_intro` rule; the service also
  forces the first question to be the intro.
- **Generic questions**: mitigated by passing the full candidate profile and job.
