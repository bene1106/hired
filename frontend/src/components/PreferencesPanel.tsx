import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Icon } from '@/components/icons/Icon'
import { Toast, useToast } from '@/components/Toast'
import { api } from '@/lib/api'
import type { ProfileResponse } from '@/lib/types'

interface PreferencesPanelProps {
  profile: ProfileResponse
  onSaved: (next: ProfileResponse) => void
}

interface DraftState {
  roles: string[]
  locations: string[]
  salaryMin: string
  priorities: string
}

function fromProfile(p: ProfileResponse): DraftState {
  return {
    roles: p.target_roles,
    locations: p.target_locations,
    salaryMin: p.target_salary_min === null ? '' : String(p.target_salary_min),
    priorities: p.priorities.join('\n'),
  }
}

/**
 * Phase 8 settings sub-page: in-place editing of the targeting signals
 * Hired. uses to score jobs.
 *
 * Backend already has the fields (target_roles_json, target_locations_json,
 * target_salary_min, priorities_json) since Phase 3 — no migration. We
 * just expose an editable surface so users can sharpen their targeting
 * without re-running the onboarding wizard.
 *
 * Per handoff §17, this is what Phase 8 owes from the deferred
 * Prefs/Priorities onboarding steps the design proposed.
 */
export function PreferencesPanel({ profile, onSaved }: PreferencesPanelProps) {
  const [draft, setDraft] = useState<DraftState>(() => fromProfile(profile))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    setDraft(fromProfile(profile))
  }, [profile])

  const dirty =
    !arraysEqual(draft.roles, profile.target_roles) ||
    !arraysEqual(draft.locations, profile.target_locations) ||
    parsedSalary(draft.salaryMin) !== profile.target_salary_min ||
    !arraysEqual(parsePriorities(draft.priorities), profile.priorities)

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const next = await api.updateProfile({
        target_roles: draft.roles,
        target_locations: draft.locations,
        target_salary_min: parsedSalary(draft.salaryMin),
        priorities: parsePriorities(draft.priorities),
      })
      onSaved(next)
      toast.show('Preferences saved')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save preferences.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card data-testid="preferences-panel">
      <CardHeader>
        <CardTitle className="text-[18px] tracking-[-0.01em] text-ink">Preferences</CardTitle>
        <CardDescription className="text-[13px] text-ink-3">
          Sharpen your target. Hired. scores new jobs against these signals.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Field label="Target roles" hint="One per chip. Press Enter or comma to add.">
          <ChipInput
            values={draft.roles}
            onChange={(roles) => setDraft((d) => ({ ...d, roles }))}
            placeholder="Backend Engineer, Platform Engineer…"
            testId="roles-input"
          />
        </Field>

        <Field label="Target locations" hint="Cities, regions, or 'Remote (EU)'.">
          <ChipInput
            values={draft.locations}
            onChange={(locations) => setDraft((d) => ({ ...d, locations }))}
            placeholder="Berlin, Remote (EU)…"
            testId="locations-input"
          />
        </Field>

        <Field label="Minimum salary (EUR / year)" hint="Optional. Leave blank to skip.">
          <input
            type="number"
            min={0}
            step={1000}
            inputMode="numeric"
            value={draft.salaryMin}
            onChange={(e) => setDraft((d) => ({ ...d, salaryMin: e.target.value }))}
            placeholder="55000"
            data-testid="salary-min-input"
            className="w-40 rounded-md border border-line bg-surface-2 px-3 py-2 text-[13px] tabular-nums text-ink outline-none focus:border-line-strong"
          />
        </Field>

        <Field
          label="Priorities"
          hint="One per line, most important first. Hired. weights matches by this order."
        >
          <textarea
            value={draft.priorities}
            onChange={(e) => setDraft((d) => ({ ...d, priorities: e.target.value }))}
            placeholder={
              'Direct impact on the product\nMentor or peer to learn from\nNo on-call rotation'
            }
            rows={5}
            data-testid="priorities-input"
            className="resize-vertical rounded-md border border-line bg-surface-2 p-3 text-[13px] leading-relaxed text-ink outline-none focus:border-line-strong"
          />
        </Field>

        {error !== null ? (
          <p role="alert" className="text-[12px] text-warn">
            {error}
          </p>
        ) : null}

        <div className="flex items-center gap-3">
          <Button
            size="sm"
            disabled={!dirty || saving}
            onClick={() => void save()}
            data-testid="save-preferences"
          >
            {saving ? (
              <>
                <Icon name="refresh" size={12} className="animate-spin" /> Saving…
              </>
            ) : (
              'Save preferences'
            )}
          </Button>
          {!dirty ? <span className="text-[12px] text-ink-3">No unsaved changes.</span> : null}
        </div>
      </CardContent>
      <Toast message={toast.message} />
    </Card>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[13px] font-medium text-ink">{label}</span>
      {hint !== undefined ? <span className="text-[11px] text-ink-3">{hint}</span> : null}
      {children}
    </div>
  )
}

interface ChipInputProps {
  values: string[]
  onChange: (next: string[]) => void
  placeholder?: string
  testId?: string
}

function ChipInput({ values, onChange, placeholder, testId }: ChipInputProps) {
  const [draft, setDraft] = useState('')

  function commitDraft() {
    const trimmed = draft.trim()
    if (trimmed === '') return
    if (!values.includes(trimmed)) onChange([...values, trimmed])
    setDraft('')
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      commitDraft()
    } else if (event.key === 'Backspace' && draft === '' && values.length > 0) {
      // Convenience: backspace on empty input removes the last chip.
      onChange(values.slice(0, -1))
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-md border border-line bg-surface-2 p-2 focus-within:border-line-strong">
      {values.map((v) => (
        <span
          key={v}
          className="inline-flex items-center gap-1 rounded-full bg-surface px-2 py-0.5 text-[12px] text-ink-2"
        >
          {v}
          <button
            type="button"
            aria-label={`Remove ${v}`}
            onClick={() => onChange(values.filter((x) => x !== v))}
            className="text-ink-3 hover:text-warn"
          >
            ×
          </button>
        </span>
      ))}
      <input
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commitDraft}
        placeholder={values.length === 0 ? placeholder : undefined}
        data-testid={testId}
        className="min-w-[140px] flex-1 bg-transparent px-1 py-0.5 text-[13px] text-ink outline-none placeholder:text-ink-3"
      />
    </div>
  )
}

function arraysEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false
  return a.every((v, i) => v === b[i])
}

function parsedSalary(raw: string): number | null {
  const trimmed = raw.trim()
  if (trimmed === '') return null
  const n = Number.parseInt(trimmed, 10)
  return Number.isFinite(n) && n >= 0 ? n : null
}

function parsePriorities(raw: string): string[] {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '')
}
