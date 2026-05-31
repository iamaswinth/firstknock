import asyncio
import base64
import structlog
import httpx
from pydantic import BaseModel
from firstknock.config import settings

logger = structlog.get_logger()

APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "harvestapi~linkedin-profile-scraper"


class LinkedInExperience(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str = ""
    is_current: bool = False


class LinkedInProfileData(BaseModel):
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    connections: int | None = None
    followers: int | None = None
    recommendations_count: int | None = None
    profile_picture_url: str | None = None
    skills: list[str] = []
    experience: list[LinkedInExperience] = []


def _parse_skills(raw: list) -> list[str]:
    result = []
    for s in raw:
        if isinstance(s, str):
            result.append(s.strip())
        elif isinstance(s, dict):
            name = s.get("name") or s.get("skill") or ""
            if name:
                result.append(str(name).strip())
    return [s for s in result if s]


def _parse_experience(raw: list) -> list[LinkedInExperience]:
    """Parse harvestapi experience items.
    Each item: {position, companyName, startDate: {text}, endDate: {text}, description}
    """
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

        result.append(LinkedInExperience(
            company=str(company).strip(),
            title=str(title).strip(),
            start_date=start.strip() if start else None,
            end_date=end.strip() if not is_current and end else None,
            description=str(pos.get("description") or "").strip(),
            is_current=is_current,
        ))
    return result


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

        location_obj = raw.get("location") or {}
        location = (
            location_obj.get("linkedinText")
            if isinstance(location_obj, dict)
            else str(location_obj)
        ) or None

        recs = raw.get("receivedRecommendations")
        rec_count = len(recs) if isinstance(recs, list) else (int(recs) if recs else None)

        experience = _parse_experience(raw.get("experience") or [])
        skills = _parse_skills(raw.get("skills") or [])

        # profilePicture is {"url": "...", "sizes": [...]}; "photo" is the flat string version.
        # We download the image server-side and store it as a data URL so the browser
        # never has to request it directly from LinkedIn's CDN (which blocks cross-origin loads).
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

        profile = LinkedInProfileData(
            headline=raw.get("headline") or None,
            summary=raw.get("about") or None,
            location=location,
            connections=raw.get("connectionsCount") or None,
            followers=raw.get("followerCount") or None,
            recommendations_count=rec_count,
            profile_picture_url=profile_picture_url,
            skills=skills,
            experience=experience,
        )

        logger.info(
            "linkedin_enriched",
            url=linkedin_url,
            positions=len(experience),
            skills=len(skills),
            connections=profile.connections,
        )
        return profile

    except Exception as exc:
        logger.warning("linkedin_enrichment_failed", url=linkedin_url, error=str(exc))
        return LinkedInProfileData()
