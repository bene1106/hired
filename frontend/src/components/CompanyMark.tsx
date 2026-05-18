export interface CompanyMarkProps {
  /** Company name; the first letter becomes the mark. */
  company?: string | null
  size?: number
  className?: string
}

// Muted, warm palette — deterministic per initial so a company keeps the
// same colour across screens. Initials only (custom avatars are §18 /
// Phase 10+, deliberately not fetched here).
const COLORS = ['#C9CFC2', '#D6CEC3', '#C8CDD3', '#D4C9CB', '#CDD4C7', '#D1CAC2', '#C3CBD0']

export function CompanyMark({ company, size = 40, className }: CompanyMarkProps) {
  const trimmed = company?.trim() ?? ''
  const initial = trimmed.length > 0 ? trimmed[0].toUpperCase() : '?'
  const bg = COLORS[initial.charCodeAt(0) % COLORS.length]

  return (
    <div
      className={className}
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.22,
        background: bg,
        color: '#1A1A17',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: size * 0.42,
        fontWeight: 600,
        letterSpacing: '-0.02em',
        border: '1px solid rgba(0,0,0,0.06)',
        flexShrink: 0,
      }}
    >
      {initial}
    </div>
  )
}
