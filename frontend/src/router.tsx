import { Navigate, Route, Routes } from 'react-router-dom'

import { ApplicationDashboard } from '@/applications/Dashboard'
import { ApplicationDetailScreen } from '@/applications/ApplicationDetail'
import { GeneratePage } from '@/applications/GeneratePage'
import { AppGate } from '@/components/AppGate'
import { AppShell } from '@/components/shell/AppShell'
import { OnboardingLayout } from '@/components/onboarding/OnboardingLayout'
import { CVStep } from '@/components/onboarding/CVStep'
import { DoneStep } from '@/components/onboarding/DoneStep'
import { ProviderStep } from '@/components/onboarding/ProviderStep'
import { ReviewStep } from '@/components/onboarding/ReviewStep'
import { WelcomeStep } from '@/components/onboarding/WelcomeStep'
import { SettingsScreen } from '@/components/SettingsScreen'
import { SourcesScreen } from '@/components/SourcesScreen'
import { FeedScreen } from '@/feed/FeedScreen'

// Phase 5 routing.
//
//   /                              → AppGate decides where to redirect
//   /onboarding/*                  → wizard steps
//   /app                           → ranked feed
//   /app/apply/:jobId              → generate materials, edit, mark applied
//   /app/applications              → dashboard table
//   /app/applications/:id          → detail (materials + interview prep)
//   /app/settings                  → provider + profile + cost panel
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
      <Route path="/app" element={<AppShell />}>
        <Route index element={<FeedScreen />} />
        <Route path="apply/:jobId" element={<GeneratePage />} />
        <Route path="applications" element={<ApplicationDashboard />} />
        <Route path="applications/:applicationId" element={<ApplicationDetailScreen />} />
        <Route path="settings" element={<SettingsScreen />} />
        <Route path="sources" element={<SourcesScreen />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
