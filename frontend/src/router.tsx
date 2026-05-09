import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AppGate } from '@/components/AppGate'
import { OnboardingLayout } from '@/components/onboarding/OnboardingLayout'
import { CVStep } from '@/components/onboarding/CVStep'
import { DoneStep } from '@/components/onboarding/DoneStep'
import { ProviderStep } from '@/components/onboarding/ProviderStep'
import { ReviewStep } from '@/components/onboarding/ReviewStep'
import { WelcomeStep } from '@/components/onboarding/WelcomeStep'
import { SettingsScreen } from '@/components/SettingsScreen'
import { FeedScreen } from '@/feed/FeedScreen'

// Phase 3 routing.
//
//   /              → AppGate decides where to redirect (wizard vs main app)
//   /onboarding/*  → wizard steps
//   /app           → main shell ("no jobs yet")
//   /app/settings  → provider + profile + delete-everything
export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<AppGate />} />
      <Route path="/onboarding" element={<OnboardingLayout />}>
        <Route index element={<Navigate to="welcome" replace />} />
        <Route path="welcome" element={<WelcomeStep />} />
        <Route path="provider" element={<ProviderStep />} />
        <Route path="cv" element={<CVStep />} />
        <Route path="review" element={<ReviewStep />} />
        <Route path="done" element={<DoneStep />} />
      </Route>
      <Route path="/app" element={<Outlet />}>
        <Route index element={<FeedScreen />} />
        <Route path="settings" element={<SettingsScreen />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
