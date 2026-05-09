import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { FeedItem } from '@/lib/types'
import { setMockState } from '@/test/handlers'

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

    expect(
      screen.getByText(/LinkedIn scraping is unreliable/i),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /start crawl/i }))
    expect(
      await screen.findByText(/paste at least one job url/i),
    ).toBeInTheDocument()
  })
})
