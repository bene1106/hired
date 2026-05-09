import { Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'

export function MainShell() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold tracking-tight">Hired.</h1>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => alert('Crawl is wired up in Phase 4.')}>
            Crawl
          </Button>
          <Button
            size="icon"
            variant="ghost"
            aria-label="Settings"
            onClick={() => navigate('/app/settings')}
          >
            <Settings />
          </Button>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center p-12">
        <div className="text-center">
          <h2 className="text-xl font-medium">No jobs yet.</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Click <strong>Crawl</strong> to find jobs matching your profile.
          </p>
        </div>
      </main>

      <footer className="flex items-center justify-end border-t border-border px-6 py-2">
        <ProviderStatusDot />
      </footer>
    </div>
  )
}

function ProviderStatusDot() {
  // TODO(phase-4): wire up to /api/setup/provider-status. Phase 3 just shows
  // a steady "ready" indicator.
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span aria-hidden className="h-2 w-2 rounded-full bg-emerald-500" />
      Provider ready
    </div>
  )
}
