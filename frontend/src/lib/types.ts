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

// ----- Phase 5 applications, interview prep, cost --------------------------

export type ApplicationStatus = 'saved' | 'applied' | 'skipped' | 'interview' | 'offer' | 'rejected'

export type MaterialType = 'company_brief' | 'cv_suggestions' | 'cover_letter'

export type StepState = 'pending' | 'running' | 'done' | 'error' | 'cached'

export type GenerationState = 'queued' | 'running' | 'done' | 'error'

export interface StartGenerationResponse {
  application_id: number
  task_id: string
}

export interface GenerationStatus {
  task_id: string
  application_id: number
  state: GenerationState
  company_brief: StepState
  cv_suggestions: StepState
  cover_letter: StepState
  error: string | null
}

export interface MaterialView {
  type: MaterialType
  content: string
  source_meta: Record<string, unknown> | null
  created_at: string
  edit_count: number
}

export interface MaterialsBundle {
  application_id: number
  company_brief: MaterialView | null
  cv_suggestions: MaterialView | null
  cover_letter: MaterialView | null
}

export interface ApplicationSummary {
  id: number
  job_id: number
  title: string
  company: string | null
  location: string | null
  url: string | null
  status: ApplicationStatus
  applied_at: string | null
  notes: string | null
}

export interface ApplicationDetail {
  id: number
  job: {
    title?: string
    company?: string | null
    location?: string | null
    remote_policy?: string | null
    salary_range?: string | null
    description?: string | null
    url?: string | null
    posted_at?: string | null
  }
  status: ApplicationStatus
  applied_at: string | null
  notes: string | null
  materials: MaterialsBundle
}

export interface InterviewQuestion {
  category: string
  question: string
  what_theyre_assessing: string | null
  difficulty: string | null
}

export interface InterviewQuestionBundle {
  application_id: number
  questions: InterviewQuestion[]
  role_context: string | null
}

export interface ImprovementNote {
  issue: string
  fix: string
}

export interface PracticeFeedback {
  what_worked: string[]
  what_to_improve: ImprovementNote[]
  sample_stronger_answer: string
  off_topic: boolean
}

export interface PracticeAttempt {
  id: number
  question: string
  category: string | null
  answer: string
  feedback: PracticeFeedback
  created_at: string
}

export type CostLabel = 'priced' | 'subscription' | 'local' | 'unknown'

export interface CostSummary {
  provider: ProviderId
  label: CostLabel
  today_usd: number | null
  week_usd: number | null
  calls_today: number
  calls_week: number
}
