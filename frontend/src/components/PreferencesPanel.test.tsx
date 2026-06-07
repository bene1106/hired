import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { PreferencesPanel } from './PreferencesPanel'

import type { ProfileResponse } from '@/lib/types'

function makeProfile(overrides: Partial<ProfileResponse> = {}): ProfileResponse {
  return {
    id: 1,
    name: 'Alex K.',
    email: 'alex@example.com',
    phone: null,
    target_roles: ['Backend Engineer'],
    target_locations: ['Berlin'],
    target_salary_min: 55000,
    priorities: ['Direct impact on the product'],
    skills: [],
    work_formats: [],
    cv_text: null,
    cv_parsed_json: null,
    profile_version: 1,
    ...overrides,
  }
}

describe('PreferencesPanel', () => {
  it('pre-fills the form from the existing profile', () => {
    render(<PreferencesPanel profile={makeProfile()} onSaved={() => {}} />)

    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Berlin')).toBeInTheDocument()
    expect(screen.getByTestId('salary-min-input')).toHaveValue(55000)
    expect(screen.getByTestId('priorities-input')).toHaveValue('Direct impact on the product')
    // Save button is disabled when nothing's been touched.
    expect(screen.getByTestId('save-preferences')).toBeDisabled()
  })

  it('adds chips on Enter, removes them via the × button, and posts on save', async () => {
    const onSaved = vi.fn()
    render(<PreferencesPanel profile={makeProfile()} onSaved={onSaved} />)

    const rolesInput = screen.getByTestId('roles-input')
    await userEvent.type(rolesInput, 'Platform Engineer{Enter}')
    expect(screen.getByText('Platform Engineer')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /remove backend engineer/i }))
    expect(screen.queryByText(/^Backend Engineer$/)).not.toBeInTheDocument()

    // Dirty → save enables.
    await waitFor(() => expect(screen.getByTestId('save-preferences')).toBeEnabled())
    await userEvent.click(screen.getByTestId('save-preferences'))

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1))
    // The MSW PUT /api/profile handler echoes the body — confirm Platform
    // Engineer is the only remaining role.
    expect(onSaved.mock.calls[0][0].target_roles).toEqual(['Platform Engineer'])
    expect(screen.getByText(/Preferences saved/i)).toBeInTheDocument()
  })

  it('parses priorities one-per-line and submits an integer salary or null', async () => {
    const onSaved = vi.fn()
    render(<PreferencesPanel profile={makeProfile()} onSaved={onSaved} />)

    const salary = screen.getByTestId('salary-min-input')
    await userEvent.clear(salary)
    // Empty → null on save.

    const priorities = screen.getByTestId('priorities-input')
    await userEvent.clear(priorities)
    await userEvent.type(
      priorities,
      'Mentor or peer to learn from{Enter}Direct product ownership{Enter}{Enter}  ',
    )

    await userEvent.click(screen.getByTestId('save-preferences'))
    await waitFor(() => expect(onSaved).toHaveBeenCalled())

    const next = onSaved.mock.calls[0][0]
    expect(next.target_salary_min).toBeNull()
    expect(next.priorities).toEqual(['Mentor or peer to learn from', 'Direct product ownership'])
  })
})
