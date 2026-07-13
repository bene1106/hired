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
  it('renders all six provider cards once detection resolves', async () => {
    renderStep()

    await waitFor(() => {
      expect(screen.getByTestId('provider-card-anthropic_api')).toBeInTheDocument()
    })
    expect(screen.getByTestId('provider-card-openai_api')).toBeInTheDocument()
    expect(screen.getByTestId('provider-card-claude_code')).toBeInTheDocument()
    expect(screen.getByTestId('provider-card-codex_cli')).toBeInTheDocument()
    expect(screen.getByTestId('provider-card-ollama')).toBeInTheDocument()
    expect(screen.getByTestId('provider-card-mock')).toBeInTheDocument()
  })

  it('marks claude_code and ollama disabled when not detected', async () => {
    renderStep()
    await waitFor(() => screen.getByTestId('provider-card-claude_code'))

    expect(screen.getByTestId('provider-card-claude_code')).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByTestId('provider-card-ollama')).toHaveAttribute('aria-disabled', 'true')
  })

  it('shows an Experimental badge on the Claude Code card', async () => {
    renderStep()
    await waitFor(() => screen.getByTestId('provider-card-claude_code'))

    const card = screen.getByTestId('provider-card-claude_code')
    expect(card).toHaveTextContent(/experimental/i)
  })

  it('enables Claude Code selection when the CLI is detected', async () => {
    setMockState({
      detect: {
        anthropic_api: { key_in_env: false, key_in_keychain: false },
        openai_api: { key_in_env: false, key_in_keychain: false },
        claude_code: { detected: true, path: '/usr/local/bin/claude', version: 'claude 2.0.0' },
        codex_cli: { detected: false, path: null, version: null, logged_in: false },
        ollama: { detected: false, models: [] },
      },
    })
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-claude_code'))
    expect(screen.getByTestId('provider-card-claude_code')).toHaveAttribute(
      'aria-disabled',
      'false',
    )

    await user.click(screen.getByTestId('provider-card-claude_code'))
    // Continue stays gated on a successful test.
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: /test cli/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /continue/i })).not.toBeDisabled(),
    )
  })

  it('shows an Experimental badge on the OpenAI Codex card', async () => {
    renderStep()
    await waitFor(() => screen.getByTestId('provider-card-codex_cli'))

    const card = screen.getByTestId('provider-card-codex_cli')
    expect(card).toHaveTextContent(/experimental/i)
    // Not installed by default in the mock state → disabled.
    expect(card).toHaveAttribute('aria-disabled', 'true')
  })

  it('flags Codex as installed-but-not-logged-in', async () => {
    setMockState({
      detect: {
        anthropic_api: { key_in_env: false, key_in_keychain: false },
        openai_api: { key_in_env: false, key_in_keychain: false },
        claude_code: { detected: false, path: null, version: null },
        codex_cli: {
          detected: true,
          path: '/usr/local/bin/codex',
          version: 'codex-cli 0.120.0',
          logged_in: false,
        },
        ollama: { detected: false, models: [] },
      },
    })
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-codex_cli'))
    expect(screen.getByTestId('provider-card-codex_cli')).toHaveTextContent(/not logged in/i)
  })

  it('enables OpenAI Codex selection when the CLI is detected and logged in', async () => {
    setMockState({
      detect: {
        anthropic_api: { key_in_env: false, key_in_keychain: false },
        openai_api: { key_in_env: false, key_in_keychain: false },
        claude_code: { detected: false, path: null, version: null },
        codex_cli: {
          detected: true,
          path: '/usr/local/bin/codex',
          version: 'codex-cli 0.120.0',
          logged_in: true,
        },
        ollama: { detected: false, models: [] },
      },
    })
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-codex_cli'))
    expect(screen.getByTestId('provider-card-codex_cli')).toHaveAttribute('aria-disabled', 'false')

    await user.click(screen.getByTestId('provider-card-codex_cli'))
    // Continue stays gated on a successful test.
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: /test cli/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /continue/i })).not.toBeDisabled(),
    )
  })

  it('lists the user’s installed Ollama models in the dropdown', async () => {
    setMockState({
      detect: {
        anthropic_api: { key_in_env: false, key_in_keychain: false },
        openai_api: { key_in_env: false, key_in_keychain: false },
        claude_code: { detected: false, path: null, version: null },
        codex_cli: { detected: false, path: null, version: null, logged_in: false },
        ollama: { detected: true, models: ['qwen2.5:14b', 'llama3.2:3b'] },
      },
    })
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-ollama'))
    await user.click(screen.getByTestId('provider-card-ollama'))

    const select = screen.getByLabelText(/model/i) as HTMLSelectElement
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.value)
    expect(options).toEqual(['qwen2.5:14b', 'llama3.2:3b'])
  })

  it('lets the user pick mock and continue without testing the API', async () => {
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-mock'))
    await user.click(screen.getByTestId('provider-card-mock'))
    await user.click(screen.getByRole('button', { name: /continue/i }))

    expect(await screen.findByText('CV step')).toBeInTheDocument()
  })

  it('returns to Settings (not the CV step) when switching provider from Settings', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/onboarding/provider?return=/app/settings']}>
        <OnboardingProvider>
          <Routes>
            <Route path="/onboarding/provider" element={<ProviderStep />} />
            <Route path="/onboarding/cv" element={<div>CV step</div>} />
            <Route path="/app/settings" element={<div>Settings screen</div>} />
          </Routes>
        </OnboardingProvider>
      </MemoryRouter>,
    )

    await waitFor(() => screen.getByTestId('provider-card-mock'))
    await user.click(screen.getByTestId('provider-card-mock'))
    await user.click(screen.getByRole('button', { name: /save provider/i }))

    expect(await screen.findByText('Settings screen')).toBeInTheDocument()
    expect(screen.queryByText('CV step')).not.toBeInTheDocument()
  })

  it('lets the user choose between Anthropic models', async () => {
    setMockState({
      detect: {
        anthropic_api: { key_in_env: false, key_in_keychain: false },
        openai_api: { key_in_env: false, key_in_keychain: false },
        claude_code: { detected: false, path: null, version: null },
        codex_cli: { detected: false, path: null, version: null, logged_in: false },
        ollama: { detected: false, models: [] },
      },
    })
    const user = userEvent.setup()
    renderStep()

    await waitFor(() => screen.getByTestId('provider-card-anthropic_api'))
    await user.click(screen.getByTestId('provider-card-anthropic_api'))

    const select = screen.getByLabelText(/model/i) as HTMLSelectElement
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.value)
    expect(options).toEqual(['claude-opus-4-7', 'claude-haiku-4-5-20251001'])
    // Default is the highest-quality model.
    expect(select.value).toBe('claude-opus-4-7')
  })

  it('requires a successful test before letting the user advance with Anthropic', async () => {
    setMockState({
      detect: {
        anthropic_api: { key_in_env: false, key_in_keychain: false },
        openai_api: { key_in_env: false, key_in_keychain: false },
        claude_code: { detected: false, path: null, version: null },
        codex_cli: { detected: false, path: null, version: null, logged_in: false },
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
