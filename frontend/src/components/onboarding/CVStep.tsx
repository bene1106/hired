import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'

import { useOnboarding } from './OnboardingContext'

const LATENCY_HINT: Record<string, string> = {
  mock: 'instant with the mock provider',
  anthropic_api: '~10 s with the Anthropic API',
  claude_code: '~15 s with Claude Code',
  ollama: '~30 s with Ollama (depends on model)',
}

export function CVStep() {
  const navigate = useNavigate()
  const onboarding = useOnboarding()

  const [cvText, setCvText] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const latencyHint =
    onboarding.selectedProvider !== null ? LATENCY_HINT[onboarding.selectedProvider] : null

  async function submitText() {
    if (cvText.trim().length === 0) {
      setError('Paste your CV text first.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const result = await api.postCvText(cvText)
      onboarding.setCvResult(result.parsed, cvText)
      navigate('/onboarding/review')
    } catch (err) {
      setError(messageFor(err))
    } finally {
      setBusy(false)
    }
  }

  async function submitFile(file: File) {
    setBusy(true)
    setError(null)
    try {
      const result = await api.postCvUpload(file)
      onboarding.setCvResult(result.parsed, result.profile.cv_text ?? '')
      navigate('/onboarding/review')
    } catch (err) {
      setError(messageFor(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload your CV</CardTitle>
        <CardDescription>
          Drop a PDF or paste your CV text. We'll extract a structured profile from it
          {latencyHint !== null ? ` — ${latencyHint}.` : '.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="cv-pdf">Upload PDF (≤ 5 MB)</Label>
          <input
            id="cv-pdf"
            type="file"
            accept="application/pdf,.pdf"
            disabled={busy}
            onChange={(e) => {
              const file = e.currentTarget.files?.[0]
              if (file) submitFile(file)
            }}
            className="text-sm"
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="cv-text">…or paste CV text</Label>
          <Textarea
            id="cv-text"
            value={cvText}
            onChange={(e) => setCvText(e.target.value)}
            disabled={busy}
            rows={10}
            placeholder="Alex K.&#10;Backend engineer with 3 years of Python experience…"
          />
          <div className="flex justify-end">
            <Button onClick={submitText} disabled={busy || cvText.trim().length === 0}>
              {busy ? 'Parsing…' : 'Parse CV'}
            </Button>
          </div>
        </div>

        {error !== null && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function messageFor(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return String(err)
}
