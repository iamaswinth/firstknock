import json
import re
import uuid
import structlog
import anthropic

from firstknock.config import settings
from firstknock.pipeline.compilation.schemas import (
    MergedProfile,
    CompiledProfile,
    CompiledExperience,
    ExperienceInsight,
    CompiledProject,
    ProjectInsight,
)

logger = structlog.get_logger()

_HAIKU_MODEL = settings.inference_model  # claude-haiku-4-5-20251001

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


# ── Tool schemas for structured output ───────────────────────────────────────

_MERGED_PROFILE_TOOL = {
    "name": "submit_merged_profile",
    "description": "Submit the matched and merged experience and education profile.",
    "input_schema": {
        "type": "object",
        "properties": {
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company":              {"type": "string"},
                        "title":                {"type": "string"},
                        "start_date":           {"type": ["string", "null"]},
                        "end_date":             {"type": ["string", "null"]},
                        "months":               {"type": ["integer", "null"]},
                        "is_current":           {"type": "boolean"},
                        "location":             {"type": ["string", "null"]},
                        "description":          {"type": "array", "items": {"type": "string"}},
                        "tech_stack":           {"type": "array", "items": {"type": "string"}},
                        "linkedin_title":       {"type": ["string", "null"]},
                        "linkedin_start_date":  {"type": ["string", "null"]},
                        "linkedin_job_skills":  {"type": "array", "items": {"type": "string"}},
                        "source":               {"type": "string", "enum": ["resume", "linkedin", "merged"]},
                    },
                    "required": ["company", "title", "source"],
                },
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution":   {"type": "string"},
                        "degree":        {"type": ["string", "null"]},
                        "field":         {"type": ["string", "null"]},
                        "start_year":    {"type": ["integer", "null"]},
                        "end_year":      {"type": ["integer", "null"]},
                        "ranking_tier":  {"type": "string"},
                        "source":        {"type": "string", "enum": ["resume", "linkedin", "merged"]},
                    },
                    "required": ["institution", "degree", "field", "source"],
                },
            },
        },
        "required": ["experience", "education"],
    },
}

_COMPILED_PROFILE_TOOL = {
    "name": "submit_compiled_profile",
    "description": "Submit the final compiled profile with validated company metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company":              {"type": "string"},
                        "title":                {"type": "string"},
                        "start_date":           {"type": ["string", "null"]},
                        "end_date":             {"type": ["string", "null"]},
                        "months":               {"type": ["integer", "null"]},
                        "is_current":           {"type": "boolean"},
                        "location":             {"type": ["string", "null"]},
                        "description":          {"type": "array", "items": {"type": "string"}},
                        "tech_stack":           {"type": "array", "items": {"type": "string"}},
                        "linkedin_title":       {"type": ["string", "null"]},
                        "linkedin_start_date":  {"type": ["string", "null"]},
                        "linkedin_job_skills":  {"type": "array", "items": {"type": "string"}},
                        "source":               {"type": "string"},
                        "company_meta": {
                            "oneOf": [
                                {"type": "null"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "industry":             {"type": ["string", "null"]},
                                        "stage":                {"type": ["string", "null"]},
                                        "headcount":            {"type": ["integer", "null"]},
                                        "founded":              {"type": ["integer", "null"]},
                                        "headquarters":         {"type": ["string", "null"]},
                                        "website":              {"type": ["string", "null"]},
                                        "linkedin_url":         {"type": ["string", "null"]},
                                        "description":          {"type": ["string", "null"]},
                                        "business_model":       {"type": ["string", "null"]},
                                        "total_funding_usd":    {"type": ["integer", "null"]},
                                        "last_round_type":      {"type": ["string", "null"]},
                                        "last_round_amount_usd":{"type": ["integer", "null"]},
                                        "last_round_date":      {"type": ["integer", "null"]},
                                        "key_investors":        {"type": "array", "items": {"type": "string"}},
                                        "founders":             {"type": "array", "items": {"type": "string"}},
                                        "ceo":                  {"type": ["string", "null"]},
                                    },
                                },
                            ]
                        },
                    },
                    "required": ["company", "title", "source"],
                },
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution":  {"type": "string"},
                        "degree":       {"type": ["string", "null"]},
                        "field":        {"type": ["string", "null"]},
                        "start_year":   {"type": ["integer", "null"]},
                        "end_year":     {"type": ["integer", "null"]},
                        "ranking_tier": {"type": "string"},
                        "source":       {"type": "string"},
                    },
                    "required": ["institution", "degree", "field", "source"],
                },
            },
        },
        "required": ["experience", "education"],
    },
}


# ── Call 1: Match & Merge ─────────────────────────────────────────────────────

async def _merge_experience_education(extracted: dict, enriched: dict) -> MergedProfile:
    linkedin = enriched.get("linkedin", {})
    institution_tiers = enriched.get("institutions", {})

    payload = {
        "resume_experience":  extracted.get("experience", []),
        "linkedin_experience": linkedin.get("experience", []),
        "resume_education":   extracted.get("education", []),
        "linkedin_education": linkedin.get("education", []),
        "institution_tiers":  institution_tiers,
    }

    system_prompt = (
        "You are a data reconciliation engine. You receive resume data and LinkedIn data "
        "for the same person from two different sources and must produce one clean merged profile."
    )

    user_prompt = (
        "Match and merge the following resume and LinkedIn data for the same person.\n\n"
        "DATE FORMAT RULE:\n"
        "- All dates in the output MUST be YYYY-MM. Convert any text date "
        "('Jun 2020' → '2020-06', 'Mar 2020' → '2020-03'). "
        "Year-only → YYYY-01. Null means unknown or currently ongoing.\n\n"
        "EXPERIENCE RULES:\n"
        "1. COMPANY MATCHING: Match LinkedIn and resume entries for the same company using "
        "semantic similarity — legal suffixes, country variants, and abbreviations are the same "
        "company (e.g. 'Acme Corp India Private Limited' = 'Acme Corp'). "
        "Always use the resume's company name for the merged entry.\n\n"
        "2. INTERNSHIP TITLES: If a LinkedIn entry has employment_type 'Internship' and the "
        "title does not already contain 'Intern' or 'Internship', append ' Intern' to the title "
        "('Software Engineer' + Internship → 'Software Engineer Intern').\n\n"
        "3. SINGLE-ROLE (company appears once in LinkedIn): Merge with the matching resume entry. "
        "Prefer the resume's start_date/end_date (cleaner format). "
        "Carry over linkedin_title, linkedin_start_date, linkedin_job_skills. Source='merged'. "
        "Resume entry with no LinkedIn match: source='resume'. "
        "LinkedIn entry with no resume match: source='linkedin', use LinkedIn dates.\n\n"
        "4. MULTI-ROLE — CRITICAL (company appears multiple times in LinkedIn, e.g. promotion or "
        "internship then full-time):\n"
        "  a) Output ONE entry PER LinkedIn role — never collapse multiple roles into one.\n"
        "  b) Use EACH LinkedIn entry's own start_date/end_date — never the resume's combined dates.\n"
        "  c) Find the ONE LinkedIn entry with the most date overlap with the resume entry. "
        "Copy resume description and tech_stack into that entry only (source='merged'). "
        "All other LinkedIn entries at the same company: source='linkedin', empty description/tech_stack.\n"
        "  EXAMPLE — Company X intern Jan 2022–Jun 2022, then full-time Jun 2022–Jun 2024. "
        "Resume shows Company X Jan 2022–Jun 2024. Full-time has 24-month overlap (wins). Correct output:\n"
        "    {company:'Company X', start:'2022-01', end:'2022-06', source:'linkedin', description:[], tech_stack:[]}\n"
        "    {company:'Company X', start:'2022-06', end:'2024-06', source:'merged', description:[...resume...]}\n"
        "  WRONG (never do this): collapsing into one entry, or using the resume's start date for "
        "the intern entry — that creates a start_date collision and loses the separate role.\n\n"
        "EDUCATION RULES:\n"
        "- Match by institution name (use semantic matching — abbreviations and full names are the same) "
        "and overlapping years.\n"
        "- Merged pair: resume is the base; backfill missing years from LinkedIn. Source='merged'.\n"
        "- Add ranking_tier from institution_tiers (default 'other' if not found).\n"
        "- LinkedIn-only education: source='linkedin'.\n"
        "- Resume-only education: source='resume'.\n\n"
        f"DATA:\n{json.dumps(payload, default=str)}\n\n"
        "Call submit_merged_profile with the result."
    )

    client = _get_client()
    response = await client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=4096,
        system=system_prompt,
        tools=[_MERGED_PROFILE_TOOL],
        tool_choice={"type": "tool", "name": "submit_merged_profile"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_merged_profile":
            return MergedProfile.model_validate(block.input)

    raise ValueError("No tool_use block in merge response")


# ── Call 2: Company Validation ────────────────────────────────────────────────

async def _validate_companies(merged: MergedProfile, enriched: dict) -> CompiledProfile:
    company_enrichment = enriched.get("companies", {})

    if not company_enrichment:
        # Nothing to validate — return as-is with all company_meta null
        return CompiledProfile(experience=merged.experience, education=merged.education)

    payload = {
        "merged_experience": [e.model_dump() for e in merged.experience],
        "company_enrichment": company_enrichment,
    }

    system_prompt = (
        "You are a data quality validator. You check whether web-sourced company data "
        "actually describes the company a person worked at, or a different company with a similar name."
    )

    user_prompt = (
        "Your ONLY job is to set company_meta on each experience entry. "
        "DO NOT modify any other field — copy every other field exactly as provided.\n\n"
        "VALIDATION RULES:\n"
        "1. Use the person's role, location, and description for that entry as ground truth.\n\n"
        "2. KEEP the enrichment (set company_meta) when the Perplexity data is consistent with "
        "the experience entry: same or closely related industry, same country/region, and a "
        "plausible company size for the role described.\n\n"
        "3. DISCARD the enrichment (company_meta: null) when any of these mismatches exist:\n"
        "   - INDUSTRY MISMATCH: The role/description describes a completely different business "
        "than the enrichment (e.g. role is at a logistics startup but enrichment describes a "
        "healthcare SaaS company with the same name).\n"
        "   - LOCATION MISMATCH: The person's work location for that role is in a different "
        "country or distant region from the enrichment headquarters "
        "(e.g. role in Germany but enrichment HQ is Australia).\n"
        "   - SCALE MISMATCH: The role context implies a very small or personal company "
        "(founder/owner, no description, early-stage) but the enrichment shows a large funded "
        "company — they are likely different companies sharing a name.\n\n"
        "4. If a company has no enrichment data at all, set company_meta: null.\n\n"
        "5. CRITICAL — copy all other fields byte-for-byte: do not change title, start_date, "
        "end_date, months, is_current, location, description, tech_stack, source, or any field "
        "other than company_meta.\n\n"
        f"DATA:\n{json.dumps(payload, default=str)}\n\n"
        "Call submit_compiled_profile with the result. Education must be passed unchanged: "
        f"{json.dumps([e.model_dump() for e in merged.education], default=str)}"
    )

    client = _get_client()
    response = await client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=4096,
        system=system_prompt,
        tools=[_COMPILED_PROFILE_TOOL],
        tool_choice={"type": "tool", "name": "submit_compiled_profile"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_compiled_profile":
            return CompiledProfile.model_validate(block.input)

    raise ValueError("No tool_use block in validation response")


# ── Call 3: Experience Insight Enrichment ────────────────────────────────────

_INSIGHT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "company":                 {"type": "string"},
        "title":                   {"type": "string"},
        "problems_solved":         {"type": "array", "items": {"type": "string"}},
        "workflows_built":         {"type": "array", "items": {"type": "string"}},
        "business_functions":      {"type": "array", "items": {"type": "string"}},
        "stakeholders_served":     {"type": "array", "items": {"type": "string"}},
        "domain_expertise":        {"type": "array", "items": {"type": "string"}},
        "ai_systems_built":        {"type": "array", "items": {"type": "string"}},
        "transferable_experience": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["company", "title"],
}

_EXPERIENCE_INSIGHTS_TOOL = {
    "name": "submit_experience_insights",
    "description": "Submit semantic insights for each work experience entry.",
    "input_schema": {
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": _INSIGHT_ITEM_SCHEMA,
            }
        },
        "required": ["insights"],
    },
}

_INSIGHT_SYSTEM = (
    "You are a career intelligence engine. You read work experience entries and extract "
    "deep semantic understanding of what the person actually did — not just the tech they used."
)

_INSIGHT_RULES = """For each experience entry, analyze the title, description bullets, and tech stack together.
Extract only what is clearly evidenced by the text. Use short, specific phrases (5-12 words). Do not pad with generics.

FIELDS — fill each only when the evidence is present:

problems_solved      — concrete problems or pain points the person addressed
                       e.g. "reduced API latency from 800ms to 120ms", "eliminated manual invoice reconciliation"

workflows_built      — end-to-end pipelines, automation chains, or repeatable processes they created
                       e.g. "CI/CD pipeline from GitHub Actions to ECS", "ETL pipeline ingesting 50M rows/day"

business_functions   — company functions the work touched (sales, ops, finance, customer success, marketing, etc.)
                       e.g. "customer onboarding automation", "revenue attribution reporting"

stakeholders_served  — who consumed or benefited from their output
                       e.g. "enterprise sales reps", "data science team", "end consumers via mobile app"

domain_expertise     — knowledge of a specific domain or industry the role built
                       e.g. "real-time payments processing", "clinical trial data management", "ad bidding systems"

ai_systems_built     — any AI, ML, NLP, LLM, or data-science systems they built or owned
                       e.g. "fine-tuned BERT for document classification", "RAG pipeline over internal knowledge base"
                       Leave empty if no AI/ML work is evidenced.

transferable_experience — skills or experience that transfer to different industries or roles
                       e.g. "owning API product from spec to launch", "leading a cross-functional squad of 8"

RULES:
- If the description is empty or too vague, output empty arrays — do NOT invent content.
- Do not re-list tech stack items as insights (React, TypeScript are not insights).
- Each item should be a statement about impact, scope, or outcome — not a job duty."""


async def _enrich_experience_insights(compiled: CompiledProfile) -> CompiledProfile:
    """Call 3 — semantic insight extraction for each experience entry."""
    experiences_with_content = [
        e for e in compiled.experience
        if e.description or e.tech_stack
    ]
    if not experiences_with_content:
        return compiled

    payload = [
        {
            "index": i,
            "company": e.company,
            "title": e.title,
            "description": e.description,
            "tech_stack": e.tech_stack,
            "linkedin_job_skills": e.linkedin_job_skills,
        }
        for i, e in enumerate(compiled.experience)
    ]

    user_prompt = (
        f"{_INSIGHT_RULES}\n\n"
        f"EXPERIENCE ENTRIES (process all {len(payload)}):\n"
        f"{json.dumps(payload, default=str)}\n\n"
        "Call submit_experience_insights with one insight object per entry, "
        "in the same order as the input array."
    )

    client = _get_client()
    response = await client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=4096,
        system=_INSIGHT_SYSTEM,
        tools=[_EXPERIENCE_INSIGHTS_TOOL],
        tool_choice={"type": "tool", "name": "submit_experience_insights"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_experience_insights":
            raw_insights: list[dict] = block.input.get("insights", [])
            for i, insight_dict in enumerate(raw_insights):
                if i < len(compiled.experience):
                    compiled.experience[i].insights = ExperienceInsight(
                        problems_solved=insight_dict.get("problems_solved") or [],
                        workflows_built=insight_dict.get("workflows_built") or [],
                        business_functions=insight_dict.get("business_functions") or [],
                        stakeholders_served=insight_dict.get("stakeholders_served") or [],
                        domain_expertise=insight_dict.get("domain_expertise") or [],
                        ai_systems_built=insight_dict.get("ai_systems_built") or [],
                        transferable_experience=insight_dict.get("transferable_experience") or [],
                    )
            return compiled

    return compiled


# ── Call 4: Project Insight Enrichment ───────────────────────────────────────

_PROJECT_INSIGHT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name":                       {"type": "string"},
        "category":                   {"type": ["string", "null"]},
        "domain":                     {"type": ["string", "null"]},
        "use_case":                   {"type": ["string", "null"]},
        "problem_solved":             {"type": ["string", "null"]},
        "customer_type":              {"type": ["string", "null"]},
        "similar_companies":          {"type": "array", "items": {"type": "string"}},
        "transferable_job_relevance": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name"],
}

_PROJECT_INSIGHTS_TOOL = {
    "name": "submit_project_insights",
    "description": "Submit semantic insights for each project entry.",
    "input_schema": {
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": _PROJECT_INSIGHT_ITEM_SCHEMA,
            }
        },
        "required": ["insights"],
    },
}

_PROJECT_INSIGHT_SYSTEM = (
    "You are a career intelligence engine. You analyze personal projects and extract structured "
    "intelligence about what the project does, who it's for, and what it signals professionally."
)

_PROJECT_INSIGHT_RULES = """For each project, analyze the name, description, and tech stack together.
Only extract what is evidenced by the text. Use short, specific phrases. Do not pad with generics.

FIELDS:

category     — classify the project type — one of:
               web app | CLI tool | ML model | API / SDK | library | data pipeline | browser extension | mobile app | other

domain       — specific vertical from: HR Tech | FinTech | EdTech | DevTools | HealthTech | LegalTech |
               ClimateTech | AdTech | MarTech | E-commerce | Logistics | Cybersecurity | Data & Analytics |
               Gaming | Media & Entertainment | other — or null if general-purpose / no clear vertical

use_case     — one sentence: "A [what] for [who] that [does what]"
               e.g. "A CLI tool for developers that scaffolds production-ready FastAPI projects"
               null if the description provides no basis for this.

problem_solved — the specific pain point or gap this addresses
               e.g. "Manual SQL query building in Python without type safety"
               null if not evident from description.

customer_type — primary audience — one of: developers | consumers | enterprise | internal tooling | students | other

similar_companies — real companies/products building in the same space, max 3, only when the comparison is genuinely apt
               e.g. ["Stripe", "Braintree"] for a payment integration project
               Empty array if no clear parallel.

transferable_job_relevance — job roles or domains this project signals to a recruiter, 2-5 items
               e.g. ["backend engineering", "ML infra", "fintech payments"]
               Be specific: "ML engineering" not "engineering"

RULES:
- category and customer_type must be one of the exact strings listed.
- If description is empty or < 10 words, output null for all string fields and empty arrays.
- Do NOT re-list tech stack items as insights.
- similar_companies must be real, well-known products — never fabricate."""


async def _enrich_project_insights(compiled: CompiledProfile, extracted: dict) -> CompiledProfile:
    """Call 4 — semantic insight extraction for each project."""
    raw_projects = extracted.get("projects") or []
    if not raw_projects:
        return compiled

    payload = [
        {
            "index": i,
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "tech_stack": p.get("tech_stack") or [],
        }
        for i, p in enumerate(raw_projects)
    ]

    user_prompt = (
        f"{_PROJECT_INSIGHT_RULES}\n\n"
        f"PROJECT ENTRIES (process all {len(payload)}):\n"
        f"{json.dumps(payload, default=str)}\n\n"
        "Call submit_project_insights with one insight object per entry, in the same order as the input array."
    )

    client = _get_client()
    response = await client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=2048,
        system=_PROJECT_INSIGHT_SYSTEM,
        tools=[_PROJECT_INSIGHTS_TOOL],
        tool_choice={"type": "tool", "name": "submit_project_insights"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    insight_map: dict[int, ProjectInsight] = {}
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_project_insights":
            for i, raw in enumerate(block.input.get("insights") or []):
                insight_map[i] = ProjectInsight(
                    category=raw.get("category") or None,
                    domain=raw.get("domain") or None,
                    use_case=raw.get("use_case") or None,
                    problem_solved=raw.get("problem_solved") or None,
                    customer_type=raw.get("customer_type") or None,
                    similar_companies=raw.get("similar_companies") or [],
                    transferable_job_relevance=raw.get("transferable_job_relevance") or [],
                )

    compiled.projects = [
        CompiledProject(
            name=p.get("name", ""),
            description=p.get("description", ""),
            tech_stack=p.get("tech_stack") or [],
            url=p.get("url"),
            github_url=p.get("github_url"),
            source="resume",
            insights=insight_map.get(i),
        )
        for i, p in enumerate(raw_projects)
    ]
    return compiled


# ── Internship title post-processing ─────────────────────────────────────────

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _month_text_to_ym(text: str | None) -> str | None:
    """Convert 'Mar 2020' -> '2020-03'. Returns None if unparseable."""
    if not text:
        return None
    m = re.match(r'(\w{3})\w*\s+(\d{4})', text.strip(), re.IGNORECASE)
    if m:
        month_num = _MONTH_MAP.get(m.group(1).lower(), 0)
        if month_num:
            return f"{m.group(2)}-{month_num:02d}"
    return None


def _norm_co(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())


def _apply_intern_titles(merged: MergedProfile, enriched: dict) -> None:
    """Deterministically append ' Intern' to titles where employment_type is Internship.

    The LLM may miss this for entries involved in multi-role scenarios.
    This runs after Call 1 and reads employment_type directly from enriched_json.
    """
    # Build set of (normalised_company, YYYY-MM_start) that are internships
    intern_keys: set[tuple[str, str]] = set()
    for li_exp in enriched.get("linkedin", {}).get("experience", []):
        if (li_exp.get("employment_type") or "").lower() == "internship":
            co = _norm_co(li_exp.get("company") or "")
            sd = _month_text_to_ym(li_exp.get("start_date")) or ""
            if co:
                intern_keys.add((co, sd))

    for exp in merged.experience:
        co = _norm_co(exp.company)
        sd = exp.start_date or ""
        if len(co) < 4:
            continue
        # Use substring matching so "vertscendautomation" matches "vertscendautomationpvtltd"
        is_intern = any(
            (co in ik_co or ik_co in co) and sd == ik_sd
            for ik_co, ik_sd in intern_keys
            if len(ik_co) >= 4
        )
        if is_intern and "intern" not in (exp.title or "").lower():
            exp.title = f"{exp.title} Intern"


# ── Public entry point ────────────────────────────────────────────────────────

async def compile_profile(resume_id: uuid.UUID) -> CompiledProfile:
    """
    Three-call LLM compilation pipeline.

    Call 1 — Match & Merge: aligns resume experience/education with LinkedIn using
    semantic matching, producing one unified entry per role/degree.

    Call 2 — Company Validation: for each merged experience entry, checks whether
    the Perplexity enrichment data actually describes that company. Sets company_meta
    to null if data belongs to a different company with a similar name.

    Call 3 — Experience Insight Enrichment: semantic analysis of each role — what
    problems were solved, what was built, who was served, domain knowledge gained, etc.

    Call 4 — Project Insight Enrichment: category, domain, use case, problem solved,
    customer type, similar companies, and transferable job relevance per project.

    Falls back gracefully at each step if a call fails.
    """
    from firstknock.pipeline.persistence.postgres_writer import get_resume_by_id

    resume = await get_resume_by_id(resume_id)
    extracted = resume.extracted_json or {}
    enriched = resume.enriched_json or {}

    # ── Call 1: Match & Merge ─────────────────────────────────────────────────
    merged: MergedProfile | None = None
    try:
        merged = await _merge_experience_education(extracted, enriched)
        _apply_intern_titles(merged, enriched)
        logger.info(
            "compilation_call1_done",
            resume_id=str(resume_id),
            experience=len(merged.experience),
            education=len(merged.education),
        )
    except Exception as exc:
        logger.warning("compilation_call1_failed", resume_id=str(resume_id), error=str(exc))

    if merged is None:
        # Fallback: wrap raw extracted data as CompiledProfile with no LinkedIn enrichment
        fallback_exp = [
            CompiledExperience(
                company=e.get("company", ""),
                title=e.get("title", ""),
                start_date=e.get("start_date"),
                end_date=e.get("end_date"),
                months=e.get("months"),
                is_current=e.get("is_current", False),
                location=e.get("location"),
                description=e.get("description", []),
                tech_stack=e.get("tech_stack", []),
                source="resume",
            )
            for e in extracted.get("experience", [])
        ]
        return CompiledProfile(experience=fallback_exp, education=[])

    # ── Call 2: Company Validation ────────────────────────────────────────────
    compiled: CompiledProfile | None = None
    try:
        compiled = await _validate_companies(merged, enriched)
        logger.info("compilation_call2_done", resume_id=str(resume_id))
    except Exception as exc:
        logger.warning("compilation_call2_failed", resume_id=str(resume_id), error=str(exc))
        compiled = CompiledProfile(experience=merged.experience, education=merged.education)

    # ── Call 3: Experience Insight Enrichment ─────────────────────────────────
    try:
        compiled = await _enrich_experience_insights(compiled)
        logger.info("compilation_call3_done", resume_id=str(resume_id))
    except Exception as exc:
        logger.warning("compilation_call3_failed", resume_id=str(resume_id), error=str(exc))

    # ── Call 4: Project Insight Enrichment ────────────────────────────────────
    try:
        compiled = await _enrich_project_insights(compiled, extracted)
        logger.info("compilation_call4_done", resume_id=str(resume_id), projects=len(compiled.projects))
    except Exception as exc:
        logger.warning("compilation_call4_failed", resume_id=str(resume_id), error=str(exc))

    return compiled
