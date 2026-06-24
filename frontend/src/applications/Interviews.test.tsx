import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Interview } from '@/lib/types'

// Mock the api module directly: keeps this test self-contained and off the
// fetch path entirely.
const listInterviews = vi.fn()
const createInterview = vi.fn()
const updateInterview = vi.fn()
const deleteInterview = vi.fn()
const prepareInterviewQuestions = vi.fn()

vi.mock('@/lib/api', () => ({
  ApiError: class ApiError extends Error {},
  api: {
    listInterviews: (...args: unknown[]) => listInterviews(...args),
    createInterview: (...args: unknown[]) => createInterview(...args),
    updateInterview: (...args: unknown[]) => updateInterview(...args),
    deleteInterview: (...args: unknown[]) => deleteInterview(...args),
    prepareInterviewQuestions: (...args: unknown[]) => prepareInterviewQuestions(...args),
  },
}))

import { InterviewsSection } from './Interviews'

function makeInterview(overrides: Partial<Interview> = {}): Interview {
  return {
    id: 1,
    application_id: 7,
    round_number: 1,
    interview_type: 'technical',
    duration_minutes: 30,
    interviewer_gender: 'female',
    scheduled_at: null,
    is_upcoming: true,
    question_count: 0,
    questions: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('InterviewsSection', () => {
  it('lists interviews with an upcoming badge', async () => {
    listInterviews.mockResolvedValue([makeInterview({ question_count: 5 })])
    render(<InterviewsSection applicationId={7} />)

    await waitFor(() => screen.getByTestId('interview-item-1'))
    const row = screen.getByTestId('interview-item-1')
    expect(row).toHaveTextContent(/Round 1/)
    expect(row).toHaveTextContent(/Technical/)
    expect(row).toHaveTextContent(/Upcoming/)
    expect(row).toHaveTextContent(/5 questions ready/)
  })

  it('disables Start mock interview until questions are prepared', async () => {
    listInterviews.mockResolvedValue([makeInterview({ question_count: 0 })])
    render(<InterviewsSection applicationId={7} />)

    await waitFor(() => screen.getByTestId('interview-item-1'))
    expect(screen.getByTestId('start-mock-1')).toBeDisabled()
  })

  it('disables Start mock interview for past interviews even with questions', async () => {
    listInterviews.mockResolvedValue([makeInterview({ is_upcoming: false, question_count: 5 })])
    render(<InterviewsSection applicationId={7} />)

    await waitFor(() => screen.getByTestId('interview-item-1'))
    expect(screen.getByTestId('start-mock-1')).toBeDisabled()
    expect(screen.getByTestId('interview-item-1')).toHaveTextContent(/Past/)
  })

  it('creates a new interview through the form', async () => {
    listInterviews.mockResolvedValueOnce([])
    createInterview.mockResolvedValue(makeInterview())
    listInterviews.mockResolvedValueOnce([makeInterview()])
    const user = userEvent.setup()
    render(<InterviewsSection applicationId={7} />)

    await waitFor(() => screen.getByTestId('add-interview'))
    await user.click(screen.getByTestId('add-interview'))

    const form = screen.getByTestId('interview-form')
    await user.clear(within(form).getByLabelText(/duration/i))
    await user.type(within(form).getByLabelText(/duration/i), '45')
    await user.click(screen.getByTestId('submit-interview'))

    await waitFor(() => expect(createInterview).toHaveBeenCalledTimes(1))
    expect(createInterview).toHaveBeenCalledWith(
      7,
      expect.objectContaining({ duration_minutes: 45, interview_type: 'hr' }),
    )
  })

  it('prepares questions and reflects the new count', async () => {
    listInterviews.mockResolvedValue([makeInterview({ question_count: 0 })])
    prepareInterviewQuestions.mockResolvedValue(makeInterview({ question_count: 5, questions: [] }))
    const user = userEvent.setup()
    render(<InterviewsSection applicationId={7} />)

    await waitFor(() => screen.getByTestId('prepare-questions-1'))
    await user.click(screen.getByTestId('prepare-questions-1'))

    await waitFor(() => expect(prepareInterviewQuestions).toHaveBeenCalledWith(7, 1))
    await waitFor(() =>
      expect(screen.getByTestId('interview-item-1')).toHaveTextContent(/5 questions ready/),
    )
    expect(screen.getByTestId('start-mock-1')).not.toBeDisabled()
  })
})
