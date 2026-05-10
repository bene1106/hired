import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
      <p role="alert" className="text-sm text-destructive">
        {error}
      </p>
    )
  }
  if (bundle === null) {
    return (
      <p className="text-sm text-muted-foreground" aria-live="polite">
        Loading interview prep…
      </p>
    )
  }

  const grouped = groupByCategory(bundle.questions)
  const practicedSet = new Set(attempts.map((a) => a.question))

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Question bank</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {Object.entries(grouped).map(([category, questions]) => (
            <div key={category} className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {CATEGORY_LABELS[category] ?? category}
              </span>
              <ul className="flex flex-col gap-1">
                {questions.map((q) => {
                  const practiced = practicedSet.has(q.question)
                  const active = activeQuestion?.question === q.question
                  return (
                    <li key={q.question}>
                      <button
                        type="button"
                        onClick={() => pickQuestion(q)}
                        data-testid={`question-${q.question}`}
                        className={`w-full rounded-md border border-border px-3 py-2 text-left text-sm hover:bg-muted/40 ${
                          active ? 'bg-muted/40' : ''
                        }`}
                      >
                        <span className="block">{q.question}</span>
                        {q.what_theyre_assessing ? (
                          <span className="mt-1 block text-xs text-muted-foreground">
                            Assesses: {q.what_theyre_assessing}
                          </span>
                        ) : null}
                        {practiced ? (
                          <span className="mt-1 inline-block text-xs text-emerald-700">
                            ✓ Practiced
                          </span>
                        ) : null}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Practice</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {activeQuestion === null ? (
            <p className="text-sm text-muted-foreground">
              Pick a question on the left to draft an answer.
            </p>
          ) : (
            <>
              <p className="text-sm font-medium">{activeQuestion.question}</p>
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
            <details className="mt-4 text-xs text-muted-foreground">
              <summary className="cursor-pointer">Role description</summary>
              <p className="mt-2 whitespace-pre-wrap">{bundle.role_context}</p>
            </details>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}

function FeedbackPanel({ feedback }: { feedback: PracticeFeedback }) {
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Feedback
      </p>
      {feedback.what_worked.length > 0 ? (
        <>
          <p className="mt-2 text-xs font-medium">What worked</p>
          <ul className="ml-4 list-disc text-sm">
            {feedback.what_worked.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
      {feedback.what_to_improve.length > 0 ? (
        <>
          <p className="mt-2 text-xs font-medium">What to improve</p>
          <ul className="ml-4 list-disc text-sm">
            {feedback.what_to_improve.map((note, idx) => (
              <li key={idx}>
                <strong>{note.issue}</strong> — {note.fix}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <p className="mt-2 text-xs font-medium">Stronger version</p>
      <p className="text-sm">{feedback.sample_stronger_answer}</p>
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
