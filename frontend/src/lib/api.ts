import type {
  ApplicationDetail,
  ApplicationStatus,
  ApplicationSummary,
  CVParseResponse,
  CostSummary,
  CrawlRequest,
  CrawlResponse,
  CrawlStatus,
  FeedItem,
  GenerationStatus,
  InterviewQuestionBundle,
  JobAction,
  JobActionStatus,
  MaterialType,
  MaterialView,
  MaterialsBundle,
  PracticeAttempt,
  ProfileResponse,
  ProfileUpdate,
  ProviderDetectionResult,
  ProviderId,
  ProviderMetadata,
  ProviderStats,
  SelectProviderResponse,
  StartGenerationResponse,
  TestProviderResult,
} from './types'

export const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? 'http://localhost:8765'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BACKEND_URL}${path}`
  let response: Response
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        ...(init?.body && !(init.body instanceof FormData)
          ? { 'Content-Type': 'application/json' }
          : {}),
        ...(init?.headers ?? {}),
      },
    })
  } catch (err) {
    // A network-level failure ("Failed to fetch") is opaque on its own.
    // The v0.1.0 packaged Windows build hit this because the webview's
    // origin (`http://tauri.localhost`) wasn't in the backend CORS
    // allowlist. Embed the live origin + target URL in the message so
    // the AppGate error screen is itself a diagnostic — readable from a
    // screenshot, no devtools needed.
    const origin = typeof window !== 'undefined' ? window.location.origin : '<no window>'
    const reason = err instanceof Error ? err.message : String(err)
    console.error('[api] fetch failed', { url, origin, reason })
    throw new ApiError(0, `Network request failed (origin ${origin} → ${url}): ${reason}`, err)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? (payload as { detail: unknown }).detail
        : payload
    const message =
      typeof detail === 'string'
        ? detail
        : `${response.status} ${response.statusText || 'Request failed'}`
    throw new ApiError(response.status, message, detail)
  }

  return payload as T
}

export const api = {
  detectProviders: (): Promise<ProviderDetectionResult> =>
    request('/api/setup/detect-providers', { method: 'POST' }),

  listProviders: (): Promise<ProviderMetadata[]> => request('/api/setup/providers'),

  testProvider: (
    provider: ProviderId,
    apiKey?: string | null,
    model?: string | null,
  ): Promise<TestProviderResult> =>
    request('/api/setup/test-provider', {
      method: 'POST',
      body: JSON.stringify({
        provider,
        api_key: apiKey ?? null,
        model: model ?? null,
      }),
    }),

  selectProvider: (
    provider: ProviderId,
    apiKey?: string | null,
    model?: string | null,
  ): Promise<SelectProviderResponse> =>
    request('/api/setup/select-provider', {
      method: 'POST',
      body: JSON.stringify({
        provider,
        api_key: apiKey ?? null,
        model: model ?? null,
      }),
    }),

  getProviderStats: (): Promise<ProviderStats> => request('/api/stats/provider'),

  postCvText: (cvText: string): Promise<CVParseResponse> =>
    request('/api/profile/cv', {
      method: 'POST',
      body: JSON.stringify({ cv_text: cvText }),
    }),

  postCvUpload: (file: File): Promise<CVParseResponse> => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/profile/cv/upload', { method: 'POST', body: form })
  },

  getProfile: (): Promise<ProfileResponse | null> =>
    request<ProfileResponse>('/api/profile').catch((err) => {
      if (err instanceof ApiError && err.status === 404) return null
      throw err
    }),

  updateProfile: (payload: ProfileUpdate): Promise<ProfileResponse> =>
    request('/api/profile', { method: 'POST', body: JSON.stringify(payload) }),

  deleteAllData: (): Promise<{ deleted: boolean }> =>
    request('/api/data/all', { method: 'DELETE' }),

  triggerCrawl: (payload: CrawlRequest): Promise<CrawlResponse> =>
    request('/api/jobs/crawl', { method: 'POST', body: JSON.stringify(payload) }),

  getCrawlStatus: (jobId: string): Promise<CrawlStatus> =>
    request(`/api/jobs/crawl/status/${jobId}`),

  getFeed: (
    options: { limit?: number; minScore?: number; excludeStatus?: string | null } = {},
  ): Promise<FeedItem[]> => {
    const params = new URLSearchParams()
    if (options.limit !== undefined) params.set('limit', String(options.limit))
    if (options.minScore !== undefined) params.set('min_score', String(options.minScore))
    if (options.excludeStatus !== undefined && options.excludeStatus !== null) {
      params.set('exclude_status', options.excludeStatus)
    } else if (options.excludeStatus === null) {
      params.set('exclude_status', '')
    }
    const qs = params.toString()
    return request(`/api/jobs/feed${qs ? `?${qs}` : ''}`)
  },

  postJobAction: (
    jobId: number,
    action: JobAction,
  ): Promise<{ job_id: number; status: JobActionStatus }> =>
    request(`/api/jobs/${jobId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  startGeneration: (jobId: number): Promise<StartGenerationResponse> =>
    request(`/api/applications/${jobId}`, { method: 'POST' }),

  getGenerationStatus: (applicationId: number, taskId: string): Promise<GenerationStatus> =>
    request(`/api/applications/${applicationId}/generation/${taskId}`),

  getMaterials: (applicationId: number): Promise<MaterialsBundle> =>
    request(`/api/applications/${applicationId}/materials`),

  saveMaterial: (
    applicationId: number,
    type: MaterialType,
    content: string,
  ): Promise<MaterialView> =>
    request(`/api/applications/${applicationId}/materials/${type}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),

  regenerateMaterial: (applicationId: number, type: MaterialType): Promise<MaterialView> =>
    request(`/api/applications/${applicationId}/materials/${type}/regenerate`, {
      method: 'POST',
    }),

  listApplications: (status?: ApplicationStatus): Promise<ApplicationSummary[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return request(`/api/applications${qs}`)
  },

  getApplication: (applicationId: number): Promise<ApplicationDetail> =>
    request(`/api/applications/${applicationId}`),

  updateApplicationStatus: (
    applicationId: number,
    status: ApplicationStatus,
    notes?: string | null,
  ): Promise<ApplicationSummary> =>
    request(`/api/applications/${applicationId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status, notes: notes ?? null }),
    }),

  getInterviewQuestions: (
    applicationId: number,
    options: { refresh?: boolean } = {},
  ): Promise<InterviewQuestionBundle> => {
    const qs = options.refresh ? '?refresh=true' : ''
    return request(`/api/applications/${applicationId}/interview/questions${qs}`)
  },

  submitPracticeAnswer: (
    applicationId: number,
    payload: { question: string; category: string | null; answer: string },
  ): Promise<PracticeAttempt> =>
    request(`/api/applications/${applicationId}/interview/practice`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listPracticeAttempts: (applicationId: number): Promise<PracticeAttempt[]> =>
    request(`/api/applications/${applicationId}/interview/attempts`),

  getCostSummary: (): Promise<CostSummary> => request('/api/stats/cost'),
}
