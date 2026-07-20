# Phase 10+ Vision: Full Automation

## Context

Bene's longer-term vision for Hired., explicitly deferred from current Phase 7-9 
roadmap. NOT to influence current PR scope.

## Vision

The endgame is a fully autonomous career agent. Today's manual UI shipped in Phase 7 
is the honest current state — but the system should ultimately:

### 1. Auto-detect Application Status from Email
- Read Gmail (OAuth) for replies from companies
- Parse status changes: applied confirmation → "Thanks for applying", 
  rejection → "We've decided to move forward with other candidates", 
  interview → "We'd like to schedule a call"
- Update Kanban automatically

### 2. Auto-crawl Job Sources
- Scheduled (e.g., daily) discovery of new jobs matching profile
- Sources: LinkedIn job alerts, Greenhouse public boards, RSS feeds, 
  newsletter parsing
- Auto-score and surface high-match items in feed

### 3. Auto-submit Applications
- LinkedIn Easy Apply API where available
- Form-filling via browser automation for company sites
- Pre-filled from generated materials (cover letter + tailored CV)
- Human-in-the-loop for final approval (toggle: auto-submit OR review-then-submit)

### 4. AI-driven Recruiter Communication
- Reply to recruiter emails via Gmail API
- Tone-matched, context-aware (knows the application, the CV, the cover letter)
- Human-in-the-loop for sensitive turns (salary, accept/decline)

## Estimated Phasing

| Phase | Scope | Complexity |
|-------|-------|------------|
| ~~Phase 10~~ | Email-Reading (Gmail API) + status auto-detect — **deferred**, see below | Medium |
| Phase 11 | Auto-Crawl (newsletter, RSS, LinkedIn alerts) | High — adapter per source |
| Phase 12 | Auto-Submission (Easy Apply + form automation) | Very high — anti-bot, per-site |
| Phase 13 | Auto-Reply | High — tone, accountability, legal-risk |

> **Deferred (2026-07-20).** Phase 10 was reassigned to CV templates, gap
> detection, and evaluation — see `docs/phases/PHASE_10.md`. Email reading is
> not cancelled, but it is not next, for three reasons:
>
> 1. **It breaks the privacy story.** Everything else here runs locally or sends
>    one user-triggered prompt. Gmail OAuth means a persistent token with read
>    access to the entire inbox — categorically larger than anything the app
>    does today, and hard to reconcile with PROJECT_DOC §7.
> 2. **It is the largest remaining item, not the smallest.** OAuth, token
>    refresh, message parsing, and status classification is a phase on its own.
> 3. **Nothing depends on it.** The Kanban board works with manual status updates.
>
> If it returns it should come back as its own phase with its own ADR covering
> the privacy trade-off, not folded into another phase.

## Implications for Current Phases (7-9)

The current manual UI should not be designed around eventual autonomy. Honest copy 
about today's behavior. When autonomy ships, copy and UI changes will be explicit 
in the relevant phase's PRs.

What WAS deferred from Phase 7 due to autonomy not being ready:
- Agent-status-card in sidebar (would advertise non-existent autonomy)
- "Your agent scans every morning" in onboarding completion copy
- Auto-discovery hints in empty states
- Auto-status-change notifications

These can return in Phase 10 when the autonomy behind them exists.

## Backend Optimizations Discovered During Phase 7

Items that are not full autonomy but enable parts of it:
- Score on ApplicationSummary (via JOIN with jobs table) — would enable MatchRing 
  in Kanban + Detail views. Currently in Phase 7 these views omit MatchRing for 
  honesty. Could land in Phase 10 alongside email-status-detection.
- CompanyMark fallback — backend company parser is unreliable; improving it would 
  populate the CompanyMark initial across the app.
- Bitpanda title parsing issue — generic parser fix, separate backend PR.
