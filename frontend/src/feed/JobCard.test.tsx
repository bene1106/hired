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
    unread: false,
    feedback_signal: null,
    feedback_reason: null,
    ...overrides,
  }
}

describe('JobCard', () => {
  it('renders the job, company, score and matched/missing skills', () => {
    render(<JobCard item={item()} onAction={() => {}} onInteract={() => {}} />)

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
    render(<JobCard item={item()} onAction={onAction} onInteract={() => {}} />)

    await user.click(screen.getByRole('button', { name: /skip/i }))
    await user.click(screen.getByRole('button', { name: /save/i }))
    await user.click(screen.getByRole('button', { name: /apply/i }))

    expect(onAction.mock.calls.map((c) => c[0])).toEqual(['skip', 'save', 'apply'])
  })

  it('shows thumbs controls and unread dot', () => {
    render(<JobCard item={item({ unread: true })} onAction={() => {}} onInteract={() => {}} />)

    // Unread button (mark as read) should be present
    expect(screen.getByRole('button', { name: /mark as read/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /thumbs up/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /thumbs down/i })).toBeInTheDocument()
  })

  it('triggers onInteract when thumbs buttons are clicked', async () => {
    const onInteract = vi.fn()
    const user = userEvent.setup()

    render(<JobCard item={item()} onAction={() => {}} onInteract={onInteract} />)

    await user.click(screen.getByRole('button', { name: /thumbs up/i }))
    expect(onInteract).toHaveBeenCalledWith('thumbs_up')

    // Thumbs down should trigger onInteract and show reasons
    await user.click(screen.getByRole('button', { name: /thumbs down/i }))

    // Now reason buttons should be visible
    expect(screen.getByRole('button', { name: /location/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /stack/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /company/i })).toBeInTheDocument()

    // Clicking a reason triggers thumbs_down with reason
    await user.click(screen.getByRole('button', { name: /stack/i }))
    expect(onInteract).toHaveBeenCalledWith('thumbs_down', 'tech_stack')
  })

  it('disables actions while an action is pending', () => {
    render(<JobCard item={item()} onAction={() => {}} onInteract={() => {}} pending />)
    for (const name of [/skip/i, /save/i, /apply/i]) {
      expect(screen.getByRole('button', { name })).toBeDisabled()
    }
  })
})
