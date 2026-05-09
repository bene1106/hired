import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { FeedItem, JobAction } from '@/lib/types'

interface JobCardProps {
  item: FeedItem
  onAction: (action: JobAction) => void
  pending?: boolean
}

export function JobCard({ item, onAction, pending = false }: JobCardProps) {
  return (
    <Card data-testid={`job-card-${item.job_id}`}>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-3">
        <div className="flex flex-col gap-1">
          <CardTitle className="text-base">{item.title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {[item.company, item.location].filter(Boolean).join(' · ') || '—'}
            {item.remote_policy ? ` · ${item.remote_policy}` : ''}
          </p>
        </div>
        <ScoreBadge score={item.score} />
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {item.rationale ? (
          <p className="text-sm leading-relaxed line-clamp-3">{item.rationale}</p>
        ) : null}

        <div className="flex flex-wrap gap-1.5">
          {item.matched_skills.map((skill) => (
            <Badge
              key={`m-${skill}`}
              variant="default"
              className="bg-emerald-100 text-emerald-900 hover:bg-emerald-100"
            >
              {skill}
            </Badge>
          ))}
          {item.missing_skills.map((skill) => (
            <Badge key={`x-${skill}`} variant="outline" className="text-muted-foreground">
              {skill}
            </Badge>
          ))}
        </div>

        {item.red_flags.length > 0 ? (
          <ul className="list-disc pl-5 text-xs text-amber-700">
            {item.red_flags.map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
        ) : null}

        <div className="flex items-center justify-between gap-2 pt-1">
          {item.url ? (
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-muted-foreground underline-offset-2 hover:underline"
            >
              View posting
            </a>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={pending}
              onClick={() => onAction('skip')}
            >
              Skip
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={pending}
              onClick={() => onAction('save')}
            >
              Save
            </Button>
            <Button size="sm" disabled={pending} onClick={() => onAction('apply')}>
              Apply
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ScoreBadge({ score }: { score: number }) {
  const tone =
    score >= 75
      ? 'bg-emerald-500 text-white'
      : score >= 50
        ? 'bg-amber-400 text-amber-900'
        : 'bg-muted text-muted-foreground'
  return (
    <div
      data-testid="score-badge"
      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-base font-semibold ${tone}`}
      aria-label={`Match score ${score} out of 100`}
    >
      {score}
    </div>
  )
}
