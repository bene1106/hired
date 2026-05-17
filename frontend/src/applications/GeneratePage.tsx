import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, api } from '@/lib/api'
import type {
  GenerationStatus,
  MaterialType,
  MaterialView,
  MaterialsBundle,
  StepState,
} from '@/lib/types'

const POLL_INTERVAL_MS = 1000

interface SectionMeta {
  type: MaterialType
  title: string
  description: string
}

const SECTIONS: SectionMeta[] = [
  {
    type: 'company_brief',
    title: 'Company brief',
    description: 'Public-source research, used to shape the cover letter.',
  },
  {
    type: 'cv_suggestions',
    title: 'CV tailoring',
    description: 'Where to emphasise, what to trim — applied per job.',
  },
  {
    type: 'cover_letter',
    title: 'Cover letter',
    description: 'Edit it. Nothing is sent unless you mark applied.',
  },
]

type StepLabel = 'pending' | 'in progress' | 'ready' | 'reused' | 'failed'

const STEP_LABELS: Record<StepState, StepLabel> = {
  pending: 'pending',
  running: 'in progress',
  done: 'ready',
  cached: 'reused',
  error: 'failed',
}

export function GeneratePage() {
  const navigate = useNavigate()
  const { jobId } = useParams<{ jobId: string }>()

  const [applicationId, setApplicationId] = useState<number | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<GenerationStatus | null>(null)
  const [materials, setMaterials] = useState<MaterialsBundle | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [marking, setMarking] = useState(false)

  const startedRef = useRef(false)

  // ---- start the pipeline once -------------------------------------------
  useEffect(() => {
    if (startedRef.current) return
    if (!jobId) return
    startedRef.current = true
    void (async () => {
      try {
        const numericJobId = Number(jobId)
        const start = await api.startGeneration(numericJobId)
        setApplicationId(start.application_id)
        setTaskId(start.task_id)
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Could not start generation.'
        setError(message)
      }
    })()
  }, [jobId])

  // ---- poll progress -----------------------------------------------------
  useEffect(() => {
    if (!applicationId || !taskId) return
    let cancelled = false

    async function tick() {
      if (!applicationId || !taskId || cancelled) return
      try {
        const next = await api.getGenerationStatus(applicationId, taskId)
        if (cancelled) return
        setStatus(next)
        // Refresh materials if any step transitioned to done/cached.
        if (
          next.company_brief !== 'pending' ||
          next.cv_suggestions !== 'pending' ||
          next.cover_letter !== 'pending'
        ) {
          await loadMaterials(applicationId)
        }
        if (next.state === 'done' || next.state === 'error') return
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Lost generation status.'
        setError(message)
        return
      }
      if (!cancelled) {
        window.setTimeout(tick, POLL_INTERVAL_MS)
      }
    }

    void tick()
    return () => {
      cancelled = true
    }
    // loadMaterials is stable (declared with useCallback below) but
    // omitted here to keep this effect's lifetime tied to the task/app
    // pair only; including it would force a re-poll on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applicationId, taskId])

  const loadMaterials = useCallback(async (id: number) => {
    const bundle = await api.getMaterials(id)
    setMaterials(bundle)
  }, [])

  const onEdit = useCallback(
    async (type: MaterialType, content: string) => {
      if (!applicationId) return
      const updated = await api.saveMaterial(applicationId, type, content)
      setMaterials((current) =>
        current ? { ...current, [type]: updated as MaterialView } : current,
      )
    },
    [applicationId],
  )

  const onRegenerate = useCallback(
    async (type: MaterialType) => {
      if (!applicationId) return
      const updated = await api.regenerateMaterial(applicationId, type)
      setMaterials((current) =>
        current ? { ...current, [type]: updated as MaterialView } : current,
      )
    },
    [applicationId],
  )

  async function handleMarkApplied() {
    if (!applicationId) return
    setMarking(true)
    try {
      await api.updateApplicationStatus(applicationId, 'applied')
      navigate('/app/applications', { replace: true })
    } finally {
      setMarking(false)
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Generate application</h1>
          <p className="text-xs text-muted-foreground">
            Materials are drafts until you click Mark applied. Nothing is auto-submitted.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate('/app')}>
            Back to feed
          </Button>
          <Button
            size="sm"
            disabled={!applicationId || marking || status?.state !== 'done'}
            onClick={handleMarkApplied}
          >
            {marking ? 'Saving…' : 'Mark applied'}
          </Button>
        </div>
      </header>

      {error ? (
        <div
          role="alert"
          className="border-b border-border bg-destructive/10 px-6 py-2 text-sm text-destructive"
        >
          {error}
        </div>
      ) : null}

      <div className="mx-auto max-w-3xl px-6 py-6 flex flex-col gap-6">
        {SECTIONS.map((section) => (
          <Section
            key={section.type}
            meta={section}
            stepState={readStepState(status, section.type)}
            material={materials ? materials[section.type] : null}
            onEdit={(content) => onEdit(section.type, content)}
            onRegenerate={() => onRegenerate(section.type)}
          />
        ))}
      </div>
    </main>
  )
}

interface SectionProps {
  meta: SectionMeta
  stepState: StepState
  material: MaterialView | null
  onEdit: (content: string) => Promise<void>
  onRegenerate: () => Promise<void>
}

function Section({ meta, stepState, material, onEdit, onRegenerate }: SectionProps) {
  const ready = stepState === 'done' || stepState === 'cached'
  const failed = stepState === 'error'
  const canEdit = meta.type === 'cover_letter'

  return (
    <Card data-testid={`section-${meta.type}`}>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-3">
        <div>
          <CardTitle className="text-base">{meta.title}</CardTitle>
          <p className="text-xs text-muted-foreground">{meta.description}</p>
        </div>
        <StepBadge state={stepState} />
      </CardHeader>
      <CardContent>
        {!ready && !failed ? (
          <p className="text-sm text-muted-foreground" aria-live="polite">
            Generating…
          </p>
        ) : failed ? (
          <p role="alert" className="text-sm text-destructive">
            This step failed. You can keep going — try Regenerate after the others finish.
          </p>
        ) : material === null ? (
          <p className="text-sm text-muted-foreground">No content yet.</p>
        ) : canEdit ? (
          <CoverLetterEditor material={material} onSave={onEdit} />
        ) : (
          <MarkdownView markdown={material.content} />
        )}
        {ready && material ? (
          <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {material.edit_count > 0
                ? `Edited ${material.edit_count} time${material.edit_count === 1 ? '' : 's'} since generation.`
                : 'No edits yet.'}
            </span>
            <Button size="sm" variant="outline" onClick={onRegenerate}>
              Regenerate
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function StepBadge({ state }: { state: StepState }) {
  const tone =
    state === 'done' || state === 'cached'
      ? 'bg-emerald-100 text-emerald-900'
      : state === 'error'
        ? 'bg-destructive/10 text-destructive'
        : state === 'running'
          ? 'bg-amber-100 text-amber-900'
          : 'bg-muted text-muted-foreground'
  return (
    <span
      data-testid={`step-state-${state}`}
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}
    >
      {STEP_LABELS[state]}
    </span>
  )
}

function MarkdownView({ markdown }: { markdown: string }) {
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </div>
  )
}

interface CoverLetterEditorProps {
  material: MaterialView
  onSave: (content: string) => Promise<void>
}

function CoverLetterEditor({ material, onSave }: CoverLetterEditorProps) {
  const [draft, setDraft] = useState(material.content)
  const [saving, setSaving] = useState(false)
  const [savedHash, setSavedHash] = useState(material.content)

  // Reset the draft when a fresh material lands (regeneration).
  useEffect(() => {
    setDraft(material.content)
    setSavedHash(material.content)
  }, [material.content])

  const dirty = useMemo(() => draft !== savedHash, [draft, savedHash])

  async function handleSave() {
    setSaving(true)
    try {
      await onSave(draft)
      setSavedHash(draft)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <div className="flex flex-col gap-2">
        <label
          className="text-xs font-medium text-muted-foreground"
          htmlFor="cover-letter-textarea"
        >
          Edit
        </label>
        <Textarea
          id="cover-letter-textarea"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={16}
        />
        <div className="flex items-center justify-end gap-2">
          <Button size="sm" disabled={!dirty || saving} onClick={handleSave}>
            {saving ? 'Saving…' : 'Save edits'}
          </Button>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium text-muted-foreground">Preview</span>
        <div className="rounded-md border border-border bg-muted/40 p-3">
          <MarkdownView markdown={draft} />
        </div>
      </div>
    </div>
  )
}

function readStepState(status: GenerationStatus | null, type: MaterialType): StepState {
  if (!status) return 'pending'
  if (type === 'company_brief') return status.company_brief
  if (type === 'cv_suggestions') return status.cv_suggestions
  return status.cover_letter
}
