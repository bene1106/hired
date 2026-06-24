import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

import { CompanyMark } from '@/components/CompanyMark'
import { Icon } from '@/components/icons/Icon'
import { SuggestionRenderer } from '@/components/SuggestionRenderer'
import { Toast, useToast } from '@/components/Toast'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, api } from '@/lib/api'
import { downloadCoverLetterPdf, downloadCvPdf } from '@/lib/pdf'
import type {
  ApplicationDetail,
  ApplicationStatus,
  GenerationStatus,
  MaterialType,
  MaterialView,
  StepState,
} from '@/lib/types'
import { cn } from '@/lib/utils'

import { InterviewPanel } from './InterviewPanel'
import { InterviewsSection } from './Interviews'

const POLL_INTERVAL_MS = 1000

const STATUS_OPTIONS: ApplicationStatus[] = [
  'saved',
  'applied',
  'interview',
  'offer',
  'rejected',
  'skipped',
]

const PIPELINE: { type: Exclude<MaterialType, never>; label: string }[] = [
  { type: 'company_brief', label: 'Company research' },
  { type: 'cv_suggestions', label: 'CV tailoring' },
  { type: 'cover_letter', label: 'Cover letter' },
]

type Tab = 'job' | 'cover' | 'cv' | 'research' | 'interview' | 'interviews'

interface MaterialsScreenProps {
  mode: 'generate' | 'detail'
  /** Feed job id (generate mode). */
  jobId?: number
  /** Existing application id (detail mode). */
  applicationId?: number
}

export function MaterialsScreen({ mode, jobId, applicationId }: MaterialsScreenProps) {
  const navigate = useNavigate()

  const [appId, setAppId] = useState<number | null>(applicationId ?? null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<GenerationStatus | null>(null)
  const [detail, setDetail] = useState<ApplicationDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('cover')
  const [marking, setMarking] = useState(false)
  const [savingStatus, setSavingStatus] = useState(false)
  const [rejectionNote, setRejectionNote] = useState('')
  const [regenerating, setRegenerating] = useState<MaterialType | null>(null)
  // The finished CV to export lives on the profile (`cv_text`), not in the
  // application materials. `cv_suggestions` is the internal tailoring analysis
  // and must never be what the CV PDF exports — so we load the résumé here.
  const [cvText, setCvText] = useState<string | null>(null)
  const { message: toastMsg, show: showToast } = useToast()

  const startedRef = useRef(false)

  const loadDetail = useCallback(async (id: number) => {
    const data = await api.getApplication(id)
    setDetail(data)
  }, [])

  // Load the user's finished résumé once so the CV tab can export it as a PDF.
  useEffect(() => {
    let cancelled = false
    void api
      .getProfile()
      .then((profile) => {
        if (!cancelled) setCvText(profile?.cv_text ?? null)
      })
      .catch(() => {
        if (!cancelled) setCvText(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // --- generate mode: kick off the pipeline once -------------------------
  useEffect(() => {
    if (mode !== 'generate' || startedRef.current || !jobId) return
    startedRef.current = true
    void (async () => {
      try {
        const start = await api.startGeneration(jobId)
        setAppId(start.application_id)
        setTaskId(start.task_id)
        await loadDetail(start.application_id)
      } catch (err) {
        setError(messageFor(err, 'Could not start generation.'))
      }
    })()
  }, [mode, jobId, loadDetail])

  // --- detail mode: load the existing application ------------------------
  useEffect(() => {
    if (mode !== 'detail' || !applicationId) return
    let cancelled = false
    void (async () => {
      try {
        const data = await api.getApplication(applicationId)
        if (!cancelled) setDetail(data)
      } catch (err) {
        if (!cancelled) setError(messageFor(err, 'Could not load application.'))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [mode, applicationId])

  // --- generate mode: poll generation status ----------------------------
  useEffect(() => {
    if (mode !== 'generate' || !appId || !taskId) return
    let cancelled = false

    async function tick() {
      if (cancelled || appId === null || taskId === null) return
      try {
        const next = await api.getGenerationStatus(appId, taskId)
        if (cancelled) return
        setStatus(next)
        if (
          next.company_brief !== 'pending' ||
          next.cv_suggestions !== 'pending' ||
          next.cover_letter !== 'pending'
        ) {
          await loadDetail(appId)
        }
        if (next.state === 'done' || next.state === 'error') return
      } catch (err) {
        if (!cancelled) setError(messageFor(err, 'Lost generation status.'))
        return
      }
      if (!cancelled) window.setTimeout(tick, POLL_INTERVAL_MS)
    }

    void tick()
    return () => {
      cancelled = true
    }
  }, [mode, appId, taskId, loadDetail])

  const generating =
    mode === 'generate' && status !== null && status.state !== 'done' && status.state !== 'error'

  const materials = detail?.materials ?? null
  const job = detail?.job

  const onRegenerate = useCallback(
    async (type: MaterialType) => {
      if (appId === null) return
      setRegenerating(type)
      try {
        const updated = await api.regenerateMaterial(appId, type)
        setDetail((cur) =>
          cur ? { ...cur, materials: { ...cur.materials, [type]: updated } } : cur,
        )
      } finally {
        setRegenerating(null)
      }
    },
    [appId],
  )

  const onSaveCover = useCallback(
    async (content: string) => {
      if (appId === null) return
      const updated = await api.saveMaterial(appId, 'cover_letter', content)
      setDetail((cur) =>
        cur ? { ...cur, materials: { ...cur.materials, cover_letter: updated } } : cur,
      )
      showToast('Cover letter saved')
    },
    [appId, showToast],
  )

  async function handleMarkApplied() {
    if (appId === null) return
    setMarking(true)
    try {
      await api.updateApplicationStatus(appId, 'applied')
      navigate('/app/applications', { replace: true })
    } finally {
      setMarking(false)
    }
  }

  async function changeStatus(next: ApplicationStatus) {
    if (appId === null) return
    setSavingStatus(true)
    try {
      const note = next === 'rejected' && rejectionNote.trim() ? rejectionNote.trim() : undefined
      await api.updateApplicationStatus(appId, next, note)
      await loadDetail(appId)
      setRejectionNote('')
    } finally {
      setSavingStatus(false)
    }
  }

  const tabs: { id: Tab; label: string; icon: 'mail' | 'file' | 'sparkle' | 'feed' }[] = [
    { id: 'cover', label: 'Cover letter', icon: 'mail' },
    { id: 'cv', label: 'CV', icon: 'file' },
    ...(mode === 'detail'
      ? [
          { id: 'interview' as const, label: 'Interview prep', icon: 'sparkle' as const },
          { id: 'interviews' as const, label: 'Interviews', icon: 'feed' as const },
        ]
      : []),
  ]

  return (
    <div className="screen mx-auto max-w-[1600px] px-8 py-6">
      {/* Toolbar */}
      <div className="mb-5 flex items-center justify-between gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(mode === 'generate' ? '/app' : '/app/applications')}
        >
          <Icon name="arrowLeft" size={14} /> Back
        </Button>
        {mode === 'generate' ? (
          <Button
            size="sm"
            disabled={appId === null || marking || status?.state !== 'done'}
            onClick={handleMarkApplied}
          >
            {marking ? 'Saving…' : 'Mark applied'}
          </Button>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="mb-4 text-sm text-warn">
          {error}
        </p>
      ) : null}

      {/* Header (banner) */}
      <header className="mb-5 flex items-center gap-3.5">
        <CompanyMark company={job?.company} size={40} />
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-3">
            {mode === 'generate' ? 'Applying to' : 'Application'}
          </div>
          <h1 className="truncate text-[18px] font-semibold tracking-[-0.01em] text-ink">
            {job?.title ?? 'Application'}
          </h1>
          <div className="text-[12px] text-ink-3">
            {[job?.company, job?.location].filter(Boolean).join(' · ') || '—'}
          </div>
        </div>
      </header>

      {/* Status switcher (detail mode) */}
      {mode === 'detail' && detail ? (
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-3">
            Status
          </span>
          {STATUS_OPTIONS.map((option) => (
            <button
              key={option}
              disabled={savingStatus}
              onClick={() => void changeStatus(option)}
              className={cn(
                'rounded-md border px-2.5 py-1 text-[12px] capitalize transition-colors disabled:opacity-50',
                detail.status === option
                  ? 'border-ink bg-ink text-background'
                  : 'border-line bg-surface text-ink-2 hover:bg-surface-2',
              )}
            >
              {option}
            </button>
          ))}
          {detail.status === 'rejected' ? (
            <div className="flex w-full items-center gap-2 pt-2">
              <Textarea
                placeholder="Optional: log why this was rejected (helps spot patterns later)."
                value={rejectionNote || detail.notes || ''}
                onChange={(event) => setRejectionNote(event.target.value)}
                rows={2}
                aria-label="Rejection notes"
              />
              <Button
                size="sm"
                variant="outline"
                disabled={savingStatus || !rejectionNote.trim()}
                onClick={() => void changeStatus('rejected')}
              >
                Save note
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Asymmetric split: narrow job post + research | wide generated tabs */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <Card className="p-5">
            <div className="mb-2 flex items-center gap-2">
              <Icon name="file" size={13} className="text-ink-3" />
              <span className="text-[12px] font-medium text-ink">Job post</span>
            </div>
            {job?.description ? (
              <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-2">
                {job.description}
              </p>
            ) : (
              <p className="text-[13px] text-ink-3">
                No job description was captured for this role.
              </p>
            )}
          </Card>

          {materials?.company_brief ? (
            <Card className="p-0">
              <details data-testid="company-research">
                <summary className="cursor-pointer list-none px-5 py-3 text-[12px] font-medium text-ink">
                  Company research
                  <span className="ml-2 font-normal text-ink-3">
                    — used to shape the cover letter
                  </span>
                </summary>
                <div className="border-t border-line px-5 py-4 text-[13px] leading-relaxed text-ink-2">
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{materials.company_brief.content}</ReactMarkdown>
                  </div>
                </div>
              </details>
            </Card>
          ) : null}
        </div>

        <Card className="flex min-h-[420px] flex-col p-0">
          <div className="flex items-center gap-1 border-b border-line px-3 py-2">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] transition-colors',
                  tab === t.id
                    ? 'bg-surface-2 font-medium text-ink'
                    : 'text-ink-3 hover:bg-surface-2',
                )}
              >
                <Icon name={t.icon} size={12} /> {t.label}
              </button>
            ))}
            {!generating && mode === 'generate' ? (
              <span className="chip chip-green ml-auto">Generated</span>
            ) : null}
          </div>

          <div className="flex min-h-0 flex-1 flex-col p-5">
            {generating ? (
              <GeneratingState status={status} />
            ) : tab === 'cover' ? (
              materials?.cover_letter ? (
                <CoverLetterEditor
                  material={materials.cover_letter}
                  jobTitle={job?.title}
                  company={job?.company}
                  onSave={onSaveCover}
                  onRegenerate={() => onRegenerate('cover_letter')}
                  regenerating={regenerating === 'cover_letter'}
                  onDownloaded={() => showToast('Cover letter PDF saved')}
                />
              ) : (
                <p className="text-[13px] text-ink-3">No cover letter yet.</p>
              )
            ) : tab === 'cv' ? (
              materials?.cv_suggestions ? (
                <div className="flex flex-col gap-3">
                  <SuggestionRenderer content={materials.cv_suggestions.content} />
                  <div className="flex justify-end gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!cvText}
                      title={cvText ? undefined : 'Add a CV to your profile to export it as a PDF.'}
                      onClick={() => {
                        if (!cvText) return
                        downloadCvPdf({
                          content: cvText,
                          jobTitle: job?.title,
                          company: job?.company,
                        })
                        showToast('CV PDF saved')
                      }}
                    >
                      <Icon name="download" size={12} /> Download PDF
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={regenerating === 'cv_suggestions'}
                      onClick={() => onRegenerate('cv_suggestions')}
                    >
                      <Icon
                        name="refresh"
                        size={12}
                        className={regenerating === 'cv_suggestions' ? 'animate-spin' : ''}
                      />{' '}
                      {regenerating === 'cv_suggestions' ? 'Regenerating…' : 'Regenerate'}
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-[13px] text-ink-3">No CV tailoring yet.</p>
              )
            ) : appId !== null && tab === 'interviews' ? (
              <InterviewsSection applicationId={appId} />
            ) : appId !== null ? (
              <InterviewPanel applicationId={appId} />
            ) : null}
          </div>
        </Card>
      </div>

      <Toast message={toastMsg} />
    </div>
  )
}

function GeneratingState({ status }: { status: GenerationStatus | null }) {
  const stepStateOf = (type: MaterialType): StepState => {
    if (!status) return 'pending'
    if (type === 'company_brief') return status.company_brief
    if (type === 'cv_suggestions') return status.cv_suggestions
    return status.cover_letter
  }
  const done = PIPELINE.filter(
    (s) => stepStateOf(s.type) === 'done' || stepStateOf(s.type) === 'cached',
  ).length
  const size = 36
  const r = (size - 4) / 2
  const c = 2 * Math.PI * r
  const offset = c - (done / PIPELINE.length) * c

  return (
    <div className="flex flex-col gap-4 py-2" aria-live="polite">
      <div className="flex items-center gap-3">
        <div className="relative" style={{ width: size, height: size }}>
          <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={r}
              stroke="var(--line)"
              strokeWidth={4}
              fill="none"
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={r}
              stroke="var(--accent)"
              strokeWidth={4}
              fill="none"
              strokeLinecap="round"
              strokeDasharray={c}
              strokeDashoffset={offset}
              style={{ transition: 'stroke-dashoffset 0.5s ease' }}
            />
          </svg>
          <Icon name="sparkle" size={14} className="absolute inset-0 m-auto text-brand-green" />
        </div>
        <div>
          <div className="text-[14px] font-semibold text-ink">Generating your materials</div>
          <div className="text-[12px] text-ink-3">This usually takes a few seconds.</div>
        </div>
      </div>
      <ul className="flex flex-col gap-2">
        {PIPELINE.map((s) => {
          const st = stepStateOf(s.type)
          const isDone = st === 'done' || st === 'cached'
          const isRunning = st === 'running'
          const isError = st === 'error'
          return (
            <li
              key={s.type}
              className={cn(
                'flex items-center gap-2.5 text-[13px]',
                isDone ? 'text-ink' : isRunning ? 'text-ink-2' : 'text-ink-4',
              )}
            >
              <span
                className={cn(
                  'flex h-4 w-4 items-center justify-center rounded-full border',
                  isDone
                    ? 'border-transparent bg-brand-green text-white'
                    : isRunning
                      ? 'border-brand-green'
                      : 'border-line-strong',
                )}
              >
                {isDone ? <Icon name="check" size={10} /> : null}
              </span>
              {s.label}
              {isError ? <span className="text-warn">— failed</span> : null}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

interface CoverLetterEditorProps {
  material: MaterialView
  jobTitle?: string | null
  company?: string | null
  onSave: (content: string) => Promise<void>
  onRegenerate: () => Promise<void>
  regenerating: boolean
  /** Called after a successful PDF download so the parent can show a toast. */
  onDownloaded: () => void
}

type CoverView = 'edit' | 'preview'

function CoverLetterEditor({
  material,
  jobTitle,
  company,
  onSave,
  onRegenerate,
  regenerating,
  onDownloaded,
}: CoverLetterEditorProps) {
  const [draft, setDraft] = useState(material.content)
  const [saving, setSaving] = useState(false)
  const [savedHash, setSavedHash] = useState(material.content)
  const [view, setView] = useState<CoverView>('edit')

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
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      {/* Full-width Edit | Preview toggle — far more readable than a nested
          side-by-side split in this panel. */}
      <div className="flex items-center justify-between gap-2">
        <div
          role="tablist"
          aria-label="Cover letter view"
          className="inline-flex w-fit rounded-md border border-line bg-surface p-0.5"
        >
          {(['edit', 'preview'] as const).map((v) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={view === v}
              onClick={() => setView(v)}
              className={cn(
                'rounded-[4px] px-3 py-1 text-[12px] font-medium capitalize transition-colors',
                view === v ? 'bg-surface-2 text-ink shadow-sm' : 'text-ink-3 hover:text-ink',
              )}
            >
              {v}
            </button>
          ))}
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            downloadCoverLetterPdf({ content: draft, jobTitle, company })
            onDownloaded()
          }}
        >
          <Icon name="download" size={12} /> Download PDF
        </Button>
      </div>

      {view === 'edit' ? (
        <Textarea
          id="cover-letter-textarea"
          aria-label="Edit cover letter"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={22}
          className="min-h-[460px] flex-1 text-[14px] leading-7"
        />
      ) : (
        <div className="min-h-[460px] flex-1 overflow-y-auto rounded-md border border-line bg-surface-2 px-8 py-6">
          <div className="prose prose-sm mx-auto max-w-[68ch] leading-relaxed text-ink-2">
            <ReactMarkdown>{toMarkdownParagraphs(draft)}</ReactMarkdown>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] text-ink-4">
          {material.edit_count > 0
            ? `Edited ${material.edit_count} time${material.edit_count === 1 ? '' : 's'} since generation.`
            : 'No edits yet.'}
        </span>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" disabled={regenerating} onClick={onRegenerate}>
            <Icon name="refresh" size={12} className={regenerating ? 'animate-spin' : ''} />{' '}
            {regenerating ? 'Regenerating…' : 'Regenerate'}
          </Button>
          <Button size="sm" disabled={!dirty || saving} onClick={handleSave}>
            {saving ? 'Saving…' : 'Save edits'}
          </Button>
        </div>
      </div>
    </div>
  )
}

/**
 * Cover letters are often plain text with blank-line-separated paragraphs and
 * hard-wrapped salutation/sign-off lines. Markdown collapses single newlines,
 * so a salutation like "Dear team,\nSincerely,\nJane" would merge onto one
 * line. Convert lone newlines to hard breaks (two trailing spaces) so the
 * preview keeps the author's line structure while blank lines still become
 * separate paragraphs.
 */
function toMarkdownParagraphs(text: string): string {
  return text
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}/)
    .map((block) =>
      block
        .split('\n')
        .map((line) => line.trimEnd())
        .join('  \n'),
    )
    .join('\n\n')
}

function messageFor(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return fallback
}
