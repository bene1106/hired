import { useCallback, useRef, useState } from 'react'

// RMS amplitude above which we treat the mic as "speaking". Tuned for typical
// laptop mics in a quiet room; the runner uses this for silence timing.
const SPEAKING_RMS = 0.02

export type MicPermission = 'idle' | 'granted' | 'denied'

export interface MicRecorder {
  supported: boolean
  permission: MicPermission
  /** Ask for mic access and start the level analyser (call once, up front). */
  requestPermission: () => Promise<boolean>
  /** Begin capturing the current answer. */
  startRecording: () => void
  /** Stop capturing; resolves with the recorded audio blob. */
  stopRecording: () => Promise<Blob>
  /** Current speech state, sampled from the analyser. */
  isSpeaking: () => boolean
  /** Current input level 0..1 (RMS), for the live meter. */
  getLevel: () => number
  /** Tear down the stream + analyser. */
  release: () => void
}

/**
 * Mic capture for the voice runner. Permission + the level analyser are set up
 * once via `requestPermission` (so the UI can show a pre-interview mic check
 * with a live meter); recording is then toggled per question. Level/speech are
 * exposed as getters (read off refs) so the meter can poll without forcing a
 * re-render every frame.
 */
export function useMicRecorder(): MicRecorder {
  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'

  const [permission, setPermission] = useState<MicPermission>('idle')

  const streamRef = useRef<MediaStream | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const rafRef = useRef<number | null>(null)
  const levelRef = useRef(0)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const requestPermission = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const Ctx =
        (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (Ctx) {
        const ctx = new Ctx()
        const source = ctx.createMediaStreamSource(stream)
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 2048
        source.connect(analyser)
        ctxRef.current = ctx
        // Created after the async getUserMedia, the context can start
        // suspended — resume it so the analyser actually sees audio.
        void ctx.resume?.()
        const buf = new Uint8Array(analyser.fftSize)
        const loop = () => {
          analyser.getByteTimeDomainData(buf)
          let sum = 0
          for (const v of buf) {
            const x = (v - 128) / 128
            sum += x * x
          }
          levelRef.current = Math.sqrt(sum / buf.length)
          rafRef.current = requestAnimationFrame(loop)
        }
        rafRef.current = requestAnimationFrame(loop)
      }
      setPermission('granted')
      return true
    } catch {
      setPermission('denied')
      return false
    }
  }, [])

  const startRecording = useCallback(() => {
    const stream = streamRef.current
    if (!stream) return
    chunksRef.current = []
    const recorder = new MediaRecorder(stream)
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.start()
    recorderRef.current = recorder
  }, [])

  const stopRecording = useCallback(async () => {
    const recorder = recorderRef.current
    recorderRef.current = null
    return new Promise<Blob>((resolve) => {
      if (!recorder || recorder.state === 'inactive') {
        resolve(new Blob(chunksRef.current, { type: 'audio/webm' }))
        return
      }
      recorder.onstop = () =>
        resolve(new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' }))
      recorder.stop()
    })
  }, [])

  const release = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    levelRef.current = 0
    if (ctxRef.current) {
      void ctxRef.current.close()
      ctxRef.current = null
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const isSpeaking = useCallback(() => levelRef.current > SPEAKING_RMS, [])
  const getLevel = useCallback(() => levelRef.current, [])

  return {
    supported,
    permission,
    requestPermission,
    startRecording,
    stopRecording,
    isSpeaking,
    getLevel,
    release,
  }
}
