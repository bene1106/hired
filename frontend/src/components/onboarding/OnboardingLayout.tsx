import { Outlet, useLocation } from 'react-router-dom'

import { OnboardingProvider } from './OnboardingContext'

const STEPS = [
  { path: '/onboarding/welcome', label: 'Welcome' },
  { path: '/onboarding/provider', label: 'Provider' },
  { path: '/onboarding/cv', label: 'Upload CV' },
  { path: '/onboarding/review', label: 'Review' },
  { path: '/onboarding/done', label: 'Done' },
]

export function OnboardingLayout() {
  const location = useLocation()
  const currentIndex = STEPS.findIndex((s) => location.pathname.startsWith(s.path))

  return (
    <OnboardingProvider>
      <main className="min-h-screen bg-background text-foreground">
        <div className="mx-auto max-w-2xl px-6 py-10 flex flex-col gap-8">
          <Stepper currentIndex={Math.max(0, currentIndex)} />
          <Outlet />
        </div>
      </main>
    </OnboardingProvider>
  )
}

function Stepper({ currentIndex }: { currentIndex: number }) {
  return (
    <ol aria-label="Onboarding steps" className="flex items-center justify-between gap-2">
      {STEPS.map((step, i) => {
        const isDone = i < currentIndex
        const isActive = i === currentIndex
        return (
          <li
            key={step.path}
            aria-current={isActive ? 'step' : undefined}
            className="flex flex-1 items-center gap-2"
          >
            <span
              className={
                'h-7 w-7 shrink-0 rounded-full flex items-center justify-center text-xs font-medium ' +
                (isActive
                  ? 'bg-primary text-primary-foreground'
                  : isDone
                    ? 'bg-primary/30 text-primary-foreground'
                    : 'bg-muted text-muted-foreground')
              }
            >
              {i + 1}
            </span>
            <span className={'text-sm ' + (isActive ? 'text-foreground' : 'text-muted-foreground')}>
              {step.label}
            </span>
            {i < STEPS.length - 1 && (
              <span aria-hidden className="ml-1 hidden flex-1 border-t border-border md:block" />
            )}
          </li>
        )
      })}
    </ol>
  )
}
