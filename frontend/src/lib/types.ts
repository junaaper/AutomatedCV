// Mirrors the backend's Pydantic models.

export interface User {
  id: string
  email: string
  is_demo: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: User
}

export interface Cv {
  id: string
  filename: string | null
  content: string
  chunk_count: number
  created_at: string
}

export interface Evidence {
  chunk_id: string
  content: string
  similarity: number
}

export type Verdict = 'match' | 'partial' | 'missing'

export interface Job {
  title: string
  company: string
  location: string | null
  seniority: 'intern' | 'junior' | 'mid' | 'senior' | 'lead' | 'unknown'
  must_have: string[]
  nice_to_have: string[]
  summary: string
}

export interface AssessedRequirement {
  requirement: string
  kind: 'must' | 'nice'
  verdict: Verdict
  evidence: string | null
  evidence_verified: boolean
  reasoning: string
}

export interface Fit {
  score: number
  requirements: AssessedRequirement[]
  strengths: string[]
  gaps: string[]
}

export interface Review {
  job: Job
  fit: Fit
  evidence: Record<string, Evidence[]>
  cover_letter: string
  revisions: number
  can_revise: boolean
}

export type RunStatus = 'running' | 'awaiting_review' | 'completed' | 'rejected' | 'failed'

export interface RunSummary {
  id: string
  status: RunStatus
  title: string | null
  company: string | null
  error: string | null
  created_at: string
  updated_at: string
  retryable: boolean
}

export interface RunDetail extends RunSummary {
  state: {
    job: Job | null
    evidence: Record<string, Evidence[]> | null
    fit: Fit | null
    cover_letter: string | null
    revisions: number | null
    application_id: string | null
  }
  review: Review | null
}

export type AgentNode =
  | 'extract_requirements'
  | 'retrieve_evidence'
  | 'score_fit'
  | 'draft_cover_letter'
  | 'human_review'
  | 'save_application'

export type RunEvent =
  | { event: 'run'; data: { run_id: string } }
  | { event: 'step'; data: { node: AgentNode } & Record<string, unknown> }
  | { event: 'review'; data: Review }
  | { event: 'done'; data: { status: RunStatus; application_id?: string } }
  | { event: 'error'; data: { message: string; retryable: boolean } }

export type ResumeAction =
  | { action: 'approve' }
  | { action: 'edit'; cover_letter: string }
  | { action: 'revise'; feedback: string }
  | { action: 'reject' }

export interface SamplePosting {
  id: string
  title: string
  company: string
  blurb: string
  posting: string
}

export type ApplicationStatus = 'saved' | 'applied' | 'interviewing' | 'offer' | 'rejected'

export interface ApplicationSummary {
  id: string
  run_id: string | null
  title: string
  company: string
  fit_score: number
  status: ApplicationStatus
  created_at: string
  updated_at: string
}

export interface ApplicationDetail extends ApplicationSummary {
  posting: string
  requirements: Job
  fit: Fit
  cover_letter: string
  notes: string | null
}
