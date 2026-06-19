/* eslint-disable react-refresh/only-export-components */
import { useCallback, useEffect, useRef, useState } from 'react'

/** How long a toast stays visible before it auto-clears (ms). */
const TOAST_DURATION_MS = 2200

export interface UseToastResult {
  /** Current toast message, or null when nothing is showing. */
  message: string | null
  /** Show a toast; auto-clears after ~2.2s. Re-showing resets the timer. */
  show: (msg: string) => void
}

/**
 * Transient toast state. A single message at a time: calling `show` again
 * replaces the message and restarts the auto-clear timer. The timer is
 * cleaned up on unmount so we never set state on an unmounted component.
 */
export function useToast(): UseToastResult {
  const [message, setMessage] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimer = useCallback(() => {
    if (timer.current !== null) {
      clearTimeout(timer.current)
      timer.current = null
    }
  }, [])

  const show = useCallback(
    (msg: string) => {
      clearTimer()
      setMessage(msg)
      timer.current = setTimeout(() => {
        setMessage(null)
        timer.current = null
      }, TOAST_DURATION_MS)
    },
    [clearTimer],
  )

  useEffect(() => clearTimer, [clearTimer])

  return { message, show }
}

export interface ToastProps {
  /** Message to display; renders nothing when null. */
  message: string | null
}

/**
 * Fixed bottom-right toast. Polite live region so screen readers announce
 * it without interrupting. Pops in with the shared `subtle-bounce` motion.
 */
export function Toast({ message }: ToastProps) {
  if (message === null) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="animate-subtle-bounce fixed bottom-5 right-5 z-50 rounded-[10px] bg-brand-green px-3.5 py-2.5 text-[13px] font-medium text-white shadow-lg"
    >
      {message}
    </div>
  )
}
