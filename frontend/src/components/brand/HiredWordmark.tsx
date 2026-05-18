export interface HiredWordmarkProps {
  /** Cap height in px. */
  size?: number
  /** Override the wordmark color. Defaults to the ink token. */
  color?: string
  className?: string
}

/**
 * "hired." wordmark — Archivo Black with an orange period.
 */
export function HiredWordmark({ size = 22, color, className }: HiredWordmarkProps) {
  return (
    <span
      className={className}
      style={{
        fontFamily: "'Archivo', system-ui, sans-serif",
        fontWeight: 900,
        fontSize: size,
        letterSpacing: '-0.04em',
        lineHeight: 1,
        color: color ?? 'var(--ink)',
      }}
    >
      hired<span style={{ color: 'var(--brand-orange)' }}>.</span>
    </span>
  )
}
