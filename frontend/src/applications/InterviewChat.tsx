import { useCallback, useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Icon } from '@/components/icons/Icon'
import { api } from '@/lib/api'
import type { ChatTurn, InterviewSessionSummary } from '@/lib/types'

interface InterviewChatProps {
  applicationId: number
}

interface ActiveSession {
  id: number
  messages: ChatTurn[]
}

const CONFIDENCE_LABELS = ['Dreading it', 'Unsure', 'Okay', 'Solid', 'Ready']

export function InterviewChat({ applicationId }: InterviewChatProps) {
  const [sessions, setSessions] = useState<InterviewSessionSummary[] | null>(null)
  const [active, setActive] = useState<ActiveSession | null>(null)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confidence, setConfidence] = useState(3)
  const scrollRef = useRef<HTMLDivElement>(null)

  const refreshSessionList = useCallback(async () => {
    try {
      const list = await api.listInterviewSessions(applicationId)
      setSessions(list)
      return list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load coach sessions.')
      return null
    }
  }, [applicationId])

  useEffect(() => {
    void refreshSessionList()
  }, [refreshSessionList])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [active?.messages.length, streaming])

  async function startSession() {
    setError(null)
    try {
      const detail = await api.createInterviewSession(applicationId)
      setActive({ id: detail.id, messages: detail.messages })
      setConfidence(3)
      await refreshSessionList()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create a session.')
    }
  }

  async function resumeSession(sessionId: number) {
    setError(null)
    try {
      const detail = await api.getInterviewSession(applicationId, sessionId)
      setActive({ id: detail.id, messages: detail.messages })
      setConfidence(3)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the session.')
    }
  }

  async function deleteSession(sessionId: number) {
    setError(null)
    try {
      await api.deleteInterviewSession(applicationId, sessionId)
      if (active?.id === sessionId) setActive(null)
      await refreshSessionList()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete the session.')
    }
  }

  async function send() {
    if (!active || streaming) return
    const text = input.trim()
    if (text === '') return

    const userTurn: ChatTurn = {
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }
    const assistantTurn: ChatTurn = { role: 'assistant', content: '', created_at: null }
    setActive((prev) =>
      prev === null ? prev : { ...prev, messages: [...prev.messages, userTurn, assistantTurn] },
    )
    setInput('')
    setStreaming(true)
    setError(null)

    try {
      for await (const event of api.chatStream(applicationId, active.id, text)) {
        if ('chunk' in event) {
          setActive((prev) => {
            if (prev === null) return prev
            const msgs = [...prev.messages]
            const last = msgs[msgs.length - 1]
            msgs[msgs.length - 1] = { ...last, content: last.content + event.chunk }
            return { ...prev, messages: msgs }
          })
        } else if ('error' in event) {
          setError(event.error)
          setActive((prev) => {
            if (prev === null) return prev
            // Drop the empty assistant bubble; the server didn't persist it.
            return { ...prev, messages: prev.messages.slice(0, -1) }
          })
          return
        }
        // `done` events: nothing extra to do — the chunks already updated the
        // bubble in place. The server's persisted transcript matches.
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Coach stream failed.')
      setActive((prev) =>
        prev === null ? prev : { ...prev, messages: prev.messages.slice(0, -1) },
      )
    } finally {
      setStreaming(false)
      void refreshSessionList()
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void send()
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[220px_1fr]" data-testid="interview-chat">
      <Card className="flex flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
            Coach sessions
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void startSession()}
            data-testid="new-session"
          >
            <Icon name="plus" size={12} /> New
          </Button>
        </div>
        {sessions === null ? (
          <p className="text-[12px] text-ink-3" aria-live="polite">
            Loading sessions…
          </p>
        ) : sessions.length === 0 ? (
          <p className="text-[12px] text-ink-3">
            No sessions yet. Start one — the coach will open with a question.
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {sessions.map((s) => {
              const isActive = active?.id === s.id
              return (
                <li key={s.id} className="flex items-stretch gap-1">
                  <button
                    type="button"
                    onClick={() => void resumeSession(s.id)}
                    data-testid={`session-${s.id}`}
                    className={`flex-1 rounded-md border px-2.5 py-2 text-left text-[12px] leading-snug transition-colors ${
                      isActive
                        ? 'border-line-strong bg-surface-2 text-ink'
                        : 'border-line bg-surface text-ink-2 hover:bg-surface-2'
                    }`}
                  >
                    <span className="block truncate font-medium">
                      {s.preview ?? 'Empty session'}
                    </span>
                    <span className="font-mono text-[10px] text-ink-3">
                      {s.turn_count} {s.turn_count === 1 ? 'turn' : 'turns'}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void deleteSession(s.id)}
                    aria-label={`Delete session ${s.id}`}
                    className="rounded-md border border-line bg-surface px-1.5 text-ink-3 hover:bg-warn-soft hover:text-warn"
                  >
                    <Icon name="trash" size={12} />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </Card>

      <Card className="flex min-h-[420px] flex-col p-4">
        {active === null ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
            <Icon name="sparkle" size={20} className="text-brand-green" />
            <p className="text-[13px] font-medium text-ink">No session selected.</p>
            <p className="max-w-sm text-[12px] text-ink-3">
              Open a past session on the left or start a new one. The coach asks one question at a
              time and critiques each answer before the next.
            </p>
            <Button size="sm" onClick={() => void startSession()}>
              <Icon name="plus" size={12} /> Start a session
            </Button>
          </div>
        ) : (
          <>
            <div ref={scrollRef} className="flex flex-1 flex-col gap-3 overflow-y-auto pb-3">
              {active.messages.length === 0 ? (
                <p className="text-[12px] text-ink-3">
                  Type your first message — for example, “Ask me a behavioural question about
                  conflict.”
                </p>
              ) : (
                active.messages.map((m, i) => <ChatBubble key={i} turn={m} />)
              )}
            </div>

            <div className="mt-2 border-t border-line pt-3">
              <div className="mb-3 flex items-center gap-3">
                <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-3">
                  Confidence
                </span>
                <div
                  className="flex gap-1"
                  role="radiogroup"
                  aria-label="Self-rated confidence for this session"
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      role="radio"
                      aria-checked={confidence === n}
                      aria-label={`Confidence ${n}`}
                      onClick={() => setConfidence(n)}
                      className={`h-3 w-8 rounded-sm transition-colors ${
                        n <= confidence ? 'bg-brand-green' : 'bg-line'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-[11px] text-ink-3">{CONFIDENCE_LABELS[confidence - 1]}</span>
              </div>

              <div className="flex items-end gap-2 rounded-md border border-line bg-surface-2 p-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your answer… (Enter to send, Shift+Enter for newline)"
                  rows={2}
                  aria-label="Chat message"
                  disabled={streaming}
                  className="flex-1 resize-none bg-transparent text-[13px] leading-relaxed text-ink outline-none placeholder:text-ink-3 disabled:opacity-60"
                />
                <Button
                  size="sm"
                  onClick={() => void send()}
                  disabled={streaming || input.trim() === ''}
                  data-testid="send-message"
                >
                  <Icon name="send" size={12} /> {streaming ? 'Streaming…' : 'Send'}
                </Button>
              </div>
            </div>
          </>
        )}

        {error !== null ? (
          <p role="alert" className="mt-3 text-[12px] text-warn">
            {error}
          </p>
        ) : null}
      </Card>
    </div>
  )
}

function ChatBubble({ turn }: { turn: ChatTurn }) {
  if (turn.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-[14px] rounded-br-[4px] bg-ink px-3.5 py-2.5 text-[13px] leading-relaxed text-bg">
          {turn.content}
        </div>
      </div>
    )
  }
  return (
    <div className="flex items-start gap-2.5" data-testid="coach-bubble">
      <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-brand-green-tint text-brand-green">
        <Icon name="sparkle" size={13} />
      </span>
      <div className="max-w-[80%] whitespace-pre-wrap rounded-[14px] rounded-bl-[4px] border border-line bg-surface px-3.5 py-2.5 text-[13px] leading-relaxed text-ink-2">
        {turn.content || (
          <span className="inline-flex gap-1" aria-label="Coach is thinking">
            <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-3" />
            <span
              className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-3"
              style={{ animationDelay: '0.15s' }}
            />
            <span
              className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-ink-3"
              style={{ animationDelay: '0.3s' }}
            />
          </span>
        )}
      </div>
    </div>
  )
}
