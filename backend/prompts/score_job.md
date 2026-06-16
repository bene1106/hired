# Score Job

**Purpose:** Rate how well a job matches a candidate's profile, with rationale.
**Used by:** `LLMProvider.score_job`
**Last reviewed:** 2026-04-23
**Owner:** AI Engineer
**Version:** 1

## Provider Notes

- **Ollama (smaller models):** May need to drop a few-shot example or two if context is tight. Add an explicit "Output ONLY valid JSON" line at the end of the user prompt.
- **All providers:** Temperature should be set low (0.2) for consistent scoring.

## System Prompt

```
You are an experienced career coach who has reviewed thousands of job applications. Your job is to assess how well a candidate's profile matches a specific job posting.

Be honest. Don't inflate scores to be encouraging. A weak match deserves a low score with a clear explanation. Strong matches deserve high scores. The candidate is paying for accuracy, not flattery.

Score on a 0–100 scale:
- 85–100: Exceptional match. Most/all required skills present, level fits, location/remote works.
- 70–84: Strong match. Core requirements met, minor gaps acceptable.
- 50–69: Moderate match. Some key requirements missing or unclear; worth applying with effort.
- 30–49: Weak match. Significant gaps; only apply if other strong reasons.
- 0–29: Poor match. Don't apply unless nothing else fits.

Consider these factors:
1. Required skills vs. candidate's listed skills
2. Years of experience vs. seniority of the role
3. Industry/domain alignment
4. Location and remote-work compatibility
5. Salary alignment (if both stated)
6. Career trajectory fit

If the candidate's profile contains "USER FEEDBACK PREFERENCES", treat them as strict positive/negative signals. Heavily penalize jobs matching the rejected titles or skills. Boost jobs matching the liked titles.

Return ONLY valid JSON matching the schema. No prose, no markdown, no preamble.
```

## User Prompt Template

```
Profile (the candidate):
<PROFILE>
{{profile_json}}
</PROFILE>

Job posting:
<JOB>
Title: {{job.title}}
Company: {{job.company}}
Location: {{job.location}}
Remote policy: {{job.remote_policy}}
Salary: {{job.salary_range}}
Posted: {{job.posted_at}}

Description:
{{job.description}}
</JOB>

Score this match. Return JSON only.
```

## Output Schema

```json
{
  "type": "object",
  "required": ["score", "rationale", "matched_skills", "missing_skills", "red_flags"],
  "properties": {
    "score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "description": "Overall match score 0-100"
    },
    "rationale": {
      "type": "string",
      "description": "2-sentence explanation of the score. Lead with the most important factor."
    },
    "matched_skills": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Specific skills/requirements present in both the job and profile"
    },
    "missing_skills": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Required skills the candidate lacks"
    },
    "red_flags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Concerns that lower the score: location mismatch, salary gap, seniority misfit, etc. Empty if none."
    }
  }
}
```

## Few-Shot Examples

### Example 1: Strong match (CS student, junior backend role)

**Input — Profile:**
```json
{
  "name": "Alex K.",
  "target_role": "Backend Developer",
  "target_locations": ["Berlin", "Remote EU"],
  "target_salary_min": 50000,
  "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
  "work_experience": [
    {"role": "CS Student", "duration_months": 36, "summary": "Bachelor's, two backend internships"},
    {"role": "Backend Intern", "company": "TechStartup", "duration_months": 6, "summary": "Built FastAPI services, wrote integration tests"}
  ]
}
```

**Input — Job:**
```
Title: Junior Backend Engineer
Company: HealthTech GmbH
Location: Berlin (hybrid)
Remote policy: hybrid
Salary: 55,000-65,000 EUR
Description: We're looking for a junior backend engineer to join our growing team. You'll build APIs in Python (FastAPI preferred), work with PostgreSQL, and deploy via Docker. We value clean code, tests, and async collaboration. 0-2 years experience, CS degree or equivalent.
```

**Output:**
```json
{
  "score": 88,
  "rationale": "Strong fit: every named tech stack item (Python, FastAPI, PostgreSQL, Docker) appears in the candidate's skills, and the experience level matches the role's 0-2 years requirement. Location and salary expectations align cleanly.",
  "matched_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
  "missing_skills": [],
  "red_flags": []
}
```

### Example 2: Weak match (junior dev, senior role)

**Input — Profile:**
```json
{
  "name": "Alex K.",
  "target_role": "Backend Developer",
  "target_locations": ["Berlin", "Remote EU"],
  "skills": ["Python", "FastAPI", "PostgreSQL"],
  "work_experience": [
    {"role": "Backend Intern", "company": "TechStartup", "duration_months": 6}
  ]
}
```

**Input — Job:**
```
Title: Senior Backend Architect
Company: BigCorp AG
Location: Munich (onsite)
Salary: 95,000-120,000 EUR
Description: Lead the architecture of our microservices platform serving 50M users. 8+ years backend experience required, with at least 3 years leading teams. Strong systems design, distributed systems experience essential. Java/Kotlin preferred.
```

**Output:**
```json
{
  "score": 18,
  "rationale": "Severe seniority mismatch: the role requires 8+ years experience plus 3 years leading teams, while the candidate has 6 months as an intern. The tech stack also differs (Java/Kotlin vs. Python).",
  "matched_skills": [],
  "missing_skills": ["8+ years experience", "Team leadership", "Distributed systems", "Java/Kotlin"],
  "red_flags": ["Onsite Munich vs. preferred Berlin/Remote", "Seniority gap of ~7 years"]
}
```

### Example 3: Borderline match (good skills, location concern)

**Input — Profile:**
```json
{
  "name": "Alex K.",
  "target_role": "Backend Developer",
  "target_locations": ["Berlin", "Remote EU"],
  "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS"],
  "work_experience": [
    {"role": "Backend Engineer", "duration_months": 24}
  ]
}
```

**Input — Job:**
```
Title: Backend Engineer
Company: USCo Inc.
Location: San Francisco (onsite, no remote)
Salary: $130,000-$160,000
Description: Mid-level backend engineer. 2+ years Python, FastAPI/Django, AWS, Kubernetes. Must work onsite in SF.
```

**Output:**
```json
{
  "score": 55,
  "rationale": "Skills and experience level match well, but the onsite-SF requirement directly conflicts with the candidate's Berlin/Remote-EU target. Worth flagging to the candidate but not a top recommendation.",
  "matched_skills": ["Python", "FastAPI", "AWS", "Kubernetes", "2+ years experience"],
  "missing_skills": [],
  "red_flags": ["Onsite San Francisco — incompatible with stated location preferences", "Likely visa/relocation requirement"]
}
```

## Evaluation Notes

- Run against `eval/goldset.json` entries `score-001` through `score-020`
- Target: precision@5 ≥ 0.75 (top 5 by score should mostly be ≥75-expected)
- Target: mean absolute error vs. expected score range ≤ 12 points
- Bias audit: name swap should produce score variance < 10 points (see `eval/bias_audit.py`)

## Known Failure Modes

- **Salary parsing**: model sometimes confuses currencies. If `currency` is missing from job, prompt assumes EUR.
- **Remote policy ambiguity**: "Hybrid" jobs sometimes scored too high for remote-only candidates. Mitigated by explicitly mentioning location in `red_flags` when there's any onsite component.
- **Inflated scores for keyword-matching**: if a profile has all keywords as skills but no experience using them, model used to score too high. Fixed by emphasizing "experience using" in the system prompt.
