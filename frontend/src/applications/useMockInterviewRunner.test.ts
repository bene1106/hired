import { describe, expect, it } from 'vitest'

import type { MockQuestion } from '@/lib/types'

import { initRunnerState, mockRunReducer, type RunnerState } from './useMockInterviewRunner'

function intro(): MockQuestion {
  return {
    category: 'behavioral',
    question: 'Tell me about yourself.',
    rephrasing: 'Walk me through your background.',
    time_limit_seconds: 300,
    is_intro: true,
  }
}

function normal(): MockQuestion {
  return {
    category: 'technical',
    question: 'Design an idempotent endpoint.',
    rephrasing: 'How would you make a POST safe to retry?',
    time_limit_seconds: 180,
    is_intro: false,
  }
}

function tick(state: RunnerState, nowMs: number): RunnerState {
  return mockRunReducer(state, { type: 'tick', nowMs })
}

describe('mockRunReducer', () => {
  it('escalates repeat → rephrase → skip when the candidate never starts', () => {
    let s = initRunnerState([intro(), normal()], 0)

    s = tick(s, 5_000) // GRACE
    expect(s.escalationStage).toBe(1)

    s = tick(s, 10_000) // 2×GRACE
    expect(s.escalationStage).toBe(2)

    s = tick(s, 15_000) // 3×GRACE → skip
    expect(s.index).toBe(1)
    expect(s.transcript).toHaveLength(1)
    expect(s.transcript[0].skipped).toBe(true)
    expect(s.transcript[0].asked_rephrasing).toBe(true)
    expect(s.transcript[0].answer).toBe('')
  })

  it('auto-advances after the min window once the box goes idle', () => {
    let s = initRunnerState([normal()], 0)
    s = mockRunReducer(s, { type: 'input', text: 'my answer', nowMs: 1_000 })
    expect(s.started).toBe(true)

    // 15s answered (>= min 15) and 15s idle (>= 5) → advance; only one question → finished.
    s = tick(s, 16_000)
    expect(s.finished).toBe(true)
    expect(s.transcript[0].answer).toBe('my answer')
    expect(s.transcript[0].skipped).toBe(false)
  })

  it('does not auto-advance before the min window even when idle', () => {
    let s = initRunnerState([normal()], 0)
    s = mockRunReducer(s, { type: 'input', text: 'hi', nowMs: 1_000 })
    s = tick(s, 10_000) // answered 9s (< min 15)
    expect(s.finished).toBe(false)
    expect(s.index).toBe(0)
  })

  it('force-advances at the max window even while actively typing', () => {
    let s = initRunnerState([normal()], 0)
    s = mockRunReducer(s, { type: 'input', text: 'a', nowMs: 1_000 })
    s = mockRunReducer(s, { type: 'input', text: 'ab', nowMs: 179_000 }) // recent activity
    s = tick(s, 181_000) // answered 180s = max
    expect(s.finished).toBe(true)
    expect(s.transcript[0].answer).toBe('ab')
    expect(s.transcript[0].skipped).toBe(false)
  })

  it('ignores a manual submit before the candidate has typed anything', () => {
    let s = initRunnerState([normal()], 0)
    s = mockRunReducer(s, { type: 'submit', nowMs: 2_000 })
    expect(s.index).toBe(0)
    expect(s.finished).toBe(false)
    expect(s.transcript).toHaveLength(0)
  })

  it('captures the full transcript across multiple questions', () => {
    let s = initRunnerState([intro(), normal()], 0)
    s = mockRunReducer(s, { type: 'input', text: 'intro answer', nowMs: 1_000 })
    s = mockRunReducer(s, { type: 'submit', nowMs: 70_000 }) // past intro min (60)
    expect(s.index).toBe(1)
    s = mockRunReducer(s, { type: 'input', text: 'second answer', nowMs: 80_000 })
    s = mockRunReducer(s, { type: 'submit', nowMs: 100_000 })
    expect(s.finished).toBe(true)
    expect(s.transcript.map((t) => t.answer)).toEqual(['intro answer', 'second answer'])
  })
})
