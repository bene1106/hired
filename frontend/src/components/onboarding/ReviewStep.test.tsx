import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { OnboardingProvider } from './OnboardingContext'
import { ReviewStep } from './ReviewStep'

function renderStep() {
  return render(
    <MemoryRouter initialEntries={['/onboarding/review']}>
      <OnboardingProvider
        initial={{
          cvParsed: { name: 'Alex K.', email: 'alex@example.com', skills: ['Python'] },
          cvText: 'raw cv text',
        }}
      >
        <Routes>
          <Route path="/onboarding/review" element={<ReviewStep />} />
          <Route path="/onboarding/cv" element={<div>CV step</div>} />
          <Route path="/onboarding/done" element={<div>Done step</div>} />
        </Routes>
      </OnboardingProvider>
    </MemoryRouter>,
  )
}

describe('ReviewStep', () => {
  it('pre-fills name and email from the parsed CV', async () => {
    renderStep()
    await waitFor(() =>
      expect((screen.getByLabelText(/^name/i) as HTMLInputElement).value).toBe('Alex K.'),
    )
  })

  it('rejects malformed email', async () => {
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByLabelText(/^name/i))
    const emailField = screen.getByLabelText(/email/i) as HTMLInputElement
    await user.clear(emailField)
    await user.type(emailField, 'not-an-email')
    await user.type(screen.getByLabelText(/target role/i), 'Backend')
    await user.click(screen.getByRole('button', { name: /save and continue/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/email address/i)
    expect(screen.queryByText('Done step')).not.toBeInTheDocument()
  })

  it('saves the profile and navigates to Done', async () => {
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByLabelText(/^name/i))
    await user.type(screen.getByLabelText(/target role/i), 'Backend Engineer')
    await user.click(screen.getByRole('button', { name: /save and continue/i }))

    expect(await screen.findByText('Done step')).toBeInTheDocument()
  })
})
