import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HiredLockup, HiredMark, HiredStacked, HiredWordmark } from './index'

describe('HiredWordmark', () => {
  it('renders the wordmark with a separate orange period', () => {
    const { container } = render(<HiredWordmark />)
    expect(container.textContent).toBe('hired.')
    // The period is its own span so it can carry the orange token.
    const period = screen.getByText('.')
    expect(period.tagName).toBe('SPAN')
    expect(period).toHaveStyle({ color: 'var(--brand-orange)' })
  })

  it('respects a color override', () => {
    render(<HiredWordmark color="#123456" />)
    expect(screen.getByText('hired')).toHaveStyle({ color: '#123456' })
  })
})

describe('HiredMark', () => {
  it('renders the serif h and is wired for dark-mode inversion', () => {
    render(<HiredMark size={48} />)
    const glyph = screen.getByText('h')
    // The circle fill and glyph color are token-driven so [data-theme]
    // flips them without a JS branch.
    expect(glyph).toHaveStyle({ color: 'var(--mark-h)' })
    expect(glyph.parentElement).toHaveStyle({ background: 'var(--brand-ink)' })
  })

  it('scales proportionally to the size prop', () => {
    render(<HiredMark size={110} />)
    // 58/110 reference ratio → ~58px glyph at the 110px reference size
    // (parseFloat tolerates floating-point: 110 * 58/110 ≈ 57.999…).
    const glyph = screen.getByText('h')
    expect(parseFloat(glyph.style.fontSize)).toBeCloseTo(58, 1)
    expect(glyph).toHaveStyle({ fontWeight: '900' })
    expect(glyph.style.fontFamily).toContain('Fraunces')
  })
})

describe('HiredLockup', () => {
  it('renders both the mark glyph and the wordmark', () => {
    const { container } = render(<HiredLockup />)
    expect(screen.getByText('h')).toBeInTheDocument()
    expect(container.textContent).toContain('hired.')
  })
})

describe('HiredStacked', () => {
  it('renders both the mark glyph and the wordmark', () => {
    const { container } = render(<HiredStacked />)
    expect(screen.getByText('h')).toBeInTheDocument()
    expect(container.textContent).toContain('hired.')
  })
})
