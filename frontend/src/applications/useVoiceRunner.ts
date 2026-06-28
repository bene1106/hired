import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '@/lib/api'
import type { MockQuestion, TranscriptItem } from '@/lib/types'

import { minWindow, WARNING_S } from './mockInterviewTiming'
import type { MicRecorder } from './useMicRecorder'
import { decideVoice, type VoiceEscalation } from './voiceRunnerLogic'

export type VoicePhase = 'speaking' | 'listening' | 'transcribing' | 'finished'

export interface VoiceRunnerView {
  index: number
  total: number
  displayText: string
  isRepeat: boolean
  isRephrased: boolean
  phase: VoicePhase
  /** Seconds the candidate has been answering (null until they start speaking). */
  secondsAnswered: number | null
  /** Whole seconds left before the max window. */
  secondsLeftToMax: number | null
  /** Minimum answer length before they may finish. */
  minSeconds: number
  /** Max answer window for the current question. */
  maxSeconds: number
  /** True once past the min window — gates the "Done answering" button. */
  canFinish: boolean
  showWarning: boolean
  /** End the current answer now (only once `canFinish`). */
  finishAnswer: () => void
  /** Backup: submit a typed answer for the current question. */
  submitText: (text: string) => void
  finished: boolean
}

const TICK_MS = 250

export function useVoiceRunner({
  mic,
  questions,
  gender,
  onComplete,
}: {
  mic: MicRecorder
  questions: MockQuestion[]
  gender: string | null
  onComplete: (transcript: TranscriptItem[]) => void
}): VoiceRunnerView {
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<VoicePhase>('speaking')
  const [stage, setStage] = useState<VoiceEscalation>(0)
  const [secondsAnswered, setSecondsAnswered] = useState<number | null>(null)
  const [secondsLeftToMax, setSecondsLeftToMax] = useState<number | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const [finished, setFinished] = useState(false)

  const indexRef = useRef(0)
  const stageRef = useRef<VoiceEscalation>(0)
  const phaseRef = useRef<VoicePhase>('speaking')
  const questionStartRef = useRef(0)
  const firstSpeechRef = useRef<number | null>(null)
  const lastSpeechRef = useRef(0)
  const busyRef = useRef(false)
  const transcriptRef = useRef<TranscriptItem[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  const setPhaseBoth = (p: VoicePhase) => {
    phaseRef.current = p
    setPhase(p)
  }
  const setStageBoth = (s: VoiceEscalation) => {
    stageRef.current = s
    setStage(s)
  }

  const textFor = useCallback(
    (idx: number, s: VoiceEscalation) =>
      s >= 2 ? questions[idx].rephrasing : questions[idx].question,
    [questions],
  )

  const playTts = useCallback(
    async (text: string) => {
      // Never let speech block the interview: cap every path so we always
      // fall through to listening even if TTS/audio stalls.
      const cap = (p: Promise<void>, ms: number) =>
        Promise.race([p, new Promise<void>((r) => window.setTimeout(r, ms))])

      const server = new Promise<void>((resolve, reject) => {
        api
          .synthesizeSpeech(text, gender)
          .then((blob) => {
            const audio = audioRef.current ?? new Audio()
            audioRef.current = audio
            const url = URL.createObjectURL(blob)
            audio.src = url
            audio.onended = () => {
              URL.revokeObjectURL(url)
              resolve()
            }
            audio.onerror = () => reject(new Error('audio error'))
            void audio.play().catch(reject)
          })
          .catch(reject)
      })

      try {
        await cap(server, 20_000)
        return
      } catch {
        // Server TTS failed — fall back to the browser's speech synthesis.
      }

      const browser = new Promise<void>((resolve) => {
        try {
          const synth = window.speechSynthesis
          if (!synth || !('SpeechSynthesisUtterance' in window)) {
            resolve()
            return
          }
          const utter = new SpeechSynthesisUtterance(text)
          utter.onend = () => resolve()
          utter.onerror = () => resolve()
          synth.speak(utter)
        } catch {
          resolve()
        }
      })
      await cap(browser, 15_000)
    },
    [gender],
  )

  const beginListening = useCallback(() => {
    questionStartRef.current = Date.now()
    firstSpeechRef.current = null
    lastSpeechRef.current = Date.now()
    setSecondsAnswered(null)
    setSecondsLeftToMax(null)
    setShowWarning(false)
    setPhaseBoth('listening')
    mic.startRecording()
  }, [mic])

  const askCurrent = useCallback(
    async (idx: number, s: VoiceEscalation) => {
      setPhaseBoth('speaking')
      await playTts(textFor(idx, s))
      if (phaseRef.current === 'finished') return
      beginListening()
    },
    [beginListening, playTts, textFor],
  )

  const advance = useCallback(() => {
    const next = indexRef.current + 1
    if (next >= questions.length) {
      setPhaseBoth('finished')
      setFinished(true)
      onCompleteRef.current(transcriptRef.current)
      return
    }
    indexRef.current = next
    setIndex(next)
    setStageBoth(0)
    void askCurrent(next, 0)
  }, [askCurrent, questions.length])

  const commit = useCallback(
    async (opts: { skipped: boolean; text?: string }) => {
      if (busyRef.current) return
      busyRef.current = true
      setPhaseBoth('transcribing')
      let answer = opts.text ?? ''
      let blob: Blob | null = null
      try {
        blob = await mic.stopRecording()
      } catch {
        blob = null
      }
      if (!opts.skipped && opts.text === undefined && blob && blob.size > 0) {
        try {
          answer = (await api.transcribeSpeech(blob)).text
        } catch {
          answer = ''
        }
      }
      transcriptRef.current = [
        ...transcriptRef.current,
        {
          question: questions[indexRef.current].question,
          answer: opts.skipped ? '' : answer,
          skipped: opts.skipped,
          asked_rephrasing: stageRef.current >= 2,
        },
      ]
      busyRef.current = false
      advance()
    },
    [advance, mic, questions],
  )

  // Drive the machine while listening.
  useEffect(() => {
    const id = window.setInterval(() => {
      if (phaseRef.current !== 'listening' || busyRef.current) return
      const now = Date.now()
      if (mic.isSpeaking()) {
        if (firstSpeechRef.current === null) firstSpeechRef.current = now
        lastSpeechRef.current = now
      }
      const q = questions[indexRef.current]
      if (firstSpeechRef.current !== null) {
        const answeredFor = (now - firstSpeechRef.current) / 1000
        setSecondsAnswered(Math.floor(answeredFor))
        const remaining = q.time_limit_seconds - answeredFor
        setSecondsLeftToMax(Math.max(0, Math.ceil(remaining)))
        setShowWarning(remaining <= WARNING_S)
      }
      const decision = decideVoice(
        {
          isIntro: q.is_intro,
          maxS: q.time_limit_seconds,
          questionStartMs: questionStartRef.current,
          firstSpeechMs: firstSpeechRef.current,
          lastSpeechMs: lastSpeechRef.current,
          escalationStage: stageRef.current,
        },
        now,
      )
      if (decision.type === 'escalate') {
        setStageBoth(decision.stage)
        void playTts(textFor(indexRef.current, decision.stage)) // re-ask, keep listening
      } else if (decision.type === 'skip') {
        void commit({ skipped: true })
      } else if (decision.type === 'end') {
        void commit({ skipped: false })
      }
    }, TICK_MS)
    return () => window.clearInterval(id)
  }, [commit, mic, playTts, questions, textFor])

  // Kick off the first question once.
  const startedRef = useRef(false)
  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    void askCurrent(0, 0)
    return () => {
      phaseRef.current = 'finished'
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const q = questions[Math.min(index, questions.length - 1)]
  const minSeconds = minWindow(q.is_intro)
  const canFinish =
    phase === 'listening' && secondsAnswered !== null && secondsAnswered >= minSeconds

  const finishAnswer = useCallback(() => {
    if (phaseRef.current === 'listening') void commit({ skipped: false })
  }, [commit])

  const submitText = useCallback(
    (text: string) => {
      if (phaseRef.current === 'listening') void commit({ skipped: false, text })
    },
    [commit],
  )

  return {
    index,
    total: questions.length,
    displayText: textFor(index, stage),
    isRepeat: phase === 'listening' && firstSpeechRef.current === null && stage === 1,
    isRephrased: stage >= 2,
    phase,
    secondsAnswered,
    secondsLeftToMax,
    minSeconds,
    maxSeconds: q.time_limit_seconds,
    canFinish,
    showWarning,
    finishAnswer,
    submitText,
    finished,
  }
}
