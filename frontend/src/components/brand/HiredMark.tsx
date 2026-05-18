export interface HiredMarkProps {
  /** Diameter in px. The serif h + accent dot scale proportionally. */
  size?: number
  className?: string
}

/**
 * Hired. brand mark — deep-ink circle with a serif "h" and an orange
 * accent dot. In dark mode the circle/glyph invert via the --mark-h and
 * --brand-ink tokens (see src/index.css). Proportions track the 110px
 * reference from the design package.
 */
export function HiredMark({ size = 32, className }: HiredMarkProps) {
  const fontSize = size * (58 / 110)
  const dotSize = size * (14 / 110)
  const dotOffset = size * (18 / 110)

  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'var(--brand-ink)',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontFamily: "'Fraunces', Georgia, serif",
          fontWeight: 900,
          fontSize,
          color: 'var(--mark-h)',
          letterSpacing: '-0.05em',
          lineHeight: 1,
          // The serif h sits a touch low without an optical nudge.
          marginTop: -size * 0.02,
        }}
      >
        h
      </span>
      <span
        style={{
          position: 'absolute',
          bottom: dotOffset,
          right: dotOffset,
          width: dotSize,
          height: dotSize,
          borderRadius: '50%',
          background: 'var(--brand-orange)',
        }}
      />
    </div>
  )
}
