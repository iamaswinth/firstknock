import asyncio
import structlog
from celery import group, chord

from firstknock.workers.celery_app import app
from firstknock.pipeline.enrichment.github import enrich_github
from firstknock.pipeline.enrichment.company import enrich_companies
from firstknock.pipeline.enrichment.institution import enrich_institutions
from firstknock.pipeline.enrichment.graph_updater import update_graph
from firstknock.pipeline.persistence.postgres_writer import save_enrichment_data

logger = structlog.get_logger()


# ── Individual enrichment tasks ───────────────────────────────────────────────

@app.task(bind=True, max_retries=2, default_retry_delay=10, name="enrichment.github")
def run_github_enrichment(self, person_id: str, github_url: str, existing_projects: list) -> dict:
    try:
        result = asyncio.run(enrich_github(person_id, github_url, existing_projects))
        return {"type": "github", "data": result}
    except Exception as exc:
        logger.warning("github_task_failed", person_id=person_id, error=str(exc))
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=2, default_retry_delay=10, name="enrichment.company")
def run_company_enrichment(self, person_id: str, company_names: list) -> dict:
    try:
        result = asyncio.run(enrich_companies(company_names))
        return {"type": "company", "data": result}
    except Exception as exc:
        logger.warning("company_task_failed", person_id=person_id, error=str(exc))
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=1, name="enrichment.institution")
def run_institution_enrichment(self, person_id: str, institution_names: list) -> dict:
    try:
        result = enrich_institutions(institution_names)
        return {"type": "institution", "data": result}
    except Exception as exc:
        logger.warning("institution_task_failed", person_id=person_id, error=str(exc))
        return {"type": "institution", "data": {}}


# ── Chord callback: runs after all 3 enrichers complete ─────────────────────

@app.task(name="enrichment.finalize")
def finalize_enrichment(
    results: list,
    resume_id: str,
    person_id: str,
    explicit_skills: list,
) -> None:
    """
    Merges all enricher results, saves to Postgres, then updates Memgraph.
    Runs as the chord callback after github/company/institution all finish.
    """
    enriched: dict = {
        "github": {},
        "companies": {},
        "institutions": {},
        "_existing_explicit_skills": set(s.lower() for s in explicit_skills),
    }

    for result in results:
        if not isinstance(result, dict):
            continue
        rtype = result.get("type")
        data = result.get("data", {})
        if rtype == "github":
            enriched["github"] = data
        elif rtype == "company":
            enriched["companies"] = data
        elif rtype == "institution":
            enriched["institutions"] = data

    # Save to Postgres
    try:
        postgres_payload = {
            "github": enriched["github"],
            "companies": enriched["companies"],
            "institutions": enriched["institutions"],
        }
        asyncio.run(save_enrichment_data(resume_id, postgres_payload))
        logger.info("enrichment_saved_postgres", resume_id=resume_id)
    except Exception as exc:
        logger.warning("enrichment_postgres_save_failed", resume_id=resume_id, error=str(exc))

    # Update Memgraph
    try:
        asyncio.run(update_graph(person_id, enriched))
        logger.info("enrichment_graph_updated", person_id=person_id)
    except Exception as exc:
        logger.warning("enrichment_graph_update_failed", person_id=person_id, error=str(exc))


# ── Entry point called from orchestrator ─────────────────────────────────────

def dispatch_enrichment(
    resume_id: str,
    person_id: str,
    github_url: str,
    linkedin_url: str,       # kept in signature for API compatibility, unused
    existing_projects: list[dict],
    company_names: list[str],
    institution_names: list[str],
    explicit_skills: list[str],
) -> None:
    """
    Fire 3 enrichers in parallel (GitHub, Perplexity company, institution tier).
    When all complete, finalize_enrichment merges results → Postgres + Memgraph.
    """
    job = chord(
        group(
            run_github_enrichment.s(person_id, github_url, existing_projects),
            run_company_enrichment.s(person_id, company_names),
            run_institution_enrichment.s(person_id, institution_names),
        ),
        finalize_enrichment.s(resume_id, person_id, explicit_skills),
    )
    job.apply_async()
    logger.info(
        "enrichment_dispatched",
        resume_id=resume_id,
        person_id=person_id,
        companies=company_names,
        institutions=institution_names,
    )
