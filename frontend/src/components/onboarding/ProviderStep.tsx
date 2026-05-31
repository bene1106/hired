import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { Icon } from '@/components/icons/Icon'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import type { ProviderDetectionResult, ProviderId } from '@/lib/types'
import { cn } from '@/lib/utils'

import { useOnboarding } from './OnboardingContext'

interface ProviderCardProps {
  id: ProviderId
  title: string
  subtitle: string
  badges: Array<{ label: string; variant?: 'secondary' | 'destructive' | 'default' }>
  disabled: boolean
  selected: boolean
  onSelect: () => void
  children?: React.ReactNode
}

function ProviderCard({
  id,
  title,
  subtitle,
  badges,
  disabled,
  selected,
  onSelect,
  children,
}: ProviderCardProps) {
  return (
    <div
      role="radio"
      aria-checked={selected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      data-testid={`provider-card-${id}`}
      onClick={() => {
        if (!disabled) onSelect()
      }}
      onKeyDown={(e) => {
        if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onSelect()
        }
      }}
      className={cn(
        'rounded-[10px] border p-4 transition-colors',
        disabled
          ? 'cursor-not-allowed border-line opacity-50'
          : 'cursor-pointer hover:border-line-strong',
        selected ? 'border-brand-green bg-brand-green-tint' : 'border-line bg-surface',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[14px] font-semibold tracking-[-0.01em] text-ink">{title}</div>
          <div className="mt-0.5 text-[12px] text-ink-3">{subtitle}</div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {badges.map((b) => (
            <Badge key={b.label} variant={b.variant ?? 'secondary'}>
              {b.label}
            </Badge>
          ))}
        </div>
      </div>
      {children !== undefined && <div className="mt-3">{children}</div>}
    </div>
  )
}

export function ProviderStep() {
  const navigate = useNavigate()
  const onboarding = useOnboarding()
  // When reached from Settings → "Switch provider" the wizard is being
  // reused purely to change the active provider. ``?return=`` carries the
  // route to go back to so we DON'T march an already-onboarded user through
  // the rest of the CV/review/done steps again.
  const [searchParams] = useSearchParams()
  const returnTo = searchParams.get('return')

  const [detection, setDetection] = useState<ProviderDetectionResult | null>(null)
  const [detectionError, setDetectionError] = useState<string | null>(null)
  const [selected, setSelected] = useState<ProviderId | null>(onboarding.selectedProvider)
  const [apiKeyInput, setApiKeyInput] = useState<string>('')
  const [ollamaModel, setOllamaModel] = useState<string>('qwen2.5:14b')
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
        <CardContent className="p-8">
          <p role="alert" className="text-[13px] text-warn">
            Could not reach the backend: {detectionError}
          </p>
        </CardContent>
      </Card>
    )
  }

  if (detection === null) {
    return (
      <Card>
        <CardContent className="p-8">
          <p className="text-[13px] text-ink-3">Checking what you have installed…</p>
        </CardContent>
      </Card>
    )
  }

  const apiHasKey = detection.anthropic_api.key_in_env || detection.anthropic_api.key_in_keychain

  async function runTest(provider: ProviderId, key: string | null, model: string | null) {
    setTestStatus('testing')
    setTestMessage(null)
    try {
      const result = await api.testProvider(provider, key ?? undefined, model ?? undefined)
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
    // Pick a sensible default if Ollama is the choice and the user has
    // models installed. We prefer the recommended model, falling back to
    // whatever's first in the detected list.
    if (provider === 'ollama' && detection?.ollama.models.length) {
      const preferred = detection.ollama.models.find((m) => m === 'qwen2.5:14b')
      setOllamaModel(preferred ?? detection.ollama.models[0])
    }
  }

  function canContinue(): boolean {
    if (selected === null) return false
    if (selected === 'mock') return true
    return testStatus === 'ok'
  }

  async function continueToCV() {
    if (selected === null) return
    const apiKey = selected === 'anthropic_api' ? apiKeyInput.trim() || null : null
    const model = selected === 'ollama' ? ollamaModel : null
    onboarding.setProvider(selected, apiKey)
    setTestStatus('testing')
    setTestMessage(null)
    try {
      await api.selectProvider(selected, apiKey, model)
      navigate(returnTo ?? '/onboarding/cv')
    } catch (err) {
      setTestStatus('error')
      setTestMessage(err instanceof Error ? err.message : String(err))
    }
  }

  const testMsgClass = cn('text-[12px]', testStatus === 'ok' ? 'text-brand-green' : 'text-warn')

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 p-8">
        <div>
          <h2 className="mb-1.5 text-[18px] font-semibold tracking-[-0.01em] text-ink">
            Pick an LLM provider
          </h2>
          <p className="text-[13px] leading-relaxed text-ink-3">
            Hired. supports several backends. The Anthropic API is the most reliable; Claude Code,
            OpenAI Codex, and Ollama are all fully supported alternatives.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <ProviderCard
            id="anthropic_api"
            title="Anthropic API"
            subtitle="Recommended. Highest quality. Pay-per-use."
            badges={apiHasKey ? [{ label: 'Key found' }] : []}
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
                    onClick={() => runTest('anthropic_api', apiKeyInput || null, null)}
                  >
                    {testStatus === 'testing' ? 'Testing…' : 'Test connection'}
                  </Button>
                  {testMessage !== null && <span className={testMsgClass}>{testMessage}</span>}
                </div>
              </div>
            )}
          </ProviderCard>

          <ProviderCard
            id="claude_code"
            title="Claude Code"
            subtitle="Use the local Claude CLI. Calls count against your Claude subscription."
            badges={[
              { label: 'Experimental', variant: 'destructive' },
              detection.claude_code.detected
                ? {
                    label: `Detected${
                      detection.claude_code.version ? ` (${detection.claude_code.version})` : ''
                    }`,
                  }
                : { label: 'Not installed' },
            ]}
            disabled={!detection.claude_code.detected}
            selected={selected === 'claude_code'}
            onSelect={() => pick('claude_code')}
          >
            {selected === 'claude_code' && (
              <div className="flex flex-col gap-2">
                <p className="text-[12px] text-ink-3">
                  Hired. shells out to your local <code>claude</code> CLI. Usage counts against your
                  Claude.ai subscription. Subject to Anthropic&rsquo;s terms.
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={testStatus === 'testing'}
                    onClick={() => runTest('claude_code', null, null)}
                  >
                    {testStatus === 'testing' ? 'Testing…' : 'Test CLI'}
                  </Button>
                  {testMessage !== null && <span className={testMsgClass}>{testMessage}</span>}
                </div>
              </div>
            )}
          </ProviderCard>

          <ProviderCard
            id="codex_cli"
            title="OpenAI Codex"
            subtitle="Use the local Codex CLI. Calls count against your ChatGPT plan or OpenAI key."
            badges={[
              { label: 'Experimental', variant: 'destructive' },
              detection.codex_cli.detected
                ? detection.codex_cli.logged_in
                  ? {
                      label: `Detected${
                        detection.codex_cli.version ? ` (${detection.codex_cli.version})` : ''
                      }`,
                    }
                  : { label: 'Not logged in', variant: 'destructive' }
                : { label: 'Not installed' },
            ]}
            disabled={!detection.codex_cli.detected}
            selected={selected === 'codex_cli'}
            onSelect={() => pick('codex_cli')}
          >
            {selected === 'codex_cli' && (
              <div className="flex flex-col gap-2">
                <p className="text-[12px] text-ink-3">
                  Hired. shells out to your local <code>codex</code> CLI. Usage counts against your
                  ChatGPT subscription (or <code>OPENAI_API_KEY</code>). Run{' '}
                  <code>codex login</code> first. Subject to OpenAI&rsquo;s terms.
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={testStatus === 'testing'}
                    onClick={() => runTest('codex_cli', null, null)}
                  >
                    {testStatus === 'testing' ? 'Testing…' : 'Test CLI'}
                  </Button>
                  {testMessage !== null && <span className={testMsgClass}>{testMessage}</span>}
                </div>
              </div>
            )}
          </ProviderCard>

          <ProviderCard
            id="ollama"
            title="Ollama (local)"
            subtitle="Fully offline. Runs on your hardware; quality depends on the chosen model."
            badges={[
              detection.ollama.detected
                ? { label: `${detection.ollama.models.length} models` }
                : { label: 'Not running' },
            ]}
            disabled={!detection.ollama.detected}
            selected={selected === 'ollama'}
            onSelect={() => pick('ollama')}
          >
            {selected === 'ollama' && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="ollama-model">Model</Label>
                <select
                  id="ollama-model"
                  value={ollamaModel}
                  onChange={(e) => setOllamaModel(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                >
                  {detection.ollama.models.length === 0 ? (
                    <option value="qwen2.5:14b">qwen2.5:14b (not pulled)</option>
                  ) : (
                    detection.ollama.models.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))
                  )}
                </select>
                <p className="text-[12px] text-ink-3">
                  Recommended: <code>qwen2.5:14b</code>. Low-end fallback: <code>llama3.2:3b</code>.
                  Generation may take up to 90s per call locally.
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={testStatus === 'testing'}
                    onClick={() => runTest('ollama', null, ollamaModel)}
                  >
                    {testStatus === 'testing' ? 'Testing…' : 'Test connection'}
                  </Button>
                  {testMessage !== null && <span className={testMsgClass}>{testMessage}</span>}
                </div>
              </div>
            )}
          </ProviderCard>

          <ProviderCard
            id="mock"
            title="Mock (offline demo)"
            subtitle="Deterministic stubs. Useful for trying out the app without an API key."
            badges={[{ label: 'Always available' }]}
            disabled={false}
            selected={selected === 'mock'}
            onSelect={() => pick('mock')}
          />
        </div>

        <div className="flex justify-end">
          <Button disabled={!canContinue()} onClick={continueToCV}>
            {returnTo ? 'Save provider' : 'Continue'} <Icon name="arrowRight" size={14} />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
