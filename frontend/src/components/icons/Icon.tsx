import type { ReactElement } from 'react'

/**
 * Line-icon set ported from the Phase 7 design package (`primitives.jsx`).
 * Consistent 1.75 stroke, 24×24 viewBox.
 *
 * `IconName` is a strict union on purpose: adding an icon means widening
 * the union, so every new glyph is a deliberate, reviewable diff rather
 * than a magic string. Later PRs extend `PATHS` (and the union) with the
 * icons their screens need.
 */
export type IconName =
  | 'feed'
  | 'kanban'
  | 'settings'
  | 'sun'
  | 'moon'
  | 'upload'
  | 'check'
  | 'arrowRight'
  | 'arrowLeft'
  | 'sparkle'
  | 'pin'
  | 'refresh'
  | 'filter'
  | 'file'
  | 'mail'
  | 'drag'
  | 'send'
  | 'trash'
  | 'plus'
  | 'building'
  | 'globe'

const PATHS: Record<IconName, ReactElement> = {
  feed: <path d="M4 7h16M4 12h16M4 17h10" />,
  kanban: <path d="M5 4h4v16H5zM15 4h4v10h-4zM10 4h4v7h-4z" />,
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.4-2.4.9a7 7 0 0 0-2-1.2L14 3h-4l-.5 2.5a7 7 0 0 0-2 1.2l-2.4-.9-2 3.4 2 1.6A7 7 0 0 0 5 12a7 7 0 0 0 .1 1.2l-2 1.6 2 3.4 2.4-.9a7 7 0 0 0 2 1.2L10 21h4l.5-2.5a7 7 0 0 0 2-1.2l2.4.9 2-3.4-2-1.6c.07-.4.1-.8.1-1.2z" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.5 1.5M17.6 17.6l1.5 1.5M4.9 19.1l1.5-1.5M17.6 6.4l1.5-1.5" />
    </>
  ),
  moon: <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z" />,
  upload: <path d="M12 15V3M7 8l5-5 5 5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />,
  check: <path d="M4 12l5 5L20 6" />,
  arrowRight: <path d="M5 12h14M12 5l7 7-7 7" />,
  arrowLeft: <path d="M19 12H5M12 19l-7-7 7-7" />,
  sparkle: <path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" />,
  pin: (
    <>
      <path d="M12 22s7-7 7-12a7 7 0 0 0-14 0c0 5 7 12 7 12z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  refresh: (
    <>
      <path d="M4 4v6h6M20 20v-6h-6" />
      <path d="M20 10A8 8 0 0 0 6 6M4 14a8 8 0 0 0 14 4" />
    </>
  ),
  filter: <path d="M4 5h16M7 12h10M10 19h4" />,
  file: (
    <>
      <path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z" />
      <path d="M13 3v6h6" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 7 9-7" />
    </>
  ),
  drag: (
    <>
      <circle cx="9" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="9" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="9" cy="18" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="18" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  send: <path d="M3 20l18-8L3 4l4 8-4 8z" />,
  trash: (
    <>
      <path d="M4 7h16M9 7V4h6v3M10 11v6M14 11v6" />
      <path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3c-2.5 3-4 5.5-4 9s1.5 6 4 9M12 3c2.5 3 4 5.5 4 9s-1.5 6-4 9M3 12h18" />
    </>
  ),
  building: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="1" />
      <path d="M9 21V9h6v12M9 13h2M13 13h2M9 17h2M13 17h2M9 9h6" />
    </>
  ),
}

export interface IconProps {
  name: IconName
  size?: number
  className?: string
}

export function Icon({ name, size = 16, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  )
}
