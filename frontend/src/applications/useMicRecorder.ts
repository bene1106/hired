import { useCallback, useRef, useState } from 'react'

// RMS amplitude above which we treat the mic as "speaking". Tuned for typical
// laptop mics in a quiet room; the runner only uses this for silence timing.
const SPEAKING_RMS = 0.02

export interface MicRecorder {
  supported: boolean
  /** Begin capturing + level monitoring. Resolves once the mic is live. */
  start: () => Promise<void>
  /** Stop capturing; resolves with the recorded audio blob. */
  stop: () => Promise<Blob>
  /** Current speech state, sampled from the analyser (read on each tick). */
  isSpeaking: () => boolean
}

/**
 * Thin wrapper over getUserMedia + MediaRecorder, plus an AnalyserNode RMS
 * meter used for silence detection. Speech state is exposed via a getter
 * (`isSpeaking`) rather than React state so the runner can poll it on a timer
 * without re-rendering every frame.
 */
export function useMicRecorder(): MicRecorder {
  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'

  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const rafRef = useRef<number | null>(null)
  const speakingRef = useRef(false)

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.current = stream
    chunksRef.current = []

    const recorder = new MediaRecorder(stream)
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.start()
    recorderRef.current = recorder

    // Best-effort level monitoring; absence (e.g. no AudioContext in a test
    // env) just means silence detection is skipped, not a crash.
    const Ctx =
      (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (Ctx) {
      const ctx = new Ctx()
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 2048
      source.connect(analyser)
      audioCtxRef.current = ctx
      const buf = new Uint8Array(analyser.fftSize)
      const loop = () => {
        analyser.getByteTimeDomainData(buf)
        let sum = 0
        for (const v of buf) {
          const x = (v - 128) / 128
          sum += x * x
        }
        speakingRef.current = Math.sqrt(sum / buf.length) > SPEAKING_RMS
        rafRef.current = requestAnimationFrame(loop)
      }
      rafRef.current = requestAnimationFrame(loop)
    }
  }, [])

  const stop = useCallback(async () => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    speakingRef.current = false
    if (audioCtxRef.current) {
      void audioCtxRef.current.close()
      audioCtxRef.current = null
    }
    const recorder = recorderRef.current
    const stream = streamRef.current
    recorderRef.current = null
    streamRef.current = null

    const blob = await new Promise<Blob>((resolve) => {
      if (!recorder || recorder.state === 'inactive') {
        resolve(new Blob(chunksRef.current, { type: 'audio/webm' }))
        return
      }
      recorder.onstop = () => {
        resolve(new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' }))
      }
      recorder.stop()
    })
    stream?.getTracks().forEach((t) => t.stop())
    return blob
  }, [])

  const isSpeaking = useCallback(() => speakingRef.current, [])

  const [recorder] = useState<MicRecorder>(() => ({
    supported,
    start,
    stop,
    isSpeaking,
  }))
  return recorder
}
