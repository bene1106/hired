import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ApiError, api } from '@/lib/api'
import type { MockEvaluation, MockQuestion, TranscriptItem } from '@/lib/types'
import { cn } from '@/lib/utils'

import femaleListening from '@/assets/interviewer/female_listening.png'
import femaleSpeaking from '@/assets/interviewer/female_speaking.png'
import maleListening from '@/assets/interviewer/male_listening.png'
import maleSpeaking from '@/assets/interviewer/male_speaking.png'

import { MockInterviewResults } from './MockInterviewResults'
import { useMicRecorder, type MicRecorder } from './useMicRecorder'
import { useMockInterviewRunner } from './useMockInterviewRunner'
import { useVoiceRunner } from './useVoiceRunner'

// Interviewer avatars per gender × state. Unspecified falls back to the female
// voice (matching the backend TTS default).
const AVATAR_IMAGES: Record<'male' | 'female', { speaking: string; listening: string }> = {
  male: { speaking: maleSpeaking, listening: maleListening },
  female: { speaking: femaleSpeaking, listening: femaleListening },
}

/** mm:ss formatter for the answer timer. */
function fmt(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

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

      <div className="mx-auto flex w-full max-w-[760px] min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-8 py-10">
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

const AVATAR_BARS = 44

/**
 * Interviewer avatar (M4). While the interviewer is speaking (TTS), a circular
 * blue spectrum of bars pulses around a "speaking" photo; while it waits for
 * the candidate it shows the "listening" photo with a thin red idle border.
 */
function InterviewerAvatar({ gender, speaking }: { gender: string | null; speaking: boolean }) {
  const set = gender === 'male' ? AVATAR_IMAGES.male : AVATAR_IMAGES.female
  const src = speaking ? set.speaking : set.listening
  const label =
    gender === 'male' ? 'Male voice' : gender === 'female' ? 'Female voice' : 'Interviewer'
  return (
    <div className="flex flex-col items-center gap-2" data-testid="interviewer-avatar">
      <div className="relative h-40 w-40">
        {speaking ? (
          <div className="absolute inset-0" data-testid="avatar-spectrum" aria-hidden>
            {Array.from({ length: AVATAR_BARS }).map((_, i) => (
              <div
                key={i}
                className="absolute left-1/2 top-1/2"
                style={{ transform: `rotate(${(i * 360) / AVATAR_BARS}deg) translateY(80px)` }}
              >
                <span
                  className="block w-[3px] rounded-full bg-gradient-to-b from-sky-300 to-sky-600"
                  style={{
                    height: 10 + (i % 6) * 4,
                    transformOrigin: 'top',
                    animation: `mi-equalize ${700 + (i % 5) * 120}ms ease-in-out ${i * 35}ms infinite`,
                  }}
                />
              </div>
            ))}
          </div>
        ) : null}
        <div
          className={cn(
            'absolute inset-3 overflow-hidden rounded-full bg-surface-2',
            speaking ? 'ring-2 ring-sky-400/60' : 'ring-2 ring-warn',
          )}
        >
          <img src={src} alt="" aria-hidden className="h-full w-full object-cover object-top" />
        </div>
      </div>
      <span className="text-[11px] text-ink-3">
        {label} · {speaking ? 'speaking…' : 'listening'}
      </span>
    </div>
  )
}

/** Live input-level meter (a row of bars that light up with your voice). */
function AudioMeter({ getLevel }: { getLevel: () => number }) {
  const [level, setLevel] = useState(0)
  useEffect(() => {
    let raf = 0
    const loop = () => {
      setLevel(getLevel())
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [getLevel])

  const bars = 14
  // ~0.3 RMS reads as a loud voice; map that to a full meter.
  const active = Math.min(bars, Math.round((level / 0.3) * bars))
  return (
    <div data-testid="audio-meter" aria-hidden className="flex h-7 items-end gap-1">
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          className={cn(
            'w-1.5 rounded-sm transition-colors',
            i < active ? 'bg-brand-green' : 'bg-line',
          )}
          style={{ height: `${30 + (i / bars) * 70}%` }}
        />
      ))}
    </div>
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
  const mic = useMicRecorder()
  const [started, setStarted] = useState(false)

  // Release the stream/analyser when leaving voice mode.
  useEffect(() => {
    return () => mic.release()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!started) {
    return <MicCheck mic={mic} onStart={() => setStarted(true)} />
  }
  return <VoiceRun mic={mic} questions={questions} gender={gender} onComplete={onComplete} />
}

/** Pre-interview gate: get mic permission + confirm audio with a live meter. */
function MicCheck({ mic, onStart }: { mic: MicRecorder; onStart: () => void }) {
  const [requesting, setRequesting] = useState(false)
  return (
    <div data-testid="mic-check" className="flex flex-col gap-4">
      <h2 className="text-[20px] font-semibold text-ink">Microphone check</h2>
      <p className="text-[13px] text-ink-2">
        Voice mode needs your microphone. We only record while you&rsquo;re answering a question.
      </p>

      {!mic.supported ? (
        <p role="alert" className="text-[12px] text-warn">
          This environment doesn&rsquo;t support microphone capture. Use Text mode instead.
        </p>
      ) : mic.permission === 'granted' ? (
        <div className="flex flex-col gap-3">
          <span className="text-[12px] text-ink-3">
            Say something — the meter should move when it hears you:
          </span>
          <AudioMeter getLevel={mic.getLevel} />
          <div>
            <Button data-testid="voice-begin" onClick={onStart}>
              Start interview
            </Button>
          </div>
        </div>
      ) : mic.permission === 'denied' ? (
        <p role="alert" className="text-[12px] text-warn">
          Microphone access was blocked. Allow it in your browser settings and reopen, or use Text
          mode.
        </p>
      ) : (
        <div>
          <Button
            data-testid="enable-mic"
            disabled={requesting}
            onClick={async () => {
              setRequesting(true)
              await mic.requestPermission()
              setRequesting(false)
            }}
          >
            {requesting ? 'Requesting…' : 'Enable microphone'}
          </Button>
        </div>
      )}
    </div>
  )
}

function VoiceRun({
  mic,
  questions,
  gender,
  onComplete,
}: {
  mic: MicRecorder
  questions: MockQuestion[]
  gender: string | null
  onComplete: (transcript: TranscriptItem[]) => void
}) {
  const runner = useVoiceRunner({ mic, questions, gender, onComplete })
  const [typing, setTyping] = useState(false)
  const [draft, setDraft] = useState('')

  const phaseLabel =
    runner.phase === 'speaking'
      ? 'Asking the question…'
      : runner.phase === 'transcribing'
        ? 'Transcribing your answer…'
        : runner.phase === 'listening'
          ? runner.secondsAnswered === null
            ? 'Listening — start speaking your answer'
            : 'Listening…'
          : ''

  const finishInSeconds =
    runner.secondsAnswered !== null ? Math.max(0, runner.minSeconds - runner.secondsAnswered) : null

  return (
    <>
      {runner.showWarning && !runner.finished ? (
        <WarningButton seconds={runner.secondsLeftToMax} onClick={runner.finishAnswer} />
      ) : null}
      <InterviewerAvatar gender={gender} speaking={runner.phase === 'speaking'} />
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
        </span>
      </div>

      {/* Per-question timing: elapsed / max, remaining, and the min gate. */}
      <div
        data-testid="voice-timing"
        className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-ink-3"
      >
        <span>
          Time <span className="font-medium text-ink">{fmt(runner.secondsAnswered ?? 0)}</span> /{' '}
          {fmt(runner.maxSeconds)}
        </span>
        {runner.secondsLeftToMax !== null ? (
          <span>{runner.secondsLeftToMax}s remaining</span>
        ) : null}
        {runner.secondsAnswered === null ? (
          <span className="text-ink-4">Waiting for you to start speaking…</span>
        ) : finishInSeconds && finishInSeconds > 0 ? (
          <span data-testid="min-gate">You can finish in {finishInSeconds}s</span>
        ) : (
          <span className="text-brand-green">Minimum reached</span>
        )}
      </div>

      {runner.phase === 'listening' ? <AudioMeter getLevel={mic.getLevel} /> : null}

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
            disabled={!runner.canFinish}
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
