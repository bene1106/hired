import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { setMockState } from '@/test/handlers'

import { Sidebar } from './Sidebar'

function renderSidebar(path = '/app') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Sidebar collapsed={false} onToggle={() => {}} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})
afterEach(() => {
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

describe('Sidebar', () => {
  it('renders the brand and exactly the three live nav links', () => {
    renderSidebar()

    expect(screen.getByText('Career Agent')).toBeInTheDocument()

    const links = screen.getAllByRole('link')
    expect(links).toHaveLength(4)
    expect(screen.getByRole('link', { name: /job feed/i })).toHaveAttribute('href', '/app')
    expect(screen.getByRole('link', { name: /applications/i })).toHaveAttribute(
      'href',
      '/app/applications',
    )
    expect(screen.getByRole('link', { name: /job sources/i })).toHaveAttribute(
      'href',
      '/app/sources',
    )
    expect(screen.getByRole('link', { name: /settings/i })).toHaveAttribute('href', '/app/settings')
  })

  it('marks the active route (and not the index route on a sub-path)', () => {
    renderSidebar('/app/applications')

    expect(screen.getByRole('link', { name: /applications/i })).toHaveAttribute(
      'aria-current',
      'page',
    )
    // `end` on /app → Job Feed must NOT be active under /app/applications.
    expect(screen.getByRole('link', { name: /job feed/i })).not.toHaveAttribute('aria-current')
  })

  it('theme toggle flips the data-theme attribute', async () => {
    const user = userEvent.setup()
    renderSidebar()

    await waitFor(() => expect(document.documentElement.getAttribute('data-theme')).toBe('light'))

    await user.click(screen.getByRole('button', { name: /switch to dark mode/i }))
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')

    await user.click(screen.getByRole('button', { name: /switch to light mode/i }))
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('populates the footer from the saved profile', async () => {
    setMockState({
      profile: {
        id: 1,
        name: 'Alex Morgan',
        email: 'alex@example.com',
        phone: null,
        target_roles: ['Product Designer'],
        target_locations: ['Berlin'],
        target_salary_min: 80000,
        priorities: ['craft'],
        skills: [],
        work_formats: [],
        cv_text: 'cv',
        cv_parsed_json: null,
        profile_version: 1,
      },
    })

    renderSidebar()

    expect(await screen.findByText('Alex Morgan')).toBeInTheDocument()
    expect(screen.getByText('Product Designer · Berlin')).toBeInTheDocument()
  })

  it('falls back gracefully when no profile is saved', async () => {
    setMockState({ profile: null })
    renderSidebar()

    // getProfile() resolves to null → footer stays minimal, never crashes.
    expect(await screen.findByText('Your profile')).toBeInTheDocument()
  })
})
