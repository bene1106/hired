// Mirror of the backend Pydantic shapes. Keep these in sync with
// backend/api/routes/*.py and backend/services/provider_*.py.

export type ProviderId = 'mock' | 'anthropic_api' | 'claude_code' | 'ollama'

export interface AnthropicDetection {
  key_in_env: boolean
  key_in_keychain: boolean
}

export interface ClaudeCodeDetection {
  detected: boolean
  path: string | null
  version: string | null
}

export interface OllamaDetection {
  detected: boolean
  models: string[]
}

export interface ProviderDetectionResult {
  anthropic_api: AnthropicDetection
  claude_code: ClaudeCodeDetection
  ollama: OllamaDetection
}

export type TestProviderErrorKind =
  | 'missing_api_key'
  | 'auth_failed'
  | 'rate_limited'
  | 'network_error'
  | 'bad_response'
  | 'unknown'
  | 'unsupported_provider'

export interface TestProviderResult {
  ok: boolean
  latency_ms: number
  error: string | null
  error_kind: TestProviderErrorKind | null
}

export interface CVParsedJson {
  name?: string | null
  email?: string | null
  phone?: string | null
  location?: string | null
  summary?: string | null
  work_experience?: Array<{
    title?: string | null
    company?: string | null
    location?: string | null
    start_date?: string | null
    end_date?: string | null
    duration_months?: number | null
    summary?: string | null
  }>
  education?: Array<{
    institution?: string
    degree?: string | null
    field?: string | null
    start_year?: number | null
    end_year?: number | null
  }>
  skills?: string[]
  languages?: Array<{ language?: string; proficiency?: string | null }>
  certifications?: Array<{ name?: string; issuer?: string | null; year?: number | null }>
}

export interface ProfileResponse {
  id: number
  name: string | null
  email: string | null
  target_roles: string[]
  target_locations: string[]
  target_salary_min: number | null
  priorities: string[]
  cv_text: string | null
  cv_parsed_json: CVParsedJson | null
  profile_version: number
}

export interface CVParseResponse {
  parsed: CVParsedJson
  profile: ProfileResponse
}

export interface ProfileUpdate {
  name?: string | null
  email?: string | null
  target_roles?: string[]
  target_locations?: string[]
  target_salary_min?: number | null
  priorities?: string[]
}

// ----- Phase 4 feed --------------------------------------------------------

export type CrawlSource = 'manual_url' | 'linkedin'

export type CrawlState = 'queued' | 'running' | 'done' | 'error'

export interface CrawlRequest {
  source: CrawlSource
  urls?: string[]
  max_jobs?: number
}

export interface CrawlResponse {
  job_id: string
}

export interface CrawlStatus {
  job_id: string
  state: CrawlState
  fetched: number
  total: number
  new: number
  duplicates: number
  scored: number
  error: string | null
}

export type JobActionStatus = 'applied' | 'saved' | 'skipped'

export type JobAction = 'apply' | 'save' | 'skip'

export interface FeedItem {
  job_id: number
  title: string
  company: string | null
  location: string | null
  remote_policy: string | null
  url: string | null
  score: number
  rationale: string
  matched_skills: string[]
  missing_skills: string[]
  red_flags: string[]
  status: JobActionStatus | null
}
