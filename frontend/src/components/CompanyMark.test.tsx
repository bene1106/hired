import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CompanyMark } from './CompanyMark'

describe('CompanyMark', () => {
  it('renders the uppercased first letter of the company', () => {
    render(<CompanyMark company="lumen labs" />)
    expect(screen.getByText('L')).toBeInTheDocument()
  })

  it('is deterministic — same company keeps the same colour', () => {
    const { container: a } = render(<CompanyMark company="Acme" />)
    const { container: b } = render(<CompanyMark company="Anvil" />)
    // Same initial 'A' → same background.
    expect(a.firstElementChild?.getAttribute('style')).toContain('background')
    expect(b.firstElementChild?.getAttribute('style')).toBe(
      a.firstElementChild?.getAttribute('style'),
    )
  })

  it('falls back to ? when the company is missing', () => {
    render(<CompanyMark company={null} />)
    expect(screen.getByText('?')).toBeInTheDocument()
  })
})
