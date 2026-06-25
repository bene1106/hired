import { GRACE_S, INACTIVITY_ADVANCE_S, minWindow } from './mockInterviewTiming'

// Pure timing core for the voice runner. The hook feeds it timestamps + the
// current speech state each tick; this decides what should happen, so the
// faithful M2 rules (grace → repeat → rephrase → skip; min/max; idle-advance)
// are unit-testable without audio/mic/STT.

export type VoiceEscalation = 0 | 1 | 2

export interface VoiceTimingState {
  isIntro: boolean
  maxS: number
  questionStartMs: number
  firstSpeechMs: number | null
  lastSpeechMs: number
  escalationStage: VoiceEscalation
}

export type VoiceDecision =
  | { type: 'none' }
  | { type: 'escalate'; stage: 1 | 2 } // re-ask: repeat (1) or rephrase (2)
  | { type: 'skip' } // never started speaking → skip the question
  | { type: 'end' } // answer complete → stop, transcribe, advance

export function decideVoice(state: VoiceTimingState, nowMs: number): VoiceDecision {
  if (state.firstSpeechMs === null) {
    // Not started: escalate at 5s, 10s; skip at 15s.
    const elapsed = (nowMs - state.questionStartMs) / 1000
    if (elapsed >= 3 * GRACE_S) return { type: 'skip' }
    if (elapsed >= 2 * GRACE_S && state.escalationStage < 2) return { type: 'escalate', stage: 2 }
    if (elapsed >= GRACE_S && state.escalationStage < 1) return { type: 'escalate', stage: 1 }
    return { type: 'none' }
  }

  // Answering: enforce max, and end once past min and gone quiet.
  const answeredFor = (nowMs - state.firstSpeechMs) / 1000
  const silenceFor = (nowMs - state.lastSpeechMs) / 1000
  if (answeredFor >= state.maxS) return { type: 'end' }
  if (answeredFor >= minWindow(state.isIntro) && silenceFor >= INACTIVITY_ADVANCE_S) {
    return { type: 'end' }
  }
  return { type: 'none' }
}
