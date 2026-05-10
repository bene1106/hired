import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { CostSummary, ProfileResponse } from '@/lib/types'

// Phase 3 Settings: enough to satisfy the spec's acceptance criteria —
// see the active provider, walk back through the wizard to switch it,
// edit the profile (re-uses Step 4), and "Delete everything" with a
// two-step confirm. The provider-stats panel lands in Phase 4 once we
// have multi-call traffic worth showing.
export function SettingsScreen() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<ProfileResponse | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [cost, setCost] = useState<CostSummary | null>(null)

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
    api
      .getCostSummary()
      .then(setCost)
      .catch(() => setCost(null))
  }, [])

  async function handleWipe() {
    setDeleting(true)
    try {
      await api.deleteAllData()
      navigate('/', { replace: true })
    } finally {
      setDeleting(false)
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-2xl px-6 py-10 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <Button variant="ghost" onClick={() => navigate('/app')}>
            Back to app
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Edit your target roles, locations, and priorities.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {profile === null ? (
              <p className="text-sm text-muted-foreground">No profile saved.</p>
            ) : (
              <>
                <p className="text-sm">
                  <strong>{profile.name ?? '—'}</strong>{' '}
                  {profile.email !== null ? `· ${profile.email}` : ''}
                </p>
                <p className="text-sm text-muted-foreground">
                  Roles: {profile.target_roles.join(', ') || '—'}
                </p>
                <p className="text-sm text-muted-foreground">
                  Locations: {profile.target_locations.join(', ') || '—'}
                </p>
              </>
            )}
            <div>
              <Button variant="outline" size="sm" onClick={() => navigate('/onboarding/review')}>
                Edit profile
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Provider</CardTitle>
            <CardDescription>
              Switch which LLM Hired. uses to score jobs and generate materials.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" size="sm" onClick={() => navigate('/onboarding/provider')}>
              Switch provider
            </Button>
          </CardContent>
        </Card>

        <Card data-testid="cost-panel">
          <CardHeader>
            <CardTitle>Cost</CardTitle>
            <CardDescription>
              Token spend on generation calls. Local providers cost nothing per request.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            {cost === null ? (
              <p className="text-muted-foreground">Loading…</p>
            ) : (
              <CostDisplay cost={cost} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Delete everything</CardTitle>
            <CardDescription>
              Wipes your profile, every saved job, and your stored API key. Cannot be undone.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {!confirmingDelete ? (
              <Button variant="destructive" onClick={() => setConfirmingDelete(true)}>
                Delete everything…
              </Button>
            ) : (
              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium">
                  Really delete everything? You'll be asked to onboard again.
                </p>
                <div className="flex gap-2">
                  <Button variant="destructive" disabled={deleting} onClick={handleWipe}>
                    {deleting ? 'Deleting…' : 'Yes, delete'}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setConfirmingDelete(false)}
                    disabled={deleting}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  )
}

function CostDisplay({ cost }: { cost: CostSummary }) {
  if (cost.label === 'subscription') {
    return (
      <div>
        <p className="font-medium">$0.00 (subscription)</p>
        <p className="text-xs text-muted-foreground">
          {cost.calls_today} calls today · {cost.calls_week} this week. Claude Code is billed via
          your Claude.ai plan.
        </p>
      </div>
    )
  }
  if (cost.label === 'local') {
    return (
      <div>
        <p className="font-medium">$0.00 (local)</p>
        <p className="text-xs text-muted-foreground">
          {cost.calls_today} calls today · {cost.calls_week} this week. Ollama runs on your
          hardware.
        </p>
      </div>
    )
  }
  if (cost.label === 'unknown') {
    return (
      <div>
        <p className="font-medium">—</p>
        <p className="text-xs text-muted-foreground">
          {cost.calls_today} calls today · {cost.calls_week} this week. The mock provider
          doesn&rsquo;t produce token counts.
        </p>
      </div>
    )
  }
  return (
    <div>
      <p className="font-medium">
        Today: {formatUsd(cost.today_usd)} · This week: {formatUsd(cost.week_usd)}
      </p>
      <p className="text-xs text-muted-foreground">
        {cost.calls_today} calls today · {cost.calls_week} this week
      </p>
    </div>
  )
}

function formatUsd(value: number | null): string {
  if (value === null) return '—'
  return `$${value.toFixed(2)}`
}
