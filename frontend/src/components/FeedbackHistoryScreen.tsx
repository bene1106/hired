import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Icon } from '@/components/icons/Icon'
import { Card, CardContent } from '@/components/ui/card'
import { api, ApiError } from '@/lib/api'
import type { InteractionHistoryItem } from '@/lib/types'
import { cn } from '@/lib/utils'

export function FeedbackHistoryScreen() {
  const [interactions, setInteractions] = useState<InteractionHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getInteractions()
      .then((data) => {
        setInteractions(data)
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : String(err))
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="screen flex min-h-screen items-center justify-center bg-paper">
        <span className="text-[13px] text-ink-3">Loading feedback history…</span>
      </div>
    )
  }

  return (
    <main className="screen min-h-screen bg-paper text-ink">
      <div className="mx-auto flex max-w-[680px] flex-col gap-6 px-8 py-10">
        <div className="mb-1">
          <Link
            to="/app/settings"
            className="mb-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-3 transition-colors hover:text-ink"
          >
            <Icon name="arrowLeft" size={12} />
            Back to Settings
          </Link>
          <h1 className="text-[28px] font-semibold tracking-[-0.025em] text-ink">
            Feedback History
          </h1>
          <p className="mt-1 text-[13px] text-ink-3">
            Jobs you have previously evaluated with a thumbs up or thumbs down.
          </p>
        </div>

        {error && (
          <div className="rounded-md border border-warn-soft bg-warn-soft/40 p-3 text-[13px] text-warn">
            {error}
          </div>
        )}

        {interactions.length === 0 && !error ? (
          <p className="text-[14px] text-ink-3">No feedback given yet.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {interactions.map((item) => {
              const isPositive = item.feedback_signal === 1
              return (
                <Card key={item.job_id}>
                  <CardContent className="flex items-center gap-4 p-4">
                    <div
                      className={cn(
                        'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
                        isPositive
                          ? 'bg-brand-green-soft text-brand-green'
                          : 'bg-warn-soft text-warn',
                      )}
                    >
                      <Icon name={isPositive ? 'thumbsUp' : 'thumbsDown'} size={18} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-[15px] font-medium text-ink">{item.title}</h3>
                      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-ink-3">
                        {item.company ? <span className="truncate">{item.company}</span> : null}
                        {item.location ? (
                          <>
                            <span className="text-ink-4">&bull;</span>
                            <span className="truncate">{item.location}</span>
                          </>
                        ) : null}
                        {item.updated_at ? (
                          <>
                            <span className="text-ink-4">&bull;</span>
                            <span>{new Date(item.updated_at).toLocaleDateString()}</span>
                          </>
                        ) : null}
                        {item.feedback_reason && (
                          <>
                            <span className="text-ink-4">&bull;</span>
                            <span className="font-medium text-ink-2">
                              Reason: {item.feedback_reason.replace('_', ' ')}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        api
                          .deleteInteraction(item.job_id)
                          .then(() => {
                            setInteractions((prev) => prev.filter((i) => i.job_id !== item.job_id))
                          })
                          .catch((err) => {
                            console.error('Failed to remove interaction:', err)
                          })
                      }}
                      className="text-ink-4 hover:text-warn transition-colors ml-2"
                      title="Remove feedback"
                      aria-label="Remove feedback"
                    >
                      <Icon name="trash" size={14} />
                    </button>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </main>
  )
}
