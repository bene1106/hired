import { useEffect, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'

import { onGlobalAuthError } from '@/lib/api'

import { Sidebar } from './Sidebar'

const SIDEBAR_KEY = 'hired.sidebar.open'

/**
 * 2-column app shell: resizable sidebar + flexible main column.
 * Sidebar width is 244px when open, 56px (icon-only) when collapsed.
 * State persists in localStorage.
 */
export function AppShell() {
  const [authMessage, setAuthMessage] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) !== 'false'
    } catch {
      return true
    }
  })

  useEffect(
    () =>
      onGlobalAuthError((err) => {
        setAuthMessage(err.message)
      }),
    [],
  )

  function toggleSidebar() {
    setSidebarOpen((v) => {
      const next = !v
      try {
        localStorage.setItem(SIDEBAR_KEY, String(next))
      } catch {}
      return next
    })
  }

  return (
    <div
      className="grid min-h-screen bg-background text-foreground"
      style={{ gridTemplateColumns: sidebarOpen ? '244px 1fr' : '56px 1fr' }}
    >
      <Sidebar collapsed={!sidebarOpen} onToggle={toggleSidebar} />
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
