import { fireEvent, render, screen } from '@testing-library/react'
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

  it('highlights the dropzone while a file is dragged over it', () => {
    renderStep()
    const dropzone = screen.getByText(/drop your cv here/i).closest('label') as HTMLElement

    // Idle: neutral surface, hover-only accent.
    expect(dropzone.className).toContain('bg-surface-2')

    fireEvent.dragOver(dropzone)
    expect(dropzone.className).not.toContain('bg-surface-2')
    expect(dropzone.className).toContain('border-brand-green')

    fireEvent.dragLeave(dropzone)
    expect(dropzone.className).toContain('bg-surface-2')
  })

  it('clears the drag highlight after a drop', () => {
    renderStep()
    const dropzone = screen.getByText(/drop your cv here/i).closest('label') as HTMLElement

    fireEvent.dragEnter(dropzone)
    expect(dropzone.className).not.toContain('bg-surface-2')

    fireEvent.drop(dropzone, { dataTransfer: { files: [] } })
    expect(dropzone.className).toContain('bg-surface-2')
  })
})
