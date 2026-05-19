import ReactMarkdown from 'react-markdown'

import { Card } from '@/components/ui/card'

interface Suggestion {
  type: string
  current: string
  suggestion: string
  rationale: string
}

interface StructuredSuggestions {
  overall_fit?: string
  suggestions: Suggestion[]
}

function isSuggestion(value: unknown): value is Suggestion {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return (
    typeof record.type === 'string' &&
    typeof record.current === 'string' &&
    typeof record.suggestion === 'string' &&
    typeof record.rationale === 'string'
  )
}

function isStructuredSuggestions(value: unknown): value is StructuredSuggestions {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  if (record.overall_fit !== undefined && typeof record.overall_fit !== 'string') return false
  if (!Array.isArray(record.suggestions)) return false
  return record.suggestions.every(isSuggestion)
}

function chipClassFor(type: string): string {
  switch (type.trim().toLowerCase()) {
    case 'emphasize':
    case 'add':
      return 'chip chip-green'
    case 'deemphasize':
    case 'remove':
    case 'cut':
      return 'chip chip-warn'
    case 'reality check':
    case 'reality_check':
    case 'reword':
      return 'chip'
    default:
      return 'chip'
  }
}

function parseStructured(content: string): StructuredSuggestions | null {
  try {
    const parsed: unknown = JSON.parse(content)
    return isStructuredSuggestions(parsed) ? parsed : null
  } catch {
    return null
  }
}

const SECTION_LABEL = 'text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-4'

export function SuggestionRenderer({ content }: { content: string }) {
  const structured = parseStructured(content)

  if (!structured) {
    return (
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {structured.overall_fit && structured.overall_fit.length > 0 ? (
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
            Overall fit
          </span>
          <p className="text-[13px] text-ink-2">{structured.overall_fit}</p>
        </div>
      ) : null}

      {structured.suggestions.map((item, index) => (
        <Card key={`suggestion-${index}`} className="flex flex-col gap-3 p-4">
          <span className={chipClassFor(item.type)}>{item.type}</span>

          <div className="flex flex-col gap-1">
            <span className={SECTION_LABEL}>Current</span>
            <p className="text-[13px] text-ink-3">{item.current}</p>
          </div>

          <div className="flex flex-col gap-1">
            <span className={SECTION_LABEL}>Suggestion</span>
            <p className="text-[13px] text-ink">{item.suggestion}</p>
          </div>

          <div className="flex flex-col gap-1">
            <span className={SECTION_LABEL}>Rationale</span>
            <p className="text-[12px] text-ink-3">{item.rationale}</p>
          </div>
        </Card>
      ))}
    </div>
  )
}
