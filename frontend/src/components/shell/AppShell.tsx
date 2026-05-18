import { Outlet } from 'react-router-dom'

import { Sidebar } from './Sidebar'

/**
 * 2-column app shell: fixed 244px sidebar + flexible main column.
 * Wraps every `/app/*` route. Onboarding and the boot gate render
 * outside the shell (no sidebar there).
 *
 * Existing screens render unchanged inside `<Outlet/>`; their own
 * in-screen headers are stripped when each is restyled in PRs C–G.
 */
export function AppShell() {
  return (
    <div className="grid min-h-screen grid-cols-[244px_1fr] bg-background text-foreground">
      <Sidebar />
      <main className="min-w-0">
        <Outlet />
      </main>
    </div>
  )
}
