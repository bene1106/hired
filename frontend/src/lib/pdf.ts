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

  /**
   * Render text preserving its source line structure: each newline starts a
   * new line, a blank line becomes a small vertical gap. Long lines still
   * wrap to the content width. Unlike `splitParagraphs` (which collapses
   * single newlines for prose), a résumé's line breaks — section headers,
   * one-bullet-per-line entries — carry meaning, so we keep them.
   */
  lines(value: string, font: FontSpec) {
    const sourceLines = value.replace(/\r\n/g, '\n').split('\n')
    for (const raw of sourceLines) {
      const line = raw.trimEnd()
      if (line.length === 0) {
        this.gap(font.leading * 0.5)
        continue
      }
      this.text(line, font)
    }
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
  /**
   * The finished CV to export — the user's résumé text from their profile
   * (`profile.cv_text`). This is the application-ready document, NOT the
   * internal `cv_suggestions` tailoring analysis, which stays in the UI and
   * must never end up in the exported CV PDF.
   */
  content: string
  jobTitle?: string | null
  company?: string | null
}

/**
 * Build a clean CV PDF from the user's finished résumé text. The source line
 * structure is preserved (section headers, bullet lines) and laid out as
 * selectable text with no app chrome. Layout fidelity to the original upload
 * is a separate concern (see the export-layout work) — this renders the
 * stored plain-text résumé faithfully.
 */
export function buildCvPdf(input: CvPdfInput): jsPDF {
  const doc = newDoc()
  const layout = new Layout(doc)
  layout.lines(stripInlineMarkdown(input.content), BODY)
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
