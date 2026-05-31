import { describe, expect, it } from 'vitest'

import {
  buildCoverLetterPdf,
  buildCvPdf,
  fileSlug,
  parseCvContent,
  splitParagraphs,
  stripInlineMarkdown,
} from './pdf'

describe('splitParagraphs', () => {
  it('splits on blank lines and collapses single newlines', () => {
    const text = 'Dear team,\n\nI am excited\nto apply.\n\nKind regards,\nJane'
    expect(splitParagraphs(text)).toEqual([
      'Dear team,',
      'I am excited to apply.',
      'Kind regards, Jane',
    ])
  })

  it('handles CRLF and trailing whitespace', () => {
    expect(splitParagraphs('A\r\n\r\nB  \r\n')).toEqual(['A', 'B'])
  })

  it('drops empty input', () => {
    expect(splitParagraphs('\n\n   \n')).toEqual([])
  })
})

describe('stripInlineMarkdown', () => {
  it('removes bold, italic, code and heading markers', () => {
    expect(stripInlineMarkdown('**bold** and *em* and `code`')).toBe('bold and em and code')
    expect(stripInlineMarkdown('# Heading')).toBe('Heading')
  })

  it('turns list bullets into a bullet glyph', () => {
    expect(stripInlineMarkdown('- one\n- two')).toBe('• one\n• two')
  })
})

describe('parseCvContent', () => {
  it('parses structured suggestions', () => {
    const json = JSON.stringify({
      overall_fit: 'Good fit.',
      suggestions: [{ type: 'emphasize', current: 'a', suggestion: 'b', rationale: 'c' }],
    })
    const doc = parseCvContent(json)
    expect(doc.raw).toBeNull()
    expect(doc.overallFit).toBe('Good fit.')
    expect(doc.suggestions).toHaveLength(1)
  })

  it('falls back to raw for plain markdown', () => {
    const doc = parseCvContent('## CV tailoring\n\n- Emphasise FastAPI.')
    expect(doc.suggestions).toEqual([])
    expect(doc.raw).toContain('Emphasise FastAPI')
  })
})

describe('fileSlug', () => {
  it('slugifies and falls back', () => {
    expect(fileSlug('Acme Co!', 'x')).toBe('acme-co')
    expect(fileSlug('', 'fallback')).toBe('fallback')
    expect(fileSlug(null, 'fallback')).toBe('fallback')
  })
})

describe('buildCoverLetterPdf', () => {
  it('produces a multi-page-capable document without throwing', () => {
    const doc = buildCoverLetterPdf({
      content: 'Dear team,\n\nBody paragraph.\n\nRegards,\nJane',
      jobTitle: 'Backend Engineer',
      company: 'AcmeCo',
    })
    expect(doc.getNumberOfPages()).toBeGreaterThanOrEqual(1)
  })

  it('handles very long content (pagination) without throwing', () => {
    const long = Array.from({ length: 200 }, (_, i) => `Paragraph ${i} with some text.`).join(
      '\n\n',
    )
    const doc = buildCoverLetterPdf({ content: long })
    expect(doc.getNumberOfPages()).toBeGreaterThan(1)
  })
})

describe('buildCvPdf', () => {
  it('renders structured suggestions without throwing', () => {
    const json = JSON.stringify({
      overall_fit: 'Strong on Python.',
      suggestions: [
        { type: 'emphasize', current: 'old', suggestion: 'new', rationale: 'why' },
        { type: 'reword', current: 'old2', suggestion: 'new2', rationale: 'why2' },
      ],
    })
    const doc = buildCvPdf({ content: json, jobTitle: 'Backend Engineer' })
    expect(doc.getNumberOfPages()).toBeGreaterThanOrEqual(1)
  })

  it('renders unstructured markdown content without throwing', () => {
    const doc = buildCvPdf({ content: '## CV tailoring\n\n- Emphasise FastAPI experience.' })
    expect(doc.getNumberOfPages()).toBeGreaterThanOrEqual(1)
  })
})
