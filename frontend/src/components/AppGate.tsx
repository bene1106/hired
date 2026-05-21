import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { api } from '@/lib/api'

// The sidecar is a separate process the Tauri shell spawns at launch; on
// a cold start the webview can mount and fire this fetch a beat before
// uvicorn is bound. v0.1.0 did a single mount-time fetch with no retry,
// so any transient unreadiness was permanently fatal. v0.1.1 added
// linear backoff for 8 attempts (~14s total) — fine for warm starts.
//
// v0.3.3 widens the window to ~60s after a real cold-start regression on
// Bene's machine: on the first launch after a reinstall, PyInstaller
// extracts the bundle to a temp dir, Windows Defender scans the .exe,
// the first import of anthropic/pydantic warms from cold disk, and
// uvicorn doesn't bind until all of that completes. We observed ~30–60s
// on a Windows 11 / Ryzen / Defender-on box. AppGate now polls every
// 1s for up to 60 attempts; the progress copy shows elapsed seconds so
// the user can see it's working rather than "Failed to fetch".
const MAX_ATTEMPTS = 60
const POLL_INTERVAL_MS = 1000

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// First page the app loads. We ask the backend whether a profile exists; if
// not, the user gets the onboarding wizard. With a profile, straight to the
// main shell. Showing a "connecting (Xs)" text reassures the user during
// the cold-start window.
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
          await sleep(POLL_INTERVAL_MS)
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
          Backend not reachable after {MAX_ATTEMPTS}s: {error}
        </p>
      </main>
    )
  }

  if (destination === null) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <p className="text-sm text-muted-foreground" data-testid="app-gate-status">
          Connecting to backend… ({attempt}s)
        </p>
      </main>
    )
  }

  return <Navigate to={destination} replace />
}
