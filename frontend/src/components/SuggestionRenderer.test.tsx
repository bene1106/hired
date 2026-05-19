import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SuggestionRenderer } from './SuggestionRenderer'

describe('SuggestionRenderer', () => {
  it('renders structured JSON: overall fit + each suggestion + type chips', () => {
    const content = JSON.stringify({
      overall_fit: 'Strong backend match, light on cloud ops.',
      suggestions: [
        {
          type: 'emphasize',
          current: 'Built APIs.',
          suggestion: 'Built and shipped FastAPI services handling 2k rps.',
          rationale: 'Quantified impact aligns with the role.',
        },
        {
          type: 'cut',
          current: 'Hobby: stamp collecting.',
          suggestion: 'Remove unrelated personal interests.',
          rationale: 'Frees space for relevant experience.',
        },
      ],
    })

    render(<SuggestionRenderer content={content} />)

    expect(screen.getByText('Strong backend match, light on cloud ops.')).toBeInTheDocument()
    expect(
      screen.getByText('Built and shipped FastAPI services handling 2k rps.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Remove unrelated personal interests.')).toBeInTheDocument()
    expect(screen.getByText('emphasize')).toBeInTheDocument()
    expect(screen.getByText('cut')).toBeInTheDocument()
  })

  it('falls back to markdown for a plain markdown string', () => {
    const content = '## CV tailoring\n\n- Emphasise FastAPI experience.'

    render(<SuggestionRenderer content={content} />)

    expect(
      screen.getByText((_, el) => el?.textContent === 'Emphasise FastAPI experience.'),
    ).toBeInTheDocument()
  })

  it('does not throw on malformed JSON and renders the markdown fallback', () => {
    const content = '{ not json'

    expect(() => render(<SuggestionRenderer content={content} />)).not.toThrow()
    // Fallback path renders the raw string inside the markdown wrapper.
    expect(document.querySelector('.prose')?.textContent).toBe(content)
  })
})
