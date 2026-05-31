import { jsPDF } from 'jspdf'

/**
 * PDF export helpers for the Application-Detail view.
 *
 * These produce clean, plain documents with REAL selectable text (vector,
 * not a rasterised screenshot) using jsPDF. No app UI chrome ends up in the
 * file — just the formatted content.
 *
 * The text-layout logic is split into small pure functions so it can be unit
 * tested without a jsPDF instance.
 */

/** US Letter geometry, in points (jsPDF default unit). */
const PAGE = { width: 612, height: 792 } as const
const MARGIN = 64
const CONTENT_WIDTH = PAGE.width - MARGIN * 2

interface FontSpec {
  size: number
  /** Leading (line height) in points. */
  leading: number
  style: 'normal' | 'bold' | 'italic'
}

const BODY: FontSpec = { size: 11, leading: 16, style: 'normal' }
const HEADING: FontSpec = { size: 15, leading: 22, style: 'bold' }
const SUBHEADING: FontSpec = { size: 12, leading: 18, style: 'bold' }
const LABEL: FontSpec = { size: 8, leading: 12, style: 'bold' }

/**
 * Split plain text into paragraphs on blank lines. Single newlines inside a
 * paragraph are collapsed to spaces so wrapping is controlled by width, not by
 * the source line breaks — except we keep paragraphs that look like a
 * salutation or sign-off (short lines) intact as their own blocks.
 *
 * Cover letters are frequently plain text with blank-line-separated
 * paragraphs; this turns those blank lines into real paragraph breaks.
 */
export function splitParagraphs(text: string): string[] {
  return text
    .replace(/\r\n/g, '\n')
    .split(/\n[ \t]*\n+/)
    .map((block) =>
      block
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
        .join(' '),
    )
    .filter((p) => p.length > 0)
}

/** Strip a small set of inline markdown so the PDF reads as plain prose. */
export function stripInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`(.+?)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ')
}

interface CvSuggestion {
  type: string
  current: string
  suggestion: string
  rationale: string
}

interface CvDocument {
  overallFit: string | null
  suggestions: CvSuggestion[]
  /** Raw markdown/plain text fallback when content is not structured JSON. */
  raw: string | null
}

/**
 * Parse the cv_suggestions material content. Mirrors SuggestionRenderer:
 * structured JSON ({ overall_fit?, suggestions: [...] }) renders as cards,
 * anything else is treated as markdown/plain text.
 */
export function parseCvContent(content: string): CvDocument {
  try {
    const parsed: unknown = JSON.parse(content)
    if (typeof parsed === 'object' && parsed !== null) {
      const record = parsed as Record<string, unknown>
      const suggestions = Array.isArray(record.suggestions)
        ? record.suggestions.filter(isCvSuggestion)
        : []
      if (suggestions.length > 0 || typeof record.overall_fit === 'string') {
        return {
          overallFit: typeof record.overall_fit === 'string' ? record.overall_fit : null,
          suggestions,
          raw: null,
        }
      }
    }
  } catch {
    // fall through to raw
  }
  return { overallFit: null, suggestions: [], raw: content }
}

function isCvSuggestion(value: unknown): value is CvSuggestion {
  if (typeof value !== 'object' || value === null) return false
  const r = value as Record<string, unknown>
  return (
    typeof r.type === 'string' &&
    typeof r.current === 'string' &&
    typeof r.suggestion === 'string' &&
    typeof r.rationale === 'string'
  )
}

/** Slugify a string for use in a download filename. */
export function fileSlug(value: string | undefined | null, fallback: string): string {
  const base = (value ?? '').trim().toLowerCase()
  const slug = base
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
  return slug.length > 0 ? slug : fallback
}

/**
 * A tiny cursor over a jsPDF document that lays text out top-to-bottom,
 * wrapping to the content width and paginating when it runs off the page.
 */
class Layout {
  private doc: jsPDF
  private y: number

  constructor(doc: jsPDF) {
    this.doc = doc
    this.y = MARGIN
  }

  private ensureRoom(height: number) {
    if (this.y + height > PAGE.height - MARGIN) {
      this.doc.addPage()
      this.y = MARGIN
    }
  }

  gap(points: number) {
    this.y += points
  }

  text(value: string, font: FontSpec) {
    this.doc.setFont('helvetica', font.style)
    this.doc.setFontSize(font.size)
    const lines = this.doc.splitTextToSize(value, CONTENT_WIDTH) as string[]
    for (const line of lines) {
      this.ensureRoom(font.leading)
      this.doc.text(line, MARGIN, this.y)
      this.y += font.leading
    }
  }

  rule() {
    this.ensureRoom(8)
    this.doc.setDrawColor(210)
    this.doc.line(MARGIN, this.y, PAGE.width - MARGIN, this.y)
    this.y += 8
  }
}

function newDoc(): jsPDF {
  return new jsPDF({ unit: 'pt', format: 'letter' })
}

/** Trigger a browser download of a jsPDF document. */
function save(doc: jsPDF, filename: string) {
  doc.save(filename)
}

export interface CoverLetterPdfInput {
  /** The cover-letter body (plain text or light markdown). */
  content: string
  /** Job title, used in the filename and an optional header line. */
  jobTitle?: string | null
  /** Company name, used in the filename. */
  company?: string | null
}

/**
 * Build a clean cover-letter PDF: paragraphs (incl. salutation and sign-off)
 * with comfortable spacing and no app chrome. Returns the jsPDF instance so it
 * can be inspected in tests; pass `download` to also save it.
 */
export function buildCoverLetterPdf(input: CoverLetterPdfInput): jsPDF {
  const doc = newDoc()
  const layout = new Layout(doc)
  const paragraphs = splitParagraphs(stripInlineMarkdown(input.content))

  for (let i = 0; i < paragraphs.length; i += 1) {
    layout.text(paragraphs[i], BODY)
    if (i < paragraphs.length - 1) layout.gap(BODY.leading * 0.6)
  }

  return doc
}

export function downloadCoverLetterPdf(input: CoverLetterPdfInput): void {
  const doc = buildCoverLetterPdf(input)
  const name = `cover-letter-${fileSlug(input.company, 'application')}-${fileSlug(
    input.jobTitle,
    'role',
  )}.pdf`
  save(doc, name)
}

export interface CvPdfInput {
  /** The cv_suggestions material content (structured JSON or markdown). */
  content: string
  jobTitle?: string | null
  company?: string | null
}

/**
 * Build a clean "tailored CV" PDF from the cv_suggestions material. Structured
 * suggestions render as a titled document (Overall fit + one block per
 * suggestion with Current / Suggestion / Rationale). Unstructured content is
 * laid out as plain prose.
 */
export function buildCvPdf(input: CvPdfInput): jsPDF {
  const doc = newDoc()
  const layout = new Layout(doc)
  const parsed = parseCvContent(input.content)

  const titleParts = ['CV tailoring', input.jobTitle ?? undefined].filter(Boolean) as string[]
  layout.text(titleParts.join(' — '), HEADING)
  layout.gap(6)

  if (parsed.raw !== null) {
    for (const para of splitParagraphs(stripInlineMarkdown(parsed.raw))) {
      layout.text(para, BODY)
      layout.gap(BODY.leading * 0.6)
    }
    return doc
  }

  if (parsed.overallFit) {
    layout.text('Overall fit', LABEL)
    layout.gap(2)
    layout.text(parsed.overallFit, BODY)
    layout.gap(BODY.leading * 0.6)
  }

  for (let i = 0; i < parsed.suggestions.length; i += 1) {
    const s = parsed.suggestions[i]
    if (i > 0) {
      layout.gap(4)
      layout.rule()
    }
    layout.text(s.type.toUpperCase(), SUBHEADING)
    layout.gap(2)

    layout.text('Current', LABEL)
    layout.text(s.current, BODY)
    layout.gap(4)

    layout.text('Suggestion', LABEL)
    layout.text(s.suggestion, BODY)
    layout.gap(4)

    layout.text('Rationale', LABEL)
    layout.text(s.rationale, BODY)
  }

  return doc
}

export function downloadCvPdf(input: CvPdfInput): void {
  const doc = buildCvPdf(input)
  const name = `cv-${fileSlug(input.company, 'application')}-${fileSlug(
    input.jobTitle,
    'role',
  )}.pdf`
  save(doc, name)
}
