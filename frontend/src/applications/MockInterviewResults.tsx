import type { MockEvaluation } from '@/lib/types'
import { cn } from '@/lib/utils'

interface MockInterviewResultsProps {
  evaluation: MockEvaluation
}

/** Color band for the overall score: red < 50, amber < 75, green otherwise. */
function scoreTone(pct: number): string {
  if (pct < 50) return 'text-warn'
  if (pct < 75) return 'text-amber-500'
  return 'text-brand-green'
}

function ratingTone(rating: number): string {
  if (rating < 50) return 'bg-warn'
  if (rating < 75) return 'bg-amber-500'
  return 'bg-brand-green'
}

/**
 * Presentational results view for a scored mock interview (M3). Reused on the
 * runner's completion screen and when viewing a past run from history.
 */
export function MockInterviewResults({ evaluation }: MockInterviewResultsProps) {
  return (
    <div data-testid="mock-results" className="flex flex-col gap-5">
      <div className="flex items-baseline gap-2">
        <span
          data-testid="overall-score"
          className={cn(
            'text-[40px] font-semibold leading-none',
            scoreTone(evaluation.overall_percentage),
          )}
        >
          {evaluation.overall_percentage}%
        </span>
        <span className="text-[13px] text-ink-3">overall</span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ListCard
          title="Strengths"
          items={evaluation.strengths}
          emptyText="No standout strengths."
        />
        <ListCard
          title="Areas to improve"
          items={evaluation.weaknesses}
          emptyText="No major gaps flagged."
        />
      </div>

      <div className="flex flex-col gap-2">
        <h4 className="text-[13px] font-semibold text-ink">Per-question feedback</h4>
        <ul className="flex flex-col gap-3">
          {evaluation.per_question.map((q, idx) => (
            <li key={idx} className="rounded-md border border-line bg-surface p-3">
              <div className="flex items-start justify-between gap-3">
                <span className="text-[13px] font-medium text-ink">{q.question}</span>
                <span className="shrink-0 text-[13px] font-semibold text-ink-2">{q.rating}</span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                <div
                  className={cn('h-full rounded-full', ratingTone(q.rating))}
                  style={{ width: `${Math.max(0, Math.min(100, q.rating))}%` }}
                />
              </div>
              {q.comment ? <p className="mt-2 text-[12px] text-ink-3">{q.comment}</p> : null}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function ListCard({
  title,
  items,
  emptyText,
}: {
  title: string
  items: string[]
  emptyText: string
}) {
  return (
    <div className="rounded-md border border-line bg-surface p-3">
      <h4 className="mb-1.5 text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-3">
        {title}
      </h4>
      {items.length === 0 ? (
        <p className="text-[12px] text-ink-4">{emptyText}</p>
      ) : (
        <ul className="flex list-disc flex-col gap-1 pl-4 text-[13px] text-ink-2">
          {items.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
