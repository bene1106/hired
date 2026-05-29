# ADR-0010: OpenAI Codex CLI Provider

## Status: Accepted

## Context

ADR-0007 established the multi-provider rollout shape: a CLI-backed adapter
(`ClaudeCodeAdapter`) and a local-HTTP adapter (`OllamaAdapter`) sit behind the
same `LLMProvider` interface, load the same prompt templates, publish token
usage through the same `record_usage` seam, and are surfaced provider-agnostically
in onboarding / Settings.

A class of users runs the **OpenAI Codex CLI** (`codex`) authenticated against a
ChatGPT Plus/Pro/Business plan (or an `OPENAI_API_KEY`) and would prefer Hired.'s
calls to be billed through that, exactly as the Claude Code path lets Claude
subscribers do. Codex is the natural OpenAI-side counterpart to Claude Code, so
the question is *how* to add it, not *whether* — the interface was built for this.

## Decision

1. **`CodexCLIAdapter` invokes the local `codex` CLI via `subprocess`.** It uses
   the non-interactive headless mode:

   ```
   codex exec --json --skip-git-repo-check --sandbox read-only \
       --color never --ephemeral -
   ```

   The prompt is piped via stdin (the trailing `-`). Codex `exec` has no
   system-prompt flag, so we fold the system prompt (and any flattened few-shot
   examples) into the single stdin prompt as labelled blocks.

2. **Errors are driven off the event stream, not the exit code.** `codex exec`
   exits **0 even when the model/auth call fails**, surfacing the failure only as
   `{"type":"error"}` / `{"type":"turn.failed"}` JSONL events. The adapter
   inspects events and raises `LLMResponseError` on either, unwrapping Codex's
   nested JSON error payloads to a human-readable `error.message`. A non-zero exit
   with no agent text is still mapped to `LLMResponseError` as a backstop.

3. **`--sandbox read-only` is the safety boundary.** Codex is an agent that can
   run shell commands; our prompts are self-contained text-generation tasks, so
   read-only keeps the agent from ever writing to the user's working tree. We also
   pass `--skip-git-repo-check` (Hired. is not always launched inside a repo) and
   `--ephemeral` (no session files persisted).

4. **No model is pinned by the factory.** Like `ClaudeCodeAdapter`, the factory
   builds `CodexCLIAdapter()` with no model so the app-wide `app_config.model`
   (an Anthropic default such as `claude-opus-4-7`) never leaks into a `codex -m`
   flag. Codex uses whatever its own `~/.codex/config.toml` selects. The adapter
   *accepts* an optional `model=` for callers that want to pin one explicitly.

5. **Streaming yields a single chunk.** `codex exec --json` does not emit token
   deltas by default — it emits the full reply in one `agent_message`
   `item.completed` event. `interview_chat_stream` yields that as one chunk; the
   SSE consumer handles single- and multi-chunk streams identically.

6. **Cost label `subscription`; flagged "Experimental".** `codex_cli` →
   `subscription`, so Settings → Cost shows `$0.00 (subscription)`. The onboarding
   card and Settings status panel carry the same destructive-tone "Experimental"
   badge Claude Code does, with copy noting usage counts against the user's ChatGPT
   plan / OpenAI key and is subject to OpenAI's terms.

7. **Detection + test round-trip check login.** Detection is
   `shutil.which("codex")` → `codex --version` → `codex login status`, so the UI
   can distinguish "installed" from "installed but not logged in". The
   `test-provider` round-trip runs `codex login status` (free, fast) and maps a
   missing login to `error_kind: auth_failed` ("Run `codex login`").

## Why this shape

- **Mirror ADR-0007 exactly.** Same prompts, same `record_usage` seam, same
  metadata-driven UI registration (`GET /api/setup/providers`). The only genuinely
  new behaviour is event-stream error handling, forced by Codex's exit-0-on-error.
- **Stdin over argv.** Same reasoning as Claude Code — long CVs blow past Windows'
  ~32 KB command-line limit and quote badly. Codex's `-`/stdin contract is unbounded.
- **`codex login status` over a real generation for the health check.** Free and
  fast, and a missing login is the single most common Codex misconfiguration. A
  failed real generation is far more likely transient; the user finds out on their
  first real call either way.

## Consequences

- ✅ A ChatGPT-subscriber can pick OpenAI Codex in onboarding/Settings with no
  other code change — every business path goes through `LLMProvider`, and
  `reset_provider_cache()` reroutes the next call.
- ✅ The read-only sandbox means the agent cannot mutate the user's files even
  though Codex is a coding agent under the hood.
- ❌ Codex `exec --json` event-schema changes (event `type` names, the
  `item.completed`/`turn.completed` shapes) will land as adapter bugs. Mitigated by
  the typed error envelope and unit tests pinned to the `codex-cli 0.120.0` shape.
- ❌ No token-by-token streaming for the coach. Acceptable — the reply still arrives
  as one chunk and the UI degrades gracefully. Revisit if Codex ships a stable
  delta-streaming flag for `exec`.

## Alternatives considered

- **Use the OpenAI HTTP API directly instead of the CLI.** Rejected for this ADR:
  the explicit goal is subscription billing via the user's existing `codex login`,
  which the CLI owns. A direct `OpenAIAPIAdapter` (pay-per-token, like
  `AnthropicAPIAdapter`) is a separate, complementary follow-up.
- **`--full-auto` / writable sandbox.** Rejected — unnecessary for text generation
  and strictly more dangerous. Read-only is the right default.
- **Trust the exit code for errors.** Rejected: empirically `codex exec` returns 0
  on a 400 from the upstream model, so exit-code-only detection would silently
  return "no agent message" instead of the real cause.

## See also

- ADR-0007 — multi-provider rollout (Claude Code + Ollama) this mirrors.
- ADR-0005 — API-first decision and Risk R-01 (CLI gray zone) that the
  "Experimental" badge keeps visible.
