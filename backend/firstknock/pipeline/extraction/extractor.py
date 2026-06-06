import anthropic
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .llm_client import call_extraction
from .schemas import ResumeExtraction


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((anthropic.APIError, ValidationError, KeyError, ValueError)),
)
async def extract_resume(text: str, embedded_links: list[str] | None = None) -> ResumeExtraction:
    raw = await call_extraction(text)
    result = ResumeExtraction.model_validate(raw)
    if embedded_links:
        result = _apply_embedded_links(result, embedded_links)
    return result


def _apply_embedded_links(result: ResumeExtraction, links: list[str]) -> ResumeExtraction:
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique = [l for l in links if not (l in seen or seen.add(l))]  # type: ignore[func-returns-value]

    github_profiles = [l for l in unique if "github.com" in l and l.count("/") == 3]
    github_repos    = [l for l in unique if "github.com" in l and l.count("/") > 3]
    linkedin_links  = [l for l in unique if "linkedin.com" in l]
    other_links     = [l for l in unique if "github.com" not in l and "linkedin.com" not in l]

    if github_profiles and not result.identity.github_url:
        result.identity.github_url = github_profiles[0]

    if linkedin_links and not result.identity.linkedin_url:
        result.identity.linkedin_url = linkedin_links[0]

    # Match repo links to projects by repo name appearing in project name
    for repo_url in github_repos:
        repo_name = repo_url.rstrip("/").split("/")[-1].lower()
        for project in result.projects:
            if not project.github_url and repo_name in project.name.lower().replace(" ", "").replace("-", ""):
                project.github_url = repo_url
                break

    # Try to match other links to companies before falling through to projects.
    # Strategy: strip protocol/www, take the domain root (before first dot), remove hyphens,
    # then check if the cleaned company name appears in it or vice versa.
    # e.g. "ask-donna.com" → "askdonna", company "Donna" → "donna" → "donna" in "askdonna" ✓
    used_as_company: set[str] = set()
    for url in other_links:
        domain = url.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").split("/")[0]
        domain_root = domain.split(".")[0].replace("-", "").replace("_", "")
        for exp in result.experience:
            if exp.company_url:
                continue
            company_clean = exp.company.lower().replace(" ", "").replace("-", "").replace("_", "")
            # Accept if company name is contained in domain root or vice versa (min 4 chars to avoid noise)
            if len(company_clean) >= 4 and len(domain_root) >= 4:
                if company_clean in domain_root or domain_root in company_clean:
                    exp.company_url = url
                    used_as_company.add(url)
                    break

    # Remaining links that weren't matched to companies go to projects by order
    project_link_iter = iter(l for l in other_links if l not in used_as_company)
    for project in result.projects:
        if not project.url:
            project.url = next(project_link_iter, None)

    return result
