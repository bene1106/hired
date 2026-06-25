// Mirror of the backend Pydantic shapes. Keep these in sync with
// backend/api/routes/*.py and backend/services/provider_*.py.

export type ProviderId = 'mock' | 'anthropic_api' | 'claude_code' | 'codex_cli' | 'ollama'

export interface AnthropicDetection {
  key_in_env: boolean
  key_in_keychain: boolean
}

export interface ClaudeCodeDetection {
  detected: boolean
  path: string | null
  version: string | null
}

export interface CodexCliDetection {
  detected: boolean
  path: string | null
  version: string | null
  logged_in: boolean
}

export interface OllamaDetection {
  detected: boolean
  models: string[]
}

export interface ProviderDetectionResult {
  anthropic_api: AnthropicDetection
  claude_code: ClaudeCodeDetection
  codex_cli: CodexCliDetection
  ollama: OllamaDetection
}

export type TestProviderErrorKind =
  | 'missing_api_key'
  | 'auth_failed'
  | 'rate_limited'
  | 'network_error'
  | 'bad_response'
  | 'model_unavailable'
  | 'binary_missing'
  | 'unknown'
  | 'unsupported_provider'

export interface TestProviderResult {
  ok: boolean
  latency_ms: number
  error: string | null
  error_kind: TestProviderErrorKind | null
}

export interface ProviderMetadata {
  name: ProviderId
  label: string
  is_experimental: boolean
  requires_api_key: boolean
  default_model: string | null
}

export interface ProviderStats {
  provider: ProviderId
  model: string | null
  last_latency_ms: number | null
  last_success: boolean | null
  calls_today: number
  success_rate_today: number | null
  construct_ok: boolean
  construct_error: string | null
}

export interface ScoringStatus {
  jobs_total: number
  jobs_with_current_score: number
  rescore_candidate_count: number
  profile_version: number
}

export interface RescoreResult {
  rescored: number
  total_candidates: number
  capped: boolean
}

export interface SelectProviderResponse {
  provider: ProviderId
  model: string | null
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
  phone: string | null
  target_roles: string[]
  target_locations: string[]
  target_salary_min: number | null
  priorities: string[]
  skills: string[]
  work_formats: string[]
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
  phone?: string | null
  target_roles?: string[]
  target_locations?: string[]
  target_salary_min?: number | null
  priorities?: string[]
  skills?: string[]
  work_formats?: string[]
}

// ----- Job sources (scheduler) --------------------------------------------

export type CrawlSourceType = 'wellfound' | 'indeed' | 'remotive' | 'stepstone'

export interface JobSourceConfig {
  id: number
  source_type: CrawlSourceType
  company_slug: string | null
  label: string
  enabled: boolean
  last_checked_at: string | null
  last_error: string | null
  is_running: boolean
  crawl_phase: 'crawling' | 'scoring' | null
  created_at: string
}

export interface SourceConfig {
  interval_hours: number
}

export interface CreateSourcePayload {
  source_type: CrawlSourceType
  company_slug?: string | null
  label?: string
  enabled?: boolean
}

export interface UpdateSourcePayload {
  label?: string
  enabled?: boolean
  company_slug?: string
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
  phase: 'crawling' | 'scoring' | null
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
  unread: boolean
  feedback_signal: number | null
  feedback_reason: string | null
}

export type JobInteractAction = 'read' | 'thumbs_up' | 'thumbs_down' | 'remove_feedback'
export type JobInteractReason = 'company' | 'location' | 'tech_stack'

export interface JobInteractPayload {
  action: JobInteractAction
  reason?: JobInteractReason | null
}

export interface JobInteractResponse {
  job_id: number
  read_at: string | null
  feedback_signal: number | null
  feedback_reason: string | null
}

export interface InteractionHistoryItem {
  job_id: number
  title: string
  company: string | null
  location: string | null
  feedback_signal: number
  feedback_reason: string | null
  updated_at: string
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

// ----- Phase 8 interview chat (coach sessions) -----------------------------

export type ChatRole = 'user' | 'assistant'

export interface ChatTurn {
  role: ChatRole
  content: string
  created_at: string | null
}

export interface InterviewSessionSummary {
  id: number
  application_id: number
  created_at: string
  last_message_at: string | null
  turn_count: number
  preview: string | null
}

export interface InterviewSessionDetail {
  id: number
  application_id: number
  created_at: string
  messages: ChatTurn[]
}

/**
 * One event parsed off the SSE stream of
 * ``POST /api/applications/{id}/interview/sessions/{sid}/messages``.
 *
 *  - ``{ chunk }`` — append to the assistant bubble currently rendering
 *  - ``{ done }`` — stream finished cleanly, transcript persisted
 *  - ``{ error }`` — mid-stream provider failure, no assistant turn persisted
 */
export type ChatStreamEvent =
  | { chunk: string }
  | { done: true; session_id: number }
  | { error: string }

// ----- Mock interviews (M1: records + prepared questions) ------------------

export type InterviewType = 'hr' | 'technical' | 'behavioral' | 'system_design' | 'other'

export type InterviewerGender = 'male' | 'female' | 'unspecified'

export interface MockQuestion {
  category: string
  question: string
  rephrasing: string
  time_limit_seconds: number
  is_intro: boolean
}

export interface Interview {
  id: number
  application_id: number
  round_number: number
  interview_type: InterviewType
  duration_minutes: number
  interviewer_gender: InterviewerGender
  scheduled_at: string | null
  is_upcoming: boolean
  question_count: number
  questions: MockQuestion[] | null
}

export interface InterviewCreateRequest {
  round_number: number
  interview_type: InterviewType
  duration_minutes: number
  interviewer_gender?: InterviewerGender
  scheduled_at?: string | null
}

export type InterviewUpdateRequest = Partial<InterviewCreateRequest>

// ----- Mock interview runs (M2: timed runner + transcript) -----------------

export interface TranscriptItem {
  question: string
  answer: string
  skipped: boolean
  asked_rephrasing: boolean
}

export interface MockRunStartResponse {
  run_id: number
  status: string
  questions: MockQuestion[]
}

export interface MockRunSummary {
  id: number
  status: string
  started_at: string
  completed_at: string | null
  question_count: number
  has_evaluation: boolean
  overall_percentage: number | null
}

export interface MockAnswerRating {
  question: string
  rating: number
  comment: string
}

export interface MockEvaluation {
  per_question: MockAnswerRating[]
  overall_percentage: number
  strengths: string[]
  weaknesses: string[]
}

export interface MockRunDetail {
  id: number
  interview_id: number
  status: string
  voice_mode: boolean
  started_at: string
  completed_at: string | null
  transcript: TranscriptItem[]
  evaluation: MockEvaluation | null
}

// ----- Voice (M4) ----------------------------------------------------------

export type VoicePrepareState = 'idle' | 'downloading' | 'ready' | 'error'

export interface VoiceStatus {
  deps_available: boolean
  models_ready: boolean
  prepare_state: VoicePrepareState
  error: string | null
}
