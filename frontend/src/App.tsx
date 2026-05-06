import { useState } from 'react'

import { HealthCheckButton } from '@/components/HealthCheckButton'

export default function App() {
  const [response, setResponse] = useState<string | null>(null)

  return (
    <main className="min-h-screen bg-background text-foreground p-8 flex flex-col items-center gap-6">
      <header className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">Hired.</h1>
        <p className="text-muted-foreground mt-1">Local-first AI career agent</p>
      </header>

      <HealthCheckButton onResult={setResponse} />

      {response !== null && (
        <pre
          aria-label="health-response"
          className="text-sm bg-muted text-muted-foreground rounded-md p-4 max-w-xl w-full overflow-auto"
        >
          {response}
        </pre>
      )}
    </main>
  )
}
