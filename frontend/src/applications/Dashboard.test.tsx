import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { FeedItem } from '@/lib/types'
import { getMockState, setMockState } from '@/test/handlers'

import { ApplicationDashboard } from './Dashboard'
import { ApplicationDetailScreen } from './ApplicationDetail'
import { GeneratePage } from './GeneratePage'

function feed(): FeedItem[] {
  return [
    {
      job_id: 1,
      title: 'Backend Engineer',
      company: 'AcmeCo',
      location: 'Berlin',
      remote_policy: 'hybrid',
      url: null,
      score: 80,
      rationale: '',
      matched_skills: [],
      missing_skills: [],
      red_flags: [],
      status: null,
    },
    {
      job_id: 2,
      title: 'Frontend Engineer',
      company: 'BetaCorp',
      location: 'Berlin',
      remote_policy: 'remote',
      url: null,
      score: 70,
      rationale: '',
      matched_skills: [],
      missing_skills: [],
      red_flags: [],
      status: null,
    },
  ]
}

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/app/apply/:jobId" element={<GeneratePage />} />
        <Route path="/app/applications" element={<ApplicationDashboard />} />
        <Route path="/app/applications/:applicationId" element={<ApplicationDetailScreen />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function seedTwoApplications() {
  setMockState({ feed: feed() })
  // Run two generations to populate the dashboard.
  for (const jobId of [1, 2]) {
    const { unmount } = renderApp(`/app/apply/${jobId}`)
    await screen.findByTestId('section-cover_letter')
    unmount()
  }
}

describe('ApplicationDashboard', () => {
  it('shows an empty state when there are no applications', async () => {
    renderApp('/app/applications')
    expect(await screen.findByText(/no applications yet/i)).toBeInTheDocument()
  })

  it('lists applications from the API', async () => {
    await seedTwoApplications()
    renderApp('/app/applications')

    expect(await screen.findByText('AcmeCo')).toBeInTheDocument()
    expect(screen.getByText('BetaCorp')).toBeInTheDocument()
  })

  it('filters by status', async () => {
    await seedTwoApplications()
    // Mark the first application applied via the mock state directly.
    const apps = getMockState().applications.map((a, idx) =>
      idx === 0 ? { ...a, status: 'applied' as const, applied_at: '2026-05-10T00:00:00Z' } : a,
    )
    setMockState({ applications: apps })

    renderApp('/app/applications')

    await screen.findByText('AcmeCo')
    await userEvent.click(screen.getByRole('button', { name: 'Applied' }))

    await waitFor(() => {
      expect(screen.queryByText('BetaCorp')).not.toBeInTheDocument()
    })
    expect(screen.getByText('AcmeCo')).toBeInTheDocument()
  })

  it('navigates to the detail view when a row is clicked', async () => {
    setMockState({
      applications: [
        {
          id: 1,
          job_id: 1,
          title: 'Backend Engineer',
          company: 'AcmeCo',
          location: 'Berlin',
          url: null,
          status: 'saved',
          applied_at: null,
          notes: null,
          materials: {
            application_id: 1,
            company_brief: {
              type: 'company_brief',
              content: '# AcmeCo brief',
              source_meta: null,
              created_at: '2026-05-10T00:00:00Z',
              edit_count: 0,
            },
            cv_suggestions: null,
            cover_letter: {
              type: 'cover_letter',
              content: 'Dear hiring team,',
              source_meta: null,
              created_at: '2026-05-10T00:00:00Z',
              edit_count: 0,
            },
          },
        },
      ],
    })

    renderApp('/app/applications')

    const acmeRow = await screen.findByTestId(/^application-row-/)
    await userEvent.click(acmeRow)

    await waitFor(() => {
      expect(
        within(screen.getByRole('banner')).getByRole('heading', { name: /Engineer/ }),
      ).toBeInTheDocument()
    })
  })
})
