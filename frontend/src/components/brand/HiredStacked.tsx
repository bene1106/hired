import { HiredMark } from './HiredMark'
import { HiredWordmark } from './HiredWordmark'

export interface HiredStackedProps {
  markSize?: number
  wordSize?: number
  gap?: number
  className?: string
}

/** Stacked mark over wordmark (onboarding hero). */
export function HiredStacked({
  markSize = 64,
  wordSize = 28,
  gap = 14,
  className,
}: HiredStackedProps) {
  return (
    <div
      className={className}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap }}
    >
      <HiredMark size={markSize} />
      <HiredWordmark size={wordSize} />
    </div>
  )
}
