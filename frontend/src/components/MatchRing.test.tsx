import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MatchRing } from './MatchRing'

function progressStroke(container: HTMLElement): string | null {
  // Second <circle> is the progress arc; the first is the track.
  const circles = container.querySelectorAll('circle')
  return circles[1]?.getAttribute('stroke') ?? null
}

describe('MatchRing', () => {
  it('renders the exact score as the score-badge text (deterministic, no count-up)', () => {
    render(<MatchRing score={73} />)
    const badge = screen.getByTestId('score-badge')
    expect(badge.textContent).toBe('73')
  })

  it('exposes an accessible match label', () => {
    render(<MatchRing score={88} />)
    expect(screen.getByLabelText('Match score 88 out of 100')).toBeInTheDocument()
  })

  it('uses semantic colour buckets', () => {
    const { container: high } = render(<MatchRing score={85} />)
    expect(progressStroke(high)).toBe('var(--accent)')

    const { container: mid } = render(<MatchRing score={70} />)
    expect(progressStroke(mid)).toBe('var(--info)')

    const { container: low } = render(<MatchRing score={69} />)
    expect(progressStroke(low)).toBe('var(--ink-3)')
  })
})
