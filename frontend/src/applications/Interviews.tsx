import { useCallback, useEffect, useState } from 'react'

import { Icon } from '@/components/icons/Icon'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError, api } from '@/lib/api'
import type {
  Interview,
  InterviewCreateRequest,
  InterviewType,
  InterviewerGender,
  MockEvaluation,
  MockQuestion,
  MockRunSummary,
  VoiceStatus,
} from '@/lib/types'

import { MockInterviewResults } from './MockInterviewResults'
import { MockInterviewRunner } from './MockInterviewRunner'

const TYPE_LABELS: Record<InterviewType, string> = {
  hr: 'HR',
  technical: 'Technical',
  behavioral: 'Behavioral',
  system_design: 'System design',
  other: 'Other',
}

const GENDER_LABELS: Record<InterviewerGender, string> = {
  male: 'Male voice',
  female: 'Female voice',
  unspecified: 'Unspecified',
}

interface InterviewsSectionProps {
  applicationId: number
}

/**
 * Milestone 1 surface for the Interview stage: record the concrete interviews
 * an application was invited to (round/type/duration/interviewer) and prepare a
 * tailored question set ahead of time. The "Start mock interview" runner is
 * wired in a later milestone — the button is shown disabled here.
 */
export function InterviewsSection({ applicationId }: InterviewsSectionProps) {
  const [interviews, setInterviews] = useState<Interview[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Interview | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [activeRun, setActiveRun] = useState<{
    runId: number
    interviewId: number
    questions: MockQuestion[]
    voiceMode: boolean
    gender: string | null
  } | null>(null)
  // Bumped when a run finishes so each interview's run history reloads.
  const [runsVersion, setRunsVersion] = useState(0)
  // Pre-flight: which interview is choosing Voice/Text before starting.
  const [startingFor, setStartingFor] = useState<Interview | null>(null)
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null)
  const [preparingVoice, setPreparingVoice] = useState(false)

  const load = useCallback(async () => {
    try {
      setInterviews(await api.listInterviews(applicationId))
    } catch (err) {
      setError(messageFor(err, 'Could not load interviews.'))
    }
  }, [applicationId])

  useEffect(() => {
    void load()
  }, [load])

  const closeForm = () => {
    setShowForm(false)
    setEditing(null)
  }

  async function handleSubmit(payload: InterviewCreateRequest) {
    if (editing) {
      await api.updateInterview(applicationId, editing.id, payload)
    } else {
      await api.createInterview(applicationId, payload)
    }
    closeForm()
    await load()
  }

  async function handleDelete(id: number) {
    setBusyId(id)
    try {
      await api.deleteInterview(applicationId, id)
      await load()
    } finally {
      setBusyId(null)
    }
  }

  async function handlePrepare(id: number) {
    setBusyId(id)
    try {
      const updated = await api.prepareInterviewQuestions(applicationId, id)
      setInterviews((cur) => (cur ?? []).map((i) => (i.id === updated.id ? updated : i)))
    } catch (err) {
      setError(messageFor(err, 'Could not prepare questions.'))
    } finally {
      setBusyId(null)
    }
  }

  useEffect(() => {
    let cancelled = false
    void api
      .getVoiceStatus()
      .then((s) => {
        if (!cancelled) setVoiceStatus(s)
      })
      .catch(() => {
        if (!cancelled) setVoiceStatus(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const voiceReady = !!voiceStatus?.deps_available && !!voiceStatus?.models_ready

  async function setupVoice() {
    setPreparingVoice(true)
    try {
      await api.prepareVoice()
      // Poll until the background download finishes (or errors).
      for (let i = 0; i < 240; i++) {
        const s = await api.getVoiceStatus()
        setVoiceStatus(s)
        if (s.models_ready || s.prepare_state === 'error' || !s.deps_available) break
        await new Promise((r) => setTimeout(r, 2000))
      }
    } catch (err) {
      setError(messageFor(err, 'Could not set up voice.'))
    } finally {
      setPreparingVoice(false)
    }
  }

  async function beginRun(interview: Interview, voiceMode: boolean) {
    setStartingFor(null)
    setBusyId(interview.id)
    try {
      const run = await api.startMockRun(applicationId, interview.id, voiceMode)
      setActiveRun({
        runId: run.run_id,
        interviewId: interview.id,
        questions: run.questions,
        voiceMode,
        gender: interview.interviewer_gender,
      })
    } catch (err) {
      setError(messageFor(err, 'Could not start the mock interview.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {activeRun ? (
        <MockInterviewRunner
          applicationId={applicationId}
          interviewId={activeRun.interviewId}
          runId={activeRun.runId}
          questions={activeRun.questions}
          voiceMode={activeRun.voiceMode}
          interviewerGender={activeRun.gender}
          onClose={() => {
            setActiveRun(null)
            setRunsVersion((v) => v + 1)
            void load()
          }}
        />
      ) : null}

      {startingFor ? (
        <StartChooser
          interview={startingFor}
          voiceReady={voiceReady}
          voiceDepsAvailable={!!voiceStatus?.deps_available}
          preparingVoice={preparingVoice}
          onSetupVoice={setupVoice}
          onPick={(voiceMode) => void beginRun(startingFor, voiceMode)}
          onCancel={() => setStartingFor(null)}
        />
      ) : null}

      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[14px] font-semibold text-ink">Interviews</h3>
          <p className="text-[12px] text-ink-3">
            Record each interview you&rsquo;re invited to, then prepare a mock interview for the
            upcoming one.
          </p>
        </div>
        {!showForm ? (
          <Button size="sm" data-testid="add-interview" onClick={() => setShowForm(true)}>
            <Icon name="plus" size={12} /> Add interview
          </Button>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="text-[12px] text-warn">
          {error}
        </p>
      ) : null}

      {showForm ? (
        <InterviewForm
          initial={editing}
          onCancel={closeForm}
          onSubmit={handleSubmit}
          onError={(msg) => setError(msg)}
        />
      ) : null}

      {interviews === null ? (
        <p className="text-[12px] text-ink-3">Loading…</p>
      ) : interviews.length === 0 && !showForm ? (
        <p className="text-[13px] text-ink-3">No interviews recorded yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {interviews.map((interview) => (
            <InterviewRow
              key={interview.id}
              interview={interview}
              busy={busyId === interview.id}
              onEdit={() => {
                setEditing(interview)
                setShowForm(true)
              }}
              onDelete={() => handleDelete(interview.id)}
              onPrepare={() => handlePrepare(interview.id)}
              onStart={() => setStartingFor(interview)}
              applicationId={applicationId}
              runsVersion={runsVersion}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function InterviewRow({
  interview,
  busy,
  onEdit,
  onDelete,
  onPrepare,
  onStart,
  applicationId,
  runsVersion,
}: {
  interview: Interview
  busy: boolean
  onEdit: () => void
  onDelete: () => void
  onPrepare: () => void
  onStart: () => void
  applicationId: number
  runsVersion: number
}) {
  const hasQuestions = interview.question_count > 0
  return (
    <li
      data-testid={`interview-item-${interview.id}`}
      className="flex flex-col gap-2 rounded-md border border-line bg-surface p-3"
    >
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-medium text-ink">
          Round {interview.round_number} · {TYPE_LABELS[interview.interview_type]}
        </span>
        {interview.is_upcoming ? (
          <span className="chip chip-green">Upcoming</span>
        ) : (
          <span className="rounded-full border border-line px-2 py-0.5 text-[10px] text-ink-3">
            Past
          </span>
        )}
      </div>
      <div className="text-[12px] text-ink-3">
        {interview.duration_minutes} min · {GENDER_LABELS[interview.interviewer_gender]}
        {interview.scheduled_at
          ? ` · ${new Date(interview.scheduled_at).toLocaleDateString()}`
          : ''}
        {hasQuestions ? ` · ${interview.question_count} questions ready` : ''}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={busy}
          data-testid={`prepare-questions-${interview.id}`}
          onClick={onPrepare}
        >
          <Icon name="sparkle" size={12} />{' '}
          {busy ? 'Preparing…' : hasQuestions ? 'Regenerate questions' : 'Prepare questions'}
        </Button>
        <Button
          size="sm"
          disabled={!interview.is_upcoming || !hasQuestions || busy}
          data-testid={`start-mock-${interview.id}`}
          title={
            !interview.is_upcoming
              ? 'Only available for upcoming interviews'
              : !hasQuestions
                ? 'Prepare questions first'
                : undefined
          }
          onClick={onStart}
        >
          Start mock interview
        </Button>
        <button
          type="button"
          className="ml-auto text-[12px] text-ink-3 hover:text-ink"
          data-testid={`edit-interview-${interview.id}`}
          onClick={onEdit}
        >
          Edit
        </button>
        <button
          type="button"
          className="text-[12px] text-warn hover:underline disabled:opacity-50"
          disabled={busy}
          data-testid={`delete-interview-${interview.id}`}
          onClick={onDelete}
        >
          Delete
        </button>
      </div>
      <InterviewRunsHistory
        applicationId={applicationId}
        interviewId={interview.id}
        refresh={runsVersion}
      />
    </li>
  )
}

function InterviewRunsHistory({
  applicationId,
  interviewId,
  refresh,
}: {
  applicationId: number
  interviewId: number
  refresh: number
}) {
  const [runs, setRuns] = useState<MockRunSummary[] | null>(null)
  const [open, setOpen] = useState(false)
  const [viewing, setViewing] = useState<{
    runId: number
    evaluation: MockEvaluation | null
  } | null>(null)

  useEffect(() => {
    let cancelled = false
    void api
      .listMockRuns(applicationId, interviewId)
      .then((r) => {
        if (!cancelled) setRuns(r)
      })
      .catch(() => {
        if (!cancelled) setRuns([])
      })
    return () => {
      cancelled = true
    }
  }, [applicationId, interviewId, refresh])

  if (!runs || runs.length === 0) return null

  async function view(runId: number) {
    setViewing({ runId, evaluation: null })
    try {
      const detail = await api.getMockRun(applicationId, interviewId, runId)
      setViewing({ runId, evaluation: detail.evaluation })
    } catch {
      setViewing(null)
    }
  }

  return (
    <div className="mt-1 border-t border-line pt-2">
      <button
        type="button"
        data-testid={`runs-toggle-${interviewId}`}
        className="text-[12px] text-ink-3 hover:text-ink"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? '▾' : '▸'} Past runs ({runs.length})
      </button>
      {open ? (
        <ul className="mt-2 flex flex-col gap-1.5">
          {runs.map((run) => (
            <li key={run.id} className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-[12px] text-ink-2">
                <span>{new Date(run.started_at).toLocaleString()}</span>
                {run.overall_percentage !== null ? (
                  <span className="font-semibold text-ink">{run.overall_percentage}%</span>
                ) : (
                  <span className="text-ink-4">{run.status}</span>
                )}
                {run.has_evaluation ? (
                  <button
                    type="button"
                    data-testid={`view-run-${run.id}`}
                    className="text-ink-3 hover:text-ink hover:underline"
                    onClick={() => void view(run.id)}
                  >
                    View
                  </button>
                ) : null}
              </div>
              {viewing && viewing.runId === run.id && viewing.evaluation ? (
                <div className="rounded-md border border-line bg-surface-2 p-3">
                  <MockInterviewResults evaluation={viewing.evaluation} />
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

const TYPE_OPTIONS = Object.keys(TYPE_LABELS) as InterviewType[]
const GENDER_OPTIONS = Object.keys(GENDER_LABELS) as InterviewerGender[]

const selectClass =
  'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm'

function InterviewForm({
  initial,
  onCancel,
  onSubmit,
  onError,
}: {
  initial: Interview | null
  onCancel: () => void
  onSubmit: (payload: InterviewCreateRequest) => Promise<void>
  onError: (message: string) => void
}) {
  const [round, setRound] = useState(String(initial?.round_number ?? 1))
  const [type, setType] = useState<InterviewType>(initial?.interview_type ?? 'hr')
  const [duration, setDuration] = useState(String(initial?.duration_minutes ?? 30))
  const [gender, setGender] = useState<InterviewerGender>(
    initial?.interviewer_gender ?? 'unspecified',
  )
  const [scheduledAt, setScheduledAt] = useState(
    initial?.scheduled_at ? initial.scheduled_at.slice(0, 10) : '',
  )
  const [saving, setSaving] = useState(false)

  async function submit() {
    setSaving(true)
    try {
      await onSubmit({
        round_number: Number(round),
        interview_type: type,
        duration_minutes: Number(duration),
        interviewer_gender: gender,
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null,
      })
    } catch (err) {
      onError(messageFor(err, 'Could not save interview.'))
    } finally {
      setSaving(false)
    }
  }

  const valid = Number(round) >= 1 && Number(duration) >= 1

  return (
    <div
      data-testid="interview-form"
      className="flex flex-col gap-3 rounded-md border border-line bg-surface-2 p-4"
    >
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="interview-round">Round</Label>
          <Input
            id="interview-round"
            type="number"
            min={1}
            value={round}
            onChange={(e) => setRound(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="interview-duration">Duration (minutes)</Label>
          <Input
            id="interview-duration"
            type="number"
            min={1}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="interview-type">Type</Label>
          <select
            id="interview-type"
            className={selectClass}
            value={type}
            onChange={(e) => setType(e.target.value as InterviewType)}
          >
            {TYPE_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="interview-gender">Interviewer</Label>
          <select
            id="interview-gender"
            className={selectClass}
            value={gender}
            onChange={(e) => setGender(e.target.value as InterviewerGender)}
          >
            {GENDER_OPTIONS.map((g) => (
              <option key={g} value={g}>
                {GENDER_LABELS[g]}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="interview-date">Scheduled date (optional)</Label>
          <Input
            id="interview-date"
            type="date"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
          />
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          size="sm"
          data-testid="submit-interview"
          disabled={!valid || saving}
          onClick={submit}
        >
          {saving ? 'Saving…' : initial ? 'Save interview' : 'Add interview'}
        </Button>
      </div>
    </div>
  )
}

function StartChooser({
  interview,
  voiceReady,
  voiceDepsAvailable,
  preparingVoice,
  onSetupVoice,
  onPick,
  onCancel,
}: {
  interview: Interview
  voiceReady: boolean
  voiceDepsAvailable: boolean
  preparingVoice: boolean
  onSetupVoice: () => void
  onPick: (voiceMode: boolean) => void
  onCancel: () => void
}) {
  return (
    <div
      data-testid="start-chooser"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Choose interview mode"
    >
      <div className="flex w-full max-w-[420px] flex-col gap-4 rounded-lg border border-line bg-surface p-6 shadow-lg">
        <div>
          <h3 className="text-[15px] font-semibold text-ink">
            Start round {interview.round_number} mock interview
          </h3>
          <p className="text-[12px] text-ink-3">Choose how you want to answer.</p>
        </div>

        <div className="flex flex-col gap-2">
          <Button data-testid="choose-text" onClick={() => onPick(false)}>
            Text mode — type your answers
          </Button>

          {voiceReady ? (
            <Button data-testid="choose-voice" variant="outline" onClick={() => onPick(true)}>
              Voice mode — spoken questions &amp; answers
            </Button>
          ) : voiceDepsAvailable ? (
            <Button
              data-testid="setup-voice"
              variant="outline"
              disabled={preparingVoice}
              onClick={onSetupVoice}
            >
              {preparingVoice ? 'Downloading voice models…' : 'Set up voice (one-time download)'}
            </Button>
          ) : (
            <p className="text-[12px] text-ink-4">
              Voice mode isn&rsquo;t available in this build. Text mode works everywhere.
            </p>
          )}
        </div>

        <div className="flex justify-end">
          <Button size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  )
}

function messageFor(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return fallback
}
