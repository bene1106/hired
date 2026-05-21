import { useEffect, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'

import { onGlobalAuthError } from '@/lib/api'

import { Sidebar } from './Sidebar'

/**
 * 2-column app shell: fixed 244px sidebar + flexible main column.
 * Wraps every `/app/*` route. Onboarding and the boot gate render
 * outside the shell (no sidebar there).
 *
 * v0.3.5: subscribes to the api wrapper's global auth-error channel
 * and shows a top-of-app banner when the backend returns 401 with
 * ``error_kind=missing_api_key``. That class of error is recoverable
 * (re-enter the key in Settings) so the banner has a deep link, and
 * dismisses itself as soon as a subsequent request succeeds.
 */
export function AppShell() {
  const [authMessage, setAuthMessage] = useState<string | null>(null)

  useEffect(
    () =>
      onGlobalAuthError((err) => {
        setAuthMessage(err.message)
      }),
    [],
  )

  return (
    <div className="grid min-h-screen grid-cols-[244px_1fr] bg-background text-foreground">
      <Sidebar />
      <main className="min-w-0">
        {authMessage !== null ? (
          <div
            role="alert"
            data-testid="auth-banner"
            className="flex items-center justify-between gap-3 border-b border-warn-soft bg-warn-soft/60 px-6 py-3 text-[13px] text-ink"
          >
            <span>
              <strong className="font-semibold">Anthropic key missing.</strong> {authMessage}
            </span>
            <Link
              to="/onboarding/provider"
              onClick={() => setAuthMessage(null)}
              className="rounded-md border border-line-strong bg-surface px-3 py-1 text-[12px] font-medium text-ink hover:bg-surface-2"
            >
              Re-enter key
            </Link>
          </div>
        ) : null}
        <Outlet />
      </main>
    </div>
  )
}
