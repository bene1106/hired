<!--
PR title format: type(scope): description
Examples:
  feat(llm): add OllamaAdapter with local model fallback
  fix(crawler): handle LinkedIn rate-limit redirects
  docs: add ADR-0006 on caching strategy
-->

## What & Why

<!-- 1-2 sentences: what does this PR do, and why does it need to happen? -->

## Phase / Spec

<!-- Which phase spec is this part of? Link to .claude/specs/PHASE_X_*.md -->
- Phase: <!-- e.g., Phase 4 (Jobs) -->
- Acceptance criteria addressed: <!-- copy the relevant bullet(s) from the spec -->

## How to test

<!-- Walk a reviewer through testing this. Be specific. -->

```bash
# Example
cd backend && uv run pytest tests/test_scoring_service.py -v
# Then in the running app: trigger a crawl and check the feed
```

## Screenshots / Recordings

<!-- For UI changes, attach a screenshot or screen recording. Required for any frontend PR. -->

## Type of change

- [ ] feat: new feature
- [ ] fix: bug fix
- [ ] refactor: code change without behavior change
- [ ] docs: documentation only
- [ ] test: tests only
- [ ] chore: build, deps, tooling

## Checklist

### Code

- [ ] Tests added/updated for new behavior
- [ ] All tests pass locally (`uv run pytest && pnpm test`)
- [ ] Linters pass (`uv run ruff check && pnpm lint`)
- [ ] Type checks pass (`uv run mypy . && pnpm typecheck`)
- [ ] No skipped tests added without an issue link explaining why
- [ ] No hardcoded credentials or PII in code/logs

### LLM-touching changes only

- [ ] Prompt changes versioned (`**Version:** N → N+1` in the .md file)
- [ ] Goldset eval run — results in PR description (e.g., precision@5: 0.78 → 0.82)
- [ ] No new banned phrases needed (or banned-phrases list updated)
- [ ] Bias audit re-run if scoring logic changed

### Documentation

- [ ] `docs/CHANGELOG.md` updated (under `## [Unreleased]`)
- [ ] If architecture changed: ADR added in `docs/adr/`
- [ ] Module README updated if module behavior changed
- [ ] `docs/CURRENT_PHASE.md` updated if phase status changed

### Provider-specific

If this PR touches the LLM layer:

- [ ] Tested with `MockProvider` (always)
- [ ] Tested with `AnthropicAPIAdapter` (if API key available)
- [ ] Tested with `ClaudeCodeAdapter` (if applicable)
- [ ] Tested with `OllamaAdapter` (if applicable)
- [ ] Provider-specific fallbacks documented in the prompt file's "Provider Notes" section

## Risks / Concerns

<!-- Anything that worries you about this change? Performance? Edge cases? Security? Cost? -->

## Reviewer notes

<!-- Optional: anything specific you want the reviewer to look at carefully? -->
