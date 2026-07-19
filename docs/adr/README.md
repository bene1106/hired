# Architecture Decision Records

Short records of decisions that were expensive to make and would be expensive to
reverse. One file per decision, numbered in the order they were written.

| ADR | Title | Phase |
|-----|-------|-------|
| [0001](0001-local-first-architecture.md) | Local-First Architecture | 1 |
| [0005](0005-api-first-llm-provider.md) | API-First LLM Provider — ship the Anthropic adapter first, defer the CLI ones | 2 |
| [0006](0006-crawler-fragility.md) | Manual URL Paste Is the Primary Crawler Path | 4 |
| [0007](0007-multi-provider-rollout.md) | Multi-Provider Rollout — Claude Code + Ollama | 6 |
| [0008](0008-phase-7-frontend-redesign.md) | Phase 7 Frontend Redesign — design source, tokens, component mapping | 7 |
| [0009](0009-phase-8-interactive-coach.md) | Interactive Interview Coach (Streaming) + Editable Preferences | 8 |
| [0010](0010-codex-cli-provider.md) | OpenAI Codex CLI Provider | 8 (point release) |

All seven are **Accepted**; none has been superseded.

## On the numbering gap

**0002, 0003, and 0004 are unused — no ADR was ever written under those
numbers.** They are not lost or deleted; `git log` over `docs/adr/` shows no
file has ever existed at those paths. The Phase 2–3 decisions they would have
covered are recorded in `docs/phases/PHASE_02.md` and `PHASE_03.md` instead.

The gap is left as-is rather than compacted, so existing cross-references to
ADR-0005 and later stay valid.

## Writing a new one

Use the next free number (0011). Keep it to: context, the decision, the
alternatives rejected, and the consequences. The `/add-adr` slash command in
`.claude/commands/` scaffolds one.
