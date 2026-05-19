import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { CompanyMark } from '@/components/CompanyMark'
import { Icon } from '@/components/icons/Icon'
import { Card } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { ApplicationStatus, ApplicationSummary } from '@/lib/types'
import { cn } from '@/lib/utils'

// 5 board columns. Hired's 6th status, `skipped`, has no column — Skip
// is the "archive" action (see the feed action semantics), so skipped
// applications stay off the board, like skipped jobs stay out of "All".
type ColumnId = Exclude<ApplicationStatus, 'skipped'>

const COLUMNS: { id: ColumnId; label: string; accent: string; empty: string }[] = [
  {
    id: 'saved',
    label: 'Saved',
    accent: 'var(--ink-3)',
    empty: 'Nothing saved yet. Apply to a job from the feed and it lands here.',
  },
  {
    id: 'applied',
    label: 'Applied',
    accent: 'var(--info)',
    empty: 'No applications submitted yet.',
  },
  {
    id: 'interview',
    label: 'Interview',
    accent: 'var(--accent)',
    empty: 'No interviews yet. Move a card here when you hear back.',
  },
  {
    id: 'offer',
    label: 'Offer',
    accent: 'var(--accent-2)',
    empty: 'No offers yet.',
  },
  {
    id: 'rejected',
    label: 'Rejected',
    accent: 'var(--warn)',
    empty: "Nothing here. Move a card here if it doesn't work out.",
  },
]

export function ApplicationDashboard() {
  const navigate = useNavigate()
  const [items, setItems] = useState<ApplicationSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState<{ id: number; from: ColumnId } | null>(null)
  const [dragOver, setDragOver] = useState<ColumnId | null>(null)

  const loadApps = useCallback(async () => {
    try {
      const list = await api.listApplications()
      setItems(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load applications.')
    }
  }, [])

  useEffect(() => {
    void loadApps()
  }, [loadApps])

  const board = useMemo(() => {
    const byColumn: Record<ColumnId, ApplicationSummary[]> = {
      saved: [],
      applied: [],
      interview: [],
      offer: [],
      rejected: [],
    }
    for (const app of items ?? []) {
      if (app.status === 'skipped') continue
      byColumn[app.status].push(app)
    }
    return byColumn
  }, [items])

  const total = items?.filter((a) => a.status !== 'skipped').length ?? 0

  async function handleDrop(toCol: ColumnId) {
    const drag = dragging
    setDragging(null)
    setDragOver(null)
    if (!drag || drag.from === toCol) return

    // Optimistic move, then persist and reconcile.
    setItems((cur) =>
      cur ? cur.map((a) => (a.id === drag.id ? { ...a, status: toCol } : a)) : cur,
    )
    try {
      await api.updateApplicationStatus(drag.id, toCol)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not move the application.')
    }
    await loadApps()
  }

  function openDetail(id: number) {
    navigate(`/app/applications/${id}`)
  }

  return (
    <div className="screen flex min-h-screen flex-col">
      <div className="border-b border-line px-8 pb-5 pt-6">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
          Applications
        </div>
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-ink">Applications</h1>
        <p className="mt-1 text-[13px] text-ink-3">
          <span className="mono text-ink">{total}</span> active · drag a card to change its status
        </p>

        {/* Stats strip — real counts from the loaded list */}
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {COLUMNS.map((c) => (
            <div
              key={c.id}
              className="rounded-md border border-line bg-surface px-3 py-2.5"
              style={{ borderLeft: `3px solid ${c.accent}` }}
            >
              <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-3">
                {c.label}
              </div>
              <div className="mono mt-1 text-[20px] font-medium tracking-[-0.02em] text-ink">
                {board[c.id].length}
              </div>
            </div>
          ))}
        </div>
      </div>

      {error ? (
        <p role="alert" className="px-8 pt-4 text-sm text-warn">
          {error}
        </p>
      ) : null}

      <div className="flex-1 overflow-x-auto bg-paper-sunk px-8 py-5">
        {items === null ? (
          <div
            className="grid grid-cols-1 gap-3.5 md:grid-cols-2 xl:grid-cols-5"
            aria-busy="true"
            aria-live="polite"
          >
            <span className="sr-only">Loading applications…</span>
            {COLUMNS.map((col) => (
              <div key={col.id} className="rounded-[10px] border border-line bg-paper">
                <div className="border-b border-line px-3.5 py-3">
                  <div className="skeleton h-3 w-20" />
                </div>
                <div className="flex flex-col gap-2 p-2.5">
                  <div className="skeleton h-[68px] w-full rounded-lg" />
                  <div className="skeleton h-[68px] w-full rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        ) : total === 0 ? (
          <div className="mx-auto max-w-md pt-12 text-center">
            <h2 className="text-lg font-medium text-ink">No applications yet.</h2>
            <p className="mt-2 text-sm text-ink-3">
              Apply to a job from the feed and it will show up here.
            </p>
          </div>
        ) : (
          <div className="grid min-h-0 grid-cols-1 gap-3.5 md:grid-cols-2 xl:grid-cols-5">
            {COLUMNS.map((col) => (
              <section
                key={col.id}
                data-testid={`kanban-col-${col.id}`}
                aria-label={col.label}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(col.id)
                }}
                onDragLeave={() => setDragOver(null)}
                onDrop={() => void handleDrop(col.id)}
                className={cn(
                  'flex flex-col rounded-[10px] border bg-paper transition-colors',
                  dragOver === col.id ? 'border-line-strong bg-surface-2' : 'border-line',
                )}
              >
                <div className="flex items-center gap-2 border-b border-line px-3.5 py-3">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: col.accent }}
                    aria-hidden
                  />
                  <span className="text-[12px] font-semibold text-ink">{col.label}</span>
                  <span className="mono ml-auto text-[11px] text-ink-3">
                    {board[col.id].length}
                  </span>
                </div>
                <div className="flex flex-1 flex-col gap-2 p-2.5">
                  {board[col.id].length === 0 ? (
                    <EmptyColumn copy={col.empty} />
                  ) : (
                    board[col.id].map((app) => (
                      <AppCard
                        key={app.id}
                        app={app}
                        columnId={col.id}
                        dragging={dragging?.id === app.id}
                        onDragStart={() => setDragging({ id: app.id, from: col.id })}
                        onDragEnd={() => {
                          setDragging(null)
                          setDragOver(null)
                        }}
                        onOpen={() => openDetail(app.id)}
                      />
                    ))
                  )}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface AppCardProps {
  app: ApplicationSummary
  columnId: ColumnId
  dragging: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onOpen: () => void
}

// HTML5 drag-and-drop only works in the Tauri webview because
// `app.windows[].dragDropEnabled` is set to `false` in
// src-tauri/tauri.conf.json. With Tauri's default (true) the native
// OS file-drop handler swallows the gesture before the webview sees it
// and cards can't be picked up. Do not re-enable it without a
// pointer-event-based DnD replacement.
function AppCard({ app, dragging, onDragStart, onDragEnd, onOpen }: AppCardProps) {
  return (
    <Card
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      role="button"
      tabIndex={0}
      data-testid={`application-card-${app.id}`}
      aria-label={`Open ${app.title} at ${app.company ?? 'unknown company'}`}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
      className={cn(
        'cursor-grab p-3 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        dragging && 'opacity-40',
      )}
    >
      <div className="flex items-start gap-2.5">
        <CompanyMark company={app.company} size={28} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[12px] font-semibold text-ink">{app.company ?? '—'}</div>
          <div className="truncate text-[11px] text-ink-3">{app.title}</div>
        </div>
        <Icon name="drag" size={14} className="shrink-0 text-ink-4" />
      </div>
      {app.notes ? (
        <div className="mt-2 rounded bg-surface-2 px-2 py-1.5 text-[11px] leading-snug text-ink-2">
          {app.notes}
        </div>
      ) : null}
      {app.applied_at ? (
        <div className="mt-2 text-[10px] text-ink-4">
          Applied {new Date(app.applied_at).toLocaleDateString()}
        </div>
      ) : null}
    </Card>
  )
}

function EmptyColumn({ copy }: { copy: string }) {
  return (
    <div className="m-auto rounded-md border border-dashed border-line-strong px-3 py-6 text-center text-[11px] leading-relaxed text-ink-3">
      {copy}
    </div>
  )
}
