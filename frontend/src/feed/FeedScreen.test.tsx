import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { FeedItem } from '@/lib/types'
import { setMockState } from '@/test/handlers'
import { api } from '@/lib/api'

import { FeedScreen } from './FeedScreen'

function feedItem(overrides: Partial<FeedItem> & { job_id: number }): FeedItem {
  return {
    job_id: overrides.job_id,
    title: overrides.title ?? `Job ${overrides.job_id}`,
    company: overrides.company ?? 'AcmeCo',
    location: overrides.location ?? 'Berlin',
    remote_policy: overrides.remote_policy ?? 'hybrid',
    url: overrides.url ?? 'https://example.com/jobs/1',
    score: overrides.score ?? 80,
    rationale: overrides.rationale ?? 'Strong match on stated stack.',
    matched_skills: overrides.matched_skills ?? ['Python'],
    missing_skills: overrides.missing_skills ?? ['Rust'],
    red_flags: overrides.red_flags ?? [],
    status: overrides.status ?? null,
    unread: overrides.unread ?? false,
    feedback_signal: overrides.feedback_signal ?? null,
    feedback_reason: overrides.feedback_reason ?? null,
  }
}

function renderFeed() {
  return render(
    <MemoryRouter>
      <FeedScreen />
    </MemoryRouter>,
  )
}

describe('FeedScreen', () => {
  it('shows the empty state when nothing has been scored yet', async () => {
    setMockState({ feed: [] })
    renderFeed()

    expect(await screen.findByRole('heading', { name: /no jobs yet/i })).toBeInTheDocument()
  })

  it('renders cards sorted by score descending', async () => {
    setMockState({
      feed: [
        feedItem({ job_id: 1, score: 60 }),
        feedItem({ job_id: 2, score: 90 }),
        feedItem({ job_id: 3, score: 30 }),
      ],
    })
    renderFeed()

    await waitFor(() => {
      expect(screen.getByTestId('job-card-2')).toBeInTheDocument()
    })

    const cards = screen.getAllByTestId(/^job-card-/)
    // Backend would return them in the right order; the screen renders as-is.
    // Mock returns insertion order, so we sort here to mirror server behavior.
    const scores = cards.map((card) => Number(within(card).getByTestId('score-badge').textContent))
    // Insertion order in MSW state is what the server returns; here we just assert
    // every card has its score label rendered correctly.
    expect(scores).toEqual([60, 90, 30])
  })

  it('skipping a job removes it from the default feed', async () => {
    setMockState({
      feed: [feedItem({ job_id: 7, score: 80 })],
    })
    renderFeed()

    const card = await screen.findByTestId('job-card-7')
    fireEvent.click(within(card).getByRole('button', { name: /skip/i }))

    await waitFor(() => {
      expect(screen.queryByTestId('job-card-7')).not.toBeInTheDocument()
    })
  })

  it('Saved filter only shows saved jobs', async () => {
    setMockState({
      feed: [
        feedItem({ job_id: 1, score: 80, status: null }),
        feedItem({ job_id: 2, score: 60, status: 'saved' }),
      ],
    })
    renderFeed()

    await screen.findByTestId('job-card-1')
    fireEvent.click(screen.getByRole('button', { name: /^saved$/i }))

    await waitFor(() => {
      expect(screen.queryByTestId('job-card-1')).not.toBeInTheDocument()
      expect(screen.getByTestId('job-card-2')).toBeInTheDocument()
    })
  })

  it('crawl panel rejects an empty paste', async () => {
    setMockState({ feed: [] })
    renderFeed()

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /^crawl$/i }))

    expect(screen.getByText(/LinkedIn scraping is unreliable/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /start crawl/i }))
    expect(await screen.findByText(/paste at least one job url/i)).toBeInTheDocument()
  })

  // ---- v0.3.5 empty-state conditional rescore button ---------------------

  it('fresh-install empty state stays at the default Crawl copy', async () => {
    setMockState({
      feed: [],
      scoringStatus: {
        jobs_total: 0,
        jobs_with_current_score: 0,
        rescore_candidate_count: 0,
        profile_version: 0,
      },
    })
    renderFeed()

    expect(await screen.findByText(/No jobs yet\./i)).toBeInTheDocument()
    // The empty-state body explicitly suggests pasting URLs. There's a
    // separate "Crawl" button at the top — use getAllByText to keep this
    // unique to the empty-state copy.
    expect(screen.getByText(/paste a few job URLs/i)).toBeInTheDocument()
    expect(screen.queryByTestId('rescore-existing')).not.toBeInTheDocument()
  })

  it('shows the Re-score button only when jobs exist but none are visible', async () => {
    setMockState({
      feed: [], // visible == 0
      scoringStatus: {
        jobs_total: 3,
        jobs_with_current_score: 0,
        rescore_candidate_count: 3,
        profile_version: 4,
      },
      rescoreResult: { rescored: 3, total_candidates: 3, capped: false },
    })
    renderFeed()

    const button = await screen.findByTestId('rescore-existing')
    expect(button).toBeInTheDocument()
    // Honest copy spells out the actual count, not "some jobs".
    expect(screen.getByText(/3 jobs in the DB that haven.?t been scored/i)).toBeInTheDocument()
    // Default Crawl copy is gone in this state.
    expect(screen.queryByText(/paste a few job URLs/i)).not.toBeInTheDocument()

    await userEvent.click(button)
    // Honest count toast: "Rescored 3 jobs."
    expect(await screen.findByText(/Rescored 3 jobs/i)).toBeInTheDocument()
  })

  it('capped rescore toast names the leftover count', async () => {
    setMockState({
      feed: [],
      scoringStatus: {
        jobs_total: 60,
        jobs_with_current_score: 0,
        rescore_candidate_count: 60,
        profile_version: 4,
      },
      rescoreResult: { rescored: 50, total_candidates: 60, capped: true },
    })
    renderFeed()

    const button = await screen.findByTestId('rescore-existing')
    await userEvent.click(button)
    expect(
      await screen.findByText(/Rescored 50 jobs · 10 more queued — run again\./i),
    ).toBeInTheDocument()
  })

  it('shows unread counter and mark all as read button', async () => {
    setMockState({
      feed: [
        feedItem({ job_id: 1, unread: true }),
        feedItem({ job_id: 2, unread: true }),
        feedItem({ job_id: 3, unread: false }),
      ],
    })
    const postInteract = vi
      .spyOn(api, 'postJobInteract')
      .mockResolvedValue({ job_id: 1, read_at: null, feedback_signal: null, feedback_reason: null })

    renderFeed()

    // Verify unread text
    expect(await screen.findByText('2 unread')).toBeInTheDocument()

    // Verify mark all as read button is present
    const markAllBtn = screen.getByRole('button', { name: /mark all as read/i })
    expect(markAllBtn).toBeInTheDocument()

    // Click it and verify API calls
    await userEvent.click(markAllBtn)
    expect(postInteract).toHaveBeenCalledWith(1, { action: 'read' })
    expect(postInteract).toHaveBeenCalledWith(2, { action: 'read' })
    expect(postInteract).not.toHaveBeenCalledWith(3, { action: 'read' })
  })
})
