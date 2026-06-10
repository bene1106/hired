import type {
  ApplicationDetail,
  ApplicationStatus,
  ApplicationSummary,
  CVParseResponse,
  ChatStreamEvent,
  CostSummary,
  CrawlRequest,
  CrawlResponse,
  CrawlStatus,
  CreateSourcePayload,
  JobSourceConfig,
  FeedItem,
  GenerationStatus,
  InterviewQuestionBundle,
  InterviewSessionDetail,
  InterviewSessionSummary,
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
  RescoreResult,
  ScoringStatus,
  SelectProviderResponse,
  SourceConfig,
  StartGenerationResponse,
  TestProviderResult,
  UpdateSourcePayload,
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

  /**
   * Pull the backend's ``error_kind`` discriminator off a structured error
   * body, if present. Used for 401 ``missing_api_key`` routing — the
   * frontend redirects the user to Settings → Switch Provider instead of
   * a generic "Backend not reachable" wall.
   */
  get errorKind(): string | null {
    if (typeof this.detail === 'object' && this.detail !== null && 'error_kind' in this.detail) {
      const kind = (this.detail as { error_kind: unknown }).error_kind
      return typeof kind === 'string' ? kind : null
    }
    return null
  }
}

// v0.3.5: subscriber pattern for "global" auth failures. The fetch
// wrapper notifies listeners when a 401 lands with
// ``error_kind="missing_api_key"`` so AppShell can show a top-of-app
// banner without each caller having to handle it.
type GlobalAuthErrorListener = (err: ApiError) => void
const authErrorListeners = new Set<GlobalAuthErrorListener>()

export function onGlobalAuthError(fn: GlobalAuthErrorListener): () => void {
  authErrorListeners.add(fn)
  return () => {
    authErrorListeners.delete(fn)
  }
}

// Test-only: replay the dispatch shape so unit tests for AppShell can
// verify the banner without going through a real fetch + MSW response.
// Production callers go through the ``request()`` 401 branch below.
export function __test_dispatchAuthError(err: ApiError): void {
  authErrorListeners.forEach((fn) => fn(err))
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
    // Pass the whole structured payload (not just `detail`) so consumers
    // can read sibling fields like `error_kind`. The bare-string `detail`
    // is still the human-facing message.
    const apiError = new ApiError(response.status, message, payload)
    if (response.status === 401 && apiError.errorKind === 'missing_api_key') {
      authErrorListeners.forEach((fn) => fn(apiError))
    }
    throw apiError
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

  updateModel: (model: string): Promise<{ model: string }> =>
    request('/api/setup/model', { method: 'PUT', body: JSON.stringify({ model }) }),

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

  getScoringStatus: (): Promise<ScoringStatus> => request('/api/jobs/scoring-status'),

  rescoreJobs: (): Promise<RescoreResult> => request('/api/jobs/rescore', { method: 'POST' }),

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

  createInterviewSession: (applicationId: number): Promise<InterviewSessionDetail> =>
    request(`/api/applications/${applicationId}/interview/sessions`, { method: 'POST' }),

  listInterviewSessions: (applicationId: number): Promise<InterviewSessionSummary[]> =>
    request(`/api/applications/${applicationId}/interview/sessions`),

  getInterviewSession: (
    applicationId: number,
    sessionId: number,
  ): Promise<InterviewSessionDetail> =>
    request(`/api/applications/${applicationId}/interview/sessions/${sessionId}`),

  deleteInterviewSession: (applicationId: number, sessionId: number): Promise<void> =>
    request(`/api/applications/${applicationId}/interview/sessions/${sessionId}`, {
      method: 'DELETE',
    }),

  /**
   * Stream the coach's reply for one user message.
   *
   * Yields parsed SSE events (`chunk` / `done` / `error`) in arrival order.
   * Consumers should:
   *   - append each `chunk.chunk` to the currently-rendering assistant bubble
   *   - stop and refresh the session detail when a `done` event arrives
   *   - surface `error` to the user; the user's own turn is already persisted
   *     server-side, so they can retry without losing their text
   *
   * Tauri WebView2: this uses `fetch()` + `ReadableStream`, not the
   * `EventSource` API. EventSource is read-only and we need to send a POST
   * body, plus Tauri's webview has historically been quirky with
   * EventSource. fetch-streaming is the well-trodden path.
   */
  chatStream: async function* (
    applicationId: number,
    sessionId: number,
    content: string,
    init?: { signal?: AbortSignal },
  ): AsyncGenerator<ChatStreamEvent, void, void> {
    const url = `${BACKEND_URL}/api/applications/${applicationId}/interview/sessions/${sessionId}/messages`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
      signal: init?.signal,
    })
    if (!response.ok) {
      const text = await response.text().catch(() => '')
      throw new ApiError(
        response.status,
        text || `Chat stream rejected with ${response.status}`,
        text,
      )
    }
    if (response.body === null) {
      throw new ApiError(0, 'Chat stream had no body (Tauri webview misconfigured?).')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // SSE frames are separated by a blank line ("\n\n"). Pull each
        // complete frame off the front of the buffer; the rest stays
        // until the next read.
        let separator = buffer.indexOf('\n\n')
        while (separator !== -1) {
          const frame = buffer.slice(0, separator)
          buffer = buffer.slice(separator + 2)
          const event = parseSseFrame(frame)
          if (event !== null) yield event
          separator = buffer.indexOf('\n\n')
        }
      }
    } finally {
      reader.releaseLock()
    }
  },

  getCostSummary: (): Promise<CostSummary> => request('/api/stats/cost'),

  // ----- Job sources -------------------------------------------------------

  listSources: (): Promise<JobSourceConfig[]> => request('/api/sources'),

  createSource: (payload: CreateSourcePayload): Promise<JobSourceConfig> =>
    request('/api/sources', { method: 'POST', body: JSON.stringify(payload) }),

  updateSource: (id: number, payload: UpdateSourcePayload): Promise<JobSourceConfig> =>
    request(`/api/sources/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),

  deleteSource: (id: number): Promise<void> => request(`/api/sources/${id}`, { method: 'DELETE' }),

  runSourceNow: (id: number): Promise<{ started: number[] }> =>
    request(`/api/sources/${id}/run-now`, { method: 'POST' }),

  runAllSourcesNow: (): Promise<{ started: number[] }> =>
    request('/api/sources/run-now', { method: 'POST' }),

  getSourceConfig: (): Promise<SourceConfig> => request('/api/sources/config'),

  updateSourceConfig: (payload: SourceConfig): Promise<SourceConfig> =>
    request('/api/sources/config', { method: 'PUT', body: JSON.stringify(payload) }),
}

function parseSseFrame(frame: string): ChatStreamEvent | null {
  for (const line of frame.split('\n')) {
    if (!line.startsWith('data: ')) continue
    const payload = line.slice('data: '.length)
    try {
      const parsed: unknown = JSON.parse(payload)
      if (isChatStreamEvent(parsed)) return parsed
    } catch {
      // ignore malformed payload — the next frame may still be valid
    }
  }
  return null
}

function isChatStreamEvent(value: unknown): value is ChatStreamEvent {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  if (typeof v.chunk === 'string') return true
  if (v.done === true && typeof v.session_id === 'number') return true
  if (typeof v.error === 'string') return true
  return false
}
