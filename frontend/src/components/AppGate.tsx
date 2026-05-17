import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { api } from '@/lib/api'

// The sidecar is a separate process the Tauri shell spawns at launch; on
// a cold start the webview can mount and fire this fetch a beat before
// uvicorn is bound. v0.1.0 did a single mount-time fetch with no retry,
// so any transient unreadiness was permanently fatal. Retry a bounded
// number of times with linear backoff before giving up — a slow sidecar
// now self-heals; a genuinely unreachable backend still surfaces, with
// the origin/URL baked into the message by lib/api.ts.
const MAX_ATTEMPTS = 8
const BACKOFF_MS = 500

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// First page the app loads. We ask the backend whether a profile exists; if
// not, the user gets the onboarding wizard. With a profile, straight to the
// main shell. Showing a tiny "checking..." text avoids a flicker while the
// fetch is in flight.
export function AppGate() {
  const [destination, setDestination] = useState<'/onboarding' | '/app' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(1)

  useEffect(() => {
    let cancelled = false

    async function probe() {
      for (let n = 1; n <= MAX_ATTEMPTS; n += 1) {
        if (cancelled) return
        setAttempt(n)
        try {
          const profile = await api.getProfile()
          if (cancelled) return
          setDestination(profile === null ? '/onboarding' : '/app')
          return
        } catch (err) {
          if (cancelled) return
          if (n === MAX_ATTEMPTS) {
            setError(err instanceof Error ? err.message : String(err))
            return
          }
          await sleep(BACKOFF_MS * n)
        }
      }
    }

    void probe()
    return () => {
      cancelled = true
    }
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
        <p className="text-sm text-muted-foreground">
          Connecting to backend… (attempt {attempt}/{MAX_ATTEMPTS})
        </p>
      </main>
    )
  }

  return <Navigate to={destination} replace />
}
