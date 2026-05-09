import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { setMockState } from '@/test/handlers'

import { OnboardingProvider } from './OnboardingContext'
import { ProviderStep } from './ProviderStep'

function renderStep() {
  return render(
    <MemoryRouter initialEntries={['/onboarding/provider']}>
      <OnboardingProvider>
        <Routes>
          <Route path="/onboarding/provider" element={<ProviderStep />} />
          <Route path="/onboarding/cv" element={<div>CV step</div>} />
        </Routes>
      </OnboardingProvider>
    </MemoryRouter>,
  )
}

describe('ProviderStep', () => {
  it('renders all four provider cards once detection resolves', async () => {
    renderStep()

    await waitFor(() => {
      expect(screen.getByTestId('provider-card-anthropic_api')).toBeInTheDocument()
    })
    expect(screen.getByTestId('provider-card-claude_code')).toBeInTheDocument()
    expect(screen.getByTestId('provider-card-ollama')).toBeInTheDocument()
    expect(screen.getByTestId('provider-card-mock')).toBeInTheDocument()
  })

  it('marks claude_code and ollama disabled when not detected', async () => {
    renderStep()
    await waitFor(() => screen.getByTestId('provider-card-claude_code'))

    expect(screen.getByTestId('provider-card-claude_code')).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByTestId('provider-card-ollama')).toHaveAttribute('aria-disabled', 'true')
  })

  it('lets the user pick mock and continue without testing the API', async () => {
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-mock'))
    await user.click(screen.getByTestId('provider-card-mock'))
    await user.click(screen.getByRole('button', { name: /continue/i }))

    expect(await screen.findByText('CV step')).toBeInTheDocument()
  })

  it('requires a successful test before letting the user advance with Anthropic', async () => {
    setMockState({
      detect: {
        anthropic_api: { key_in_env: false, key_in_keychain: false },
        claude_code: { detected: false, path: null, version: null },
        ollama: { detected: false, models: [] },
      },
    })
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-anthropic_api'))
    await user.click(screen.getByTestId('provider-card-anthropic_api'))

    // Without a test connection, Continue stays disabled.
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()

    await user.type(screen.getByLabelText(/api key/i), 'sk-ant-fake')
    await user.click(screen.getByRole('button', { name: /test connection/i }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /continue/i })).not.toBeDisabled(),
    )
  })
})
