import { act, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import App from '@/App'
import { ApiError, __test_dispatchAuthError } from '@/lib/api'
import { setMockState } from '@/test/handlers'

import { AppShell } from './AppShell'

describe('AppShell', () => {
  it('renders the sidebar around the routed screen', () => {
    render(
      <MemoryRouter initialEntries={['/app/example']}>
        <Routes>
          <Route path="/app" element={<AppShell />}>
            <Route path="example" element={<div>ROUTED SCREEN</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Career Agent')).toBeInTheDocument()
    expect(screen.getByText('ROUTED SCREEN')).toBeInTheDocument()
  })

  it('does not wrap onboarding in the shell', () => {
    setMockState({ profile: null })
    render(
      <MemoryRouter initialEntries={['/onboarding/welcome']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText(/welcome to hired/i)).toBeInTheDocument()
    // The sidebar's distinctive tagline must be absent outside /app.
    expect(screen.queryByText('Career Agent')).not.toBeInTheDocument()
  })

  it('surfaces a global banner with re-enter link when a 401 missing_api_key lands', () => {
    render(
      <MemoryRouter initialEntries={['/app/example']}>
        <Routes>
          <Route path="/app" element={<AppShell />}>
            <Route path="example" element={<div>SCREEN</div>} />
          </Route>
          <Route path="/onboarding/provider" element={<div>PROVIDER STEP</div>} />
        </Routes>
      </MemoryRouter>,
    )

    // No banner until a 401 hits.
    expect(screen.queryByTestId('auth-banner')).not.toBeInTheDocument()

    // Simulate the api.ts wrapper dispatching after a 401 response with
    // ``error_kind=missing_api_key``. ``__test_dispatchAuthError`` is the
    // test-only entry into the same subscriber set the production fetch
    // hits — keeps this assertion focused on the UI, not on MSW round-trips.
    act(() => {
      __test_dispatchAuthError(
        new ApiError(401, 'Anthropic key is not configured.', {
          detail: 'Anthropic key is not configured.',
          error_kind: 'missing_api_key',
        }),
      )
    })

    expect(screen.getByTestId('auth-banner')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /re-enter key/i })).toHaveAttribute(
      'href',
      '/onboarding/provider',
    )
  })
})
