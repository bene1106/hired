import { describe, expect, it } from 'vitest'

import {
  buildCoverLetterPdf,
  buildCvPdf,
  fileSlug,
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
  it('renders the finished résumé text, preserving line structure', () => {
    const cv = 'JANE DOE\nSenior Engineer\n\nEXPERIENCE\n- Built FastAPI services'
    const doc = buildCvPdf({ content: cv, jobTitle: 'Backend Engineer' })
    expect(doc.getNumberOfPages()).toBeGreaterThanOrEqual(1)
  })

  it('handles a long résumé (pagination) without throwing', () => {
    const long = Array.from({ length: 200 }, (_, i) => `Line ${i} of the résumé.`).join('\n')
    const doc = buildCvPdf({ content: long })
    expect(doc.getNumberOfPages()).toBeGreaterThan(1)
  })
})
