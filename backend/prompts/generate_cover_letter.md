# Generate Cover Letter

**Purpose:** Generate a tailored cover letter for a specific role.
**Used by:** `LLMProvider.generate_cover_letter`
**Last reviewed:** 2026-05-17
**Owner:** AI Engineer
**Version:** 2

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
- Acknowledge gaps neutrally and factually. Do NOT frame the candidate as a burden, cost, downside, or risk to the team. The line is: "I don't have X yet — I'd ramp up on it" (good) vs. "and that's a real cost to the team" / "I'd slow the team down" (bad). Honest is not the same as self-deprecating. State the gap, state the plan to close it, then move on. One sentence per gap, maximum. Never editorialize about what the gap means for the employer.

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

### Example 3: Junior applying to a senior role — gap acknowledged, no self-flagellation

This example exists specifically to teach the *stopping point*. The
candidate has a real, significant gap (student vs. senior role, doesn't
know the company's stack). The letter names the gap once, states the
plan, and stops. It never tells the employer the gap is "a cost" or
that the candidate would "slow the team down" — that editorializing is
the failure mode this example guards against.

**Input — Profile (excerpt):**
```
Skills: Python, JavaScript, SQL. B.Sc. Computer Science (final year).
Experience: Two internships (8 months total) building internal tools in
Python/Flask. No Go, no Ruby, no production experience at scale.
```

**Input — Job:**
```
Title: Senior Backend Engineer
Company: Qonto
Description: Senior backend engineer, 5+ years. Our stack is Go and Ruby.
You'll own a payments-adjacent service end to end and set technical
direction for a squad.
```

**Input — Company Brief (excerpt):**
```
Qonto is a European business-banking platform (~500k SMB customers,
founded 2016, Paris). Engineering writes publicly about their Go
migration off a Ruby monolith and their strong incident-review culture.
```

**Output:**
```
Dear Qonto team,

Your public writing about migrating off the Ruby monolith — and being
candid about what the migration got wrong, not just what it got right —
is what made me look closer. I want to learn from a team that reviews
its own incidents in the open.

I'll be direct about where I stand: I'm finishing my B.Sc. and my
production experience is two internships building internal tools in
Python and Flask, not five years owning a payments-adjacent service. I
don't know Go or Ruby yet; I'd ramp up on both, and I learn languages
quickly once I'm reading real code rather than tutorials. What I can
point to is the work itself — at my last internship I took a brittle
manual reconciliation script and turned it into a tested Flask service
the finance team now relies on daily, including the boring parts:
retries, idempotency, an audit trail.

I'm not going to pretend the seniority gap isn't real. I'm applying
because the work is exactly what I want to be doing and I'd rather make
the case honestly than pad a CV. If there's a more junior opening on
the same team, I'd be just as glad to talk about that.

Thanks for reading.

Best,
Sam
```

Note what the letter does NOT say: it never says the gap is "a real
cost to the team", never says Sam would "slow the squad down", never
apologizes for applying. It states the gap as fact, states the plan,
and redirects to concrete evidence and genuine motivation. That is the
calibration target.

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
- **Self-deprecation creep**: when the candidate has a real gap, the model sometimes escalates past honest acknowledgment ("I'd ramp up on Go") into actively framing the candidate as a liability to the employer ("and that's a real cost to the team", "I'd slow the squad down", "I'd be a drain on resources"). Honest ≠ self-flagellating. Mitigated by the explicit honesty rule in the system prompt, Example 3 (which demonstrates the stopping point), and the burden-framing banned phrases. Found in manual testing of a B.Sc. student → senior Qonto role; fixed in v2.

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
- "a real cost" / "cost to the team" (burden-framing — acknowledge gaps neutrally instead)
- "slow the team down" / "drain on resources" (self-deprecation creep)
