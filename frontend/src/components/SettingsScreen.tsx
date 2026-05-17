import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { CostSummary, ProfileResponse, ProviderId, ProviderStats } from '@/lib/types'

// Phase 6 Settings: live provider status alongside the wizard re-entry,
// profile editing, cost rollups, and the two-step "Delete everything"
// confirm. The provider stats endpoint already exists; we just surface
// it here so users can see latency / call count without leaving the app.
export function SettingsScreen() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<ProfileResponse | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [cost, setCost] = useState<CostSummary | null>(null)
  const [stats, setStats] = useState<ProviderStats | null>(null)

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
    api
      .getCostSummary()
      .then(setCost)
      .catch(() => setCost(null))
    api
      .getProviderStats()
      .then(setStats)
      .catch(() => setStats(null))
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

        <Card data-testid="provider-panel">
          <CardHeader>
            <CardTitle>Provider</CardTitle>
            <CardDescription>
              Switch which LLM Hired. uses to score jobs and generate materials.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {stats === null ? (
              <p className="text-sm text-muted-foreground">Loading provider status…</p>
            ) : (
              <ProviderStatus stats={stats} />
            )}
            <div>
              <Button variant="outline" size="sm" onClick={() => navigate('/onboarding/provider')}>
                Switch provider
              </Button>
            </div>
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

const PROVIDER_LABELS: Record<ProviderId, string> = {
  anthropic_api: 'Anthropic API',
  claude_code: 'Claude Code',
  ollama: 'Ollama (local)',
  mock: 'Mock (dev only)',
}

function ProviderStatus({ stats }: { stats: ProviderStats }) {
  const label = PROVIDER_LABELS[stats.provider] ?? stats.provider
  const healthy = stats.last_success === null ? null : stats.last_success
  const latency = stats.last_latency_ms === null ? null : `${stats.last_latency_ms} ms`
  const successRate =
    stats.success_rate_today === null
      ? null
      : `${Math.round(stats.success_rate_today * 100)}% success`
  return (
    <div className="flex flex-col gap-1 text-sm" aria-live="polite">
      <p className="font-medium">
        Currently using: {label}
        {stats.provider === 'claude_code' ? (
          <Badge variant="destructive" className="ml-2 align-middle">
            Experimental
          </Badge>
        ) : null}
      </p>
      <p className="text-xs text-muted-foreground">
        {healthy === null
          ? 'No calls yet — pick a job to score or generate to populate stats.'
          : healthy
            ? '✓ Healthy'
            : '⚠ Last call failed'}
        {latency ? ` · ${latency} latency` : ''} · {stats.calls_today} calls today
        {successRate ? ` · ${successRate}` : ''}
      </p>
    </div>
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
