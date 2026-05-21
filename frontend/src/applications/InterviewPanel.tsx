import { useState } from 'react'

import { InterviewChat } from './InterviewChat'
import { InterviewPrep } from './InterviewPrep'

interface InterviewPanelProps {
  applicationId: number
}

type Mode = 'practice' | 'coach'

/**
 * Container that lets the user switch between the Phase 5 Question Bank
 * (Practice) and the Phase 8 streaming Coach. Defaults to Practice so
 * returning users see the same surface — Phase 5 tests still target
 * `<InterviewPrep>` directly and continue to pass without changes.
 */
export function InterviewPanel({ applicationId }: InterviewPanelProps) {
  const [mode, setMode] = useState<Mode>('practice')

  return (
    <div className="flex flex-col gap-4">
      <div
        role="tablist"
        aria-label="Interview prep mode"
        className="inline-flex w-fit rounded-md border border-line bg-surface p-0.5"
      >
        <ModeTab
          label="Practice"
          active={mode === 'practice'}
          onClick={() => setMode('practice')}
          testId="mode-practice"
        />
        <ModeTab
          label="Coach"
          active={mode === 'coach'}
          onClick={() => setMode('coach')}
          testId="mode-coach"
        />
      </div>

      {mode === 'practice' ? (
        <InterviewPrep applicationId={applicationId} />
      ) : (
        <InterviewChat applicationId={applicationId} />
      )}
    </div>
  )
}

function ModeTab({
  label,
  active,
  onClick,
  testId,
}: {
  label: string
  active: boolean
  onClick: () => void
  testId: string
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      data-testid={testId}
      className={`rounded-[4px] px-3 py-1 text-[12px] font-medium transition-colors ${
        active ? 'bg-surface-2 text-ink shadow-sm' : 'text-ink-3 hover:text-ink'
      }`}
    >
      {label}
    </button>
  )
}
