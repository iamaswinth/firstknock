from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class IngestResponse(BaseModel):
    resume_id: str
    user_id: str
    status: str
    stages_complete: list[str]
    stages_pending: list[str]


class DeleteResumeResponse(BaseModel):
    resume_id: str
    user_id: str
    deleted: bool


# ── Health ────────────────────────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    name: str
    status: str            # "ok" | "error"
    latency_ms: float | None = None
    detail: str | None = None


class DeepHealthResponse(BaseModel):
    overall: str           # "ok" | "degraded" | "error"
    services: list[ServiceStatus]


# ── Resume / Profile ──────────────────────────────────────────────────────────

class ResumeStatusResponse(BaseModel):
    resume_id: str
    user_id: str
    status: str
    graph_built: bool
    ingested_at: str
    updated_at: str
    identity: dict
    experience: list[dict]
    projects: list[dict]
    skills: dict
    education: list[dict]
    certifications: list[str]
    enriched: dict | None = None


class ProfileResponse(BaseModel):
    user_id: str
    name: str
    email: str
    headline: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    seniority: str | None = None
    total_experience_months: int | None = None
    github_followers: int | None = None
    public_repos: int | None = None
    profile_picture_url: str | None = None
    experience: list[dict]
    projects: list[dict]
    education: list[dict]
    skills_summary: dict   # {explicit_count, inferred_count, total}


class CompletenessSection(BaseModel):
    name: str
    score: int
    max: int
    pct: int
    missing: list[str]
    suggestion: str | None = None


class ProfileCompletenessResponse(BaseModel):
    user_id: str
    overall_score: int
    label: str
    top_suggestion: str
    sections: list[CompletenessSection]
    enrichment_status: dict[str, bool]


# ── Role fit ─────────────────────────────────────────────────────────────────

class RoleMatch(BaseModel):
    title: str
    reason: str


class RoleFitResponse(BaseModel):
    user_id: str
    roles: list[RoleMatch]


# ── Skills ────────────────────────────────────────────────────────────────────

class SkillItem(BaseModel):
    name: str
    category: str
    source: str            # "explicit" | "inferred" | "graph_algo"
    confidence: float
    inferred_by: str | None = None
    reason: str | None = None


class SkillsResponse(BaseModel):
    user_id: str
    explicit: list[SkillItem]
    inferred: list[SkillItem]
    total: int


# ── Graph visualization (react-force-graph format) ────────────────────────────

class GraphNode(BaseModel):
    id: str
    name: str
    type: str              # "Person" | "Skill" | "Company" | "Project" | "Institution"
    val: float = 5.0       # node size — mapped from confidence
    community_id: int | None = None
    confidence: float | None = None
    source_type: str | None = None
    properties: dict = {}


class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    confidence: float | None = None
    source_type: str | None = None
    co_occurrence: int | None = None
    properties: dict = {}


class GraphCommunity(BaseModel):
    id: int
    name: str
    color: str
    skills: list[str]


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]
    communities: list[GraphCommunity]


# ── Analytics ─────────────────────────────────────────────────────────────────

class CareerEntry(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    months: int | None = None
    is_current: bool = False


class BridgeSkill(BaseModel):
    name: str
    centrality: float
    category: str | None = None


class InferredSkillDetail(BaseModel):
    name: str
    category: str
    source: str
    confidence: float
    inferred_by: str | None = None
    reason: str | None = None


class SkillCommunity(BaseModel):
    id: int
    name: str
    skills: list[str]


class AnalyticsResponse(BaseModel):
    user_id: str
    seniority: str | None = None
    total_experience_months: int | None = None
    career_timeline: list[CareerEntry]
    skill_communities: list[SkillCommunity] | None = None
    bridge_skills: list[BridgeSkill] | None = None
    inferred_skills: list[InferredSkillDetail]


# ── Career Timeline (dedicated endpoint) ──────────────────────────────────────

class CompanyDetail(BaseModel):
    name: str
    industry: str | None = None
    stage: str | None = None
    headcount: int | None = None
    founded: int | None = None
    headquarters: str | None = None
    website: str | None = None
    total_funding_usd: float | None = None
    last_round_type: str | None = None
    last_round_amount_usd: float | None = None
    key_investors: list[str] = []
    founders: list[str] = []
    ceo: str | None = None


class TimelineEvent(BaseModel):
    id: str
    type: Literal["experience", "education"]
    label: str
    entity: str
    start_date: str | None = None
    end_date: str | None = None
    months: int | None = None
    is_current: bool = False
    tech_stack: list[str] = []
    field: str | None = None
    company_detail: CompanyDetail | None = None


class CareerTimelineResponse(BaseModel):
    user_id: str
    total_experience_months: int | None = None
    events: list[TimelineEvent]
