import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import type {
  InterviewQuestion,
  InterviewQuestionBundle,
  PracticeAttempt,
  PracticeFeedback,
} from '@/lib/types'

interface InterviewPrepProps {
  applicationId: number
}

const CATEGORY_LABELS: Record<string, string> = {
  technical: 'Technical',
  behavioral: 'Behavioral',
  role_specific: 'Role-specific',
  company_fit: 'Company fit',
}

export function InterviewPrep({ applicationId }: InterviewPrepProps) {
  const [bundle, setBundle] = useState<InterviewQuestionBundle | null>(null)
  const [attempts, setAttempts] = useState<PracticeAttempt[]>([])
  const [activeQuestion, setActiveQuestion] = useState<InterviewQuestion | null>(null)
  const [answer, setAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<PracticeFeedback | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const [questions, history] = await Promise.all([
          api.getInterviewQuestions(applicationId),
          api.listPracticeAttempts(applicationId),
        ])
        if (cancelled) return
        setBundle(questions)
        setAttempts(history)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Could not load interview prep.'
        setError(message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [applicationId])

  function pickQuestion(question: InterviewQuestion) {
    setActiveQuestion(question)
    setAnswer('')
    setFeedback(null)
  }

  async function submit() {
    if (!activeQuestion || !answer.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const result = await api.submitPracticeAnswer(applicationId, {
        question: activeQuestion.question,
        category: activeQuestion.category,
        answer,
      })
      setFeedback(result.feedback)
      setAttempts((prev) => [result, ...prev])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not submit answer.'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  if (error) {
    return (
      <p role="alert" className="text-[13px] text-warn">
        {error}
      </p>
    )
  }
  if (bundle === null) {
    return (
      <p className="text-[13px] text-ink-3" aria-live="polite">
        Loading interview prep…
      </p>
    )
  }

  const grouped = groupByCategory(bundle.questions)
  const practicedSet = new Set(attempts.map((a) => a.question))

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="flex flex-col p-5">
        <div className="mb-4 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
          Question bank
        </div>
        <div className="flex flex-col gap-5">
          {Object.entries(grouped).map(([category, questions]) => (
            <div key={category} className="flex flex-col gap-2">
              <span className="text-[12px] font-semibold tracking-[-0.01em] text-ink">
                {CATEGORY_LABELS[category] ?? category}
              </span>
              <ul className="flex flex-col gap-1.5">
                {questions.map((q) => {
                  const practiced = practicedSet.has(q.question)
                  const active = activeQuestion?.question === q.question
                  return (
                    <li key={q.question}>
                      <button
                        type="button"
                        onClick={() => pickQuestion(q)}
                        data-testid={`question-${q.question}`}
                        className={`w-full rounded-md border px-3 py-2.5 text-left text-[13px] leading-relaxed transition-colors ${
                          active
                            ? 'border-line-strong bg-surface-2 text-ink'
                            : 'border-line bg-surface text-ink-2 hover:bg-surface-2'
                        }`}
                      >
                        <span className="block">{q.question}</span>
                        {q.what_theyre_assessing ? (
                          <span className="mt-1 block text-[12px] text-ink-3">
                            Assesses: {q.what_theyre_assessing}
                          </span>
                        ) : null}
                        {practiced ? (
                          <span className="chip chip-green mt-1.5">✓ Practiced</span>
                        ) : null}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>
      </Card>

      <Card className="flex flex-col p-5">
        <div className="mb-4 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
          Practice
        </div>
        <div className="flex flex-col gap-3">
          {activeQuestion === null ? (
            <p className="text-[13px] text-ink-3">
              Pick a question on the left to draft an answer.
            </p>
          ) : (
            <>
              <p className="text-[14px] font-medium tracking-[-0.01em] text-ink">
                {activeQuestion.question}
              </p>
              <Textarea
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder="Type your answer…"
                rows={6}
                aria-label="Practice answer"
              />
              <div className="flex justify-end">
                <Button size="sm" disabled={submitting || !answer.trim()} onClick={submit}>
                  {submitting ? 'Scoring…' : 'Get feedback'}
                </Button>
              </div>
              {feedback ? <FeedbackPanel feedback={feedback} /> : null}
            </>
          )}
          {bundle.role_context ? (
            <details className="mt-4 text-[12px] text-ink-3">
              <summary className="cursor-pointer font-medium text-ink-2 hover:text-ink">
                Role description
              </summary>
              <p className="mt-2 whitespace-pre-wrap leading-relaxed">{bundle.role_context}</p>
            </details>
          ) : null}
        </div>
      </Card>
    </div>
  )
}

function FeedbackPanel({ feedback }: { feedback: PracticeFeedback }) {
  return (
    <div className="rounded-md border border-brand-green-soft bg-brand-green-tint p-4 text-[13px]">
      <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-brand-green">
        Feedback
      </p>
      {feedback.what_worked.length > 0 ? (
        <>
          <p className="mt-3 text-[12px] font-semibold tracking-[-0.01em] text-ink">What worked</p>
          <ul className="mt-1 ml-4 list-disc text-[13px] leading-relaxed text-ink-2">
            {feedback.what_worked.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
      {feedback.what_to_improve.length > 0 ? (
        <>
          <p className="mt-3 text-[12px] font-semibold tracking-[-0.01em] text-ink">
            What to improve
          </p>
          <ul className="mt-1 ml-4 list-disc text-[13px] leading-relaxed text-ink-2">
            {feedback.what_to_improve.map((note, idx) => (
              <li key={idx}>
                <strong className="font-semibold text-ink">{note.issue}</strong> — {note.fix}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <p className="mt-3 text-[12px] font-semibold tracking-[-0.01em] text-ink">Stronger version</p>
      <p className="mt-1 text-[13px] leading-relaxed text-ink-2">
        {feedback.sample_stronger_answer}
      </p>
    </div>
  )
}

function groupByCategory(questions: InterviewQuestion[]): Record<string, InterviewQuestion[]> {
  const out: Record<string, InterviewQuestion[]> = {}
  for (const q of questions) {
    const key = q.category || 'other'
    out[key] ??= []
    out[key].push(q)
  }
  return out
}
