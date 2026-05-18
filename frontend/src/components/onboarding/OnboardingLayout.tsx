import { Outlet, useLocation } from 'react-router-dom'

import { HiredStacked } from '@/components/brand/HiredStacked'
import { Icon } from '@/components/icons/Icon'
import { cn } from '@/lib/utils'

import { OnboardingProvider } from './OnboardingContext'

const STEPS = [
  { path: '/onboarding/welcome', label: 'Welcome' },
  { path: '/onboarding/provider', label: 'Provider' },
  { path: '/onboarding/cv', label: 'Upload CV' },
  { path: '/onboarding/review', label: 'Review' },
  { path: '/onboarding/done', label: 'Done' },
]

// Per-route hero copy. The wizard frame stays constant; only the eyebrow
// + headline change so the page reads right at each stage.
const HERO: Record<string, { eyebrow: string; title: string }> = {
  '/onboarding/welcome': { eyebrow: 'Welcome', title: "Let's get you set up." },
  '/onboarding/provider': { eyebrow: 'Profile setup', title: "Let's get your agent ready." },
  '/onboarding/cv': { eyebrow: 'Profile setup', title: "Let's get your agent ready." },
  '/onboarding/review': { eyebrow: 'Profile setup', title: "Let's get your agent ready." },
  '/onboarding/done': { eyebrow: 'All set', title: 'Your agent is ready.' },
}

export function OnboardingLayout() {
  const location = useLocation()
  const currentIndex = Math.max(
    0,
    STEPS.findIndex((s) => location.pathname.startsWith(s.path)),
  )
  const hero = HERO[STEPS[currentIndex].path] ?? HERO['/onboarding/welcome']

  return (
    <OnboardingProvider>
      <main className="min-h-screen bg-background text-foreground">
        <div className="mx-auto flex max-w-[820px] flex-col gap-8 px-10 py-8">
          {/* Hero */}
          <div className="flex flex-col items-center gap-7">
            <HiredStacked markSize={64} wordSize={28} gap={14} />
            <div className="text-center">
              <div className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">
                {hero.eyebrow}
              </div>
              <h1 className="font-serif text-[26px] font-black tracking-[-0.02em] text-ink">
                {hero.title}
              </h1>
            </div>
            <Stepper currentIndex={currentIndex} />
          </div>

          <Outlet />
        </div>
      </main>
    </OnboardingProvider>
  )
}

// Display-only: no links/buttons. The wizard is guard-railed — steps are
// reached by completing the prior one, never by clicking the stepper.
function Stepper({ currentIndex }: { currentIndex: number }) {
  return (
    <ol
      aria-label="Onboarding steps"
      className="flex items-center justify-center gap-1.5 text-[12px]"
    >
      {STEPS.map((step, i) => {
        const isDone = i < currentIndex
        const isActive = i === currentIndex
        return (
          <li key={step.path} className="flex items-center gap-1.5">
            <div
              aria-current={isActive ? 'step' : undefined}
              className={cn(
                'flex items-center gap-2 rounded-[7px] border px-2.5 py-1.5',
                isActive ? 'border-line bg-surface' : 'border-transparent',
              )}
            >
              <span
                className={cn(
                  'flex h-5 w-5 items-center justify-center rounded-full font-mono text-[10px] font-semibold',
                  isDone
                    ? 'bg-brand-green text-white'
                    : isActive
                      ? 'bg-ink text-white'
                      : 'bg-line text-ink-3',
                )}
              >
                {isDone ? <Icon name="check" size={10} /> : i + 1}
              </span>
              <span className={isActive ? 'font-medium text-ink' : 'text-ink-3'}>{step.label}</span>
            </div>
            {i < STEPS.length - 1 && <span aria-hidden className="h-px w-5 bg-line" />}
          </li>
        )
      })}
    </ol>
  )
}
