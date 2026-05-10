import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { FeedItem } from '@/lib/types'
import { setMockState } from '@/test/handlers'

import { ApplicationDashboard } from './Dashboard'
import { GeneratePage } from './GeneratePage'

function seed(): FeedItem {
  return {
    job_id: 42,
    title: 'Backend Engineer',
    company: 'AcmeCo',
    location: 'Berlin',
    remote_policy: 'hybrid',
    url: 'https://example.com/jobs/42',
    score: 85,
    rationale: 'Strong match on Python and FastAPI.',
    matched_skills: ['Python'],
    missing_skills: [],
    red_flags: [],
    status: null,
  }
}

function renderRoutes(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/app/apply/:jobId" element={<GeneratePage />} />
        <Route path="/app/applications" element={<ApplicationDashboard />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('GeneratePage', () => {
  it('renders all three material sections after generation finishes', async () => {
    setMockState({ feed: [seed()] })
    renderRoutes('/app/apply/42')

    await waitFor(() => {
      expect(screen.getByTestId('section-company_brief')).toBeInTheDocument()
    })
    expect(await screen.findByText(/AcmeCo brief/i)).toBeInTheDocument()
    expect(screen.getByTestId('section-cv_suggestions')).toBeInTheDocument()
    expect(screen.getByTestId('section-cover_letter')).toBeInTheDocument()
  })

  it('saves an edited cover letter and increments the edit count', async () => {
    setMockState({ feed: [seed()] })
    renderRoutes('/app/apply/42')

    const textarea = await screen.findByLabelText(/edit/i)
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'My edited cover letter.')

    await userEvent.click(screen.getByRole('button', { name: /save edits/i }))

    await waitFor(() => {
      expect(screen.getByText(/Edited 1 time since generation/i)).toBeInTheDocument()
    })
  })

  it('marks the application applied and navigates to the dashboard', async () => {
    setMockState({ feed: [seed()] })
    renderRoutes('/app/apply/42')

    await screen.findByTestId('section-cover_letter')

    await userEvent.click(screen.getByRole('button', { name: /mark applied/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /applications/i })).toBeInTheDocument()
    })
    expect(await screen.findByText('AcmeCo')).toBeInTheDocument()
  })
})
