import { useState } from 'react'

const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? 'http://localhost:8765'

interface HealthCheckButtonProps {
  onResult: (text: string) => void
}

export function HealthCheckButton({ onResult }: HealthCheckButtonProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleClick() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${BACKEND_URL}/health`)
      const text = await res.text()
      onResult(text)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="rounded-md bg-primary text-primary-foreground px-4 py-2 font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {loading ? 'Checking…' : 'Run health check'}
      </button>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
