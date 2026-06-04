import uuid
import json
import structlog
import httpx
import anthropic
from firstknock.config import settings

logger = structlog.get_logger()

GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"

PINNED_REPOS_QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          forkCount
          pushedAt
          primaryLanguage { name }
          repositoryTopics(first: 10) {
            nodes { topic { name } }
          }
          object(expression: "HEAD:README.md") {
            ... on Blob { text }
          }
        }
      }
    }
  }
}
"""


def _extract_username(github_url: str) -> str | None:
    if not github_url:
        return None
    parts = github_url.rstrip("/").split("/")
    return parts[-1] if parts else None


def _match_project(repo_name: str, repo_url: str, existing_projects: list[dict]) -> str | None:
    """Return project_id if this repo matches an existing project node."""
    repo_name_lower = repo_name.lower()
    for proj in existing_projects:
        # Match by github_url
        if (proj.get("github_url") or "").rstrip("/").lower().endswith(f"/{repo_name_lower}"):
            return proj["project_id"]
        # Match by name similarity
        if proj.get("name", "").lower() == repo_name_lower:
            return proj["project_id"]
    return None


async def _parse_readme(readme_text: str, repo_name: str) -> dict:
    """Use Claude Haiku to extract summary and skills from README."""
    if not readme_text or len(readme_text.strip()) < 50:
        return {"summary": "", "skills": []}

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = f"""Given this GitHub README for a project called "{repo_name}":

{readme_text[:3000]}

Return JSON only — no explanation:
{{
  "summary": "2-3 sentence description of what this project does and its technical impact",
  "skills": ["skill1", "skill2"]
}}

Rules:
- summary must describe the project purpose and tech approach concisely
- skills must be specific technologies found in the README (max 10)
- skills must be properly capitalized (e.g. "FastAPI" not "fastapi")
- Return ONLY valid JSON, no markdown fences"""

    try:
        response = await client.messages.create(
            model=settings.inference_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as exc:
        logger.warning("github_readme_parse_failed", repo=repo_name, error=str(exc))
        return {"summary": "", "skills": []}


async def enrich_github(
    person_id: str,
    github_url: str,
    existing_projects: list[dict],
) -> dict:
    """
    Fetch pinned repos via GitHub GraphQL + user profile via REST.
    existing_projects: list of {project_id, name, github_url} from graph.
    Returns enriched data dict.
    """
    if not settings.github_token:
        logger.warning("github_token_missing", person_id=person_id)
        return {}

    username = _extract_username(github_url)
    if not username:
        logger.warning("github_url_invalid", github_url=github_url)
        return {}

    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        # ── GraphQL: pinned repos ─────────────────────────────────────────────
        try:
            gql_resp = await client.post(
                GRAPHQL_URL,
                headers=headers,
                json={"query": PINNED_REPOS_QUERY, "variables": {"login": username}},
            )
            gql_resp.raise_for_status()
            gql_data = gql_resp.json()
        except Exception as exc:
            logger.warning("github_graphql_failed", username=username, error=str(exc))
            return {}

        pinned_nodes = (
            gql_data.get("data", {})
            .get("user", {})
            .get("pinnedItems", {})
            .get("nodes", [])
        )

        # ── REST: user profile ────────────────────────────────────────────────
        profile = {}
        try:
            prof_resp = await client.get(f"{REST_URL}/users/{username}", headers=headers)
            if prof_resp.status_code == 200:
                p = prof_resp.json()
                profile = {
                    "followers": p.get("followers", 0),
                    "public_repos": p.get("public_repos", 0),
                    "bio": p.get("bio") or "",
                }
        except Exception as exc:
            logger.warning("github_profile_failed", username=username, error=str(exc))

    # ── Process pinned repos ──────────────────────────────────────────────────
    pinned_repos = []
    for node in pinned_nodes:
        if not node:
            continue

        repo_name = node.get("name", "")
        repo_url = node.get("url", "")
        readme_text = (node.get("object") or {}).get("text", "")

        topics = [
            t["topic"]["name"]
            for t in node.get("repositoryTopics", {}).get("nodes", [])
            if t.get("topic", {}).get("name")
        ]
        primary_language = (node.get("primaryLanguage") or {}).get("name", "")

        matched_id = _match_project(repo_name, repo_url, existing_projects)
        is_new = matched_id is None

        readme_parsed = await _parse_readme(readme_text, repo_name)

        # For new projects, generate a stable project_id
        if is_new:
            matched_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{person_id}:{repo_name}:github"))

        pinned_repos.append({
            "name": repo_name,
            "github_url": repo_url,
            "description": node.get("description") or "",
            "readme_summary": readme_parsed.get("summary", ""),
            "stars": node.get("stargazerCount", 0),
            "forks": node.get("forkCount", 0),
            "primary_language": primary_language,
            "topics": topics,
            "last_pushed": node.get("pushedAt", ""),
            "matched_project_id": matched_id,
            "is_new": is_new,
            "extracted_skills": readme_parsed.get("skills", []),
        })

    logger.info(
        "github_enrichment_complete",
        person_id=person_id,
        username=username,
        pinned=len(pinned_repos),
        new_projects=sum(1 for r in pinned_repos if r["is_new"]),
    )

    return {"profile": profile, "pinned_repos": pinned_repos}
