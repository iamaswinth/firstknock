// All API response types for FirstKnock backend

export interface IngestResponse {
  resume_id: string
  user_id: string
  status: string
  stages_complete: string[]
  stages_pending: string[]
}

export interface ResumeStatusResponse {
  resume_id: string
  user_id: string
  status: "extracted" | "enriched" | "ingested"
  graph_built: boolean
  ingested_at: string
  updated_at: string
  identity: {
    name: string
    email: string | null
    phone: string | null
    location: string | null
    headline: string | null
    github_url: string | null
    linkedin_url: string | null
  }
  experience: ExperienceEntry[]
  projects: ProjectEntry[]
  skills: {
    languages: string[]
    frameworks: string[]
    ai_ml: string[]
    databases: string[]
    devops: string[]
    other: string[]
  }
  education: EducationEntry[]
  certifications: string[]
  enriched: EnrichedData | null
}

export interface ExperienceEntry {
  company: string
  title: string
  location: string | null
  start_date: string | null
  end_date: string | null
  is_current: boolean
  months: number | null
  description: string[]
  tech_stack: string[]
}

export interface ProjectEntry {
  name: string
  description: string
  tech_stack: string[]
  url: string | null
  github_url: string | null
}

export interface EducationEntry {
  institution: string
  degree: string
  field: string
  start_year: string | null
  end_year: string | null
}

export interface EnrichedData {
  github?: {
    profile: { followers: number; public_repos: number; bio: string }
    pinned_repos: PinnedRepo[]
  }
  companies: Record<string, CompanyData>
  institutions: Record<string, { ranking_tier: string }>
}

export interface PinnedRepo {
  name: string
  stars: number
  forks: number
  primary_language: string
  topics: string[]
  readme_summary: string
  extracted_skills: string[]
  is_new: boolean
}

export interface CompanyData {
  stage: string | null
  industry: string | null
  headcount: number | null
  founded: number | null
  headquarters: string | null
  website?: string | null
  total_funding_usd?: number | null
  last_round_type?: string | null
  last_round_amount_usd?: number | null
  business_model?: string | null
  key_investors?: string[] | null
  founders?: string[] | null
  ceo?: string | null
}

export interface ProfileResponse {
  user_id: string
  name: string
  email: string
  headline: string | null
  github_url: string | null
  linkedin_url: string | null
  location: string | null
  seniority: "junior" | "mid" | "senior" | "staff" | null
  total_experience_months: number | null
  github_followers: number | null
  public_repos: number | null
  profile_picture_url: string | null
  experience: ExperienceEntry[]
  projects: ProjectEntry[]
  education: EducationEntry[]
  skills_summary: {
    explicit_count: number
    inferred_count: number
    total: number
  }
}

export interface SkillItem {
  name: string
  category: string
  source: "explicit" | "inferred" | "graph_algo"
  confidence: number
  inferred_by: string | null
  reason: string | null
}

export interface SkillsResponse {
  user_id: string
  explicit: SkillItem[]
  inferred: SkillItem[]
  total: number
}

export interface GraphNode {
  id: string
  name: string
  type: "Person" | "Skill" | "Company" | "Project" | "Institution"
  val: number
  community_id: number | null
  confidence: number | null
  source_type: "explicit" | "inferred" | "graph_algo" | null
  properties: Record<string, unknown>
}

export interface GraphLink {
  source: string
  target: string
  type: string
  confidence: number | null
  source_type: string | null
  co_occurrence: number | null
  properties: Record<string, unknown>
}

export interface GraphCommunity {
  id: number
  name: string
  color: string
  skills: string[]
}

export interface GraphResponse {
  nodes: GraphNode[]
  links: GraphLink[]
  communities: GraphCommunity[]
}

export interface CareerEntry {
  company: string
  title: string
  start_date: string | null
  end_date: string | null
  months: number | null
  is_current: boolean
}

export interface BridgeSkill {
  name: string
  centrality: number
  category: string | null
}

export interface InferredSkillDetail {
  name: string
  category: string
  source: string
  confidence: number
  inferred_by: string | null
  reason: string | null
}

export interface SkillCommunity {
  id: number
  name: string
  skills: string[]
}

export interface AnalyticsResponse {
  user_id: string
  seniority: string | null
  total_experience_months: number | null
  career_timeline: CareerEntry[]
  skill_communities: SkillCommunity[] | null
  bridge_skills: BridgeSkill[] | null
  inferred_skills: InferredSkillDetail[]
}

export interface RoleMatch {
  title: string
  reason: string
}

export interface RoleFitResponse {
  user_id: string
  roles: RoleMatch[]
}

export interface CompletenessSection {
  name: string
  score: number
  max: number
  pct: number
  missing: string[]
  suggestion: string | null
}

export interface ProfileCompletenessResponse {
  user_id: string
  overall_score: number
  label: string
  top_suggestion: string
  sections: CompletenessSection[]
  enrichment_status: {
    github: boolean
    linkedin: boolean
    company: boolean
    institution: boolean
  }
}

// ── Career Timeline ───────────────────────────────────────────────────────────

export interface CompanyDetail {
  name: string
  industry: string | null
  stage: string | null
  headcount: number | null
  founded: number | null
  headquarters: string | null
  website: string | null
  total_funding_usd: number | null
  last_round_type: string | null
  last_round_amount_usd: number | null
  key_investors: string[]
  founders: string[]
  ceo: string | null
}

export interface TimelineEvent {
  id: string
  type: "experience" | "education"
  label: string
  entity: string
  start_date: string | null
  end_date: string | null
  months: number | null
  is_current: boolean
  tech_stack: string[]
  field: string | null
  company_detail: CompanyDetail | null
}

export interface CareerTimelineResponse {
  user_id: string
  total_experience_months: number | null
  events: TimelineEvent[]
}

export interface DeleteResumeResponse {
  resume_id: string
  user_id: string
  deleted: boolean
}
