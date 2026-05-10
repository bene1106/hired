import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import type { ApplicationDetail, ApplicationStatus } from '@/lib/types'

import { InterviewPrep } from './InterviewPrep'

const STATUS_OPTIONS: ApplicationStatus[] = [
  'saved',
  'applied',
  'interview',
  'offer',
  'rejected',
  'skipped',
]

type Tab = 'materials' | 'interview'

export function ApplicationDetailScreen() {
  const navigate = useNavigate()
  const { applicationId } = useParams<{ applicationId: string }>()
  const numericId = applicationId ? Number(applicationId) : null

  const [detail, setDetail] = useState<ApplicationDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('materials')
  const [savingStatus, setSavingStatus] = useState(false)
  const [rejectionNote, setRejectionNote] = useState('')

  useEffect(() => {
    if (!numericId) return
    let cancelled = false
    void (async () => {
      try {
        const data = await api.getApplication(numericId)
        if (!cancelled) setDetail(data)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Could not load application.'
        setError(message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [numericId])

  async function changeStatus(next: ApplicationStatus) {
    if (!numericId || !detail) return
    setSavingStatus(true)
    try {
      const note = next === 'rejected' && rejectionNote.trim() ? rejectionNote.trim() : undefined
      await api.updateApplicationStatus(numericId, next, note)
      const refreshed = await api.getApplication(numericId)
      setDetail(refreshed)
      setRejectionNote('')
    } finally {
      setSavingStatus(false)
    }
  }

  if (error) {
    return <p className="px-6 py-6 text-sm text-destructive">{error}</p>
  }
  if (!detail) {
    return <p className="px-6 py-6 text-sm text-muted-foreground">Loading…</p>
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            {detail.job.title ?? 'Application'}
          </h1>
          <p className="text-xs text-muted-foreground">
            {detail.job.company ?? '—'}
            {detail.job.location ? ` · ${detail.job.location}` : ''}
          </p>
        </div>
        <Button size="sm" variant="ghost" onClick={() => navigate('/app/applications')}>
          Dashboard
        </Button>
      </header>

      <section className="border-b border-border px-6 py-3 flex flex-wrap items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">Status</span>
        {STATUS_OPTIONS.map((option) => (
          <Button
            key={option}
            size="sm"
            variant={detail.status === option ? 'default' : 'outline'}
            disabled={savingStatus}
            onClick={() => void changeStatus(option)}
          >
            {option}
          </Button>
        ))}
        {detail.status === 'rejected' ? (
          <div className="flex w-full items-center gap-2 pt-3">
            <Textarea
              placeholder="Optional: log why this was rejected (helps spot patterns later)."
              value={rejectionNote || detail.notes || ''}
              onChange={(event) => setRejectionNote(event.target.value)}
              rows={2}
              aria-label="Rejection notes"
            />
            <Button
              size="sm"
              variant="outline"
              disabled={savingStatus || !rejectionNote.trim()}
              onClick={() => void changeStatus('rejected')}
            >
              Save note
            </Button>
          </div>
        ) : null}
      </section>

      <section className="border-b border-border px-6 py-2 flex items-center gap-2">
        <Button
          size="sm"
          variant={tab === 'materials' ? 'default' : 'outline'}
          onClick={() => setTab('materials')}
        >
          Materials
        </Button>
        <Button
          size="sm"
          variant={tab === 'interview' ? 'default' : 'outline'}
          onClick={() => setTab('interview')}
        >
          Interview prep
        </Button>
      </section>

      <div className="px-6 py-6">
        {tab === 'materials' ? (
          <div className="grid gap-4">
            {detail.materials.company_brief ? (
              <Card data-testid="detail-company-brief">
                <CardHeader>
                  <CardTitle className="text-base">Company brief</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{detail.materials.company_brief.content}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            ) : null}
            {detail.materials.cv_suggestions ? (
              <Card data-testid="detail-cv-suggestions">
                <CardHeader>
                  <CardTitle className="text-base">CV tailoring</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{detail.materials.cv_suggestions.content}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            ) : null}
            {detail.materials.cover_letter ? (
              <Card data-testid="detail-cover-letter">
                <CardHeader>
                  <CardTitle className="text-base">Cover letter</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="whitespace-pre-wrap text-sm">
                    {detail.materials.cover_letter.content}
                  </pre>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {detail.materials.cover_letter.edit_count > 0
                      ? `Edited ${detail.materials.cover_letter.edit_count} time${
                          detail.materials.cover_letter.edit_count === 1 ? '' : 's'
                        } since generation.`
                      : 'No edits yet.'}
                  </p>
                </CardContent>
              </Card>
            ) : null}
            {!detail.materials.company_brief && !detail.materials.cover_letter ? (
              <p className="text-sm text-muted-foreground">
                No generated materials yet. Open from the feed and click Apply.
              </p>
            ) : null}
          </div>
        ) : numericId ? (
          <InterviewPrep applicationId={numericId} />
        ) : null}
      </div>
    </main>
  )
}
