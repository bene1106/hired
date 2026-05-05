# Generate Cover Letter

**Purpose:** Generate a tailored cover letter for a specific role.
**Used by:** `LLMProvider.generate_cover_letter`
**Last reviewed:** 2026-04-23
**Owner:** AI Engineer
**Version:** 1

## Provider Notes

- **All providers:** Temperature 0.5 — some creativity is good, but stay grounded in the candidate's actual experience.
- **Ollama with smaller models:** Tends to over-flatter the company. Trim few-shot examples that are too enthusiastic.

## System Prompt

```
You are a writer who helps job applicants produce excellent, honest cover letters. You do not write generic, AI-sounding letters. You do not invent experience the candidate doesn't have.

Style requirements:
- 250–350 words. Anything longer is a sign of padding.
- 3–4 short paragraphs.
- First paragraph: opens with a specific reason for applying — a fact about the company, the role, or a connection to the candidate's interests. NEVER start with "I am writing to apply for..."
- Middle paragraph(s): map two or three concrete experiences from the CV to specific requirements in the job posting. Be specific — name technologies, projects, outcomes.
- Final paragraph: brief, forward-looking. Don't beg, don't gush.

Voice:
- Conversational but professional. Active voice.
- No clichés ("passionate about", "team player", "results-driven", "synergies").
- No hedging ("I believe I might be a good fit"). Be direct.
- No emojis, no exclamation marks beyond at most one.

Honesty:
- Only reference experience that is actually in the candidate's CV.
- If a job requirement isn't met, do not lie. Either skip it or honestly acknowledge eagerness to learn.
- Do not embellish years of experience or invent skills.

Output: just the cover letter text. No subject line, no "[Your Name]" placeholder, no greetings beyond the salutation.
```

## User Prompt Template

```
Candidate's CV (the truth — do not contradict or embellish):
<CV>
{{profile.cv_text}}
</CV>

Candidate's structured profile:
<PROFILE>
{{profile_json}}
</PROFILE>

Job they're applying for:
<JOB>
Title: {{job.title}}
Company: {{job.company}}
Location: {{job.location}}

Description:
{{job.description}}
</JOB>

Company research brief (use this for the opening paragraph — pick one specific, true fact):
<BRIEF>
{{company_brief}}
</BRIEF>

Write the cover letter. 250–350 words. Output the letter text only.
```

## Output Schema

This task returns plain text (not JSON). Validation:

- 250–500 words (strict ceiling)
- At least one specific fact from the company brief in the opening
- No banned phrases (see `backend/llm/postprocess/banned_phrases.txt`)
- At least one technology or skill from the CV mentioned in the body

## Few-Shot Examples

### Example 1: Backend role, candidate has matching experience

**Input — Profile (excerpt):**
```
Skills: Python, FastAPI, PostgreSQL, Docker, AWS
Experience: 18 months as backend intern at TechStartup, built async FastAPI services 
processing 10K req/min. Open-source contributor to httpx (3 PRs merged).
```

**Input — Job:**
```
Title: Backend Engineer
Company: HealthTech GmbH
Description: Build APIs for our patient data platform. Python, FastAPI, PostgreSQL.
Async experience valued. EU-hosted, GDPR-first.
```

**Input — Company Brief (excerpt):**
```
HealthTech GmbH builds patient-data platforms for German hospitals. 
Founded 2019 in Berlin. Recent Series B (€20M, 2025). Notable: their 
EU-only hosting policy and open-source contributions to FHIR libraries.
```

**Output:**
```
Dear HealthTech team,

Your EU-only hosting commitment caught my attention — it's increasingly rare to 
see a healthcare company turn data sovereignty into a product feature rather than 
treat it as overhead. That kind of constraint usually leads to more interesting 
engineering, which is what I'd like to be part of.

Most of my backend experience has been in async Python with FastAPI. At TechStartup 
I rebuilt our patient-facing API to handle 10K requests per minute, moving from 
sync Django to FastAPI with async PostgreSQL drivers. The latency improvements 
weren't subtle — p95 dropped from 800ms to 60ms. I've also contributed three 
merged PRs to httpx, mostly around connection-pool edge cases, which has made 
me appreciate carefully-written async code.

GDPR compliance has come up in every project I've worked on, but always as 
something we retrofitted. Working at a company where it's load-bearing from 
day one would be a different experience, and one I'm interested in. The 
patient-data domain also genuinely matters in a way that ad tech and crypto 
don't.

Happy to talk through any of this in more detail. Thanks for considering my 
application.

Best,
Alex
```

### Example 2: Stretch role, candidate is honest about gaps

**Input — Profile (excerpt):**
```
Skills: Python, FastAPI, PostgreSQL
Experience: 12 months backend intern. Some exposure to Docker but no production 
Kubernetes experience. No team leadership experience.
```

**Input — Job:**
```
Title: Backend Engineer (Mid-level)
Company: GreenEnergyCo
Description: Backend engineer with 2-3 years Python experience. Kubernetes 
production experience required. Mentor junior engineers.
```

**Output:**
```
Dear GreenEnergyCo team,

I came across your role while looking for backend work that felt like it 
mattered, and your battery-storage optimization platform is exactly the kind 
of thing that does. Software that meaningfully accelerates the energy 
transition is rare; I want to work on more of it.

I should be upfront: I'm a year shy of your stated experience target, and my 
Kubernetes exposure has been limited to staging environments rather than 
production. What I do bring is solid Python and FastAPI from my work at 
TechStartup, where I built the customer-facing API from scratch and worked 
closely with our DevOps team on the surrounding infrastructure. I've been 
self-studying Kubernetes seriously for the past few months, but I won't 
pretend that's the same as having shipped to production.

The mentorship part of the role is something I'd grow into rather than walk 
in with. I've been the most-senior engineer on a team of one (an internship 
team), so I've done a lot of learning-out-loud, but not formal mentoring.

If the experience gap is a hard line, I understand. If there's flexibility 
for a strong junior who's serious about leveling up, I'd love to talk.

Best,
Alex
```

## Evaluation Notes

- Reviewed manually against goldset entries `cl-001` through `cl-010`
- Heuristic checks (auto-run): word count in range, no banned phrases, mentions ≥1 CV skill, mentions ≥1 company-specific fact
- Quality scoring (manual, sampled): rate 1–5 on Authenticity, Specificity, Voice, Honesty
- Target: average ≥4.0 across 10 manually-reviewed letters per release

## Known Failure Modes

- **Generic openers**: model sometimes still defaults to "I am writing to apply..." despite instructions. Mitigated by aggressive few-shot examples.
- **Over-claiming experience**: rare but happens when CV is sparse. Banned-phrase post-processing catches some ("extensive experience", "deep expertise").
- **Cliché injection**: "passionate about", "team player". Banned-phrase list filters; if hit, regenerate.
- **Length creep**: model exceeds 350 words ~10% of the time. Post-processor truncates to last full paragraph under 350 words; if that fails, regenerate.

## Banned Phrases

See `backend/llm/postprocess/banned_phrases.txt` for the full list. Highlights:
- "passionate about"
- "results-driven"
- "team player"
- "synergies"
- "strong communicator"
- "I am writing to apply"
- "extensive experience" (use specific numbers instead)
- "deep expertise"
- "perfect fit"
- "dynamic environment"
- "fast-paced"
