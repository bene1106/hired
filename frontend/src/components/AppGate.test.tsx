import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { server } from '@/test/server'

import { AppGate } from './AppGate'

const BACKEND = 'http://localhost:8765'

function renderGate() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<AppGate />} />
        <Route path="/onboarding" element={<div data-testid="dest-onboarding" />} />
        <Route path="/app" element={<div data-testid="dest-app" />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AppGate cold-start retry (v0.3.3 regression)', () => {
  it('shows elapsed-seconds copy while the backend is still booting', async () => {
    // Sidecar dead for the lifetime of this test: every probe fails.
    server.use(http.get(`${BACKEND}/api/profile`, () => HttpResponse.error()))
    renderGate()

    // First render shows attempt 1 immediately.
    const status = await screen.findByTestId('app-gate-status')
    expect(status).toHaveTextContent(/Connecting to backend… \(1s\)/)
    // Not the old "attempt 1/8" copy.
    expect(status.textContent).not.toMatch(/attempt \d+\/\d+/)
  })

  it('survives a slow cold start by retrying past attempt 8', async () => {
    // Sidecar boots only on the 12th probe — well past the old 8-attempt
    // budget. AppGate must keep polling until success.
    let probeCount = 0
    server.use(
      http.get(`${BACKEND}/api/profile`, () => {
        probeCount += 1
        if (probeCount < 12) return HttpResponse.error()
        return HttpResponse.json({
          id: 1,
          name: 'Alex',
          email: 'alex@example.com',
          target_roles: [],
          target_locations: [],
          target_salary_min: null,
          priorities: [],
          cv_text: null,
          cv_parsed_json: null,
          profile_version: 0,
        })
      }),
    )
    renderGate()

    // Cap at 30s so the test never runs to the new 60s ceiling.
    await waitFor(() => expect(screen.getByTestId('dest-app')).toBeInTheDocument(), {
      timeout: 30_000,
    })
    expect(probeCount).toBeGreaterThanOrEqual(12)
  }, 35_000)
})
