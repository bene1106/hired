# Hired. — Add-Ons Package

This zip extends the base `hired_setup` package with three things:

## 📁 Contents

```
hired_addons/
├── README.md                                # this file
├── .github/                                 # GitHub repo templates
│   ├── pull_request_template.md             # auto-applied to every PR
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       ├── feature_request.md
│       ├── prompt_regression.md             # for LLM-quality issues
│       └── config.yml                       # disables blank issues
└── backend/
    ├── prompts/                             # versioned prompt library (the IP)
    │   ├── README.md
    │   ├── parse_cv.md                      # extract structured data from CV
    │   ├── score_job.md                     # 0-100 match score with rationale
    │   ├── research_company.md              # 1-page company brief
    │   ├── tailor_cv.md                     # CV emphasis suggestions
    │   ├── generate_cover_letter.md         # tailored cover letter (key prompt!)
    │   ├── generate_interview_questions.md  # role-specific question bank
    │   └── evaluate_answer.md               # feedback on practice answers
    └── llm/
        ├── prompts.py                       # parses .md files into PromptTemplate objects
        └── postprocess/
            └── banned_phrases.txt           # filters AI-slop from cover letters
```

## 🚀 How to install

### Step 1: Apply on top of `hired_setup`

After you've extracted `hired_setup.zip` into your repo, extract `hired_addons.zip` on top:

```bash
cd hired/
unzip /path/to/hired_addons.zip -d /tmp/addons
cp -r /tmp/addons/hired_addons/. .
```

This adds the `.github/` and `backend/prompts/` and `backend/llm/` folders without overwriting your existing files.

### Step 2: Commit

```bash
git add .github/ backend/
git commit -m "chore: add PR template, issue templates, and prompt library"
```

### Step 3: Use it

- **PRs**: every new PR will auto-fill with the template — fill it out, don't delete sections you didn't touch (mark them N/A)
- **Issues**: when someone opens an issue, they'll pick from Bug / Feature / Prompt-Regression
- **Prompts**: when implementing Phase 2, point Claude Code at `backend/prompts/` — the structure is already there

## 🎯 Why these three things together?

They're the highest-leverage items not in the base setup:

| Add-on | What it gives you | Notenkriterium it helps |
|--------|-------------------|-------------------------|
| **Prompt Library** | Real, tested prompts with few-shot examples | LLM Integration Quality (7) |
| **PR Template** | Forced checklist incl. eval results, ADR check | Engineering Practice (5), Documentation (10) |
| **Prompt Regression Issue Template** | Structured way to track LLM quality issues | LLM Integration Quality (7), Innovation/Ethics (5) |

## 📝 Notes on the Prompt Library

### What's in each prompt file

Every prompt file has the same structure:
- **Header**: purpose, version, last reviewed, owner
- **Provider Notes**: what differs across Claude API / Claude Code / Ollama
- **System Prompt**: the role/instructions for the model
- **User Prompt Template**: what gets rendered with `{{placeholders}}`
- **Output Schema**: JSON Schema for structured outputs (or "plain text")
- **Few-Shot Examples**: 1-3 carefully designed examples
- **Evaluation Notes**: how to test changes don't regress quality
- **Known Failure Modes**: gotchas the model has hit

### The most important prompts

If you only invest deeply in three:

1. **`score_job.md`** — drives match relevance (the user's first impression)
2. **`generate_cover_letter.md`** — drives perceived quality (the user's *lasting* impression)
3. **`parse_cv.md`** — drives everything downstream (bad parse = bad scores = bad letters)

These three are the ones with the most few-shot examples and the most detailed failure-mode notes. The other four are simpler and shorter.

### How the prompt loader works

`backend/llm/prompts.py` parses these `.md` files at runtime:

```python
from backend.llm.prompts import load_prompt

# Returns a RenderedPrompt with system, user, schema, and few-shot examples
prompt = load_prompt("score_job", profile=profile, job=job)

# Convert to Anthropic API messages format
messages = prompt.to_messages()
```

The loader:
- Caches parsed templates after first load
- Renders `{{placeholders}}` using dotted keys (`{{job.title}}`)
- Auto-converts dict/list values to JSON
- Bundles few-shot examples as alternating user/assistant turns

### Banned phrases

`backend/llm/postprocess/banned_phrases.txt` is the kill-list for AI-slop in cover letters. The post-processor checks generated letters against this list; if a banned phrase is present, the system either:

1. Logs it and lets it through (default — for shipping speed)
2. Regenerates with explicit "do not use these phrases" addendum (configurable)

You can extend the list as you spot new offenders. Format: one phrase per line, comments with `#`, case-insensitive substring matching.

## 🔄 When to update the prompt library

| Trigger | Action |
|---------|--------|
| New banned phrase spotted in user feedback | Add to `banned_phrases.txt`, version-bump `generate_cover_letter.md` |
| Goldset eval shows regression | Adjust prompt; bump version; document change in PR |
| Provider quirk discovered (e.g., Ollama needs different format) | Update "Provider Notes" section in the prompt file |
| New task added (e.g., salary negotiation) | Add new `.md` file following the same structure |

## ⚠️ Things to watch out for

- **Prompt drift**: prompts are easy to keep tweaking. Every change should be motivated by an eval result, not a vibe.
- **Provider-specific bloat**: keep "Provider Notes" short. If a provider needs a fundamentally different prompt, fork it (e.g., `score_job.ollama.md`) rather than littering the main file with conditionals.
- **Few-shot rot**: if you change the schema, every few-shot example breaks. Run goldset eval after schema changes — it'll catch this.
- **Banned-phrases over-correction**: don't ban every cliché. The list should be ~30 entries max. If it grows past 50, the model is probably trying too hard to be "creative" and the system prompt needs work instead.

## 🎓 What this contributes to the grade

Concretely, this addon package lets you say in the final presentation:

> *"We treat prompts as versioned code. Every prompt has explicit failure modes documented, automated eval against a 20-pair goldset, post-processing for AI-slop phrases, and a structured way to track quality regressions through GitHub. Provider differences are documented per-prompt, so the same task works across the API, Claude Code, and Ollama with provider-specific tweaks where needed."*

That's a much stronger story than "we wrote some prompts and they seem to work."
