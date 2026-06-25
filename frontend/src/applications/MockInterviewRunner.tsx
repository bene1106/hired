import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, api } from '@/lib/api'
import type { MockQuestion, TranscriptItem } from '@/lib/types'

import { useMockInterviewRunner } from './useMockInterviewRunner'

interface MockInterviewRunnerProps {
  applicationId: number
  interviewId: number
  runId: number
  questions: MockQuestion[]
  /** Called after the run is submitted or the candidate ends it early. */
  onClose: (opts: { completed: boolean }) => void
}

/**
 * Full-screen, timed, text-mode mock interview (M2). The timing state machine
 * lives in `useMockInterviewRunner`; this component is the surface plus the
 * completion call. Scoring/feedback is M3.
 */
export function MockInterviewRunner({
  applicationId,
  interviewId,
  runId,
  questions,
  onClose,
}: MockInterviewRunnerProps) {
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleComplete(transcript: TranscriptItem[]) {
    setSubmitting(true)
    try {
      await api.completeMockRun(applicationId, interviewId, runId, transcript)
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit the interview.')
    } finally {
      setSubmitting(false)
    }
  }

  const runner = useMockInterviewRunner({ questions, onComplete: handleComplete })

  return (
    <div
      data-testid="mock-runner"
      className="fixed inset-0 z-50 flex flex-col bg-background"
      role="dialog"
      aria-modal="true"
      aria-label="Mock interview"
    >
      {/* Blinking red warning, top-center, during the final seconds. */}
      {runner.showWarning && !runner.finished ? (
        <button
          type="button"
          data-testid="runner-warning"
          onClick={runner.submitNow}
          className="absolute left-1/2 top-4 z-10 -translate-x-1/2 animate-pulse rounded-full bg-warn px-3 py-1 text-[12px] font-semibold text-white shadow"
        >
          {runner.secondsLeftToMax}s left — wrap up
        </button>
      ) : null}

      <div className="flex items-center justify-between border-b border-line px-8 py-4">
        <div className="text-[12px] font-medium text-ink-3">
          {runner.finished || done
            ? 'Mock interview'
            : `Question ${runner.index + 1} of ${runner.total}`}
        </div>
        <Button
          size="sm"
          variant="ghost"
          data-testid="runner-end"
          onClick={() => onClose({ completed: done })}
        >
          {done ? 'Close' : 'End interview'}
        </Button>
      </div>

      <div className="mx-auto flex w-full max-w-[760px] flex-1 flex-col gap-5 px-8 py-10">
        {done ? (
          <div data-testid="runner-complete" className="flex flex-col gap-3">
            <h2 className="text-[20px] font-semibold text-ink">Interview submitted</h2>
            <p className="text-[14px] text-ink-2">
              Your answers were recorded. Automated scoring and feedback arrive in the next update.
            </p>
            <div>
              <Button onClick={() => onClose({ completed: true })}>Back to interviews</Button>
            </div>
          </div>
        ) : submitting ? (
          <p className="text-[14px] text-ink-3">Submitting your answers…</p>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              {runner.isRepeat ? (
                <span className="text-[12px] font-medium text-warn">Let me repeat that…</span>
              ) : null}
              {runner.isRephrased ? (
                <span className="text-[12px] font-medium text-ink-3">
                  Let me put it another way…
                </span>
              ) : null}
              <h2 data-testid="runner-question" className="text-[20px] font-semibold text-ink">
                {runner.displayText}
              </h2>
              {runner.phase === 'answering' && runner.secondsLeftToMax !== null ? (
                <span className="text-[12px] text-ink-3">{runner.secondsLeftToMax}s remaining</span>
              ) : (
                <span className="text-[12px] text-ink-4">Start typing your answer…</span>
              )}
            </div>

            <Textarea
              data-testid="runner-answer"
              aria-label="Your answer"
              value={runner.answer}
              onChange={(e) => runner.onAnswerChange(e.target.value)}
              rows={12}
              className="flex-1 text-[15px] leading-7"
              autoFocus
            />

            {error ? (
              <p role="alert" className="text-[12px] text-warn">
                {error}
              </p>
            ) : null}

            <div className="flex justify-end">
              <Button
                data-testid="runner-submit"
                disabled={!runner.canSubmit}
                onClick={runner.submitNow}
              >
                {runner.index + 1 === runner.total ? 'Finish' : 'Submit answer'}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
