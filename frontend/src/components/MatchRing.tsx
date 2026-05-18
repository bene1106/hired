import { useEffect, useState } from 'react'

export interface MatchRingProps {
  /** 0–100 match score. */
  score: number
  size?: number
  stroke?: number
  /** Show the "MATCH" caption below the ring. */
  label?: boolean
}

// Semantic colour buckets (design tokens).
function ringColor(score: number): string {
  if (score >= 85) return 'var(--accent)'
  if (score >= 70) return 'var(--info)'
  return 'var(--ink-3)'
}

/**
 * Signature match indicator. The number is rendered final from the first
 * frame (correct + screen-reader-stable, and keeps `score-badge` tests
 * deterministic in jsdom). Only the ring arc animates, via a CSS
 * stroke-dashoffset transition.
 */
export function MatchRing({ score, size = 56, stroke = 4, label = true }: MatchRingProps) {
  const r = (size - stroke) / 2
  const circumference = 2 * Math.PI * r
  const target = circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference

  // Start empty, then settle to the target so the arc sweeps in (CSS only).
  const [offset, setOffset] = useState(circumference)
  useEffect(() => {
    const id = window.requestAnimationFrame(() => setOffset(target))
    return () => window.cancelAnimationFrame(id)
  }, [target])

  const color = ringColor(score)

  return (
    <div
      className="inline-flex flex-col items-center gap-0.5"
      aria-label={`Match score ${score} out of 100`}
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke="var(--line)"
            strokeWidth={stroke}
            fill="none"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke={color}
            strokeWidth={stroke}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.9s ease, stroke 0.2s ease' }}
          />
        </svg>
        <span
          data-testid="score-badge"
          className="mono absolute inset-0 flex items-center justify-center font-medium tabular-nums text-ink"
          style={{ fontSize: size * 0.34 }}
        >
          {score}
        </span>
      </div>
      {label && (
        <span className="text-[9px] font-semibold uppercase tracking-[0.1em] text-ink-4">
          Match
        </span>
      )}
    </div>
  )
}
