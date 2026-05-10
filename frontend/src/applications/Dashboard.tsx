import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { ApplicationStatus, ApplicationSummary } from '@/lib/types'

const STATUSES: { id: ApplicationStatus | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'saved', label: 'Saved' },
  { id: 'applied', label: 'Applied' },
  { id: 'interview', label: 'Interview' },
  { id: 'offer', label: 'Offer' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'skipped', label: 'Skipped' },
]

const STATUS_TONES: Record<ApplicationStatus, string> = {
  saved: 'bg-muted text-muted-foreground',
  applied: 'bg-sky-100 text-sky-900',
  skipped: 'bg-muted text-muted-foreground',
  interview: 'bg-amber-100 text-amber-900',
  offer: 'bg-emerald-100 text-emerald-900',
  rejected: 'bg-destructive/10 text-destructive',
}

type SortKey = 'date' | 'company'

export function ApplicationDashboard() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<ApplicationStatus | 'all'>('all')
  const [sort, setSort] = useState<SortKey>('date')
  const [items, setItems] = useState<ApplicationSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setItems(null)
    setError(null)
    void (async () => {
      try {
        const list = await api.listApplications(filter === 'all' ? undefined : filter)
        if (!cancelled) setItems(list)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Could not load applications.'
        setError(message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [filter])

  const sorted = useMemo(() => {
    if (items === null) return null
    const copy = [...items]
    if (sort === 'company') {
      copy.sort((a, b) => (a.company ?? '').localeCompare(b.company ?? ''))
    } else {
      // Most recently created first; backend already returns desc by id.
      copy.sort((a, b) => b.id - a.id)
    }
    return copy
  }, [items, sort])

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold tracking-tight">Applications</h1>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={() => navigate('/app')}>
            Back to feed
          </Button>
          <Button size="sm" variant="ghost" onClick={() => navigate('/app/settings')}>
            Settings
          </Button>
        </div>
      </header>

      <section className="border-b border-border px-6 py-3 flex flex-wrap items-center gap-2">
        {STATUSES.map((option) => (
          <Button
            key={option.id}
            size="sm"
            variant={filter === option.id ? 'default' : 'outline'}
            onClick={() => setFilter(option.id)}
          >
            {option.label}
          </Button>
        ))}
        <span className="ml-auto text-xs text-muted-foreground">Sort:</span>
        <Button
          size="sm"
          variant={sort === 'date' ? 'default' : 'outline'}
          onClick={() => setSort('date')}
        >
          Newest
        </Button>
        <Button
          size="sm"
          variant={sort === 'company' ? 'default' : 'outline'}
          onClick={() => setSort('company')}
        >
          Company
        </Button>
      </section>

      <div className="px-6 py-6">
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {sorted === null ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : sorted.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No applications yet. Apply to a job from the feed.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 pr-4">Company</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2 pr-4">Applied</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2"></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.id}
                  className="cursor-pointer border-t border-border hover:bg-muted/40"
                  data-testid={`application-row-${row.id}`}
                  onClick={() => navigate(`/app/applications/${row.id}`)}
                >
                  <td className="py-2 pr-4 font-medium">{row.company ?? '—'}</td>
                  <td className="py-2 pr-4">{row.title}</td>
                  <td className="py-2 pr-4 text-muted-foreground">
                    {row.applied_at ? new Date(row.applied_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="py-2 pr-4">
                    <StatusPill status={row.status} />
                  </td>
                  <td className="py-2 text-right">
                    <Button size="sm" variant="ghost">
                      Open
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  )
}

function StatusPill({ status }: { status: ApplicationStatus }) {
  return (
    <span
      data-testid={`status-${status}`}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_TONES[status]}`}
    >
      {status}
    </span>
  )
}
