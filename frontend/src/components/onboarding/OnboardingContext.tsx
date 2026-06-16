/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

import type { CVParsedJson, ProviderId } from '@/lib/types'

// State that lives across the wizard's 5 steps. Provider + API key are
// transient — committed to the backend (and OS keychain) when the user
// finishes Step 2. Parsed CV is what the LLM returned in Step 3 and what
// Step 4's form pre-fills from.

export interface OnboardingState {
  selectedProvider: ProviderId | null
  apiKey: string | null
  cvParsed: CVParsedJson | null
  cvText: string | null
}

interface OnboardingContextValue extends OnboardingState {
  setProvider: (provider: ProviderId, apiKey: string | null) => void
  setCvResult: (parsed: CVParsedJson, cvText: string) => void
  reset: () => void
}

const OnboardingContext = createContext<OnboardingContextValue | null>(null)

const initialState: OnboardingState = {
  selectedProvider: null,
  apiKey: null,
  cvParsed: null,
  cvText: null,
}

export function OnboardingProvider({
  children,
  initial,
}: {
  children: ReactNode
  initial?: Partial<OnboardingState>
}) {
  const [state, setState] = useState<OnboardingState>({ ...initialState, ...initial })

  const value = useMemo<OnboardingContextValue>(
    () => ({
      ...state,
      setProvider: (provider, apiKey) =>
        setState((prev) => ({ ...prev, selectedProvider: provider, apiKey })),
      setCvResult: (parsed, cvText) => setState((prev) => ({ ...prev, cvParsed: parsed, cvText })),
      reset: () => setState(initialState),
    }),
    [state],
  )

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>
}

export function useOnboarding(): OnboardingContextValue {
  const ctx = useContext(OnboardingContext)
  if (ctx === null) {
    throw new Error('useOnboarding must be used inside <OnboardingProvider>')
  }
  return ctx
}
