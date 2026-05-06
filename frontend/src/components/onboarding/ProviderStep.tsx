import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import type { ProviderDetectionResult, ProviderId } from '@/lib/types'

import { useOnboarding } from './OnboardingContext'

interface ProviderCardProps {
  id: ProviderId
  title: string
  subtitle: string
  badge: string | null
  disabled: boolean
  selected: boolean
  onSelect: () => void
  children?: React.ReactNode
}

function ProviderCard({
  id,
  title,
  subtitle,
  badge,
  disabled,
  selected,
  onSelect,
  children,
}: ProviderCardProps) {
  return (
    <Card
      role="radio"
      aria-checked={selected}
      aria-disabled={disabled}
      data-testid={`provider-card-${id}`}
      onClick={() => {
        if (!disabled) onSelect()
      }}
      className={
        'cursor-pointer transition-colors ' +
        (selected ? 'border-primary' : '') +
        (disabled ? ' opacity-50 cursor-not-allowed' : ' hover:border-primary/50')
      }
    >
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{title}</CardTitle>
          {badge !== null && <Badge variant="secondary">{badge}</Badge>}
        </div>
        <CardDescription>{subtitle}</CardDescription>
      </CardHeader>
      {children !== undefined && <CardContent>{children}</CardContent>}
    </Card>
  )
}

export function ProviderStep() {
  const navigate = useNavigate()
  const onboarding = useOnboarding()

  const [detection, setDetection] = useState<ProviderDetectionResult | null>(null)
  const [detectionError, setDetectionError] = useState<string | null>(null)
  const [selected, setSelected] = useState<ProviderId | null>(onboarding.selectedProvider)
  const [apiKeyInput, setApiKeyInput] = useState<string>('')
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')
  const [testMessage, setTestMessage] = useState<string | null>(null)

  useEffect(() => {
    api
      .detectProviders()
      .then(setDetection)
      .catch((err) => setDetectionError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (detectionError !== null) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p role="alert" className="text-sm text-destructive">
            Could not reach the backend: {detectionError}
          </p>
        </CardContent>
      </Card>
    )
  }

  if (detection === null) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Checking what you have installed…</p>
        </CardContent>
      </Card>
    )
  }

  const apiHasKey = detection.anthropic_api.key_in_env || detection.anthropic_api.key_in_keychain

  async function runTest(provider: ProviderId, key: string | null) {
    setTestStatus('testing')
    setTestMessage(null)
    try {
      const result = await api.testProvider(provider, key ?? undefined)
      if (result.ok) {
        setTestStatus('ok')
        setTestMessage(`Connected (${result.latency_ms} ms).`)
      } else {
        setTestStatus('error')
        setTestMessage(result.error ?? 'Provider test failed.')
      }
    } catch (err) {
      setTestStatus('error')
      setTestMessage(err instanceof Error ? err.message : String(err))
    }
  }

  function pick(provider: ProviderId) {
    setSelected(provider)
    setTestStatus('idle')
    setTestMessage(null)
    if (provider !== 'anthropic_api') {
      setApiKeyInput('')
    }
  }

  function canContinue(): boolean {
    if (selected === null) return false
    if (selected === 'anthropic_api') return testStatus === 'ok'
    return selected === 'mock'
  }

  async function continueToCV() {
    if (selected === null) return
    const apiKey = selected === 'anthropic_api' ? apiKeyInput.trim() || null : null
    onboarding.setProvider(selected, apiKey)
    setTestStatus('testing')
    setTestMessage(null)
    try {
      await api.selectProvider(selected, apiKey ?? undefined)
      navigate('/onboarding/cv')
    } catch (err) {
      setTestStatus('error')
      setTestMessage(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pick an LLM provider</CardTitle>
        <CardDescription>
          Hired. supports several backends. The Anthropic API is the most reliable; the
          others are coming in v0.6.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-3">
          <ProviderCard
            id="anthropic_api"
            title="Anthropic API"
            subtitle="Recommended. Highest quality. Pay-per-use."
            badge={apiHasKey ? 'Key found' : null}
            disabled={false}
            selected={selected === 'anthropic_api'}
            onSelect={() => pick('anthropic_api')}
          >
            {selected === 'anthropic_api' && (
              <div className="flex flex-col gap-2">
                {!apiHasKey && (
                  <>
                    <Label htmlFor="api-key">API key</Label>
                    <Input
                      id="api-key"
                      type="password"
                      autoComplete="off"
                      value={apiKeyInput}
                      onChange={(e) => setApiKeyInput(e.target.value)}
                      placeholder="sk-ant-…"
                    />
                  </>
                )}
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={testStatus === 'testing' || (!apiHasKey && apiKeyInput.length < 5)}
                    onClick={() => runTest('anthropic_api', apiKeyInput || null)}
                  >
                    {testStatus === 'testing' ? 'Testing…' : 'Test connection'}
                  </Button>
                  {testMessage !== null && (
                    <span
                      className={
                        'text-xs ' +
                        (testStatus === 'ok' ? 'text-foreground' : 'text-destructive')
                      }
                    >
                      {testMessage}
                    </span>
                  )}
                </div>
              </div>
            )}
          </ProviderCard>

          <ProviderCard
            id="claude_code"
            title="Claude Code"
            subtitle="Use the Claude CLI on your machine. Coming in v0.6."
            badge={
              detection.claude_code.detected
                ? `Detected${detection.claude_code.version ? ` (${detection.claude_code.version})` : ''}`
                : 'Not installed'
            }
            disabled
            selected={false}
            onSelect={() => undefined}
          />

          <ProviderCard
            id="ollama"
            title="Ollama"
            subtitle="Fully offline. Coming in v0.6."
            badge={detection.ollama.detected ? `${detection.ollama.models.length} models` : 'Not running'}
            disabled
            selected={false}
            onSelect={() => undefined}
          />

          <ProviderCard
            id="mock"
            title="Mock (offline demo)"
            subtitle="Deterministic stubs. Useful for trying out the app without an API key."
            badge="Always available"
            disabled={false}
            selected={selected === 'mock'}
            onSelect={() => pick('mock')}
          />
        </div>

        <div className="flex justify-end">
          <Button disabled={!canContinue()} onClick={continueToCV}>
            Continue
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
