import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '@/lib/api'
import type { MockQuestion, TranscriptItem } from '@/lib/types'

import { WARNING_S } from './mockInterviewTiming'
import { useMicRecorder } from './useMicRecorder'
import { decideVoice, type VoiceEscalation } from './voiceRunnerLogic'

export type VoicePhase = 'speaking' | 'listening' | 'transcribing' | 'finished'

export interface VoiceRunnerView {
  index: number
  total: number
  displayText: string
  isRepeat: boolean
  isRephrased: boolean
  phase: VoicePhase
  secondsLeftToMax: number | null
  showWarning: boolean
  /** End the current answer now (manual "Done answering"). */
  finishAnswer: () => void
  /** Backup: submit a typed answer for the current question (STT/mic trouble). */
  submitText: (text: string) => void
  finished: boolean
}

const TICK_MS = 250

export function useVoiceRunner({
  questions,
  gender,
  onComplete,
}: {
  questions: MockQuestion[]
  gender: string | null
  onComplete: (transcript: TranscriptItem[]) => void
}): VoiceRunnerView {
  const mic = useMicRecorder()

  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<VoicePhase>('speaking')
  const [stage, setStage] = useState<VoiceEscalation>(0)
  const [secondsLeftToMax, setSecondsLeftToMax] = useState<number | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const [finished, setFinished] = useState(false)

  // Mutable timing state read by the tick without stale closures.
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
      try {
        const blob = await api.synthesizeSpeech(text, gender)
        await new Promise<void>((resolve, reject) => {
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
        return
      } catch {
        // Fall back to the browser's built-in speech synthesis.
      }
      try {
        const synth = window.speechSynthesis
        if (synth && 'SpeechSynthesisUtterance' in window) {
          await new Promise<void>((resolve) => {
            const utter = new SpeechSynthesisUtterance(text)
            utter.onend = () => resolve()
            utter.onerror = () => resolve()
            synth.speak(utter)
          })
        }
      } catch {
        // No audio available — proceed silently to listening.
      }
    },
    [gender],
  )

  const beginListening = useCallback(async () => {
    questionStartRef.current = Date.now()
    firstSpeechRef.current = null
    lastSpeechRef.current = Date.now()
    setSecondsLeftToMax(null)
    setShowWarning(false)
    setPhaseBoth('listening')
    try {
      await mic.start()
    } catch {
      // Mic denied/unavailable mid-run: stay in listening so the user can use
      // the "Type instead" backup; timers still escalate/skip.
    }
  }, [mic])

  const askCurrent = useCallback(
    async (idx: number, s: VoiceEscalation) => {
      setPhaseBoth('speaking')
      await playTts(textFor(idx, s))
      if (phaseRef.current === 'finished') return
      await beginListening()
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
        blob = await mic.stop()
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
      void mic.stop().catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    secondsLeftToMax,
    showWarning,
    finishAnswer,
    submitText,
    finished,
  }
}
