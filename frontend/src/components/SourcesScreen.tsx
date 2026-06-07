import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Icon } from '@/components/icons/Icon'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { api, ApiError } from '@/lib/api'
import type { CrawlSourceType, JobSourceConfig, SourceConfig } from '@/lib/types'
// ScoringStatus and RescoreResult come from the api wrapper — no extra import needed.
import { cn } from '@/lib/utils'

const INTERVAL_OPTIONS: { value: number; label: string }[] = [
  { value: 12, label: 'Every 12 hours' },
  { value: 24, label: 'Daily' },
  { value: 72, label: 'Every 3 days' },
  { value: 168, label: 'Weekly' },
  { value: 0, label: 'Disabled' },
]

const SOURCE_META: Record<
  CrawlSourceType,
  { label: string; description: string; needsSlug: boolean; slugPlaceholder?: string }
> = {
  greenhouse: {
    label: 'Greenhouse',
    description: "Fetches all open jobs from a company's Greenhouse board via the public JSON API.",
    needsSlug: true,
    slugPlaceholder: 'company-slug  (e.g. stripe)',
  },
  lever: {
    label: 'Lever',
    description: "Fetches all published postings from a company's Lever board via the public JSON API.",
    needsSlug: true,
    slugPlaceholder: 'company-slug  (e.g. vercel)',
  },
  wellfound: {
    label: 'Wellfound',
    description:
      'Searches Wellfound (formerly AngelList) using role keywords and location from your profile. Results depend on server-side rendering availability.',
    needsSlug: false,
  },
  indeed: {
    label: 'Indeed.de',
    description:
      'Searches de.indeed.com using your target role and location. Scrapes HTML with a conservative delay between requests.',
    needsSlug: false,
  },
}

function formatChecked(dt: string | null): string {
  if (!dt) return 'Never'
  const d = new Date(dt)
  const now = Date.now()
  const diffMs = now - d.getTime()
  const mins = Math.floor(diffMs / 60_000)
  if (mins < 2) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function SourcesScreen() {
  const navigate = useNavigate()
  const [sources, setSources] = useState<JobSourceConfig[]>([])
  const [config, setConfig] = useState<SourceConfig>({ interval_hours: 6 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Immediate visual feedback: true from the moment the user clicks until
  // the first reload confirms is_running=true on at least one source.
  const [starting, setStarting] = useState(false)

  // Completion state: null = no run yet, number = new scored jobs from last run
  const [completionNewJobs, setCompletionNewJobs] = useState<number | null>(null)

  // Rescore state
  const [unscoredCount, setUnscoredCount] = useState(0)
  const [rescoring, setRescoring] = useState(false)

  // Scored count baseline captured just before triggering a run.
  const baselineScoredRef = useRef<number | null>(null)

  // Use a ref so the polling interval always sees fresh sources without being
  // listed as an effect dependency (avoids re-creating the interval on every reload).
  const sourcesRef = useRef(sources)
  sourcesRef.current = sources

  const fetchUnscoredCount = useCallback(async () => {
    try {
      const status = await api.getScoringStatus()
      setUnscoredCount(status.rescore_candidate_count)
    } catch {
      // non-critical
    }
  }, [])

  const reload = useCallback(async () => {
    try {
      const [srcs, cfg] = await Promise.all([api.listSources(), api.getSourceConfig()])
      const wasRunning = sourcesRef.current.some((s) => s.is_running)
      const nowRunning = srcs.some((s) => s.is_running)

      // Once running is confirmed, clear the "starting" flicker state.
      if (nowRunning) setStarting(false)

      // Transition: was running → now done. Read scored count and diff it.
      if (wasRunning && !nowRunning) {
        setStarting(false)
        try {
          const status = await api.getScoringStatus()
          const baseline = baselineScoredRef.current ?? 0
          setCompletionNewJobs(status.jobs_with_current_score - baseline)
          setUnscoredCount(status.rescore_candidate_count)
        } catch {
          setCompletionNewJobs(0)
        }
      }

      setSources(srcs)
      setConfig(cfg)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
    void fetchUnscoredCount()
    // Poll every 1.5 s while any source is running; use ref to avoid stale closure.
    const id = window.setInterval(() => {
      if (sourcesRef.current.some((s) => s.is_running) || starting) void reload()
    }, 1500)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload, fetchUnscoredCount])

  async function triggerRun(runFn: () => Promise<void>) {
    setCompletionNewJobs(null)
    setStarting(true)
    // Capture baseline before run so we can diff after.
    try {
      const status = await api.getScoringStatus()
      baselineScoredRef.current = status.jobs_with_current_score
    } catch {
      baselineScoredRef.current = null
    }
    await runFn()
    // If sources finished before we even confirmed running, clear starting.
    if (!sourcesRef.current.some((s) => s.is_running)) setStarting(false)
  }

  async function handleRunAll() {
    await triggerRun(async () => {
      await api.runAllSourcesNow()
      await reload()
    })
  }

  async function handleIntervalChange(hours: number) {
    const updated = await api.updateSourceConfig({ interval_hours: hours })
    setConfig(updated)
  }

  async function handleDelete(id: number) {
    await api.deleteSource(id)
    setSources((prev) => prev.filter((s) => s.id !== id))
  }

  async function handleToggle(source: JobSourceConfig) {
    const updated = await api.updateSource(source.id, { enabled: !source.enabled })
    setSources((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
  }

  async function handleRunOne(id: number) {
    await triggerRun(async () => {
      await api.runSourceNow(id)
      await reload()
    })
  }

  async function handleRescore() {
    setRescoring(true)
    try {
      const result = await api.rescoreJobs()
      await fetchUnscoredCount()
      if (result.rescored > 0) {
        setCompletionNewJobs((prev) => (prev ?? 0) + result.rescored)
      }
    } finally {
      setRescoring(false)
    }
  }

  function onCreated(source: JobSourceConfig) {
    setSources((prev) => [...prev, source])
  }

  const anyRunning = sources.some((s) => s.is_running)
  const showRunning = anyRunning || starting
  const runningLabels = sources.filter((s) => s.is_running).map((s) => s.label)
  const showDone = completionNewJobs !== null && !showRunning

  if (loading) {
    return (
      <div className="screen flex items-center justify-center">
        <span className="text-[13px] text-ink-3">Loading…</span>
      </div>
    )
  }

  return (
    <div className="screen mx-auto max-w-[720px] px-8 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-semibold tracking-[-0.01em] text-ink">Job Sources</h1>
          <p className="mt-0.5 text-[13px] text-ink-3">
            Automatically discover and import jobs into your feed.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={config.interval_hours}
            onChange={(e) => void handleIntervalChange(Number(e.target.value))}
            className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-[12px] text-ink focus:outline-none focus:ring-1 focus:ring-line-strong"
          >
            {INTERVAL_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <Button size="sm" onClick={() => void handleRunAll()} disabled={showRunning}>
            <Icon name="refresh" size={13} className={showRunning ? 'animate-spin' : ''} />
            {showRunning ? 'Running…' : 'Run all now'}
          </Button>
        </div>
      </div>

      {/* Running banner — shown immediately on click, stays until done */}
      {showRunning && (
        <div className="mb-5 overflow-hidden rounded-lg border border-line bg-surface">
          <div className="h-1 w-full overflow-hidden bg-line">
            <div className="h-full w-full animate-scrape-progress bg-brand-green" />
          </div>
          <div className="flex items-center gap-3 px-4 py-3">
            <Icon name="refresh" size={14} className="animate-spin shrink-0 text-brand-green" />
            <div className="min-w-0 flex-1">
              <span className="text-[13px] font-medium text-ink">
                {starting && !anyRunning ? 'Starting…' : 'Fetching and scoring jobs…'}
              </span>
              {runningLabels.length > 0 && (
                <span className="ml-1.5 text-[12px] text-ink-3">
                  {runningLabels.join(', ')}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Done banner — honest about what actually happened */}
      {showDone && (
        <div className={cn(
          'mb-5 flex items-center gap-3 rounded-lg border px-4 py-3',
          completionNewJobs! > 0
            ? 'border-brand-green-soft bg-brand-green-soft/40'
            : 'border-line bg-surface-2',
        )}>
          <Icon
            name={completionNewJobs! > 0 ? 'check' : 'refresh'}
            size={14}
            className={cn('shrink-0', completionNewJobs! > 0 ? 'text-brand-green' : 'text-ink-3')}
          />
          <span className="flex-1 text-[13px] text-ink">
            {completionNewJobs! > 0
              ? `${completionNewJobs} new job${completionNewJobs! > 1 ? 's' : ''} scored and added to your feed.`
              : 'Scraping finished — no new jobs found this time.'}
          </span>
          {completionNewJobs! > 0 && (
            <Button size="sm" onClick={() => navigate('/app')}>
              View feed
              <Icon name="arrowRight" size={12} />
            </Button>
          )}
          <button
            type="button"
            onClick={() => setCompletionNewJobs(null)}
            className="text-ink-3 hover:text-ink"
            aria-label="Dismiss"
          >
            <Icon name="plus" size={13} className="rotate-45" />
          </button>
        </div>
      )}

      {/* Rescore nudge — shown when there are unscored jobs in the DB */}
      {unscoredCount > 0 && !showRunning && (
        <div className="mb-5 flex items-center gap-3 rounded-lg border border-info-soft bg-info-soft/30 px-4 py-3">
          <Icon name="sparkle" size={14} className="shrink-0 text-info" />
          <span className="flex-1 text-[13px] text-ink">
            {unscoredCount} job{unscoredCount > 1 ? 's' : ''} in your database{' '}
            {unscoredCount > 1 ? 'haven\'t' : 'hasn\'t'} been scored yet against your current profile.
          </span>
          <Button size="sm" variant="outline" onClick={() => void handleRescore()} disabled={rescoring}>
            {rescoring ? (
              <><Icon name="refresh" size={11} className="animate-spin" /> Scoring…</>
            ) : (
              'Score now'
            )}
          </Button>
        </div>
      )}

      {error && (
        <p role="alert" className="mb-4 text-[13px] text-warn">
          {error}
        </p>
      )}

      <div className="flex flex-col gap-6">
        {(['greenhouse', 'lever', 'wellfound', 'indeed'] as CrawlSourceType[]).map((type) => {
          const meta = SOURCE_META[type]
          const typeSources = sources.filter((s) => s.source_type === type)
          return (
            <SourceTypeCard
              key={type}
              type={type}
              meta={meta}
              sources={typeSources}
              onDelete={handleDelete}
              onToggle={handleToggle}
              onRunOne={handleRunOne}
              onCreated={onCreated}
            />
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Per-type card
// ---------------------------------------------------------------------------

interface SourceTypeCardProps {
  type: CrawlSourceType
  meta: (typeof SOURCE_META)[CrawlSourceType]
  sources: JobSourceConfig[]
  onDelete: (id: number) => Promise<void>
  onToggle: (source: JobSourceConfig) => Promise<void>
  onRunOne: (id: number) => Promise<void>
  onCreated: (source: JobSourceConfig) => void
}

function SourceTypeCard({
  type,
  meta,
  sources,
  onDelete,
  onToggle,
  onRunOne,
  onCreated,
}: SourceTypeCardProps) {
  const [adding, setAdding] = useState(false)
  const [slug, setSlug] = useState('')
  const [label, setLabel] = useState('')
  const [saving, setSaving] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  async function handleAdd() {
    const trimSlug = slug.trim()
    const trimLabel = label.trim() || (meta.needsSlug ? trimSlug : meta.label)
    if (meta.needsSlug && !trimSlug) {
      setAddError('Company slug is required.')
      return
    }
    setSaving(true)
    setAddError(null)
    try {
      const created = await api.createSource({
        source_type: type,
        company_slug: meta.needsSlug ? trimSlug : null,
        label: trimLabel,
      })
      onCreated(created)
      setSlug('')
      setLabel('')
      setAdding(false)
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardContent className="p-5">
        {/* Card header */}
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-[14px] font-semibold text-ink">{meta.label}</h2>
            <p className="mt-0.5 text-[12px] leading-relaxed text-ink-3">{meta.description}</p>
          </div>
          {meta.needsSlug && (
            <Button size="sm" variant="outline" onClick={() => setAdding((v) => !v)}>
              <Icon name="plus" size={12} /> Add
            </Button>
          )}
        </div>

        {/* Add form */}
        {adding && meta.needsSlug && (
          <div className="mb-3 flex flex-col gap-2 rounded-md border border-line bg-surface-2 p-3">
            <Input
              placeholder={meta.slugPlaceholder}
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void handleAdd()}
            />
            <Input
              placeholder="Display label (optional)"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void handleAdd()}
            />
            {addError && <p className="text-[12px] text-warn">{addError}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={() => void handleAdd()} disabled={saving}>
                {saving ? 'Adding…' : 'Add'}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setAdding(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Source rows */}
        {sources.length > 0 ? (
          <div className="flex flex-col divide-y divide-line">
            {sources.map((s) => (
              <SourceRow
                key={s.id}
                source={s}
                onDelete={onDelete}
                onToggle={onToggle}
                onRunOne={onRunOne}
              />
            ))}
          </div>
        ) : (
          !meta.needsSlug ? (
            // Wellfound/Indeed: show a "not added yet" row with a single Add button
            <AddSearchSourceRow type={type} meta={meta} onCreated={onCreated} />
          ) : (
            <p className="text-[12px] text-ink-4">
              No companies added yet. Click <strong>Add</strong> to configure one.
            </p>
          )
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Single source row
// ---------------------------------------------------------------------------

interface SourceRowProps {
  source: JobSourceConfig
  onDelete: (id: number) => Promise<void>
  onToggle: (source: JobSourceConfig) => Promise<void>
  onRunOne: (id: number) => Promise<void>
}

function SourceRow({ source, onDelete, onToggle, onRunOne }: SourceRowProps) {
  const [deleting, setDeleting] = useState(false)
  const [running, setRunning] = useState(false)

  async function handleDelete() {
    if (!window.confirm(`Remove "${source.label}"?`)) return
    setDeleting(true)
    await onDelete(source.id)
  }

  async function handleRunOne() {
    setRunning(true)
    await onRunOne(source.id)
    setRunning(false)
  }

  return (
    <div className="flex items-center gap-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-[13px] font-medium text-ink">{source.label}</span>
          {source.company_slug && (
            <span className="font-mono text-[11px] text-ink-4">{source.company_slug}</span>
          )}
          {source.is_running && (
            <span className="flex items-center gap-1 text-[11px] text-brand-green">
              <Icon name="refresh" size={10} className="animate-spin" /> Running…
            </span>
          )}
        </div>
        <div className="mt-0.5 flex items-center gap-2">
          <span className="text-[11px] text-ink-4">
            Checked: {formatChecked(source.last_checked_at)}
          </span>
          {source.last_error && (
            <span className="max-w-[300px] truncate text-[11px] text-warn" title={source.last_error}>
              {source.last_error}
            </span>
          )}
        </div>
      </div>

      {/* Enable/disable toggle */}
      <button
        type="button"
        onClick={() => void onToggle(source)}
        className={cn(
          'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200',
          source.enabled ? 'bg-brand-green' : 'bg-line-strong',
        )}
        aria-label={source.enabled ? 'Disable source' : 'Enable source'}
      >
        <span
          className={cn(
            'inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200',
            source.enabled ? 'translate-x-4' : 'translate-x-0',
          )}
        />
      </button>

      <Button
        size="sm"
        variant="outline"
        disabled={running || source.is_running}
        onClick={() => void handleRunOne()}
      >
        <Icon name="refresh" size={11} className={running || source.is_running ? 'animate-spin' : ''} />
        Run
      </Button>

      <button
        type="button"
        onClick={() => void handleDelete()}
        disabled={deleting}
        className="text-ink-4 transition-colors hover:text-warn disabled:opacity-50"
        aria-label="Remove source"
      >
        <Icon name="trash" size={14} />
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// One-click "Add" for search-based sources (Wellfound, Indeed)
// ---------------------------------------------------------------------------

interface AddSearchSourceRowProps {
  type: CrawlSourceType
  meta: (typeof SOURCE_META)[CrawlSourceType]
  onCreated: (source: JobSourceConfig) => void
}

function AddSearchSourceRow({ type, meta, onCreated }: AddSearchSourceRowProps) {
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function handleAdd() {
    setSaving(true)
    setErr(null)
    try {
      const created = await api.createSource({ source_type: type, label: meta.label })
      onCreated(created)
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[12px] text-ink-4">
        Uses your profile's target role and location as search terms.
      </p>
      {err && <p className="text-[12px] text-warn">{err}</p>}
      <Button size="sm" variant="outline" className="self-start" onClick={() => void handleAdd()} disabled={saving}>
        <Icon name="plus" size={12} /> {saving ? 'Adding…' : `Enable ${meta.label}`}
      </Button>
    </div>
  )
}
