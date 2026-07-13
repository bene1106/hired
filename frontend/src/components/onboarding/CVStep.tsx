import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Icon } from '@/components/icons/Icon'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

import { useOnboarding } from './OnboardingContext'

const LATENCY_HINT: Record<string, string> = {
  mock: 'instant with the mock provider',
  anthropic_api: '~10 s with the Anthropic API',
  openai_api: '~10 s with the OpenAI API',
  claude_code: '~15 s with Claude Code',
  codex_cli: '~20 s with OpenAI Codex',
  ollama: '~30 s with Ollama (depends on model)',
}

export function CVStep() {
  const navigate = useNavigate()
  const onboarding = useOnboarding()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [cvText, setCvText] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

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

  if (busy) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-4 px-6 py-12 text-center">
          <span
            aria-hidden
            className="h-12 w-12 rounded-full border-[3px] border-line border-t-brand-green animate-spin"
          />
          <div>
            <h2 className="text-[18px] font-semibold tracking-[-0.01em] text-ink">
              Reading your CV…
            </h2>
            <p className="mt-1 text-[13px] text-ink-3">Pulling out roles, skills, and dates.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 p-8">
        <div>
          <h2 className="mb-1.5 text-[18px] font-semibold tracking-[-0.01em] text-ink">
            Start with your CV.
          </h2>
          <p className="text-[13px] leading-relaxed text-ink-3">
            Drop a PDF or paste your CV text. We'll extract a structured profile from it
            {latencyHint !== null ? ` — ${latencyHint}.` : '.'} You review it before anything is
            saved.
          </p>
        </div>

        {/* Drop zone */}
        <label
          htmlFor="cv-pdf"
          onDragEnter={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragOver={(e) => {
            // preventDefault is required, or the browser never fires `drop`.
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={(e) => {
            e.preventDefault()
            setDragging(false)
          }}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            const file = e.dataTransfer.files?.[0]
            if (file) submitFile(file)
          }}
          className={cn(
            'flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
            dragging
              ? 'border-brand-green bg-brand-green-tint'
              : 'border-line-strong bg-surface-2 hover:border-brand-green hover:bg-brand-green-tint',
          )}
        >
          <Icon name="upload" size={26} className="text-ink-3" />
          <span className="text-[14px] font-medium text-ink">
            Drop your CV here, or click to browse
          </span>
          <span className="text-[12px] text-ink-3">PDF — up to 5 MB</span>
          <input
            ref={fileInputRef}
            id="cv-pdf"
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only"
            onChange={(e) => {
              const file = e.currentTarget.files?.[0]
              if (file) submitFile(file)
            }}
          />
        </label>

        <div className="flex items-center gap-3 text-[11px] text-ink-4">
          <span className="h-px flex-1 bg-line" />
          or
          <span className="h-px flex-1 bg-line" />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="cv-text">…or paste CV text</Label>
          <Textarea
            id="cv-text"
            value={cvText}
            onChange={(e) => setCvText(e.target.value)}
            rows={10}
            placeholder="Alex K.&#10;Backend engineer with 3 years of Python experience…"
          />
          <div className="flex justify-end">
            <Button onClick={submitText} disabled={cvText.trim().length === 0}>
              Parse CV <Icon name="arrowRight" size={14} />
            </Button>
          </div>
        </div>

        <p className="text-center text-[11px] text-ink-4">
          Never shared with employers · stored locally on this machine
        </p>

        {error !== null && (
          <p role="alert" className="text-[13px] text-warn">
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
