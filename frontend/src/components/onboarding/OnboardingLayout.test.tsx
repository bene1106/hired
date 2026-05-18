import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { OnboardingLayout } from './OnboardingLayout'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/onboarding" element={<OnboardingLayout />}>
          <Route path="cv" element={<div>step body</div>} />
          <Route path="done" element={<div>step body</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('OnboardingLayout', () => {
  it('renders the stepper, marks the active step, and is not navigable', () => {
    renderAt('/onboarding/cv')

    const stepper = screen.getByRole('list', { name: /onboarding steps/i })
    for (const label of ['Welcome', 'Provider', 'Upload CV', 'Review', 'Done']) {
      expect(within(stepper).getByText(label)).toBeInTheDocument()
    }

    // Guard-rail: the stepper is display-only — no links or buttons to
    // jump steps.
    expect(within(stepper).queryAllByRole('link')).toHaveLength(0)
    expect(within(stepper).queryAllByRole('button')).toHaveLength(0)

    const active = stepper.querySelector('[aria-current="step"]')
    expect(active).not.toBeNull()
    expect(active).toHaveTextContent('Upload CV')
  })

  it('shows per-route hero copy', () => {
    renderAt('/onboarding/cv')
    expect(screen.getByRole('heading', { name: /let's get your agent ready/i })).toBeInTheDocument()

    renderAt('/onboarding/done')
    expect(screen.getByRole('heading', { name: /your agent is ready/i })).toBeInTheDocument()
  })
})
