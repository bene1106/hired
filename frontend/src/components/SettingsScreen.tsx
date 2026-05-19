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
    <main className="screen min-h-screen bg-paper text-ink">
      <div className="mx-auto flex max-w-[680px] flex-col gap-6 px-8 py-10">
        <div className="mb-1">
          <div className="mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
            Settings
          </div>
          <h1 className="text-[28px] font-semibold tracking-[-0.025em] text-ink">Settings</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-[18px] tracking-[-0.01em] text-ink">Profile</CardTitle>
            <CardDescription className="text-[13px] text-ink-3">
              Edit your target roles, locations, and priorities.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {profile === null ? (
              <p className="text-[13px] text-ink-3">No profile saved.</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                <p className="text-[14px] text-ink">
                  <strong className="font-semibold">{profile.name ?? '—'}</strong>{' '}
                  {profile.email !== null ? (
                    <span className="text-ink-3">· {profile.email}</span>
                  ) : (
                    ''
                  )}
                </p>
                <p className="text-[13px] text-ink-3">
                  Roles: {profile.target_roles.join(', ') || '—'}
                </p>
                <p className="text-[13px] text-ink-3">
                  Locations: {profile.target_locations.join(', ') || '—'}
                </p>
              </div>
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
            <CardTitle className="text-[18px] tracking-[-0.01em] text-ink">Provider</CardTitle>
            <CardDescription className="text-[13px] text-ink-3">
              Switch which LLM Hired. uses to score jobs and generate materials.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {stats === null ? (
              <p className="text-[13px] text-ink-3">Loading provider status…</p>
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
            <CardTitle className="text-[18px] tracking-[-0.01em] text-ink">Cost</CardTitle>
            <CardDescription className="text-[13px] text-ink-3">
              Token spend on generation calls. Local providers cost nothing per request.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {cost === null ? (
              <p className="text-[13px] text-ink-3">Loading…</p>
            ) : (
              <CostDisplay cost={cost} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-[18px] tracking-[-0.01em] text-ink">
              Delete everything
            </CardTitle>
            <CardDescription className="text-[13px] text-ink-3">
              Wipes your profile, every saved job, and your stored API key. Cannot be undone.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {!confirmingDelete ? (
              <div>
                <Button variant="destructive" onClick={() => setConfirmingDelete(true)}>
                  Delete everything…
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-3 rounded-md border border-warn-soft bg-warn-soft/40 p-4">
                <p className="text-[13px] font-medium text-ink">
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
    <div className="flex flex-col gap-1.5" aria-live="polite">
      <p className="flex items-center gap-2 text-[14px] font-medium text-ink">
        Currently using: {label}
        {stats.provider === 'claude_code' ? (
          <Badge variant="destructive" className="align-middle">
            Experimental
          </Badge>
        ) : null}
      </p>
      <p className="text-[12px] text-ink-3">
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
      <div className="flex flex-col gap-1">
        <p className="text-[15px] font-semibold text-ink">$0.00 (subscription)</p>
        <p className="text-[12px] text-ink-3">
          {cost.calls_today} calls today · {cost.calls_week} this week. Claude Code is billed via
          your Claude.ai plan.
        </p>
      </div>
    )
  }
  if (cost.label === 'local') {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-[15px] font-semibold text-ink">$0.00 (local)</p>
        <p className="text-[12px] text-ink-3">
          {cost.calls_today} calls today · {cost.calls_week} this week. Ollama runs on your
          hardware.
        </p>
      </div>
    )
  }
  if (cost.label === 'unknown') {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-[15px] font-semibold text-ink">—</p>
        <p className="text-[12px] text-ink-3">
          {cost.calls_today} calls today · {cost.calls_week} this week. The mock provider
          doesn&rsquo;t produce token counts.
        </p>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-1">
      <p className="text-[15px] font-semibold text-ink">
        Today: {formatUsd(cost.today_usd)} · This week: {formatUsd(cost.week_usd)}
      </p>
      <p className="text-[12px] text-ink-3">
        {cost.calls_today} calls today · {cost.calls_week} this week
      </p>
    </div>
  )
}

function formatUsd(value: number | null): string {
  if (value === null) return '—'
  return `$${value.toFixed(2)}`
}
