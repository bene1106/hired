import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, api } from '@/lib/api'
import type { MockEvaluation, MockQuestion, TranscriptItem } from '@/lib/types'

import { MockInterviewResults } from './MockInterviewResults'
import { useMockInterviewRunner } from './useMockInterviewRunner'
import { useVoiceRunner } from './useVoiceRunner'

interface MockInterviewRunnerProps {
  applicationId: number
  interviewId: number
  runId: number
  questions: MockQuestion[]
  voiceMode?: boolean
  interviewerGender?: string | null
  /** Called after the run is submitted or the candidate ends it early. */
  onClose: (opts: { completed: boolean }) => void
}

/**
 * Full-screen mock interview shell. Owns submission + scoring + completion; the
 * in-progress surface is either the text runner (M2) or the voice runner (M4),
 * chosen by `voiceMode`. Both feed the same `handleComplete`.
 */
export function MockInterviewRunner({
  applicationId,
  interviewId,
  runId,
  questions,
  voiceMode = false,
  interviewerGender = null,
  onClose,
}: MockInterviewRunnerProps) {
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [evaluation, setEvaluation] = useState<MockEvaluation | null>(null)
  const [evalError, setEvalError] = useState<string | null>(null)

  async function runEvaluation() {
    setEvaluating(true)
    setEvalError(null)
    try {
      const detail = await api.evaluateMockRun(applicationId, interviewId, runId)
      setEvaluation(detail.evaluation)
    } catch (err) {
      setEvalError(err instanceof ApiError ? err.message : 'Could not score the interview.')
    } finally {
      setEvaluating(false)
    }
  }

  async function handleComplete(transcript: TranscriptItem[]) {
    setSubmitting(true)
    try {
      await api.completeMockRun(applicationId, interviewId, runId, transcript)
      setDone(true)
      setSubmitting(false)
      await runEvaluation()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit the interview.')
      setSubmitting(false)
    }
  }

  return (
    <div
      data-testid="mock-runner"
      className="fixed inset-0 z-50 flex flex-col bg-background"
      role="dialog"
      aria-modal="true"
      aria-label="Mock interview"
    >
      <div className="flex items-center justify-between border-b border-line px-8 py-4">
        <div className="text-[12px] font-medium text-ink-3">Mock interview</div>
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
          <div data-testid="runner-complete" className="flex flex-col gap-4">
            <h2 className="text-[20px] font-semibold text-ink">Interview submitted</h2>
            {evaluating ? (
              <p className="text-[14px] text-ink-3">Scoring your answers…</p>
            ) : evaluation ? (
              <MockInterviewResults evaluation={evaluation} />
            ) : (
              <div className="flex flex-col gap-2">
                <p className="text-[14px] text-ink-2">
                  Your answers were recorded
                  {evalError ? `, but scoring failed: ${evalError}` : '.'}
                </p>
                <div>
                  <Button size="sm" variant="outline" onClick={() => void runEvaluation()}>
                    Score now
                  </Button>
                </div>
              </div>
            )}
            <div>
              <Button onClick={() => onClose({ completed: true })}>Back to interviews</Button>
            </div>
          </div>
        ) : submitting ? (
          <p className="text-[14px] text-ink-3">Submitting your answers…</p>
        ) : error ? (
          <p role="alert" className="text-[12px] text-warn">
            {error}
          </p>
        ) : voiceMode ? (
          <VoiceSurface
            questions={questions}
            gender={interviewerGender}
            onComplete={handleComplete}
          />
        ) : (
          <TextSurface questions={questions} onComplete={handleComplete} />
        )}
      </div>
    </div>
  )
}

function WarningButton({ seconds, onClick }: { seconds: number | null; onClick: () => void }) {
  return (
    <button
      type="button"
      data-testid="runner-warning"
      onClick={onClick}
      className="absolute left-1/2 top-4 z-10 -translate-x-1/2 animate-pulse rounded-full bg-warn px-3 py-1 text-[12px] font-semibold text-white shadow"
    >
      {seconds}s left — wrap up
    </button>
  )
}

function TextSurface({
  questions,
  onComplete,
}: {
  questions: MockQuestion[]
  onComplete: (transcript: TranscriptItem[]) => void
}) {
  const runner = useMockInterviewRunner({ questions, onComplete })
  return (
    <>
      {runner.showWarning && !runner.finished ? (
        <WarningButton seconds={runner.secondsLeftToMax} onClick={runner.submitNow} />
      ) : null}
      <div className="flex flex-col gap-1">
        <span className="text-[12px] text-ink-3">
          Question {runner.index + 1} of {runner.total}
        </span>
        {runner.isRepeat ? (
          <span className="text-[12px] font-medium text-warn">Let me repeat that…</span>
        ) : null}
        {runner.isRephrased ? (
          <span className="text-[12px] font-medium text-ink-3">Let me put it another way…</span>
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

      <div className="flex justify-end">
        <Button data-testid="runner-submit" disabled={!runner.canSubmit} onClick={runner.submitNow}>
          {runner.index + 1 === runner.total ? 'Finish' : 'Submit answer'}
        </Button>
      </div>
    </>
  )
}

function VoiceSurface({
  questions,
  gender,
  onComplete,
}: {
  questions: MockQuestion[]
  gender: string | null
  onComplete: (transcript: TranscriptItem[]) => void
}) {
  const runner = useVoiceRunner({ questions, gender, onComplete })
  const [typing, setTyping] = useState(false)
  const [draft, setDraft] = useState('')

  const phaseLabel =
    runner.phase === 'speaking'
      ? 'Asking the question…'
      : runner.phase === 'transcribing'
        ? 'Transcribing your answer…'
        : runner.phase === 'listening'
          ? 'Listening — answer out loud'
          : ''

  return (
    <>
      {runner.showWarning && !runner.finished ? (
        <WarningButton seconds={runner.secondsLeftToMax} onClick={runner.finishAnswer} />
      ) : null}
      <div className="flex flex-col gap-1">
        <span className="text-[12px] text-ink-3">
          Question {runner.index + 1} of {runner.total}
        </span>
        {runner.isRepeat ? (
          <span className="text-[12px] font-medium text-warn">Let me repeat that…</span>
        ) : null}
        {runner.isRephrased ? (
          <span className="text-[12px] font-medium text-ink-3">Let me put it another way…</span>
        ) : null}
        <h2 data-testid="runner-question" className="text-[20px] font-semibold text-ink">
          {runner.displayText}
        </h2>
        <span className="text-[12px] text-ink-3" aria-live="polite">
          {phaseLabel}
          {runner.phase === 'listening' && runner.secondsLeftToMax !== null
            ? ` · ${runner.secondsLeftToMax}s left`
            : ''}
        </span>
      </div>

      {typing ? (
        <div className="flex flex-col gap-2">
          <Textarea
            data-testid="voice-text"
            aria-label="Type your answer instead"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={8}
            className="text-[15px] leading-7"
          />
          <div className="flex justify-end">
            <Button
              data-testid="voice-text-submit"
              disabled={runner.phase !== 'listening'}
              onClick={() => {
                runner.submitText(draft)
                setDraft('')
                setTyping(false)
              }}
            >
              Submit answer
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <Button
            data-testid="voice-done"
            disabled={runner.phase !== 'listening'}
            onClick={runner.finishAnswer}
          >
            Done answering
          </Button>
          <button
            type="button"
            data-testid="voice-type-toggle"
            className="text-[12px] text-ink-3 hover:text-ink"
            onClick={() => setTyping(true)}
          >
            Type instead
          </button>
        </div>
      )}
    </>
  )
}
