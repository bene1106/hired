import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { api } from '@/lib/api'

// First page the app loads. We ask the backend whether a profile exists; if
// not, the user gets the onboarding wizard. With a profile, straight to the
// main shell. Showing a tiny "checking..." text avoids a flicker while the
// fetch is in flight.
export function AppGate() {
  const [destination, setDestination] = useState<'/onboarding' | '/app' | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getProfile()
      .then((profile) => setDestination(profile === null ? '/onboarding' : '/app'))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error !== null) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <p role="alert" className="text-sm text-destructive">
          Backend not reachable: {error}
        </p>
      </main>
    )
  }

  if (destination === null) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </main>
    )
  }

  return <Navigate to={destination} replace />
}
