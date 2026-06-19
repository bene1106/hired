import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
      unread: false,
      feedback_signal: null,
      feedback_reason: null,
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
      unread: false,
      feedback_signal: null,
      feedback_reason: null,
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
  for (const jobId of [1, 2]) {
    const { unmount } = renderApp(`/app/apply/${jobId}`)
    await screen.findByLabelText(/edit/i)
    unmount()
  }
}

// Phase 7 PR F turned the dashboard table into a 5-column Kanban board.
// table→board is a substantial DOM change, so this file was rewritten;
// every prior behaviour is still asserted (empty state, applications
// listed, status grouping — now columns instead of a filter, row→detail
// — now card→detail) plus a new drag-to-change-status test.
describe('ApplicationDashboard (Kanban)', () => {
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

  it('places each application in its status column', async () => {
    await seedTwoApplications()
    const apps = getMockState().applications.map((a, idx) =>
      idx === 0 ? { ...a, status: 'applied' as const, applied_at: '2026-05-10T00:00:00Z' } : a,
    )
    setMockState({ applications: apps })

    renderApp('/app/applications')

    const applied = await screen.findByTestId('kanban-col-applied')
    const saved = screen.getByTestId('kanban-col-saved')
    await waitFor(() => expect(within(applied).getByText('AcmeCo')).toBeInTheDocument())
    expect(within(saved).getByText('BetaCorp')).toBeInTheDocument()
    expect(within(applied).queryByText('BetaCorp')).not.toBeInTheDocument()
  })

  it('opens the detail view when a card is activated', async () => {
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
            company_brief: null,
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

    const card = await screen.findByTestId(/^application-card-/)
    await userEvent.click(card)

    await waitFor(() => {
      expect(
        within(screen.getByRole('banner')).getByRole('heading', { name: /Engineer/ }),
      ).toBeInTheDocument()
    })
  })

  it('drag-and-drop moves a card and persists the new status', async () => {
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
            company_brief: null,
            cv_suggestions: null,
            cover_letter: null,
          },
        },
      ],
    })

    renderApp('/app/applications')

    const card = await screen.findByTestId('application-card-1')
    const appliedCol = screen.getByTestId('kanban-col-applied')

    // Code-level DnD preconditions a regression could silently break
    // (jsdom can't exercise the real Tauri/native lifecycle, but it can
    // lock these): the card must actually be draggable, and the drop
    // target must preventDefault on dragover or the browser rejects the
    // drop entirely (the classic HTML5 footgun).
    expect(card).toHaveAttribute('draggable', 'true')
    fireEvent.dragStart(card)
    // fireEvent returns false iff a handler called preventDefault.
    expect(fireEvent.dragOver(appliedCol)).toBe(false)
    fireEvent.drop(appliedCol)

    await waitFor(() => {
      expect(within(appliedCol).getByText('AcmeCo')).toBeInTheDocument()
    })
    expect(within(screen.getByTestId('kanban-col-saved')).queryByText('AcmeCo')).toBeNull()
    // Persisted: refetch reflects the new status.
    await waitFor(() => {
      expect(getMockState().applications[0].status).toBe('applied')
    })
  })
})
