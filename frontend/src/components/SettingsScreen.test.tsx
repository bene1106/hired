import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { setMockState } from '@/test/handlers'

import { SettingsScreen } from './SettingsScreen'

function renderSettings() {
  return render(
    <MemoryRouter initialEntries={['/app/settings']}>
      <Routes>
        <Route path="/app/settings" element={<SettingsScreen />} />
        <Route path="/" element={<div>Gate</div>} />
        <Route path="/app" element={<div>Main</div>} />
        <Route path="/onboarding/review" element={<div>Edit profile</div>} />
        <Route path="/onboarding/provider" element={<div>Switch provider</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SettingsScreen', () => {
  it('renders the saved profile fields', async () => {
    setMockState({
      profile: {
        id: 1,
        name: 'Alex',
        email: 'alex@example.com',
        target_roles: ['Backend Engineer'],
        target_locations: ['Berlin'],
        target_salary_min: 60000,
        priorities: ['impact'],
        cv_text: 'cv',
        cv_parsed_json: null,
        profile_version: 1,
      },
    })

    renderSettings()

    await waitFor(() => expect(screen.getByText(/alex@example.com/)).toBeInTheDocument())
    expect(screen.getByText(/backend engineer/i)).toBeInTheDocument()
  })

  it('shows the priced cost panel for anthropic_api', async () => {
    setMockState({
      cost: {
        provider: 'anthropic_api',
        label: 'priced',
        today_usd: 0.27,
        week_usd: 1.42,
        calls_today: 4,
        calls_week: 18,
      },
    })

    renderSettings()

    expect(await screen.findByText(/Today: \$0\.27 · This week: \$1\.42/)).toBeInTheDocument()
  })

  it('shows an em-dash for the mock provider in the cost panel', async () => {
    setMockState({
      cost: {
        provider: 'mock',
        label: 'unknown',
        today_usd: null,
        week_usd: null,
        calls_today: 0,
        calls_week: 0,
      },
    })

    renderSettings()

    const panel = await screen.findByTestId('cost-panel')
    expect(panel).toHaveTextContent('—')
    expect(panel).toHaveTextContent(/doesn.?t produce token counts/i)
  })

  it('shows the subscription label for claude_code', async () => {
    setMockState({
      cost: {
        provider: 'claude_code',
        label: 'subscription',
        today_usd: null,
        week_usd: null,
        calls_today: 2,
        calls_week: 5,
      },
    })

    renderSettings()

    expect(await screen.findByText('$0.00 (subscription)')).toBeInTheDocument()
  })

  it('shows the local label for ollama', async () => {
    setMockState({
      cost: {
        provider: 'ollama',
        label: 'local',
        today_usd: null,
        week_usd: null,
        calls_today: 0,
        calls_week: 0,
      },
    })

    renderSettings()

    expect(await screen.findByText('$0.00 (local)')).toBeInTheDocument()
  })

  it('asks for confirmation before deleting everything and then bounces to the gate', async () => {
    const user = userEvent.setup()
    setMockState({
      profile: {
        id: 1,
        name: 'Alex',
        email: null,
        target_roles: [],
        target_locations: [],
        target_salary_min: null,
        priorities: [],
        cv_text: null,
        cv_parsed_json: null,
        profile_version: 1,
      },
    })

    renderSettings()

    await user.click(await screen.findByRole('button', { name: /delete everything/i }))
    expect(screen.getByText(/really delete everything/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /yes, delete/i }))

    expect(await screen.findByText('Gate')).toBeInTheDocument()
  })
})
