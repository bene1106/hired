# ADR-0005: API-First LLM Provider

## Status: Accepted

## Context

Hired. has three target LLM backends:

1. **Anthropic public API** — paid, ToS-clean, official SDK, predictable.
2. **Claude Code CLI** — uses the user's existing Claude subscription, no
   extra cost, but driven via stdio against a CLI not designed for
   programmatic embedding.
3. **Ollama** — free local inference, no network, but smaller models with
   different prompt sensitivity and no structured-output guarantees.

We have to ship one first. The decision shapes which prompt patterns,
JSON-handling code, and error semantics the rest of the layer is built
around — and which surprises we hit before we have any users.

## Decision

Implement the **AnthropicAPIAdapter first** in Phase 2. Defer the
ClaudeCodeAdapter and OllamaAdapter to Phase 6.

## Why API first

- **Officially supported.** Anthropic ships an SDK; errors are typed,
  versions are documented, regressions are public. Claude Code is a
  great product but not a public LLM-execution API.
- **Easier to debug.** Clear error messages, predictable latency, real
  HTTP status codes. Stdio scrapers and prompt injection through CLI
  flags are interesting Phase 6 problems, not Phase 2 ones.
- **ToS-clean.** No gray-area concerns about scripting a subscription
  product during early development.
- **Best signal for prompt quality.** If a prompt works against the API
  with structured outputs, we know whether the prompt itself is good
  before we layer adapter quirks on top.
- **Once the interface is proven, the rest is mechanical.** All adapters
  have to satisfy the same `LLMProvider` Protocol — swapping in Claude
  Code or Ollama becomes "make this method return the right shape,"
  not "design the layer."

## Consequences

- ✅ Fast iteration on prompt quality without fighting an unfamiliar runtime.
- ✅ Real `LLMProvider` contract, validated against a real model, before
  Phase 3 starts depending on it.
- ✅ Optional `@pytest.mark.integration` lane lets us run the adapter
  end-to-end on demand without burning tokens in CI.
- ❌ Anyone running the app today with no API key falls back to MockProvider
  only. That's accepted — the local-only Claude Code path comes in Phase 6.
- ❌ Phase 6 will likely surface adapter-specific quirks (stricter JSON
  parsing for Ollama, stdio framing for Claude Code) that force prompt
  tweaks. Mitigated by keeping prompts in versioned `.md` files with
  `Provider Notes` sections so per-adapter guidance stays close to the
  prompt itself.

## Alternatives considered

- **ClaudeCodeAdapter first.** Aligns with the local-first ethos but
  ships the riskiest integration earliest, with no fallback if it
  doesn't work. We'd debug stdio framing while also designing the
  abstraction. Rejected.
- **MockProvider only for Phase 2, no real adapter.** Tempting and
  cheap, but we wouldn't catch interface mistakes (e.g., a method
  signature that's awkward for real models) until Phase 6. The whole
  point of writing the abstraction is to prove it against a real
  backend. Rejected.
