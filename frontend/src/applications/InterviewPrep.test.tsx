import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { setMockState } from '@/test/handlers'

import { InterviewPrep } from './InterviewPrep'

describe('InterviewPrep', () => {
  it('renders questions grouped by category', async () => {
    render(<InterviewPrep applicationId={42} />)

    expect(await screen.findByText('Technical')).toBeInTheDocument()
    expect(screen.getByText('Behavioral')).toBeInTheDocument()
    expect(screen.getByText('Tell me about a tough debugging session.')).toBeInTheDocument()
  })

  it('submits an answer and shows feedback', async () => {
    render(<InterviewPrep applicationId={42} />)

    const question = await screen.findByText('How would you design an idempotent endpoint?')
    await userEvent.click(question)

    const textarea = screen.getByLabelText(/practice answer/i)
    await userEvent.type(textarea, 'I would use a request id key in a deduping table.')

    await userEvent.click(screen.getByRole('button', { name: /get feedback/i }))

    expect(await screen.findByText('Stronger version stub.')).toBeInTheDocument()
    expect(screen.getByText(/Could be more specific/i)).toBeInTheDocument()
  })

  it('marks a question as practiced after submission', async () => {
    setMockState({
      practiceAttempts: {
        42: [
          {
            id: 1,
            question: 'Tell me about a tough debugging session.',
            category: 'behavioral',
            answer: 'I once...',
            feedback: {
              what_worked: ['ok'],
              what_to_improve: [],
              sample_stronger_answer: '...',
              off_topic: false,
            },
            created_at: '2026-05-10T00:00:00Z',
          },
        ],
      },
    })

    render(<InterviewPrep applicationId={42} />)

    expect(await screen.findByText(/✓ Practiced/i)).toBeInTheDocument()
  })
})
