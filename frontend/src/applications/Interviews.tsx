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
  MockQuestion,
} from '@/lib/types'

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
  } | null>(null)

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

  async function handleStart(id: number) {
    setBusyId(id)
    try {
      const run = await api.startMockRun(applicationId, id)
      setActiveRun({ runId: run.run_id, interviewId: id, questions: run.questions })
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
          onClose={() => {
            setActiveRun(null)
            void load()
          }}
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
              onStart={() => handleStart(interview.id)}
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
}: {
  interview: Interview
  busy: boolean
  onEdit: () => void
  onDelete: () => void
  onPrepare: () => void
  onStart: () => void
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
    </li>
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

function messageFor(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return fallback
}
