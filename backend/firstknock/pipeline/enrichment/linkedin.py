import asyncio
import base64
import re
import structlog
import httpx
from pydantic import BaseModel
from firstknock.config import settings

logger = structlog.get_logger()

APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "harvestapi~linkedin-profile-scraper"


# ── Data models ───────────────────────────────────────────────────────────────

class LinkedInLocation(BaseModel):
    text: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    country_code: str | None = None


class LinkedInSkill(BaseModel):
    name: str
    endorsements: int = 0


class LinkedInExperience(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str = ""
    is_current: bool = False
    location: str | None = None
    employment_type: str | None = None
    workplace_type: str | None = None
    company_linkedin_url: str | None = None
    company_universal_name: str | None = None
    duration: str | None = None
    job_skills: list[str] = []


class LinkedInEducation(BaseModel):
    school_name: str
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    school_linkedin_url: str | None = None
    skills: list[str] = []


class LinkedInCertification(BaseModel):
    title: str
    issued_at: str | None = None
    issued_by: str | None = None


class LinkedInProject(BaseModel):
    title: str
    description: str = ""
    start_date: str | None = None
    end_date: str | None = None


class LinkedInVolunteering(BaseModel):
    role: str
    organization_name: str | None = None
    cause: str | None = None
    duration: str | None = None


class LinkedInCourse(BaseModel):
    title: str
    associated_with: str | None = None


class LinkedInPublication(BaseModel):
    title: str
    published_at: str | None = None
    link: str | None = None


class LinkedInHonor(BaseModel):
    title: str
    issued_by: str | None = None
    issued_at: str | None = None
    description: str = ""


class LinkedInLanguage(BaseModel):
    name: str
    proficiency: str | None = None


class LinkedInProfileData(BaseModel):
    # Identity
    linkedin_id: str | None = None
    public_identifier: str | None = None
    linkedin_url: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    # Headline / about
    headline: str | None = None
    summary: str | None = None
    # Location
    location: str | None = None
    location_parsed: LinkedInLocation | None = None
    # Social signals
    connections: int | None = None
    followers: int | None = None
    recommendations_count: int | None = None
    open_to_work: bool = False
    hiring: bool = False
    premium: bool = False
    verified: bool = False
    # Meta
    registered_at: str | None = None
    top_skills: str | None = None
    current_company: str | None = None
    profile_picture_url: str | None = None
    # Rich sections
    skills: list[LinkedInSkill] = []
    experience: list[LinkedInExperience] = []
    education: list[LinkedInEducation] = []
    certifications: list[LinkedInCertification] = []
    linkedin_projects: list[LinkedInProject] = []
    volunteering: list[LinkedInVolunteering] = []
    courses: list[LinkedInCourse] = []
    publications: list[LinkedInPublication] = []
    honors: list[LinkedInHonor] = []
    languages: list[LinkedInLanguage] = []
    patents: list[dict] = []


# ── Parse helpers ─────────────────────────────────────────────────────────────

def _parse_endorsement_count(raw: str | None) -> int:
    if not raw:
        return 0
    m = re.search(r"(\d+)", str(raw))
    return int(m.group(1)) if m else 0


def _parse_skills(raw: list) -> list[LinkedInSkill]:
    result = []
    seen: set[str] = set()
    for s in raw:
        if isinstance(s, str):
            name = s.strip()
            endorsements = 0
        elif isinstance(s, dict):
            name = str(s.get("name") or s.get("skill") or "").strip()
            endorsements = _parse_endorsement_count(s.get("endorsements"))
        else:
            continue
        if name and name not in seen:
            seen.add(name)
            result.append(LinkedInSkill(name=name, endorsements=endorsements))
    return result


def _parse_experience(raw: list) -> list[LinkedInExperience]:
    result = []
    for pos in raw:
        if not isinstance(pos, dict):
            continue
        company = pos.get("companyName") or ""
        title = pos.get("position") or pos.get("title") or ""
        if not company or not title:
            continue

        start_obj = pos.get("startDate") or {}
        end_obj = pos.get("endDate") or {}
        start = start_obj.get("text") or "" if isinstance(start_obj, dict) else str(start_obj)
        end = end_obj.get("text") or "" if isinstance(end_obj, dict) else str(end_obj)
        is_current = end.lower() in ("present", "", "null", "none") or end is None

        job_skills = [s.name for s in _parse_skills(pos.get("skills") or [])]

        result.append(LinkedInExperience(
            company=str(company).strip(),
            title=str(title).strip(),
            start_date=start.strip() if start else None,
            end_date=end.strip() if not is_current and end else None,
            description=str(pos.get("description") or "").strip(),
            is_current=is_current,
            location=pos.get("location") or None,
            employment_type=pos.get("employmentType") or None,
            workplace_type=pos.get("workplaceType") or None,
            company_linkedin_url=pos.get("companyLinkedinUrl") or None,
            company_universal_name=pos.get("companyUniversalName") or None,
            duration=pos.get("duration") or None,
            job_skills=job_skills,
        ))
    return result


def _parse_education(raw: list) -> list[LinkedInEducation]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        school = item.get("schoolName") or ""
        if not school:
            continue

        start_obj = item.get("startDate") or {}
        end_obj = item.get("endDate") or {}
        start_year = (start_obj.get("year") if isinstance(start_obj, dict) else None)
        end_year = (end_obj.get("year") if isinstance(end_obj, dict) else None)

        skills = [s.name for s in _parse_skills(item.get("skills") or [])]

        result.append(LinkedInEducation(
            school_name=str(school).strip(),
            degree=item.get("degree") or None,
            field_of_study=item.get("fieldOfStudy") or None,
            start_year=int(start_year) if start_year else None,
            end_year=int(end_year) if end_year else None,
            school_linkedin_url=item.get("schoolLinkedinUrl") or None,
            skills=skills,
        ))
    return result


def _parse_certifications(raw: list) -> list[LinkedInCertification]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title:
            continue
        result.append(LinkedInCertification(
            title=str(title).strip(),
            issued_at=item.get("issuedAt") or None,
            issued_by=item.get("issuedBy") or None,
        ))
    return result


def _parse_projects(raw: list) -> list[LinkedInProject]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title:
            continue
        start_obj = item.get("startDate") or {}
        end_obj = item.get("endDate") or {}
        start = start_obj.get("text") if isinstance(start_obj, dict) else None
        end = end_obj.get("text") if isinstance(end_obj, dict) else None
        result.append(LinkedInProject(
            title=str(title).strip(),
            description=str(item.get("description") or "").strip(),
            start_date=str(start).strip() if start else None,
            end_date=str(end).strip() if end else None,
        ))
    return result


def _parse_volunteering(raw: list) -> list[LinkedInVolunteering]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role") or ""
        if not role:
            continue
        result.append(LinkedInVolunteering(
            role=str(role).strip(),
            organization_name=item.get("organizationName") or None,
            cause=item.get("cause") or None,
            duration=item.get("duration") or None,
        ))
    return result


def _parse_courses(raw: list) -> list[LinkedInCourse]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title:
            continue
        result.append(LinkedInCourse(
            title=str(title).strip(),
            associated_with=item.get("associatedWith") or None,
        ))
    return result


def _parse_publications(raw: list) -> list[LinkedInPublication]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title:
            continue
        result.append(LinkedInPublication(
            title=str(title).strip(),
            published_at=item.get("publishedAt") or None,
            link=item.get("link") or None,
        ))
    return result


def _parse_honors(raw: list) -> list[LinkedInHonor]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title:
            continue
        result.append(LinkedInHonor(
            title=str(title).strip(),
            issued_by=item.get("issuedBy") or None,
            issued_at=item.get("issuedAt") or None,
            description=str(item.get("description") or "").strip(),
        ))
    return result


def _parse_languages(raw: list) -> list[LinkedInLanguage]:
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or ""
        if not name:
            continue
        result.append(LinkedInLanguage(
            name=str(name).strip(),
            proficiency=item.get("proficiency") or None,
        ))
    return result


# ── Main enricher ─────────────────────────────────────────────────────────────

async def enrich_linkedin(linkedin_url: str) -> LinkedInProfileData:
    """
    Scrape a LinkedIn profile via Apify harvestapi/linkedin-profile-scraper.
    Returns LinkedInProfileData. Falls back to empty on any failure.
    """
    if not settings.apify_api_key:
        logger.warning("apify_api_key_missing")
        return LinkedInProfileData()

    if not linkedin_url:
        return LinkedInProfileData()

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # Start run
            run_resp = await client.post(
                f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
                params={"token": settings.apify_api_key},
                json={"urls": [linkedin_url]},
            )
            run_resp.raise_for_status()
            run_id = run_resp.json()["data"]["id"]

            # Poll until finished (max ~2 min)
            for _ in range(24):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"{APIFY_BASE}/actor-runs/{run_id}",
                    params={"token": settings.apify_api_key},
                )
                status_resp.raise_for_status()
                status = status_resp.json()["data"]["status"]
                if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                    break

            if status != "SUCCEEDED":
                logger.warning("linkedin_run_failed", run_id=run_id, status=status)
                return LinkedInProfileData()

            dataset_resp = await client.get(
                f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items",
                params={"token": settings.apify_api_key},
            )
            dataset_resp.raise_for_status()
            items = dataset_resp.json()

        if not items:
            logger.warning("linkedin_scraper_empty", url=linkedin_url)
            return LinkedInProfileData()

        raw = items[0] if isinstance(items, list) else items

        # ── Location ──────────────────────────────────────────────────────────
        location_obj = raw.get("location") or {}
        location_text = (
            location_obj.get("linkedinText")
            if isinstance(location_obj, dict)
            else str(location_obj)
        ) or None

        location_parsed: LinkedInLocation | None = None
        parsed_obj = location_obj.get("parsed") if isinstance(location_obj, dict) else None
        if isinstance(parsed_obj, dict):
            location_parsed = LinkedInLocation(
                text=parsed_obj.get("text") or None,
                city=parsed_obj.get("city") or None,
                state=parsed_obj.get("state") or None,
                country=parsed_obj.get("country") or None,
                country_code=parsed_obj.get("countryCode") or None,
            )

        # ── Counts ────────────────────────────────────────────────────────────
        recs = raw.get("receivedRecommendations")
        rec_count = len(recs) if isinstance(recs, list) else (int(recs) if recs else None)

        # ── Current company ───────────────────────────────────────────────────
        current_pos = raw.get("currentPosition") or []
        current_company: str | None = None
        if isinstance(current_pos, list) and current_pos:
            current_company = current_pos[0].get("companyName") or None

        # ── Profile picture ───────────────────────────────────────────────────
        # profilePicture is {"url": "...", "sizes": [...]}; "photo" is the flat string version.
        # Download server-side and store as data URL so browser doesn't hit LinkedIn CDN directly.
        pic_raw = raw.get("profilePicture") or {}
        cdn_url = (pic_raw.get("url") if isinstance(pic_raw, dict) else None) or raw.get("photo") or None
        profile_picture_url: str | None = None
        if cdn_url:
            try:
                async with httpx.AsyncClient(timeout=15) as pic_client:
                    pic_resp = await pic_client.get(cdn_url, headers={"Referer": "https://www.linkedin.com/"})
                if pic_resp.status_code == 200:
                    mime = pic_resp.headers.get("content-type", "image/jpeg").split(";")[0]
                    b64 = base64.b64encode(pic_resp.content).decode()
                    profile_picture_url = f"data:{mime};base64,{b64}"
                else:
                    logger.warning("linkedin_pic_download_failed", status=pic_resp.status_code)
            except Exception as pic_exc:
                logger.warning("linkedin_pic_download_error", error=str(pic_exc))

        # ── Parse all sections ────────────────────────────────────────────────
        experience = _parse_experience(raw.get("experience") or [])
        skills = _parse_skills(raw.get("skills") or [])
        education = _parse_education(raw.get("education") or [])
        certifications = _parse_certifications(raw.get("certifications") or [])
        li_projects = _parse_projects(raw.get("projects") or [])
        volunteering = _parse_volunteering(raw.get("volunteering") or [])
        courses = _parse_courses(raw.get("courses") or [])
        publications = _parse_publications(raw.get("publications") or [])
        honors = _parse_honors(raw.get("honorsAndAwards") or [])
        languages = _parse_languages(raw.get("languages") or [])
        patents = raw.get("patents") or []

        profile = LinkedInProfileData(
            linkedin_id=raw.get("entityId") or raw.get("id") or None,
            public_identifier=raw.get("publicIdentifier") or None,
            linkedin_url=raw.get("linkedinUrl") or linkedin_url,
            first_name=raw.get("firstName") or None,
            last_name=raw.get("lastName") or None,
            headline=raw.get("headline") or None,
            summary=raw.get("about") or None,
            location=location_text,
            location_parsed=location_parsed,
            connections=raw.get("connectionsCount") or None,
            followers=raw.get("followerCount") or None,
            recommendations_count=rec_count,
            open_to_work=bool(raw.get("openToWork", False)),
            hiring=bool(raw.get("hiring", False)),
            premium=bool(raw.get("premium", False)),
            verified=bool(raw.get("verified", False)),
            registered_at=raw.get("registeredAt") or None,
            top_skills=raw.get("topSkills") or None,
            current_company=current_company,
            profile_picture_url=profile_picture_url,
            skills=skills,
            experience=experience,
            education=education,
            certifications=certifications,
            linkedin_projects=li_projects,
            volunteering=volunteering,
            courses=courses,
            publications=publications,
            honors=honors,
            languages=languages,
            patents=[p for p in patents if isinstance(p, dict)],
        )

        logger.info(
            "linkedin_enriched",
            url=linkedin_url,
            positions=len(experience),
            skills=len(skills),
            education=len(education),
            certifications=len(certifications),
            languages=len(languages),
            connections=profile.connections,
        )
        return profile

    except Exception as exc:
        logger.warning("linkedin_enrichment_failed", url=linkedin_url, error=str(exc))
        return LinkedInProfileData()
