import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import App from '@/App'
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
})
