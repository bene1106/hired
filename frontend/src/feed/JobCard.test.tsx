import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { FeedItem } from '@/lib/types'

import { JobCard } from './JobCard'

function item(overrides: Partial<FeedItem> = {}): FeedItem {
  return {
    job_id: 42,
    title: 'Backend Engineer',
    company: 'Lumen Labs',
    location: 'Berlin',
    remote_policy: 'hybrid',
    url: 'https://example.com/jobs/42',
    score: 88,
    rationale: 'Strong match on the stated Python stack.',
    matched_skills: ['Python'],
    missing_skills: ['Rust'],
    red_flags: [],
    status: null,
    ...overrides,
  }
}

describe('JobCard', () => {
  it('renders the job, company, score and matched/missing skills', () => {
    render(<JobCard item={item()} onAction={() => {}} />)

    expect(screen.getByTestId('job-card-42')).toBeInTheDocument()
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Lumen Labs')).toBeInTheDocument()
    expect(screen.getByTestId('score-badge').textContent).toBe('88')
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Rust')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view posting/i })).toHaveAttribute(
      'href',
      'https://example.com/jobs/42',
    )
  })

  it('wires Skip/Save/Apply to onAction', async () => {
    const onAction = vi.fn()
    const user = userEvent.setup()
    render(<JobCard item={item()} onAction={onAction} />)

    await user.click(screen.getByRole('button', { name: /skip/i }))
    await user.click(screen.getByRole('button', { name: /save/i }))
    await user.click(screen.getByRole('button', { name: /apply/i }))

    expect(onAction.mock.calls.map((c) => c[0])).toEqual(['skip', 'save', 'apply'])
  })

  it('has no up/down feedback controls (deferred to Phase 9)', () => {
    render(<JobCard item={item()} onAction={() => {}} />)

    expect(
      screen.queryByRole('button', { name: /good match|bad match|thumb|feedback/i }),
    ).toBeNull()
    // Exactly the three action buttons.
    expect(screen.getAllByRole('button')).toHaveLength(3)
  })

  it('disables actions while an action is pending', () => {
    render(<JobCard item={item()} onAction={() => {}} pending />)
    for (const name of [/skip/i, /save/i, /apply/i]) {
      expect(screen.getByRole('button', { name })).toBeDisabled()
    }
  })
})
