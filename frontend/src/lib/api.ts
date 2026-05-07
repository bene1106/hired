import type {
  CVParseResponse,
  ProfileResponse,
  ProfileUpdate,
  ProviderDetectionResult,
  ProviderId,
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
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...(init?.headers ?? {}),
    },
  })

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

  testProvider: (provider: ProviderId, apiKey?: string): Promise<TestProviderResult> =>
    request('/api/setup/test-provider', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey ?? null }),
    }),

  selectProvider: (provider: ProviderId, apiKey?: string): Promise<{ provider: string }> =>
    request('/api/setup/select-provider', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey ?? null }),
    }),

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
}
