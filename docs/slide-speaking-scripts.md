# Hired. — Slide Speaking Scripts
**3 slides · ~2:30 total spoken time**

---

## SLIDE 1 — The Problem & Our User
**Target: 30 seconds (~75 words)**

> *Start recording. Camera on. Jump straight in.*

---

"We're CS students — we job hunt, and we pay for Claude Pro. And yet we still spend hours manually tailoring CVs, writing cover letters from scratch, and losing track of where we even applied. Meanwhile, recruiters are already running AI filters on the other side. That's the gap. **Hired.** is a local career agent that runs entirely on your machine and uses the AI subscription you already pay for. Zero extra cost. Zero data leaving your device."

---
**⏱ ~28 seconds**

---

## SLIDE 2 — Architecture / LLM Integration
**Target: 1 minute (~140 words)**

> *Switch to the architecture slide.*

---

"Let me walk you through how it's built. Everything here — every single component — runs on the user's machine. There's no cloud backend we operate.

The **Tauri shell** is the native desktop window. It talks to a **FastAPI sidecar** — a local Python process — over HTTP. That's where all the business logic lives: the crawler, the scoring engine, the material generator.

The key design decision is this **LLMProvider interface** in the middle — a single Python Protocol that every AI task goes through. Behind it we have four concrete adapters: the Anthropic API, the Claude Code CLI which uses the user's existing subscription at zero extra cost, Ollama for fully local inference, and a new Codex CLI adapter for OpenAI users.

Every LLM call is grounded — the full CV and job description are in the prompt every time. No model memory. Every output goes to the user before it's used anywhere."

---
**⏱ ~58 seconds**

---

## SLIDE 3 — Lessons Learned & Next Steps
**Target: 1 minute (~140 words)**

> *Switch to the lessons slide.*

---

"Three things genuinely surprised us.

LinkedIn is basically unscrappable. It worked for two days, then they changed the DOM. Our fix: manual URL paste is the primary path — honest about the limitation, still totally usable.

The LLM abstraction paid off immediately. When we added the Ollama and Codex adapters, we touched zero business logic. Just a new file, a few tests, done. The interface investment from Week 2 kept every later addition clean.

And SQLite was enough. We debated Postgres early on. We never needed it.

For the final stretch: we want smarter job ranking that learns from your thumbs-downs, a full mock interview loop with upskilling gap analysis, and proper per-task model routing — a fast cheap model for scoring, a powerful one for cover letters. We're calling that **Diversity of LLMs**. Plus code-signed packaging so users don't have to click through security warnings on install."

---
**⏱ ~62 seconds**

---

## COMBINED TIMING CHECK

| Segment | Script words | Time |
|---|---|---|
| Slide 1 — Problem | ~75 | 0:28 |
| Demo (screen walkthrough) | — | ~2:30 |
| Slide 2 — Architecture | ~140 | 0:58 |
| Slide 3 — Lessons & Next Steps | ~145 | 1:02 |
| **Total** | | **~5:00** |

---

## DELIVERY NOTES

- **Slide 1**: Speak fast and punchy — this is a hook, not an explanation. Land on "Zero extra cost. Zero data leaving your device." with a beat.
- **Slide 2**: Point at the diagram as you speak each layer. Slow down on "LLMProvider interface" — it's the concept you want them to remember.
- **Slide 3**: The three lessons go fast (one breath each). Slow down on next steps — those are your forward promise. End on "Diversity of LLMs" as a deliberate, quotable phrase.
- **General**: If you run short on the demo, add 15 seconds to the cover letter editing step. If you run long, cut the interview prep demo entirely and just mention it verbally.
