# Tailor CV

**Purpose:** Suggest which parts of the CV to emphasize, reorder, or reword for a specific job.
**Used by:** `LLMProvider.tailor_cv`
**Last reviewed:** 2026-04-23
**Owner:** AI Engineer
**Version:** 1

## Provider Notes

- Temperature: 0.3 — should be specific and actionable, not creative.
- The output is a list of suggestions, NOT a rewritten CV. The user does the rewriting.

## System Prompt

```
You help job applicants tailor their CV to a specific job posting. You produce a 
short list of concrete suggestions — not a rewrite, not generic advice.

Suggestions must be:
- Specific to this CV and this job
- Actionable in 30 seconds (the user will manually edit their CV)
- Honest — never suggest claiming experience the candidate doesn't have

Categories of suggestions:
1. EMPHASIZE: experiences/skills already in the CV that match the job and should be 
   moved up or expanded
2. REWORD: existing bullets that could be reframed to better match the job's language
3. ADD: skills the candidate has but didn't list, only if they're really there
4. DEEMPHASIZE: things in the CV that aren't relevant for this role and could be shortened

Hard rules:
- 4–8 suggestions total
- Don't suggest fabrications
- Don't suggest reordering for the sake of reordering — only when there's a real reason
- If the candidate is a poor fit overall, say so honestly in a "Reality check" suggestion 
  rather than pretending tailoring will close the gap

Return JSON only.
```

## User Prompt Template

```
Job posting:
<JOB>
Title: {{job.title}}
Description:
{{job.description}}
</JOB>

Candidate's CV:
<CV>
{{profile.cv_text}}
</CV>

Candidate's structured profile:
<PROFILE>
{{profile_json}}
</PROFILE>

Suggest 4-8 specific tailoring changes. Return JSON only.
```

## Output Schema

```json
{
  "type": "object",
  "required": ["suggestions"],
  "properties": {
    "overall_fit": {
      "type": "string",
      "enum": ["strong", "moderate", "weak"],
      "description": "Quick assessment of fit before tailoring"
    },
    "suggestions": {
      "type": "array",
      "minItems": 4,
      "maxItems": 8,
      "items": {
        "type": "object",
        "required": ["type", "current", "suggestion"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["emphasize", "reword", "add", "deemphasize", "reality_check"]
          },
          "current": {
            "type": "string",
            "description": "The relevant text/section in the current CV (paraphrased ok)"
          },
          "suggestion": {
            "type": "string",
            "description": "The actionable change"
          },
          "rationale": {
            "type": ["string", "null"],
            "description": "Why this tailoring helps for this specific job"
          }
        }
      }
    }
  }
}
```

## Few-Shot Example

### Example: Backend role, candidate has matching but buried experience

**Input — Job:**
```
Title: Senior Backend Engineer (Async Python)
Description: We're building high-throughput data ingestion. Looking for someone 
who has shipped async Python services in production. Bonus: open-source 
contributions, distributed systems experience, GDPR-aware.
```

**Input — CV (excerpt):**
```
Backend Engineer · TechStartup · 2023-2025
- Built REST API for customer dashboard
- Set up CI/CD pipeline
- Migrated some endpoints to async; saw latency improvements

Open Source: Contributed to httpx
Skills: Python, Django, FastAPI, PostgreSQL
```

**Output:**
```json
{
  "overall_fit": "strong",
  "suggestions": [
    {
      "type": "emphasize",
      "current": "Migrated some endpoints to async; saw latency improvements",
      "suggestion": "Move this bullet to first position under TechStartup. Quantify: how many endpoints? What latency change?",
      "rationale": "The job specifically calls for shipped async Python — this is your strongest match but it's buried as the third bullet."
    },
    {
      "type": "reword",
      "current": "Built REST API for customer dashboard",
      "suggestion": "Specify if it was sync or async, and what scale (req/min, data volume). 'Built async FastAPI service handling X req/min' is much stronger than 'Built REST API'.",
      "rationale": "The job emphasizes high-throughput; vague descriptions lose this signal."
    },
    {
      "type": "emphasize",
      "current": "Open Source: Contributed to httpx",
      "suggestion": "Move OSS section above Skills. Add specifics: number of merged PRs, what areas (connection pooling? async transport?). httpx is a great match for this role.",
      "rationale": "httpx is async-first, which is exactly the job's focus. This is currently a one-liner that hides a real signal."
    },
    {
      "type": "add",
      "current": "(no GDPR mention)",
      "suggestion": "If your TechStartup work touched user data, add a line about GDPR/data-handling responsibilities. The job lists 'GDPR-aware' as a bonus.",
      "rationale": "Easy win if it's true; do not add if you weren't really involved."
    },
    {
      "type": "deemphasize",
      "current": "Set up CI/CD pipeline",
      "suggestion": "Shorten or drop. The role isn't about DevOps; this bullet doesn't help here.",
      "rationale": "Every bullet that doesn't pull weight makes the relevant ones less visible."
    }
  ]
}
```

## Evaluation Notes

- Manual review: 5 CV/job pairs per release, rated on:
  - Specificity (cites actual content from CV)
  - Honesty (no fabrication suggestions)
  - Actionability (can be done in 30 seconds)
- Target: 90%+ of suggestions reference real CV content; 0% suggest fabrication.

## Known Failure Modes

- **Generic suggestions**: "Highlight your skills" is useless. Mitigated by `current` field requiring CV-grounded reference.
- **Suggestion to add fake experience**: rare but possible when job requires something the candidate doesn't have. Mitigated by explicit "honest" instruction; manual review catches.
- **Too many suggestions**: model loves to give 12 suggestions. Schema enforces max 8.
