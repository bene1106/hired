import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { setMockState } from '@/test/handlers'

import { ApplicationDetailScreen } from './ApplicationDetail'

// Mock the PDF helpers: jsPDF's `save()` is not jsdom-friendly, and these tests
// only care about *what* the CV export is handed — not the bytes it produces.
vi.mock('@/lib/pdf', () => ({
  downloadCvPdf: vi.fn(),
  downloadCoverLetterPdf: vi.fn(),
}))

import { downloadCvPdf } from '@/lib/pdf'

beforeEach(() => {
  vi.clearAllMocks()
})

function seedProfileCv(cvText: string) {
  setMockState({
    profile: {
      id: 1,
      name: 'Jane Doe',
      email: null,
      target_roles: [],
      target_locations: [],
      target_salary_min: null,
      priorities: [],
      cv_text: cvText,
      cv_parsed_json: null,
      profile_version: 1,
    },
  })
}

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

    // Company brief retained as the secondary "Company research" block.
    expect(screen.getByTestId('company-research')).toHaveTextContent(/AcmeCo brief/i)

    // CV behind its tab; Interview prep is offered in detail mode.
    expect(screen.getByRole('button', { name: /^cv$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /interview prep/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /^cv$/i }))
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

  it('offers a Download PDF button on the cover letter and CV tabs', async () => {
    seedApplication()
    renderDetail()

    // Cover letter tab (default) exposes a PDF download.
    await screen.findByLabelText(/edit cover letter/i)
    expect(screen.getByRole('button', { name: /download pdf/i })).toBeInTheDocument()

    // CV tab exposes its own PDF download.
    await userEvent.click(screen.getByRole('button', { name: /^cv$/i }))
    expect(await screen.findByText(/Emphasise FastAPI/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download pdf/i })).toBeInTheDocument()
  })

  it('exports the finished CV (profile cv_text), never the tailoring analysis, and toasts', async () => {
    seedApplication()
    seedProfileCv('JANE DOE\nSenior Engineer\n\nEXPERIENCE\n- Built FastAPI services')
    renderDetail()

    await screen.findByLabelText(/edit/i)
    await userEvent.click(screen.getByRole('button', { name: /^cv$/i }))

    // The analysis (cv_suggestions) stays visible in the UI...
    expect(await screen.findByText(/Emphasise FastAPI/i)).toBeInTheDocument()

    // ...but the CV export is the résumé, enabled once the profile loads.
    const downloadBtn = screen.getByRole('button', { name: /download pdf/i })
    await waitFor(() => expect(downloadBtn).toBeEnabled())
    await userEvent.click(downloadBtn)

    expect(downloadCvPdf).toHaveBeenCalledTimes(1)
    const arg = vi.mocked(downloadCvPdf).mock.calls[0][0]
    expect(arg.content).toContain('JANE DOE')
    expect(arg.content).not.toMatch(/suggestion|rationale|overall_fit|Emphasise FastAPI/i)

    const toast = await screen.findByRole('status')
    expect(toast).toHaveTextContent(/cv pdf saved/i)
  })

  it('disables the CV Download until a profile CV exists', async () => {
    seedApplication() // no profile seeded → getProfile 404 → no cv_text
    renderDetail()

    await screen.findByLabelText(/edit/i)
    await userEvent.click(screen.getByRole('button', { name: /^cv$/i }))
    await screen.findByText(/Emphasise FastAPI/i)

    expect(screen.getByRole('button', { name: /download pdf/i })).toBeDisabled()
  })

  it('toggles the cover letter between edit and preview', async () => {
    seedApplication()
    renderDetail()

    const editor = (await screen.findByLabelText(/edit cover letter/i)) as HTMLTextAreaElement
    expect(editor.value).toMatch(/Dear hiring team/i)

    await userEvent.click(screen.getByRole('tab', { name: /preview/i }))
    // The textarea is replaced by the rendered preview.
    expect(screen.queryByLabelText(/edit cover letter/i)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /^edit$/i }))
    expect(await screen.findByLabelText(/edit cover letter/i)).toBeInTheDocument()
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
