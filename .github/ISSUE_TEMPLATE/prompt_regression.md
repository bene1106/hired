---
name: 🤖 Prompt regression
about: An LLM-generated output is wrong, low-quality, or unexpected
title: "prompt: "
labels: ["prompt-quality", "needs-triage"]
---

## Which prompt

<!-- Which file in backend/prompts/ ? -->

- File: `backend/prompts/______.md`
- Version: <!-- check the **Version:** footer in the file -->

## What was wrong

<!-- Describe the problem. Examples:
  - "Generated cover letter contained 'passionate about' despite banned-phrases filter"
  - "Score for this profile/job pair was 90, expected ~50"
  - "CV parser missed the education section entirely"
-->

## Provider used

- [ ] Anthropic API (which model?)
- [ ] Claude Code
- [ ] Ollama (which model?)
- [ ] Mock

## Reproduction

<!-- Provide the input that triggered the bad output, redacted for PII -->

**Input:**
```

```

**Bad output:**
```

```

**Expected output (or what would have been better):**
```

```

## Suspected cause

<!-- Optional. Where do you think the issue is?
  - Missing few-shot example?
  - Wrong instruction in system prompt?
  - Provider-specific issue (e.g., Ollama context too small)?
  - Edge case in input that prompt doesn't handle?
-->

## Goldset impact

<!-- If you ran the goldset evaluation, what changed?
  - precision@5 before → after
  - any specific entries flipped?
-->

## Suggested fix

<!-- Optional. If you have an idea, drop it here. -->
