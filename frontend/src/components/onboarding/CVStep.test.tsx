import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { CVStep } from './CVStep'
import { OnboardingProvider } from './OnboardingContext'

function renderStep() {
  return render(
    <MemoryRouter initialEntries={['/onboarding/cv']}>
      <OnboardingProvider>
        <Routes>
          <Route path="/onboarding/cv" element={<CVStep />} />
          <Route path="/onboarding/review" element={<div>Review step</div>} />
        </Routes>
      </OnboardingProvider>
    </MemoryRouter>,
  )
}

describe('CVStep', () => {
  it('rejects an empty paste and refuses to navigate', async () => {
    const user = userEvent.setup()
    renderStep()

    const button = screen.getByRole('button', { name: /parse cv/i })
    expect(button).toBeDisabled()

    await user.click(button)
    expect(screen.queryByText('Review step')).not.toBeInTheDocument()
  })

  it('parses pasted text and advances to Review', async () => {
    const user = userEvent.setup()
    renderStep()

    await user.type(screen.getByLabelText(/paste cv text/i), 'Alex K. — backend engineer')
    await user.click(screen.getByRole('button', { name: /parse cv/i }))

    expect(await screen.findByText('Review step')).toBeInTheDocument()
  })
})
