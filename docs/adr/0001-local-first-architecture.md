# ADR-0001: Local-First Architecture

## Status: Accepted

## Context
We need to decide where user data and AI inference happen. Options: cloud-hosted SaaS, hybrid (cloud backend + local frontend), or fully local-first.

## Decision
Fully local-first. Tauri desktop app, SQLite local DB, AI calls go directly from user's machine to whichever provider they configured (Claude Code, Ollama, Anthropic API).

## Consequences
- ✅ Strong privacy story — no third-party cloud touches user data
- ✅ Users can use existing AI subscriptions (no extra cost)
- ✅ No backend infrastructure for us to operate or pay for
- ❌ Cross-platform packaging is harder (signed builds for 3 OSes)
- ❌ No multi-device sync (out of scope by design)
- ❌ Crawler runs from user IP, more likely to hit rate limits
