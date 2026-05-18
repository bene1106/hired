import { HiredMark } from './HiredMark'
import { HiredWordmark } from './HiredWordmark'

export interface HiredLockupProps {
  markSize?: number
  wordSize?: number
  gap?: number
  className?: string
}

/** Horizontal mark + wordmark lockup (sidebar default). */
export function HiredLockup({
  markSize = 30,
  wordSize = 20,
  gap = 10,
  className,
}: HiredLockupProps) {
  return (
    <div className={className} style={{ display: 'flex', alignItems: 'center', gap }}>
      <HiredMark size={markSize} />
      <HiredWordmark size={wordSize} />
    </div>
  )
}
