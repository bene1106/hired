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
    unread: false,
    feedback_signal: null,
    feedback_reason: null,
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

// The Phase 7 merge folds GeneratePage into the unified MaterialsScreen
// (tabbed). DOM changed, so these were rewritten — every prior behaviour
// is still asserted: all three materials are produced, the cover letter
// is editable with an edit count, and Mark applied lands on the dashboard.
describe('GeneratePage (generate mode)', () => {
  it('produces cover letter, CV tailoring, and company research', async () => {
    setMockState({ feed: [seed()] })
    renderRoutes('/app/apply/42')

    // Cover letter is the default tab and editable once generation lands.
    const textarea = (await screen.findByLabelText(/edit/i)) as HTMLTextAreaElement
    expect(textarea.value).toMatch(/Dear hiring team/i)

    // Company brief is always visible in the left column.
    expect(await screen.findByText(/AcmeCo brief/i)).toBeInTheDocument()

    // CV tailoring lives behind its own tab.
    await userEvent.click(screen.getByRole('button', { name: /^cv$/i }))
    expect(await screen.findByText(/Emphasise FastAPI experience/i)).toBeInTheDocument()
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

    await screen.findByLabelText(/edit/i)
    const markApplied = await screen.findByRole('button', { name: /mark applied/i })
    await waitFor(() => expect(markApplied).toBeEnabled())
    await userEvent.click(markApplied)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /applications/i })).toBeInTheDocument()
    })
    expect(await screen.findByText('AcmeCo')).toBeInTheDocument()
  })
})
