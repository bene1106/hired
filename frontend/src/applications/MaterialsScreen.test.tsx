import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { setMockState } from '@/test/handlers'

import { ApplicationDetailScreen } from './ApplicationDetail'

function seedApplication() {
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
          cv_suggestions: {
            type: 'cv_suggestions',
            content: '## CV tailoring\n\n- Emphasise FastAPI.',
            source_meta: null,
            created_at: '2026-05-10T00:00:00Z',
            edit_count: 0,
          },
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
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/app/applications/1']}>
      <Routes>
        <Route path="/app/applications/:applicationId" element={<ApplicationDetailScreen />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('MaterialsScreen (detail mode)', () => {
  it('shows the job in a banner with the three materials reachable', async () => {
    seedApplication()
    renderDetail()

    const banner = await screen.findByRole('banner')
    expect(within(banner).getByRole('heading', { name: /Backend Engineer/ })).toBeInTheDocument()

    // Cover letter is the default tab and editable.
    const textarea = (await screen.findByLabelText(/edit/i)) as HTMLTextAreaElement
    expect(textarea.value).toMatch(/Dear hiring team/i)

    // Company brief is behind the Company research tab.
    await userEvent.click(screen.getByRole('button', { name: /company research/i }))
    expect(await screen.findByTestId('company-research')).toHaveTextContent(/AcmeCo brief/i)

    // CV and Interview prep tabs are offered in detail mode.
    expect(screen.getByRole('button', { name: /cv suggestions/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /interview prep/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /cv suggestions/i }))
    expect(await screen.findByText(/Emphasise FastAPI/i)).toBeInTheDocument()
  })

  it('switches application status', async () => {
    seedApplication()
    renderDetail()

    await screen.findByLabelText(/edit/i)
    const appliedBtn = screen.getByRole('button', { name: 'applied' })
    await userEvent.click(appliedBtn)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'applied' }).className).toMatch(/bg-ink/)
    })
  })

  it('shows a toast after saving the cover letter (PR D feedback gap)', async () => {
    seedApplication()
    renderDetail()

    const editor = await screen.findByLabelText(/edit/i)
    await userEvent.type(editor, ' — edited')
    await userEvent.click(screen.getByRole('button', { name: /save edits/i }))

    const toast = await screen.findByRole('status')
    expect(toast).toHaveTextContent(/cover letter saved/i)
  })
})
