import { CompanyMark } from '@/components/CompanyMark'
import { MatchRing } from '@/components/MatchRing'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { FeedItem, JobAction } from '@/lib/types'

interface JobCardProps {
  item: FeedItem
  onAction: (action: JobAction) => void
  pending?: boolean
}

export function JobCard({ item, onAction, pending = false }: JobCardProps) {
  const meta = [item.location, item.remote_policy].filter(Boolean).join(' · ')

  return (
    <Card
      data-testid={`job-card-${item.job_id}`}
      className="grid grid-cols-[auto_1fr_auto] gap-4 p-[18px]"
    >
      <CompanyMark company={item.company} size={40} />

      <div className="min-w-0">
        <div className="mb-1 flex flex-wrap items-baseline gap-2">
          <h3 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">{item.title}</h3>
          {item.company ? (
            <>
              <span className="text-[13px] text-ink-3">·</span>
              <span className="text-[13px] font-medium text-ink-2">{item.company}</span>
            </>
          ) : null}
        </div>

        {meta ? (
          <div className="mb-2.5 flex items-center gap-1 text-[12px] text-ink-3">
            <span>{meta}</span>
          </div>
        ) : null}

        {item.rationale ? (
          <p className="mb-2.5 line-clamp-3 text-[13px] leading-relaxed text-ink-2">
            {item.rationale}
          </p>
        ) : null}

        {item.matched_skills.length > 0 ? (
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            <span className="sr-only">Matched skills:</span>
            {item.matched_skills.map((skill) => (
              <span key={`m-${skill}`} className="chip chip-green">
                {skill}
              </span>
            ))}
          </div>
        ) : null}
        {item.missing_skills.length > 0 ? (
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            <span className="sr-only">Missing skills:</span>
            {item.missing_skills.map((skill) => (
              <span key={`x-${skill}`} className="chip">
                {skill}
              </span>
            ))}
          </div>
        ) : null}
        {item.red_flags.length > 0 ? (
          <ul className="mt-1 list-disc pl-5 text-[12px] text-warn">
            {item.red_flags.map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
        ) : null}

        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-[12px] text-ink-3 underline-offset-2 hover:underline"
          >
            View posting
          </a>
        ) : null}
      </div>

      <div className="flex min-w-[120px] flex-col items-end gap-3">
        <MatchRing score={item.score} size={60} stroke={4} />
        <div className="flex gap-1.5">
          <Button variant="outline" size="sm" disabled={pending} onClick={() => onAction('skip')}>
            Skip
          </Button>
          <Button variant="outline" size="sm" disabled={pending} onClick={() => onAction('save')}>
            Save
          </Button>
          <Button size="sm" disabled={pending} onClick={() => onAction('apply')}>
            Apply
          </Button>
        </div>
      </div>
    </Card>
  )
}
