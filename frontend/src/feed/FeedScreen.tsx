import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Icon } from '@/components/icons/Icon'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, api } from '@/lib/api'
import type { CrawlStatus, FeedItem, JobAction, JobActionStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

import { JobCard } from './JobCard'

type Filter = 'all' | 'saved' | 'skipped' | 'applied'

const POLL_INTERVAL_MS = 1500

const FILTER_OPTIONS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'saved', label: 'Saved' },
  { id: 'applied', label: 'Applied' },
  { id: 'skipped', label: 'Skipped' },
]

export function FeedScreen() {
  const navigate = useNavigate()

  const [filter, setFilter] = useState<Filter>('all')
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [feedError, setFeedError] = useState<string | null>(null)
  const [pendingActions, setPendingActions] = useState<Set<number>>(new Set())

  const [crawlOpen, setCrawlOpen] = useState(false)
  const [urlsText, setUrlsText] = useState('')
  const [activeCrawl, setActiveCrawl] = useState<CrawlStatus | null>(null)
  const [crawlError, setCrawlError] = useState<string | null>(null)

  const refreshFeed = useCallback(async (currentFilter: Filter) => {
    setFeedError(null)
    try {
      const params =
        currentFilter === 'all' ? { excludeStatus: 'skipped' } : ({ excludeStatus: null } as const)
      const all = await api.getFeed(params)
      const filtered =
        currentFilter === 'all'
          ? all
          : all.filter((item) => item.status === filterToStatus(currentFilter))
      setItems(filtered)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not load feed.'
      setFeedError(message)
    }
  }, [])

  useEffect(() => {
    void refreshFeed(filter)
  }, [filter, refreshFeed])

  // Poll the active crawl until it lands in a terminal state.
  useEffect(() => {
    if (!activeCrawl || activeCrawl.state === 'done' || activeCrawl.state === 'error') {
      return
    }
    const id = window.setInterval(async () => {
      try {
        const next = await api.getCrawlStatus(activeCrawl.job_id)
        setActiveCrawl(next)
        if (next.state === 'done') {
          await refreshFeed(filter)
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Lost crawl status.'
        setCrawlError(message)
        setActiveCrawl({ ...activeCrawl, state: 'error', error: message })
      }
    }, POLL_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [activeCrawl, filter, refreshFeed])

  async function handleStartCrawl() {
    setCrawlError(null)
    const urls = urlsText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0)

    if (urls.length === 0) {
      setCrawlError('Paste at least one job URL, one per line.')
      return
    }

    try {
      const response = await api.triggerCrawl({
        source: 'manual_url',
        urls,
        max_jobs: Math.max(urls.length, 5),
      })
      setActiveCrawl({
        job_id: response.job_id,
        state: 'queued',
        fetched: 0,
        total: urls.length,
        new: 0,
        duplicates: 0,
        scored: 0,
        error: null,
      })
    } catch (error) {
      if (error instanceof ApiError) {
        setCrawlError(error.message)
      } else if (error instanceof Error) {
        setCrawlError(error.message)
      } else {
        setCrawlError('Crawl failed.')
      }
    }
  }

  async function handleAction(jobId: number, action: JobAction) {
    if (action === 'apply') {
      // Apply jumps straight to the generation flow; the user is the one
      // who flips status to "applied" later, after editing materials.
      navigate(`/app/apply/${jobId}`)
      return
    }
    setPendingActions((prev) => new Set(prev).add(jobId))
    try {
      await api.postJobAction(jobId, action)
      await refreshFeed(filter)
    } finally {
      setPendingActions((prev) => {
        const next = new Set(prev)
        next.delete(jobId)
        return next
      })
    }
  }

  return (
    <div className="screen mx-auto max-w-[1120px] px-10 py-8">
      {/* Header */}
      <div className="mb-7">
        <div className="mb-2 flex items-end justify-between gap-4">
          <div>
            <div className="mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
              Job Feed
            </div>
            <h1 className="text-[28px] font-semibold tracking-[-0.025em] text-ink">
              Today&rsquo;s matches
            </h1>
          </div>
          <Button
            onClick={() => setCrawlOpen((open) => !open)}
            aria-expanded={crawlOpen}
            aria-controls="crawl-panel"
          >
            <Icon name="refresh" size={14} />
            {crawlOpen ? 'Close crawl' : 'Crawl'}
          </Button>
        </div>
        <p className="max-w-[640px] text-[13px] text-ink-3">
          Ranked by how well each job matches your profile and preferences.
        </p>
      </div>

      {crawlOpen ? (
        <div id="crawl-panel" className="mb-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Paste job URLs</CardTitle>
              <p className="text-xs text-ink-3">
                One per line. Works against LinkedIn, Greenhouse, Lever, Workday, and most career
                pages.
                <br />
                <span className="font-medium">
                  LinkedIn scraping is unreliable. Paste job URLs directly for reliable results.
                </span>
              </p>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Textarea
                value={urlsText}
                onChange={(event) => setUrlsText(event.target.value)}
                placeholder="https://example.com/jobs/1234"
                rows={5}
                aria-label="Job URLs"
              />
              {crawlError ? <p className="text-xs text-warn">{crawlError}</p> : null}
              {activeCrawl ? <CrawlStatusLine status={activeCrawl} /> : null}
              <div className="flex justify-end">
                <Button
                  onClick={handleStartCrawl}
                  disabled={activeCrawl?.state === 'queued' || activeCrawl?.state === 'running'}
                >
                  Start crawl
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Filters */}
      <div className="mb-5 flex items-center gap-2">
        <Icon name="filter" size={13} className="text-ink-3" />
        {FILTER_OPTIONS.map((option) => {
          const active = filter === option.id
          return (
            <button
              key={option.id}
              onClick={() => setFilter(option.id)}
              className={cn(
                'rounded-md border px-2.5 py-1 text-[12px] transition-colors',
                active
                  ? 'border-ink bg-ink text-background'
                  : 'border-line bg-surface text-ink-2 hover:bg-surface-2',
              )}
            >
              {option.label}
            </button>
          )
        })}
      </div>

      {/* List */}
      {feedError ? (
        <p role="alert" className="text-sm text-warn">
          {feedError}
        </p>
      ) : items === null ? (
        <div className="flex flex-col gap-3" aria-busy="true" aria-live="polite">
          <span className="sr-only">Loading jobs…</span>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="grid grid-cols-[auto_1fr_auto] gap-4 rounded-[16px] border border-line bg-surface p-[18px]"
            >
              <div className="skeleton h-10 w-10 rounded-[9px]" />
              <div className="flex flex-col gap-2">
                <div className="skeleton h-4 w-1/2" />
                <div className="skeleton h-3 w-1/3" />
                <div className="skeleton mt-1 h-3 w-5/6" />
                <div className="skeleton h-3 w-2/3" />
              </div>
              <div className="skeleton h-[60px] w-[60px] rounded-full" />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState filter={filter} />
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <JobCard
              key={item.job_id}
              item={item}
              pending={pendingActions.has(item.job_id)}
              onAction={(action) => handleAction(item.job_id, action)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function CrawlStatusLine({ status }: { status: CrawlStatus }) {
  if (status.state === 'queued') {
    return <p className="text-xs text-ink-3">Queued…</p>
  }
  if (status.state === 'running') {
    return (
      <p className="text-xs text-ink-3">
        Crawling… fetched {status.fetched}/{status.total}
      </p>
    )
  }
  if (status.state === 'error') {
    return <p className="text-xs text-warn">Error: {status.error ?? 'unknown'}</p>
  }
  return (
    <p className="text-xs text-brand-green">
      Done. {status.new} new, {status.duplicates} duplicate, {status.scored} scored.
    </p>
  )
}

function EmptyState({ filter }: { filter: Filter }) {
  if (filter === 'all') {
    return (
      <div className="mx-auto max-w-md pt-12 text-center">
        <h2 className="text-xl font-medium text-ink">No jobs yet.</h2>
        <p className="mt-2 text-sm text-ink-3">
          Click <strong>Crawl</strong>, paste a few job URLs, and we&rsquo;ll score them against
          your profile.
        </p>
      </div>
    )
  }
  return <p className="mx-auto max-w-md pt-12 text-center text-sm text-ink-3">No {filter} jobs.</p>
}

function filterToStatus(filter: Filter): JobActionStatus | null {
  if (filter === 'saved') return 'saved'
  if (filter === 'applied') return 'applied'
  if (filter === 'skipped') return 'skipped'
  return null
}
