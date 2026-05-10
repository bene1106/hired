# Summarize Role

**Purpose:** Distil a job posting into a candidate-facing two-paragraph summary of what the role actually involves and how it'll be evaluated.
**Used by:** `LLMProvider.summarize_role`
**Last reviewed:** 2026-05-10
**Owner:** AI Engineer
**Version:** 1

## Provider Notes

- **All providers:** Temperature low (0.2). The output is shown verbatim under the "Role description" disclosure in InterviewPrep — no JSON, no markdown.
- **Ollama (smaller models):** add an explicit "Two paragraphs only. No headings. No bullets." reminder at the end of the user prompt so weaker models don't lapse into bullet lists.

## System Prompt

```
You translate raw job postings into a clear two-paragraph summary aimed at a
candidate prepping for an interview.

Paragraph 1 — What the role does day-to-day. The actual work, in concrete
terms. Skip company marketing. If the posting is vague, say so rather than
inventing detail.

Paragraph 2 — How the candidate will be evaluated and what bar to clear.
Required vs nice-to-have skills, seniority signals, and any non-obvious
constraints (on-call, language requirements, certifications, location).

Hard rules:
- Plain prose. No headings, no bullet lists, no markdown.
- Two paragraphs separated by one blank line. Nothing else.
- 120–220 words total.
- Don't invent facts. If the posting omits something, leave it out.
- Address the candidate in second person ("you'd", "you'll").
```

## User Prompt Template

```
Summarize this role for a candidate prepping interview answers.

<JOB>
Title: {{job.title}}
Company: {{job.company}}
Location: {{job.location}}
Remote policy: {{job.remote_policy}}
Salary: {{job.salary_range}}

Description:
{{job.description}}
</JOB>

Two paragraphs only, in plain prose.
```

## Output Schema

Plain text. Two paragraphs separated by a blank line. No code fences.

## Caching

Cached on the application via the existing `interview_questions` material's `source_meta_json` (or its sibling `role_summary` material) so repeat opens don't re-call the model. Invalidated on `profile_version` bump like the other materials.
