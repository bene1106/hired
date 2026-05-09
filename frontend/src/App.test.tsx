import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import App from './App'
import { setMockState } from './test/handlers'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App router', () => {
  it('routes a fresh install to the onboarding wizard', async () => {
    setMockState({ profile: null })
    renderAt('/')

    expect(await screen.findByText(/welcome to hired/i)).toBeInTheDocument()
  })

  it('routes a user with a saved profile to the main shell', async () => {
    setMockState({
      profile: {
        id: 1,
        name: 'Alex',
        email: 'alex@example.com',
        target_roles: ['Backend'],
        target_locations: ['Berlin'],
        target_salary_min: 60000,
        priorities: ['impact'],
        cv_text: 'cv',
        cv_parsed_json: null,
      },
    })
    renderAt('/')

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /no jobs yet/i })).toBeInTheDocument()
    })
  })
})
