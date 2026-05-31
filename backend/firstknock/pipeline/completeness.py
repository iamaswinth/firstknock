from __future__ import annotations


def calculate_completeness(
    extracted_json: dict,
    enriched_json: dict | None,
) -> dict:
    identity = extracted_json.get("identity", {})
    experience = extracted_json.get("experience", [])
    projects = extracted_json.get("projects", [])
    skills_raw = extracted_json.get("skills", {})
    education = extracted_json.get("education", [])
    enriched = enriched_json or {}

    skill_count = sum(
        len(v) for v in skills_raw.values() if isinstance(v, list)
    )

    sections = [
        _score_identity(identity),
        _score_experience(experience),
        _score_skills(skill_count),
        _score_projects(projects),
        _score_education(education),
        _score_enrichment(identity, enriched),
    ]

    total_score = sum(s["score"] for s in sections)
    total_max = sum(s["max"] for s in sections)
    overall = round(total_score / total_max * 100) if total_max else 0

    enrichment_status = {
        "github": bool(enriched.get("github_data")),
        "linkedin": bool(enriched.get("linkedin_data")),
        "company": bool(enriched.get("company_data")),
        "institution": bool(enriched.get("institution_data")),
    }

    top_suggestion = _pick_suggestion(identity, enriched, skill_count, projects)

    return {
        "overall_score": overall,
        "label": f"{overall}% complete",
        "top_suggestion": top_suggestion,
        "sections": sections,
        "enrichment_status": enrichment_status,
    }


# ── Section scorers ────────────────────────────────────────────────────────────

def _score_identity(identity: dict) -> dict:
    score = 0
    missing = []

    if identity.get("name"):
        score += 5
    else:
        missing.append("name")

    if identity.get("headline"):
        score += 5
    else:
        missing.append("headline")

    if identity.get("location"):
        score += 3
    else:
        missing.append("location")

    if identity.get("linkedin_url"):
        score += 4
    else:
        missing.append("linkedin_url")

    if identity.get("github_url"):
        score += 3
    else:
        missing.append("github_url")

    return _section("Identity", score, 20, missing,
                    "Add a headline, location, and social links to complete your identity.")


def _score_experience(experience: list) -> dict:
    MAX = 25
    score = 0
    missing = []

    if not experience:
        missing.extend(["jobs", "dates", "tech_stack", "description"])
        return _section("Experience", 0, MAX, missing,
                        "Add at least one work experience entry.")

    score += 10

    has_dates = any(e.get("start_date") for e in experience)
    if has_dates:
        score += 5
    else:
        missing.append("start_date on jobs")

    has_stack = any(e.get("tech_stack") for e in experience)
    if has_stack:
        score += 5
    else:
        missing.append("tech_stack on jobs")

    has_desc = any(e.get("description") for e in experience)
    if has_desc:
        score += 5
    else:
        missing.append("description bullets on jobs")

    return _section("Experience", score, MAX, missing,
                    "Add tech stacks and bullet points to each role." if missing else None)


def _score_skills(skill_count: int) -> dict:
    MAX = 20
    if skill_count >= 30:
        score = 20
    elif skill_count >= 20:
        score = 15
    elif skill_count >= 10:
        score = 10
    elif skill_count >= 1:
        score = 5
    else:
        score = 0

    missing = [] if score == MAX else [f"more skills (have {skill_count}, aim for 30+)"]
    return _section("Skills", score, MAX, missing,
                    "Add more skills to your resume to improve match accuracy." if score < MAX else None)


def _score_projects(projects: list) -> dict:
    MAX = 15
    score = 0
    missing = []

    if not projects:
        missing.extend(["projects", "github_urls", "descriptions"])
        return _section("Projects", 0, MAX, missing,
                        "Add at least one project to showcase your work.")

    score += 5

    has_github = any(p.get("github_url") for p in projects)
    if has_github:
        score += 5
    else:
        missing.append("github_url on projects")

    has_desc = any(p.get("description") for p in projects)
    if has_desc:
        score += 5
    else:
        missing.append("description on projects")

    return _section("Projects", score, MAX, missing,
                    "Add GitHub URLs and descriptions to your projects." if missing else None)


def _score_education(education: list) -> dict:
    MAX = 10
    score = 0
    missing = []

    if not education:
        missing.extend(["institution", "degree", "years"])
        return _section("Education", 0, MAX, missing,
                        "Add your education history.")

    score += 4
    edu = education[0]

    if edu.get("degree") and edu.get("field"):
        score += 4
    else:
        missing.append("degree and field")

    if edu.get("start_year") or edu.get("end_year"):
        score += 2
    else:
        missing.append("graduation year")

    return _section("Education", score, MAX, missing,
                    "Complete your education entry with degree, field, and years." if missing else None)


def _score_enrichment(identity: dict, enriched: dict) -> dict:
    MAX = 10
    score = 0
    missing = []

    if enriched.get("github_data"):
        score += 5
    else:
        missing.append("GitHub enrichment")

    if enriched.get("linkedin_data"):
        score += 5
    else:
        missing.append("LinkedIn enrichment")

    has_gh_url = bool(identity.get("github_url"))
    has_li_url = bool(identity.get("linkedin_url"))
    suggestion = None
    if not has_gh_url and not has_li_url:
        suggestion = "Add LinkedIn and GitHub URLs to enable automatic enrichment."
    elif not has_gh_url:
        suggestion = "Add your GitHub URL to enable repo enrichment."
    elif not has_li_url:
        suggestion = "Add your LinkedIn URL to enable career enrichment."
    elif missing:
        suggestion = "Re-ingest your resume to trigger pending enrichment."

    return _section("Enrichment", score, MAX, missing, suggestion)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(name: str, score: int, max_: int, missing: list[str], suggestion: str | None) -> dict:
    pct = round(score / max_ * 100) if max_ else 0
    return {"name": name, "score": score, "max": max_, "pct": pct,
            "missing": missing, "suggestion": suggestion}


def _pick_suggestion(identity: dict, enriched: dict, skill_count: int, projects: list) -> str:
    if not identity.get("linkedin_url"):
        return "Add your LinkedIn URL to unlock enriched job matching"
    if not identity.get("github_url"):
        return "Link your GitHub to showcase real projects"
    if not enriched.get("linkedin_data"):
        return "LinkedIn enrichment pending — re-ingest to refresh"
    if not enriched.get("github_data"):
        return "GitHub enrichment pending — re-ingest to refresh"
    if skill_count < 10:
        return "List more skills on your resume to improve match accuracy"
    if not projects:
        return "Add projects to highlight your practical experience"
    if not identity.get("headline"):
        return "Add a professional headline to stand out"
    return "Your profile looks great!"
