from pydantic import BaseModel


class ExperienceInsight(BaseModel):
    problems_solved: list[str] = []
    workflows_built: list[str] = []
    business_functions: list[str] = []
    stakeholders_served: list[str] = []
    domain_expertise: list[str] = []
    ai_systems_built: list[str] = []
    transferable_experience: list[str] = []


class CompanyMeta(BaseModel):
    industry: str | None = None
    stage: str | None = None
    headcount: int | None = None
    founded: int | None = None
    headquarters: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    description: str | None = None
    business_model: str | None = None
    domain: str | None = None
    customer_type: str | None = None
    company_size: str | None = None
    tags: list[str] = []
    total_funding_usd: int | None = None
    last_round_type: str | None = None
    last_round_amount_usd: int | None = None
    last_round_date: int | None = None
    key_investors: list[str] = []
    founders: list[str] = []
    ceo: str | None = None


class CompiledExperience(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    months: int | None = None
    is_current: bool = False
    location: str | None = None
    description: list[str] = []
    tech_stack: list[str] = []           # kept as tech_stack for _write_tx compatibility
    linkedin_title: str | None = None
    linkedin_start_date: str | None = None
    linkedin_job_skills: list[str] = []
    source: str = "resume"               # "resume" | "linkedin" | "merged"
    company_meta: CompanyMeta | None = None
    insights: ExperienceInsight | None = None


class CompiledEducation(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    ranking_tier: str = "other"
    source: str = "resume"               # "resume" | "linkedin" | "merged"


class ProjectInsight(BaseModel):
    category: str | None = None             # "web app" | "CLI tool" | "ML model" | "API / SDK" | "library" | "data pipeline" | "browser extension" | "mobile app" | "other"
    domain: str | None = None               # HR Tech | FinTech | EdTech | DevTools | HealthTech | etc.
    use_case: str | None = None             # one sentence: what it does and for whom
    problem_solved: str | None = None       # specific pain point addressed
    customer_type: str | None = None        # "developers" | "consumers" | "enterprise" | "internal tooling" | "students" | "other"
    similar_companies: list[str] = []       # real companies building in the same space, max 3
    transferable_job_relevance: list[str] = []  # job roles/functions this signals


class CompiledProject(BaseModel):
    name: str
    description: str = ""
    tech_stack: list[str] = []
    url: str | None = None
    github_url: str | None = None
    source: str = "resume"
    insights: ProjectInsight | None = None


class MergedProfile(BaseModel):
    """Output of Call 1 — experience + education matched and merged from resume + LinkedIn."""
    experience: list[CompiledExperience]
    education: list[CompiledEducation]


class CompiledProfile(BaseModel):
    """Final output — company_meta validated, insights enriched per experience and project."""
    experience: list[CompiledExperience]
    education: list[CompiledEducation]
    projects: list[CompiledProject] = []
