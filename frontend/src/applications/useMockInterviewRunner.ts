import { useEffect, useReducer, useRef } from 'react'

import type { MockQuestion, TranscriptItem } from '@/lib/types'

import { GRACE_S, INACTIVITY_ADVANCE_S, WARNING_S, minWindow } from './mockInterviewTiming'

// Escalation while the candidate hasn't begun: 0 none → 1 repeated → 2 rephrased.
export type EscalationStage = 0 | 1 | 2

export interface RunnerState {
  questions: MockQuestion[]
  index: number
  answer: string
  escalationStage: EscalationStage
  started: boolean
  questionStartMs: number
  firstInputMs: number | null
  lastActivityMs: number
  nowMs: number
  transcript: TranscriptItem[]
  finished: boolean
}

export type RunnerAction =
  | { type: 'tick'; nowMs: number }
  | { type: 'input'; text: string; nowMs: number }
  | { type: 'submit'; nowMs: number }

export function initRunnerState(questions: MockQuestion[], nowMs: number): RunnerState {
  return {
    questions,
    index: 0,
    answer: '',
    escalationStage: 0,
    started: false,
    questionStartMs: nowMs,
    firstInputMs: null,
    lastActivityMs: nowMs,
    nowMs,
    transcript: [],
    finished: false,
  }
}

function currentQuestion(state: RunnerState): MockQuestion {
  return state.questions[state.index]
}

function advance(state: RunnerState, opts: { skipped: boolean; nowMs: number }): RunnerState {
  const q = currentQuestion(state)
  const item: TranscriptItem = {
    question: q.question,
    answer: opts.skipped ? '' : state.answer,
    skipped: opts.skipped,
    asked_rephrasing: state.escalationStage >= 2,
  }
  const transcript = [...state.transcript, item]
  const nextIndex = state.index + 1
  if (nextIndex >= state.questions.length) {
    return { ...state, transcript, finished: true, nowMs: opts.nowMs }
  }
  return {
    ...state,
    transcript,
    index: nextIndex,
    answer: '',
    escalationStage: 0,
    started: false,
    questionStartMs: opts.nowMs,
    firstInputMs: null,
    lastActivityMs: opts.nowMs,
    nowMs: opts.nowMs,
  }
}

/**
 * Pure state machine for the timed runner. Exported so the timing rules can be
 * unit-tested deterministically without wall-clock flakiness.
 */
export function mockRunReducer(state: RunnerState, action: RunnerAction): RunnerState {
  if (state.finished) return state

  switch (action.type) {
    case 'input': {
      const hasText = action.text.length > 0
      return {
        ...state,
        answer: action.text,
        started: state.started || hasText,
        firstInputMs: state.firstInputMs ?? (hasText ? action.nowMs : null),
        lastActivityMs: action.nowMs,
        nowMs: action.nowMs,
      }
    }

    case 'submit': {
      // Manual "Submit answer" only works once the candidate has begun.
      if (!state.started) return { ...state, nowMs: action.nowMs }
      return advance(state, { skipped: false, nowMs: action.nowMs })
    }

    case 'tick': {
      const s = { ...state, nowMs: action.nowMs }
      const q = currentQuestion(s)

      if (!s.started) {
        // Not-started escalation: repeat (5s) → rephrase (10s) → skip (15s).
        const elapsed = (action.nowMs - s.questionStartMs) / 1000
        if (elapsed >= 3 * GRACE_S) {
          return advance({ ...s, escalationStage: 2 }, { skipped: true, nowMs: action.nowMs })
        }
        if (elapsed >= 2 * GRACE_S) return { ...s, escalationStage: 2 }
        if (elapsed >= GRACE_S) return { ...s, escalationStage: 1 }
        return s
      }

      // Answering: enforce max, and auto-advance once past min and idle.
      const answeredFor = (action.nowMs - (s.firstInputMs ?? action.nowMs)) / 1000
      const inactiveFor = (action.nowMs - s.lastActivityMs) / 1000
      if (answeredFor >= q.time_limit_seconds) {
        return advance(s, { skipped: false, nowMs: action.nowMs })
      }
      if (answeredFor >= minWindow(q.is_intro) && inactiveFor >= INACTIVITY_ADVANCE_S) {
        return advance(s, { skipped: false, nowMs: action.nowMs })
      }
      return s
    }

    default:
      return state
  }
}

export interface RunnerView {
  index: number
  total: number
  /** The text to show: question, or its rephrasing once escalated. */
  displayText: string
  /** True between 5–10s of no input (shows a "let me repeat that" hint). */
  isRepeat: boolean
  /** True once the question has been rephrased (≥10s of no input). */
  isRephrased: boolean
  phase: 'waiting' | 'answering'
  answer: string
  onAnswerChange: (text: string) => void
  submitNow: () => void
  /** Whole seconds left before the max window (only while answering). */
  secondsLeftToMax: number | null
  /** True during the final WARNING_S seconds before max. */
  showWarning: boolean
  /** Manual submit is allowed once the min window has passed. */
  canSubmit: boolean
  finished: boolean
}

export function useMockInterviewRunner({
  questions,
  onComplete,
}: {
  questions: MockQuestion[]
  onComplete: (transcript: TranscriptItem[]) => void
}): RunnerView {
  const [state, dispatch] = useReducer(mockRunReducer, questions, (q) =>
    initRunnerState(q, Date.now()),
  )

  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete
  const firedRef = useRef(false)

  useEffect(() => {
    const id = window.setInterval(() => dispatch({ type: 'tick', nowMs: Date.now() }), 250)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    if (state.finished && !firedRef.current) {
      firedRef.current = true
      onCompleteRef.current(state.transcript)
    }
  }, [state.finished, state.transcript])

  const safeIndex = Math.min(state.index, state.questions.length - 1)
  const q = state.questions[safeIndex]
  const isRephrased = state.escalationStage >= 2
  const isRepeat = !state.started && state.escalationStage === 1

  let secondsLeftToMax: number | null = null
  let showWarning = false
  let canSubmit = false
  if (state.started && state.firstInputMs !== null) {
    const answeredFor = (state.nowMs - state.firstInputMs) / 1000
    const remaining = q.time_limit_seconds - answeredFor
    secondsLeftToMax = Math.max(0, Math.ceil(remaining))
    showWarning = remaining <= WARNING_S
    canSubmit = answeredFor >= minWindow(q.is_intro)
  }

  return {
    index: safeIndex,
    total: state.questions.length,
    displayText: isRephrased ? q.rephrasing : q.question,
    isRepeat,
    isRephrased,
    phase: state.started ? 'answering' : 'waiting',
    answer: state.answer,
    onAnswerChange: (text) => dispatch({ type: 'input', text, nowMs: Date.now() }),
    submitNow: () => dispatch({ type: 'submit', nowMs: Date.now() }),
    secondsLeftToMax,
    showWarning,
    canSubmit,
    finished: state.finished,
  }
}
