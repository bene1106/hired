import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { MockQuestion } from '@/lib/types'

const completeMockRun = vi.fn()

vi.mock('@/lib/api', () => ({
  ApiError: class ApiError extends Error {},
  api: {
    completeMockRun: (...args: unknown[]) => completeMockRun(...args),
  },
}))

import { MockInterviewRunner } from './MockInterviewRunner'

function singleQuestion(): MockQuestion[] {
  return [
    {
      category: 'technical',
      question: 'Design an idempotent endpoint.',
      rephrasing: 'How would you make a POST safe to retry?',
      time_limit_seconds: 180,
      is_intro: false,
    },
  ]
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('MockInterviewRunner', () => {
  it('runs a single-question interview and submits the transcript', async () => {
    completeMockRun.mockResolvedValue({ id: 1 })
    const onClose = vi.fn()

    render(
      <MockInterviewRunner
        applicationId={7}
        interviewId={3}
        runId={9}
        questions={singleQuestion()}
        onClose={onClose}
      />,
    )

    expect(screen.getByTestId('runner-question')).toHaveTextContent('idempotent')
    // Submit is gated until the min window passes.
    expect(screen.getByTestId('runner-submit')).toBeDisabled()

    // Type an answer (set the controlled value the React way).
    const box = screen.getByTestId('runner-answer') as HTMLTextAreaElement
    act(() => {
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        'value',
      )?.set
      setter?.call(box, 'my answer')
      box.dispatchEvent(new Event('input', { bubbles: true }))
    })

    // Advance past the 15s min window with no further typing: the runner
    // auto-advances on inactivity and, being the only question, completes.
    await act(async () => {
      vi.advanceTimersByTime(16_000)
      await Promise.resolve()
    })

    expect(completeMockRun).toHaveBeenCalledWith(7, 3, 9, [
      expect.objectContaining({ answer: 'my answer', skipped: false }),
    ])
    expect(screen.getByTestId('runner-complete')).toBeInTheDocument()
  })
})
