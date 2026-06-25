import { describe, expect, it } from 'vitest'

import { decideVoice, type VoiceTimingState } from './voiceRunnerLogic'

function base(overrides: Partial<VoiceTimingState> = {}): VoiceTimingState {
  return {
    isIntro: false,
    maxS: 180,
    questionStartMs: 0,
    firstSpeechMs: null,
    lastSpeechMs: 0,
    escalationStage: 0,
    ...overrides,
  }
}

describe('decideVoice', () => {
  it('does nothing in the first grace window', () => {
    expect(decideVoice(base(), 4_000)).toEqual({ type: 'none' })
  })

  it('escalates to repeat at 5s, then rephrase at 10s', () => {
    expect(decideVoice(base({ escalationStage: 0 }), 5_000)).toEqual({ type: 'escalate', stage: 1 })
    expect(decideVoice(base({ escalationStage: 1 }), 10_000)).toEqual({
      type: 'escalate',
      stage: 2,
    })
  })

  it('skips when no speech by 15s', () => {
    expect(decideVoice(base({ escalationStage: 2 }), 15_000)).toEqual({ type: 'skip' })
  })

  it('ends once past the min window and silent for the grace period', () => {
    // started at 1s, last speech at 17s, now 22s → answered 21s (≥15 min),
    // silent 5s → end.
    const s = base({ firstSpeechMs: 1_000, lastSpeechMs: 17_000 })
    expect(decideVoice(s, 22_000)).toEqual({ type: 'end' })
  })

  it('does not end before the min window even when silent', () => {
    const s = base({ firstSpeechMs: 1_000, lastSpeechMs: 1_000 })
    // answered 10s (< 15 min) → keep waiting despite silence
    expect(decideVoice(s, 11_000)).toEqual({ type: 'none' })
  })

  it('uses the longer intro min window', () => {
    const s = base({ isIntro: true, firstSpeechMs: 1_000, lastSpeechMs: 1_000 })
    // answered 30s, silent 30s, but intro min is 60s → still waiting
    expect(decideVoice(s, 31_000)).toEqual({ type: 'none' })
  })

  it('force-ends at the max window', () => {
    const s = base({ maxS: 180, firstSpeechMs: 0, lastSpeechMs: 179_000 })
    expect(decideVoice(s, 180_000)).toEqual({ type: 'end' })
  })
})
