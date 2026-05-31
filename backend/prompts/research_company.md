# Research Company

**Purpose:** Generate a one-page company research brief for interview prep and cover letter context.
**Used by:** `LLMProvider.research_company`
**Last reviewed:** 2026-05-31
**Owner:** AI Engineer
**Version:** 2

## Provider Notes

Web search is now wired up live for the web-capable providers — the "search the
web" instruction in the user template is real, not aspirational, so the
`## Sources` section should carry actual URLs the model retrieved.

- **Anthropic API**: the stable `web_search_20250305` tool is activated on this
  call. Sources are extracted from the real `web_search_tool_result` /
  `web_search_result_location` blocks (the `## Sources` markdown is only a
  fallback when the tool returned nothing).
- **Claude Code**: the `WebSearch` tool is allow-listed for this call
  (`--allowedTools WebSearch`). Sources are scraped from `## Sources`.
- **Codex CLI**: web search is enabled via `-c tools.web_search=true` on this
  call. Sources are scraped from `## Sources`.
- **Ollama**: no web access — produce a brief based on training data only, with a
  clear disclaimer that it may be outdated. Adjust prompt accordingly (omit
  "with sources" requirement); the adapter never surfaces fabricated sources.
- Temperature: 0.3 — factual task, low creativity.

## System Prompt

```
You produce concise company research briefs for job applicants. The brief helps 
the candidate write a more specific cover letter and walk into interviews informed.

Structure (use these exact section headings):

## What they do
2–3 sentences on the company's product/service and target market.

## Size & Stage
Approximate headcount, funding stage, year founded, location of HQ.

## Notable Facts
3–5 bullet points: recent news, distinctive engineering practices, public 
commitments, leadership backgrounds, anything specific enough to mention in a 
cover letter without sounding generic.

## Why someone might want to work here
2–3 honest reasons. Don't gush. If the company is controversial, note that too.

## What to ask in an interview
3 specific questions a candidate could ask, based on the above.

## Sources
List the URLs you actually used. If you couldn't find solid info on a section, 
note that — never invent specifics.

Hard rules:
- If you don't have a fact, don't invent it. Say "couldn't confirm" instead.
- Keep total length under 400 words.
- Be specific. "They value innovation" is useless. "They open-sourced their 
  feature-flag system in 2023" is useful.
- Acknowledge uncertainty when relevant.
```

## User Prompt Template

```
Research this company and produce a brief: {{company_name}}

Optional context (use only if accurate):
- Company website: {{company_url}}
- Industry hint: {{industry_hint}}

Search the web for current information. Mark anything uncertain. Keep it to one page.
```

## Output Schema

Plain markdown text. Validation:
- Contains all 6 section headers
- Total word count 200–500
- "Sources" section present and non-empty (when web search is available)

## Few-Shot Example

### Example: Mid-size healthtech company

**Input:** `company_name = "Doctolib"`, `industry_hint = "healthtech"`

**Output:**
```markdown
## What they do
Doctolib provides online appointment booking and practice-management software for 
doctors, clinics, and patients across France, Germany, and Italy. Their two-sided 
platform handles ~80M appointments per month.

## Size & Stage
~3,000 employees as of 2024. Founded in 2013 in Paris. Last raised €500M in 2022 
(Series F led by Eurazeo and Bpifrance), valuing the company at €5.8B. Privately 
held, headquartered in Levallois-Perret near Paris.

## Notable Facts
- Strong engineering blog with detailed posts on Ruby on Rails at scale and 
  monolith-to-services migration.
- Public commitment to interview every applicant in the local language (FR/DE/IT) 
  rather than defaulting to English — uncommon for tech companies of this scale.
- Heavy GDPR/healthcare compliance focus given patient-data handling.
- Faced criticism in 2021 for hosting some controversial healthcare practitioners; 
  responded with stricter onboarding controls.
- Operates HDS-certified hosting in France for medical data.

## Why someone might want to work here
- Genuine impact in a slow-to-modernize sector (healthcare scheduling).
- Mature engineering culture with public technical writing.
- Multinational team with strong language-localization values.
The flip side: large company, less greenfield work; pace varies by team.

## What to ask in an interview
1. How does the team balance shipping new features with the ongoing healthcare-
   compliance overhead?
2. What's the day-to-day mix between platform/infra work and patient-facing features?
3. How do you decide when to extract a service from the Rails monolith vs. keep it embedded?

## Sources
- doctolib.com (company website)
- doctolib.engineering (engineering blog)
- TechCrunch coverage of 2022 Series F
- Le Monde reporting on 2021 onboarding controversy
```

## Caching

**Important:** This prompt's output is **cached per company name** (case-insensitive normalized). 
Multiple jobs at the same company → one research call.

Cache key: `slugify(company_name.lower())`
TTL: 30 days (re-fetch after that)
Invalidation: manual button in the UI ("Re-research this company")

## Evaluation Notes

- Sample manually: pick 5 companies of varying size/visibility, run the prompt, 
  rate the brief 1–5 on:
  - Specificity (no generic platitudes)
  - Accuracy (verifiable claims only)
  - Usefulness (could you mention any of this in a cover letter?)
- Target: average ≥4.0 across all dimensions

## Known Failure Modes

- **Tiny/private companies**: model may fabricate when it has no real info. Catch via "Sources" section being empty or mostly speculation.
- **Outdated info (Ollama mode)**: model's training data lags reality by months. Brief includes a disclaimer in this mode.
- **Generic positivity**: tendency to write "Why someone might want to work here" as a marketing pitch. Mitigated by the "honest reasons; if controversial, note that" instruction.
