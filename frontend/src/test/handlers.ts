import { http, HttpResponse } from 'msw'

import type {
  CVParseResponse,
  ProfileResponse,
  ProviderDetectionResult,
  TestProviderResult,
} from '@/lib/types'

const BACKEND = 'http://localhost:8765'

// ----- in-memory state per test --------------------------------------------
// Tests can mutate via `setMockState({...})` to drive specific scenarios.
// `resetMockState()` is called by handlers in beforeEach (test/setup.ts).

interface MockState {
  detect: ProviderDetectionResult
  testProvider: TestProviderResult
  profile: ProfileResponse | null
  cvParse: CVParseResponse
}

const defaultState = (): MockState => ({
  detect: {
    anthropic_api: { key_in_env: false, key_in_keychain: false },
    claude_code: { detected: false, path: null, version: null },
    ollama: { detected: false, models: [] },
  },
  testProvider: { ok: true, latency_ms: 12, error: null, error_kind: null },
  profile: null,
  cvParse: {
    parsed: {
      name: 'Alex K.',
      email: 'alex@example.com',
      summary: 'Backend engineer with FastAPI experience.',
      skills: ['Python', 'FastAPI'],
      work_experience: [],
      education: [],
      languages: [],
      certifications: [],
    },
    profile: {
      id: 1,
      name: 'Alex K.',
      email: 'alex@example.com',
      target_roles: [],
      target_locations: [],
      target_salary_min: null,
      priorities: [],
      cv_text: 'Pretend CV text',
      cv_parsed_json: null,
      profile_version: 1,
    },
  },
})

let state: MockState = defaultState()

export function setMockState(patch: Partial<MockState>): void {
  state = { ...state, ...patch }
}

export function resetMockState(): void {
  state = defaultState()
}

export function getMockState(): MockState {
  return state
}

// ----- handlers ------------------------------------------------------------

export const handlers = [
  http.post(`${BACKEND}/api/setup/detect-providers`, () => HttpResponse.json(state.detect)),

  http.post(`${BACKEND}/api/setup/test-provider`, () => HttpResponse.json(state.testProvider)),

  http.post(`${BACKEND}/api/setup/select-provider`, async ({ request }) => {
    const body = (await request.json()) as { provider: string }
    return HttpResponse.json({ provider: body.provider })
  }),

  http.post(`${BACKEND}/api/profile/cv`, async () => {
    state = { ...state, profile: state.cvParse.profile }
    return HttpResponse.json(state.cvParse)
  }),

  http.post(`${BACKEND}/api/profile/cv/upload`, async () => {
    state = { ...state, profile: state.cvParse.profile }
    return HttpResponse.json(state.cvParse)
  }),

  http.get(`${BACKEND}/api/profile`, () => {
    if (state.profile === null) {
      return HttpResponse.json({ detail: 'No profile saved yet.' }, { status: 404 })
    }
    return HttpResponse.json(state.profile)
  }),

  http.post(`${BACKEND}/api/profile`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const next: ProfileResponse = {
      id: 1,
      name: (body.name as string | null) ?? state.profile?.name ?? null,
      email: (body.email as string | null) ?? state.profile?.email ?? null,
      target_roles: (body.target_roles as string[]) ?? state.profile?.target_roles ?? [],
      target_locations:
        (body.target_locations as string[]) ?? state.profile?.target_locations ?? [],
      target_salary_min:
        (body.target_salary_min as number | null) ?? state.profile?.target_salary_min ?? null,
      priorities: (body.priorities as string[]) ?? state.profile?.priorities ?? [],
      cv_text: state.profile?.cv_text ?? null,
      cv_parsed_json: state.profile?.cv_parsed_json ?? null,
      profile_version: (state.profile?.profile_version ?? 0) + 1,
    }
    state = { ...state, profile: next }
    return HttpResponse.json(next)
  }),

  http.delete(`${BACKEND}/api/data/all`, () => {
    state = defaultState()
    return HttpResponse.json({ deleted: true })
  }),
]
