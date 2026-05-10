# ADR-0007: Multi-Provider Rollout — Claude Code + Ollama

## Status: Accepted

## Context

Phase 2 shipped `AnthropicAPIAdapter` with the explicit decision (ADR-0005) to defer Claude Code and Ollama until the LLM-provider abstraction had been validated against a real backend. Phase 6 is the cash-out: those two adapters land, and the onboarding wizard / Settings panel start treating them as first-class options.

The interface was designed with this rollout in mind, so the question isn't *whether* to build them but *how* — particularly given that the Claude Code path remains a documented gray zone (see Risk R-01 in `docs/PROJECT_DOC.md`).

## Decision

1. **`ClaudeCodeAdapter` invokes the local `claude` CLI via `subprocess.run`.** Single-turn mode (`-p --output-format json --append-system-prompt …`), user prompt piped via stdin to dodge CLI length / quoting limits. Few-shot examples are flattened into the single user turn.
2. **`OllamaAdapter` talks to `http://localhost:11434/api/chat`.** System + alternating user/assistant turns map directly from the prompt template; the same code path works for `qwen2.5:14b` (recommended) and `llama3.2:3b` (low-end fallback).
3. **Prompts are unchanged.** Both adapters load the same `.md` templates the API adapter uses. The "Provider Notes" section already inside each prompt carries any per-adapter caveats. We accept that smaller Ollama models will sometimes drift on strict-JSON tasks; that's a per-prompt knob to add later, not an interface change.
4. **Both new providers carry friendly cost labels.** `claude_code` → `subscription`, `ollama` → `local`. Settings → Cost shows `$0.00 (subscription)` / `$0.00 (local)` — we deliberately don't fabricate per-call pricing.
5. **Claude Code is flagged "Experimental" in the UI.** A destructive-tone badge on the onboarding card and the Settings status panel; copy underneath says "Hired. uses your local Claude Code installation. Your usage counts against your Claude subscription. Subject to Anthropic's terms." This makes R-01 visible at the moment the user picks the provider.

## Why this shape

- **Same prompts everywhere.** Diverging prompt files per adapter would create N×M maintenance fan-out and make eval results incomparable.
- **Stdin over argv for the CLI.** Argv inlining hits Windows command-line length limits (~32 KB) on long CVs and quotes badly. Stdin is unbounded and binary-safe.
- **Chat shape over generate shape for Ollama.** `/api/chat` accepts the system message + few-shot turns natively; `/api/generate` would force us to flatten and risk training-context off-by-ones.
- **Token usage flows through the existing `record_usage` contextvar.** Claude Code returns a `usage` object on its JSON envelope; Ollama returns `prompt_eval_count` / `eval_count`. Both publish through the same seam the API adapter uses, so `RecordingProvider` and the cost panel stay generic.
- **Selectability gate is the test round-trip, not just detection.** `claude --version` for Claude Code, `/api/tags` for Ollama (which also confirms the requested model is pulled). Failure surfaces as `error_kind: model_unavailable` with an `ollama pull <name>` hint.

## Consequences

- ✅ A user with Claude Pro can switch from API to Claude Code in Settings without restarting the app or losing data — the factory's `reset_provider_cache()` reroutes the next call.
- ✅ A privacy-focused user can run fully offline against Ollama with no code changes elsewhere — every business path goes through `LLMProvider`.
- ✅ The "Experimental" label on Claude Code keeps R-01 in the user's face at the decision point, not buried in docs.
- ❌ Smaller Ollama models occasionally return invalid JSON; we surface this as `LLMResponseError` and rely on the user to pick a stronger model. Per-prompt knobs to drop few-shot examples for tight contexts are a follow-up if real users report trouble.
- ❌ `claude` CLI breaking changes (different flag names, JSON shape changes) will land as adapter bugs. Mitigated by pinning supported versions in install docs and the typed error envelope on top of subprocess output.

## Alternatives considered

- **Per-adapter prompt forks.** Rejected. Forces prompt engineers to sync three trees by hand and breaks eval comparability.
- **Run `claude` interactively over a long-lived stdin pipe to amortise startup.** Tempting for performance but the CLI's interactive mode is not designed for programmatic embedding, and recovery from a bad message is fiddly. We picked the simpler one-shot model and will revisit if cold-start latency becomes the user-visible bottleneck.
- **Ship Claude Code without the Experimental label.** Rejected: R-01 is real (gray zone on subscription scripting), and the lighter the friction at selection time, the more support cost we eat when Anthropic tightens terms.

## See also

- ADR-0005 — API-first decision that put both adapters into Phase 6.
- `.claude/specs/PHASE_6_polish.md` — implementation contract.
- `docs/PROJECT_DOC.md` Risk Register R-01 — gray-zone summary.
