import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { MockEvaluation } from '@/lib/types'

import { MockInterviewResults } from './MockInterviewResults'

const evaluation: MockEvaluation = {
  per_question: [
    { question: 'Tell me about yourself.', rating: 85, comment: 'Strong and concrete.' },
    { question: 'A hard bug?', rating: 20, comment: 'Too vague.' },
  ],
  overall_percentage: 64,
  strengths: ['Clear structure', 'Relevant examples'],
  weaknesses: ['Quantify outcomes'],
}

describe('MockInterviewResults', () => {
  it('renders the overall score, strengths, weaknesses, and per-question feedback', () => {
    render(<MockInterviewResults evaluation={evaluation} />)

    expect(screen.getByTestId('overall-score')).toHaveTextContent('64%')
    expect(screen.getByText('Clear structure')).toBeInTheDocument()
    expect(screen.getByText('Quantify outcomes')).toBeInTheDocument()
    expect(screen.getByText('Tell me about yourself.')).toBeInTheDocument()
    expect(screen.getByText('Too vague.')).toBeInTheDocument()
    // Both per-question ratings show.
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('20')).toBeInTheDocument()
  })
})
