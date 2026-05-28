import asyncio
import structlog
from firstknock.workers.celery_app import app

from firstknock.pipeline.enrichment.github import enrich_github
from firstknock.pipeline.enrichment.company import enrich_companies
from firstknock.pipeline.enrichment.institution import enrich_institutions
from firstknock.pipeline.enrichment.linkedin import enrich_linkedin
from firstknock.pipeline.persistence.postgres_writer import save_enrichment_data, get_resume_by_id
from firstknock.pipeline.persistence.db import dispose_engine
from firstknock.pipeline.graph.writers import write_graph_final_layer

logger = structlog.get_logger()


@app.task(bind=True, max_retries=1, name="enrichment.process")
def process_enrichment(
    self,
    resume_id: str,
    person_id: str,
    github_url: str,
    linkedin_url: str,
    existing_projects: list,
    company_names: list,
    institution_names: list,
    explicit_skills: list,
) -> dict:
    """
    Single task that runs all 4 enrichers sequentially, enriches any
    LinkedIn-only companies via Perplexity, then writes to Postgres + Memgraph.
    Runs entirely in one Celery task to avoid solo-pool chord issues on Windows.
    """
    logger.info("enrichment_started", person_id=person_id, resume_id=resume_id)

    async def _run():
        import uuid as _uuid

        # ── 1. GitHub ────────────────────────────────────────────────────────
        github_data = {}
        if github_url:
            try:
                github_data = await enrich_github(person_id, github_url, existing_projects)
                logger.info("enrichment_github_done", person_id=person_id,
                            pinned=len(github_data.get("pinned_repos", [])))
            except Exception as exc:
                logger.warning("enrichment_github_failed", person_id=person_id, error=str(exc))

        # ── 2. Company (resume companies) ────────────────────────────────────
        company_data = {}
        if company_names:
            try:
                company_data = await enrich_companies(company_names)
                logger.info("enrichment_company_done", person_id=person_id,
                            count=len(company_data))
            except Exception as exc:
                logger.warning("enrichment_company_failed", person_id=person_id, error=str(exc))

        # ── 3. Institution ───────────────────────────────────────────────────
        institution_data = {}
        if institution_names:
            try:
                institution_data = enrich_institutions(institution_names)
                logger.info("enrichment_institution_done", person_id=person_id,
                            count=len(institution_data))
            except Exception as exc:
                logger.warning("enrichment_institution_failed", person_id=person_id, error=str(exc))

        # ── 4. LinkedIn ──────────────────────────────────────────────────────
        linkedin_data = {}
        if linkedin_url:
            try:
                li = await enrich_linkedin(linkedin_url)
                linkedin_data = li.model_dump()
                logger.info("enrichment_linkedin_done", person_id=person_id,
                            positions=len(li.experience), skills=len(li.skills))
            except Exception as exc:
                logger.warning("enrichment_linkedin_failed", person_id=person_id, error=str(exc))

        # ── 5. Enrich LinkedIn-only companies ────────────────────────────────
        li_experience = linkedin_data.get("experience", [])
        if li_experience:
            resume_set = {c.lower() for c in company_names if c}
            new_companies = list({
                exp["company"]
                for exp in li_experience
                if exp.get("company") and exp["company"].lower() not in resume_set
            })
            if new_companies:
                logger.info("enrichment_linkedin_new_companies", person_id=person_id,
                            companies=new_companies)
                try:
                    new_data = await enrich_companies(new_companies)
                    for name, data in new_data.items():
                        if name not in company_data:
                            company_data[name] = data
                except Exception as exc:
                    logger.warning("enrichment_linkedin_company_failed",
                                   person_id=person_id, error=str(exc))

        postgres_payload = {
            "github": github_data,
            "companies": company_data,
            "institutions": institution_data,
            "linkedin": linkedin_data,
        }

        # ── 6. Save to Postgres ──────────────────────────────────────────────
        try:
            await save_enrichment_data(resume_id, postgres_payload)
            logger.info("enrichment_postgres_saved", resume_id=resume_id)
        except Exception as exc:
            logger.warning("enrichment_postgres_failed", resume_id=resume_id, error=str(exc))

        # ── 7. Read inferred_json then write final graph layer ───────────────
        inferred_json = None
        try:
            resume = await get_resume_by_id(_uuid.UUID(resume_id))
            inferred_json = resume.inferred_json
        except Exception as exc:
            logger.warning("enrichment_inferred_read_failed", resume_id=resume_id, error=str(exc))

        try:
            await write_graph_final_layer(
                person_id,
                inferred_json,
                postgres_payload,
                set(s.lower() for s in explicit_skills),
            )
            logger.info("enrichment_graph_written", person_id=person_id)
        except Exception as exc:
            logger.warning("enrichment_graph_failed", person_id=person_id, error=str(exc))

        await dispose_engine()

    try:
        asyncio.run(_run())
        logger.info("enrichment_complete", person_id=person_id, resume_id=resume_id)
        return {"status": "ok", "person_id": person_id}
    except Exception as exc:
        logger.warning("enrichment_task_failed", person_id=person_id, error=str(exc))
        raise self.retry(exc=exc)


def dispatch_enrichment(
    resume_id: str,
    person_id: str,
    github_url: str,
    linkedin_url: str,
    existing_projects: list[dict],
    company_names: list[str],
    institution_names: list[str],
    explicit_skills: list[str],
) -> None:
    process_enrichment.apply_async(args=[
        resume_id, person_id, github_url, linkedin_url,
        existing_projects, company_names, institution_names, explicit_skills,
    ])
    logger.info(
        "enrichment_dispatched",
        resume_id=resume_id,
        person_id=person_id,
        companies=company_names,
        institutions=institution_names,
        linkedin_url=linkedin_url,
    )
