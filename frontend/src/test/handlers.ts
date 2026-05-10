import { http, HttpResponse } from 'msw'

import type {
  ApplicationDetail,
  ApplicationStatus,
  ApplicationSummary,
  CVParseResponse,
  CostSummary,
  CrawlStatus,
  FeedItem,
  GenerationStatus,
  InterviewQuestionBundle,
  JobAction,
  JobActionStatus,
  MaterialView,
  MaterialsBundle,
  PracticeAttempt,
  ProfileResponse,
  ProviderDetectionResult,
  TestProviderResult,
} from '@/lib/types'

const BACKEND = 'http://localhost:8765'

// ----- in-memory state per test --------------------------------------------
// Tests can mutate via `setMockState({...})` to drive specific scenarios.
// `resetMockState()` is called by handlers in beforeEach (test/setup.ts).

interface ApplicationRow {
  id: number
  job_id: number
  title: string
  company: string | null
  location: string | null
  url: string | null
  status: ApplicationStatus
  applied_at: string | null
  notes: string | null
  materials: MaterialsBundle
}

interface MockState {
  detect: ProviderDetectionResult
  testProvider: TestProviderResult
  profile: ProfileResponse | null
  cvParse: CVParseResponse
  feed: FeedItem[]
  crawl: CrawlStatus | null
  applications: ApplicationRow[]
  generationByTask: Record<string, GenerationStatus>
  interviewQuestions: Record<number, InterviewQuestionBundle>
  practiceAttempts: Record<number, PracticeAttempt[]>
  cost: CostSummary
  generationCallCount: Record<number, number>
}

const defaultState = (): MockState => ({
  detect: {
    anthropic_api: { key_in_env: false, key_in_keychain: false },
    claude_code: { detected: false, path: null, version: null },
    ollama: { detected: false, models: [] },
  },
  testProvider: { ok: true, latency_ms: 12, error: null, error_kind: null },
  profile: null,
  feed: [],
  crawl: null,
  applications: [],
  generationByTask: {},
  interviewQuestions: {},
  practiceAttempts: {},
  cost: {
    provider: 'mock',
    label: 'unknown',
    today_usd: null,
    week_usd: null,
    calls_today: 0,
    calls_week: 0,
  },
  generationCallCount: {},
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

  http.get(`${BACKEND}/api/jobs/feed`, ({ request }) => {
    const url = new URL(request.url)
    const excludeStatus = url.searchParams.get('exclude_status')
    const minScore = Number(url.searchParams.get('min_score') ?? '0')
    const filtered = state.feed
      .filter((item) => item.score >= minScore)
      .filter((item) => {
        if (excludeStatus === null || excludeStatus === '') return true
        return item.status !== excludeStatus
      })
    return HttpResponse.json(filtered)
  }),

  http.post(`${BACKEND}/api/jobs/crawl`, () => {
    const next: CrawlStatus = {
      job_id: 'crawl-test',
      state: 'done',
      fetched: state.feed.length,
      total: state.feed.length,
      new: state.feed.length,
      duplicates: 0,
      scored: state.feed.length,
      error: null,
    }
    state = { ...state, crawl: next }
    return HttpResponse.json({ job_id: next.job_id })
  }),

  http.get(`${BACKEND}/api/jobs/crawl/status/:jobId`, () => {
    if (!state.crawl) {
      return HttpResponse.json({ detail: 'Unknown crawl job id.' }, { status: 404 })
    }
    return HttpResponse.json(state.crawl)
  }),

  http.post<{ jobId: string }>(`${BACKEND}/api/jobs/:jobId/action`, async ({ params, request }) => {
    const jobId = Number(params.jobId)
    const body = (await request.json()) as { action: JobAction }
    const statusMap: Record<JobAction, JobActionStatus> = {
      apply: 'applied',
      save: 'saved',
      skip: 'skipped',
    }
    const newStatus = statusMap[body.action]
    state = {
      ...state,
      feed: state.feed.map((item) =>
        item.job_id === jobId ? { ...item, status: newStatus } : item,
      ),
    }
    return HttpResponse.json({ job_id: jobId, status: newStatus })
  }),

  // ----- Phase 5 application generation ------------------------------------

  http.post<{ jobId: string }>(`${BACKEND}/api/applications/:jobId`, ({ params }) => {
    const jobId = Number(params.jobId)
    const feedItem = state.feed.find((item) => item.job_id === jobId)
    let row = state.applications.find((a) => a.job_id === jobId)
    if (!row) {
      row = {
        id: state.applications.length + 1,
        job_id: jobId,
        title: feedItem?.title ?? `Job ${jobId}`,
        company: feedItem?.company ?? `Company ${jobId}`,
        location: feedItem?.location ?? null,
        url: feedItem?.url ?? null,
        status: 'saved',
        applied_at: null,
        notes: null,
        materials: {
          application_id: state.applications.length + 1,
          company_brief: makeMaterial('company_brief', `# ${feedItem?.company ?? 'Mock'} brief`),
          cv_suggestions: makeMaterial(
            'cv_suggestions',
            '## CV tailoring\n\n- Emphasise FastAPI experience.',
          ),
          cover_letter: makeMaterial('cover_letter', 'Dear hiring team,\n\nI would love to apply.'),
        },
      }
      state = { ...state, applications: [...state.applications, row] }
    }
    const taskId = `task-${row.id}-${Date.now()}`
    const status: GenerationStatus = {
      task_id: taskId,
      application_id: row.id,
      state: 'done',
      company_brief: 'done',
      cv_suggestions: 'done',
      cover_letter: 'done',
      error: null,
    }
    state = {
      ...state,
      generationByTask: { ...state.generationByTask, [taskId]: status },
      generationCallCount: {
        ...state.generationCallCount,
        [jobId]: (state.generationCallCount[jobId] ?? 0) + 1,
      },
    }
    return HttpResponse.json({ application_id: row.id, task_id: taskId })
  }),

  http.get(`${BACKEND}/api/applications/:applicationId/generation/:taskId`, ({ params }) => {
    const status = state.generationByTask[String(params.taskId)]
    if (!status) {
      return HttpResponse.json({ detail: 'Unknown generation task.' }, { status: 404 })
    }
    return HttpResponse.json(status)
  }),

  http.get(`${BACKEND}/api/applications/:applicationId/materials`, ({ params }) => {
    const id = Number(params.applicationId)
    const row = state.applications.find((a) => a.id === id)
    if (!row) {
      return HttpResponse.json({ detail: 'Unknown application.' }, { status: 404 })
    }
    return HttpResponse.json(row.materials)
  }),

  http.put(
    `${BACKEND}/api/applications/:applicationId/materials/:materialType`,
    async ({ params, request }) => {
      const id = Number(params.applicationId)
      const type = String(params.materialType) as keyof Pick<
        MaterialsBundle,
        'company_brief' | 'cv_suggestions' | 'cover_letter'
      >
      const body = (await request.json()) as { content: string }
      const row = state.applications.find((a) => a.id === id)
      if (!row) {
        return HttpResponse.json({ detail: 'Unknown application.' }, { status: 404 })
      }
      const previous = row.materials[type]
      const updated: MaterialView = {
        type,
        content: body.content,
        source_meta: previous?.source_meta ?? null,
        created_at: new Date().toISOString(),
        edit_count: (previous?.edit_count ?? 0) + 1,
      }
      const newRow: ApplicationRow = {
        ...row,
        materials: { ...row.materials, [type]: updated },
      }
      state = {
        ...state,
        applications: state.applications.map((a) => (a.id === id ? newRow : a)),
      }
      return HttpResponse.json(updated)
    },
  ),

  http.post(
    `${BACKEND}/api/applications/:applicationId/materials/:materialType/regenerate`,
    ({ params }) => {
      const id = Number(params.applicationId)
      const type = String(params.materialType) as keyof Pick<
        MaterialsBundle,
        'company_brief' | 'cv_suggestions' | 'cover_letter'
      >
      const row = state.applications.find((a) => a.id === id)
      if (!row) {
        return HttpResponse.json({ detail: 'Unknown application.' }, { status: 404 })
      }
      const fresh: MaterialView = {
        type,
        content: `Regenerated ${type} for ${row.company ?? 'Company'}.`,
        source_meta: null,
        created_at: new Date().toISOString(),
        edit_count: 0,
      }
      const newRow: ApplicationRow = {
        ...row,
        materials: { ...row.materials, [type]: fresh },
      }
      state = {
        ...state,
        applications: state.applications.map((a) => (a.id === id ? newRow : a)),
      }
      return HttpResponse.json(fresh)
    },
  ),

  http.get(`${BACKEND}/api/applications`, ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    const filtered = status
      ? state.applications.filter((a) => a.status === status)
      : state.applications
    const summaries: ApplicationSummary[] = filtered.map((a) => ({
      id: a.id,
      job_id: a.job_id,
      title: a.title,
      company: a.company,
      location: a.location,
      url: a.url,
      status: a.status,
      applied_at: a.applied_at,
      notes: a.notes,
    }))
    return HttpResponse.json(summaries)
  }),

  http.get(`${BACKEND}/api/applications/:applicationId`, ({ params }) => {
    const id = Number(params.applicationId)
    const row = state.applications.find((a) => a.id === id)
    if (!row) {
      return HttpResponse.json({ detail: 'Unknown application.' }, { status: 404 })
    }
    const detail: ApplicationDetail = {
      id: row.id,
      status: row.status,
      applied_at: row.applied_at,
      notes: row.notes,
      job: {
        title: row.title,
        company: row.company,
        location: row.location,
        url: row.url,
        description: 'Build APIs.',
      },
      materials: row.materials,
    }
    return HttpResponse.json(detail)
  }),

  http.put(`${BACKEND}/api/applications/:applicationId/status`, async ({ params, request }) => {
    const id = Number(params.applicationId)
    const body = (await request.json()) as { status: ApplicationStatus; notes: string | null }
    const row = state.applications.find((a) => a.id === id)
    if (!row) {
      return HttpResponse.json({ detail: 'Unknown application.' }, { status: 404 })
    }
    const updated: ApplicationRow = {
      ...row,
      status: body.status,
      notes: body.notes ?? row.notes,
      applied_at:
        body.status === 'applied' && row.applied_at === null
          ? new Date().toISOString()
          : row.applied_at,
    }
    state = {
      ...state,
      applications: state.applications.map((a) => (a.id === id ? updated : a)),
    }
    return HttpResponse.json({
      id: updated.id,
      job_id: updated.job_id,
      title: updated.title,
      company: updated.company,
      location: updated.location,
      url: updated.url,
      status: updated.status,
      applied_at: updated.applied_at,
      notes: updated.notes,
    })
  }),

  http.get(`${BACKEND}/api/applications/:applicationId/interview/questions`, ({ params }) => {
    const id = Number(params.applicationId)
    const cached = state.interviewQuestions[id]
    if (cached) return HttpResponse.json(cached)
    const bundle: InterviewQuestionBundle = {
      application_id: id,
      questions: [
        {
          category: 'behavioral',
          question: 'Tell me about a tough debugging session.',
          what_theyre_assessing: 'Problem solving',
          difficulty: 'standard',
        },
        {
          category: 'technical',
          question: 'How would you design an idempotent endpoint?',
          what_theyre_assessing: 'API design',
          difficulty: 'standard',
        },
      ],
      role_context: 'Build Python APIs.',
    }
    state = {
      ...state,
      interviewQuestions: { ...state.interviewQuestions, [id]: bundle },
    }
    return HttpResponse.json(bundle)
  }),

  http.post(
    `${BACKEND}/api/applications/:applicationId/interview/practice`,
    async ({ params, request }) => {
      const id = Number(params.applicationId)
      const body = (await request.json()) as {
        question: string
        category: string | null
        answer: string
      }
      const attempt: PracticeAttempt = {
        id: Date.now(),
        question: body.question,
        category: body.category,
        answer: body.answer,
        feedback: {
          what_worked: ['Clear structure'],
          what_to_improve: [{ issue: 'Could be more specific', fix: 'Add a metric.' }],
          sample_stronger_answer: 'Stronger version stub.',
          off_topic: false,
        },
        created_at: new Date().toISOString(),
      }
      const list = state.practiceAttempts[id] ?? []
      state = {
        ...state,
        practiceAttempts: { ...state.practiceAttempts, [id]: [attempt, ...list] },
      }
      return HttpResponse.json(attempt)
    },
  ),

  http.get(`${BACKEND}/api/applications/:applicationId/interview/attempts`, ({ params }) => {
    const id = Number(params.applicationId)
    return HttpResponse.json(state.practiceAttempts[id] ?? [])
  }),

  http.get(`${BACKEND}/api/stats/cost`, () => HttpResponse.json(state.cost)),
]

function makeMaterial(type: MaterialView['type'], content: string): MaterialView {
  return {
    type,
    content,
    source_meta: null,
    created_at: new Date().toISOString(),
    edit_count: 0,
  }
}
