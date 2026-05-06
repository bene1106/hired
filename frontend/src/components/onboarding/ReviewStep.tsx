import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, ApiError } from '@/lib/api'

import { useOnboarding } from './OnboardingContext'

const PRIORITY_OPTIONS = [
  'Compensation',
  'Growth & learning',
  'Mission / impact',
  'Work-life balance',
  'Remote-first',
  'Strong team',
] as const

export function ReviewStep() {
  const navigate = useNavigate()
  const onboarding = useOnboarding()
  const parsed = onboarding.cvParsed

  // Pre-fill from the parsed CV; everything else stays empty until the user
  // types it.
  const [name, setName] = useState(parsed?.name ?? '')
  const [email, setEmail] = useState(parsed?.email ?? '')
  const [targetRoles, setTargetRoles] = useState('')
  const [targetLocations, setTargetLocations] = useState('')
  const [salaryMin, setSalaryMin] = useState('')
  const [priorities, setPriorities] = useState<string[]>([])

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (parsed === null) {
      navigate('/onboarding/cv', { replace: true })
    }
  }, [parsed, navigate])

  function togglePriority(option: string) {
    setPriorities((prev) =>
      prev.includes(option) ? prev.filter((p) => p !== option) : [...prev, option],
    )
  }

  async function submit() {
    if (name.trim().length === 0) {
      setError('Name is required.')
      return
    }
    if (email.length > 0 && !/^\S+@\S+\.\S+$/.test(email)) {
      setError('That email address looks off.')
      return
    }
    if (targetRoles.trim().length === 0) {
      setError('Add at least one target role.')
      return
    }

    setBusy(true)
    setError(null)
    try {
      await api.updateProfile({
        name: name.trim(),
        email: email.trim() || null,
        target_roles: splitCsv(targetRoles),
        target_locations: splitCsv(targetLocations),
        target_salary_min: salaryMin ? Number(salaryMin) : null,
        priorities,
      })
      navigate('/onboarding/done')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Confirm your profile</CardTitle>
        <CardDescription>
          We pre-filled what we could from your CV. Edit anything that's off.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Field id="name" label="Name" value={name} onChange={setName} required />
        <Field id="email" label="Email" type="email" value={email} onChange={setEmail} />
        <Field
          id="target-roles"
          label="Target role(s)"
          hint="Comma-separated. E.g. 'Backend Engineer, Platform Engineer'."
          value={targetRoles}
          onChange={setTargetRoles}
          required
        />
        <Field
          id="target-locations"
          label="Target locations"
          hint="Comma-separated. Use 'Remote' if you want only remote roles."
          value={targetLocations}
          onChange={setTargetLocations}
        />
        <Field
          id="target-salary"
          label="Minimum salary (annual, your currency)"
          type="number"
          value={salaryMin}
          onChange={setSalaryMin}
        />

        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium">Priorities</legend>
          <div className="grid grid-cols-2 gap-2">
            {PRIORITY_OPTIONS.map((option) => {
              const checked = priorities.includes(option)
              return (
                <label
                  key={option}
                  className={
                    'flex items-center gap-2 rounded-md border px-3 py-2 text-sm cursor-pointer ' +
                    (checked ? 'border-primary bg-primary/5' : 'border-input')
                  }
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => togglePriority(option)}
                  />
                  {option}
                </label>
              )
            })}
          </div>
        </fieldset>

        {error !== null && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="flex justify-between">
          <Button variant="outline" onClick={() => navigate('/onboarding/cv')}>
            Back
          </Button>
          <Button onClick={submit} disabled={busy}>
            {busy ? 'Saving…' : 'Save and continue'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

interface FieldProps {
  id: string
  label: string
  value: string
  onChange: (next: string) => void
  type?: string
  required?: boolean
  hint?: string
}

function Field({ id, label, value, onChange, type = 'text', required, hint }: FieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>
        {label}
        {required && <span aria-hidden className="text-destructive"> *</span>}
      </Label>
      <Input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint !== undefined && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

function splitCsv(input: string): string[] {
  return input
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}
