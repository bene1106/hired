import { useState } from 'react'

import { CompanyMark } from '@/components/CompanyMark'
import { Icon } from '@/components/icons/Icon'
import { MatchRing } from '@/components/MatchRing'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { FeedItem, JobAction, JobInteractAction, JobInteractReason } from '@/lib/types'

interface JobCardProps {
  item: FeedItem
  onAction: (action: JobAction) => void
  onInteract: (action: JobInteractAction, reason?: JobInteractReason) => void
  pending?: boolean
}

export function JobCard({ item, onAction, onInteract, pending = false }: JobCardProps) {
  const [showReasons, setShowReasons] = useState<false | 'up' | 'down'>(false)

  const meta = [item.location, item.remote_policy].filter(Boolean).join(' · ')

  const handleLinkClick = () => {
    if (item.unread) {
      onInteract('read')
    }
  }

  const handleThumbsDown = () => {
    if (item.feedback_signal === -1) {
      onInteract('remove_feedback')
      setShowReasons(false)
      return
    }
    if (showReasons !== 'down') {
      setShowReasons('down')
      onInteract('thumbs_down')
    } else {
      setShowReasons(false)
    }
  }

  const handleThumbsUp = () => {
    if (item.feedback_signal === 1) {
      onInteract('remove_feedback')
      setShowReasons(false)
      return
    }
    if (showReasons !== 'up') {
      setShowReasons('up')
      onInteract('thumbs_up')
    } else {
      setShowReasons(false)
    }
  }

  return (
    <Card
      data-testid={`job-card-${item.job_id}`}
      className="relative grid grid-cols-[auto_1fr_auto] gap-4 p-[18px]"
    >
      {item.unread && (
        <button
          className="group absolute left-2 top-2 z-10 flex items-center justify-center overflow-hidden rounded-full text-blue-500 hover:bg-blue-50 border border-transparent hover:border-blue-100 transition-all"
          onClick={() => onInteract('read')}
          title="Mark as read"
          aria-label="Mark as read"
        >
          {/* The dot state: visible when NOT hovered */}
          <div className="h-2 w-2 rounded-full bg-blue-500 group-hover:hidden" />

          {/* The expanded state: visible only on hover */}
          <div className="hidden items-center gap-1 px-1.5 py-0.5 group-hover:flex">
            <Icon name="check" size={12} strokeWidth={3} />
            <span className="text-[10px] font-medium whitespace-nowrap">Mark as read</span>
          </div>
        </button>
      )}

      <div className="relative self-start">
        <CompanyMark company={item.company} size={40} />
      </div>

      <div className="min-w-0">
        <div className="mb-1 flex flex-wrap items-center gap-2">
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
            onClick={handleLinkClick}
          >
            View posting
          </a>
        ) : null}
      </div>

      <div className="flex min-w-[120px] flex-col items-end gap-3">
        <MatchRing score={item.score} size={60} stroke={4} />

        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-1.5">
            {item.feedback_signal === 1 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-ink-3 hover:text-ink"
                onClick={() => setShowReasons(showReasons === 'up' ? false : 'up')}
              >
                <Icon name={showReasons === 'up' ? 'chevronUp' : 'chevronDown'} size={14} />
                <span className="sr-only">Toggle reasons</span>
              </Button>
            )}

            {item.feedback_signal === -1 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-ink-3 hover:text-ink"
                onClick={() => setShowReasons(showReasons === 'down' ? false : 'down')}
              >
                <Icon name={showReasons === 'down' ? 'chevronUp' : 'chevronDown'} size={14} />
                <span className="sr-only">Toggle reasons</span>
              </Button>
            )}

            <Button
              variant="ghost"
              size="sm"
              className={cn(
                'h-7 w-7 p-0',
                item.feedback_signal === 1 ? 'text-brand-green' : 'text-ink-3 hover:text-ink',
              )}
              onClick={handleThumbsUp}
            >
              <Icon name="thumbsUp" size={14} strokeWidth={item.feedback_signal === 1 ? 3 : 1.75} />
              <span className="sr-only">Thumbs up</span>
            </Button>

            <Button
              variant="ghost"
              size="sm"
              className={cn(
                'h-7 w-7 p-0',
                item.feedback_signal === -1 ? 'text-warn' : 'text-ink-3 hover:text-ink',
              )}
              onClick={handleThumbsDown}
            >
              <Icon
                name="thumbsDown"
                size={14}
                strokeWidth={item.feedback_signal === -1 ? 3 : 1.75}
              />
              <span className="sr-only">Thumbs down</span>
            </Button>
          </div>

          {showReasons && (
            <div className="flex gap-1.5 animate-in fade-in slide-in-from-top-2">
              <Button
                variant={item.feedback_reason === 'location' ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-[11px] px-2"
                onClick={() => {
                  onInteract(showReasons === 'up' ? 'thumbs_up' : 'thumbs_down', 'location')
                  setShowReasons(false)
                }}
              >
                Location
              </Button>
              <Button
                variant={item.feedback_reason === 'tech_stack' ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-[11px] px-2"
                onClick={() => {
                  onInteract(showReasons === 'up' ? 'thumbs_up' : 'thumbs_down', 'tech_stack')
                  setShowReasons(false)
                }}
              >
                Tech-Stack
              </Button>
              <Button
                variant={item.feedback_reason === 'company' ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-[11px] px-2"
                onClick={() => {
                  onInteract(showReasons === 'up' ? 'thumbs_up' : 'thumbs_down', 'company')
                  setShowReasons(false)
                }}
              >
                Company
              </Button>
            </div>
          )}
        </div>

        <div className="mt-auto flex gap-1.5">
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
