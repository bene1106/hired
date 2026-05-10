import { useCallback, useEffect, useState } from 'react'
import { Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, api } from '@/lib/api'
import type { CrawlStatus, FeedItem, JobAction, JobActionStatus } from '@/lib/types'

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
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold tracking-tight">Hired.</h1>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setCrawlOpen((open) => !open)}
            aria-expanded={crawlOpen}
            aria-controls="crawl-panel"
          >
            {crawlOpen ? 'Close crawl' : 'Crawl'}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => navigate('/app/applications')}>
            Applications
          </Button>
          <Button
            size="icon"
            variant="ghost"
            aria-label="Settings"
            onClick={() => navigate('/app/settings')}
          >
            <Settings />
          </Button>
        </div>
      </header>

      {crawlOpen ? (
        <div id="crawl-panel" className="border-b border-border bg-muted/30 px-6 py-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Paste job URLs</CardTitle>
              <p className="text-xs text-muted-foreground">
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
              {crawlError ? <p className="text-xs text-destructive">{crawlError}</p> : null}
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

      <div className="border-b border-border px-6 py-3 flex items-center gap-2">
        {FILTER_OPTIONS.map((option) => (
          <Button
            key={option.id}
            size="sm"
            variant={filter === option.id ? 'default' : 'outline'}
            onClick={() => setFilter(option.id)}
          >
            {option.label}
          </Button>
        ))}
      </div>

      <main className="flex-1 px-6 py-6">
        {feedError ? (
          <p className="text-sm text-destructive">{feedError}</p>
        ) : items === null ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : items.length === 0 ? (
          <EmptyState filter={filter} />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-4">
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
      </main>
    </div>
  )
}

function CrawlStatusLine({ status }: { status: CrawlStatus }) {
  if (status.state === 'queued') {
    return <p className="text-xs text-muted-foreground">Queued…</p>
  }
  if (status.state === 'running') {
    return (
      <p className="text-xs text-muted-foreground">
        Crawling… fetched {status.fetched}/{status.total}
      </p>
    )
  }
  if (status.state === 'error') {
    return <p className="text-xs text-destructive">Error: {status.error ?? 'unknown'}</p>
  }
  return (
    <p className="text-xs text-emerald-700">
      Done. {status.new} new, {status.duplicates} duplicate, {status.scored} scored.
    </p>
  )
}

function EmptyState({ filter }: { filter: Filter }) {
  if (filter === 'all') {
    return (
      <div className="mx-auto max-w-md text-center pt-12">
        <h2 className="text-xl font-medium">No jobs yet.</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Click <strong>Crawl</strong>, paste a few job URLs, and we&rsquo;ll score them against
          your profile.
        </p>
      </div>
    )
  }
  return (
    <p className="mx-auto max-w-md text-center pt-12 text-sm text-muted-foreground">
      No {filter} jobs.
    </p>
  )
}

function filterToStatus(filter: Filter): JobActionStatus | null {
  if (filter === 'saved') return 'saved'
  if (filter === 'applied') return 'applied'
  if (filter === 'skipped') return 'skipped'
  return null
}
