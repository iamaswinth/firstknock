import asyncio
import structlog
from firstknock.workers.celery_app import app

from firstknock.pipeline.enrichment.github import enrich_github
from firstknock.pipeline.enrichment.company import enrich_companies
from firstknock.pipeline.enrichment.institution import enrich_institutions
from firstknock.pipeline.enrichment.linkedin import enrich_linkedin
from firstknock.pipeline.persistence.postgres_writer import (
    save_enrichment_data,
    save_compiled_profile,
    get_resume_by_id,
    mark_graph_built,
    update_resume_status,
)
from firstknock.pipeline.persistence.db import dispose_engine
from firstknock.pipeline.graph.writers import build_full_graph
from firstknock.pipeline.graph.client import close_driver

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
    company_hints: dict | None = None,
) -> dict:
    """
    Single task that runs all 4 enrichers concurrently, then enriches any
    LinkedIn-only companies, and finally writes to Postgres + Memgraph.
    Kept as one Celery task to avoid solo-pool chord issues on Windows.
    """
    logger.info("enrichment_started", person_id=person_id, resume_id=resume_id)

    async def _run():
        import uuid as _uuid

        # ── 1-4. All enrichers are independent — run concurrently ────────────
        from firstknock.config import settings

        async def _do_github() -> dict:
            if not github_url or not settings.enable_github_enrichment:
                return {}
            try:
                data = await enrich_github(person_id, github_url, existing_projects)
                logger.info("enrichment_github_done", person_id=person_id,
                            pinned=len(data.get("pinned_repos", [])))
                return data
            except Exception as exc:
                logger.warning("enrichment_github_failed", person_id=person_id, error=str(exc))
                return {}

        async def _do_company() -> dict:
            if not company_names or not settings.enable_company_enrichment:
                return {}
            try:
                data = await enrich_companies(company_names, hints=company_hints or {})
                logger.info("enrichment_company_done", person_id=person_id, count=len(data))
                return data
            except Exception as exc:
                logger.warning("enrichment_company_failed", person_id=person_id, error=str(exc))
                return {}

        async def _do_institution() -> dict:
            if not institution_names or not settings.enable_institution_enrichment:
                return {}
            try:
                data = enrich_institutions(institution_names)
                logger.info("enrichment_institution_done", person_id=person_id, count=len(data))
                return data
            except Exception as exc:
                logger.warning("enrichment_institution_failed", person_id=person_id, error=str(exc))
                return {}

        async def _do_linkedin() -> dict:
            if not linkedin_url or not settings.enable_linkedin_enrichment:
                return {}
            try:
                li = await enrich_linkedin(linkedin_url)
                data = li.model_dump()
                logger.info("enrichment_linkedin_done", person_id=person_id,
                            positions=len(li.experience), skills=len(li.skills))
                return data
            except Exception as exc:
                logger.warning("enrichment_linkedin_failed", person_id=person_id, error=str(exc))
                return {}

        github_data, company_data, institution_data, linkedin_data = await asyncio.gather(
            _do_github(),
            _do_company(),
            _do_institution(),
            _do_linkedin(),
        )

        # ── 5. Enrich LinkedIn-only companies ────────────────────────────────
        from firstknock.pipeline.resolution.entity_normalizer import _strip_company
        li_experience = linkedin_data.get("experience", [])
        if li_experience:
            resume_set = {_strip_company(c).lower() for c in company_names if c}
            new_companies = list({
                _strip_company(exp["company"])
                for exp in li_experience
                if exp.get("company") and _strip_company(exp["company"]).lower() not in resume_set
            })
            if new_companies and settings.enable_company_enrichment:
                # Build hints for LinkedIn-only companies so the founder gating in
                # company.py fires (it checks for "role: <founder-role>" in the hint).
                li_company_hints: dict[str, str] = {}
                for exp in li_experience:
                    co = _strip_company(exp.get("company") or "")
                    if co and co.lower() not in resume_set:
                        parts: list[str] = []
                        if exp.get("location"):
                            parts.append(exp["location"])
                        if exp.get("title"):
                            parts.append(f"role: {exp['title']}")
                        li_company_hints[co] = " | ".join(parts)

                logger.info("enrichment_linkedin_new_companies", person_id=person_id,
                            companies=new_companies)
                try:
                    new_data = await enrich_companies(new_companies, hints=li_company_hints)
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

        # ── 6. Save enrichment to Postgres ───────────────────────────────────
        try:
            await save_enrichment_data(resume_id, postgres_payload)
            logger.info("enrichment_postgres_saved", resume_id=resume_id)
        except Exception as exc:
            logger.warning("enrichment_postgres_failed", resume_id=resume_id, error=str(exc))

        # ── 7. LLM compilation (reconcile resume + LinkedIn + company data) ───
        await update_resume_status(_uuid.UUID(resume_id), "compiling")
        try:
            from firstknock.pipeline.compilation.compiler import compile_profile
            compiled = await compile_profile(_uuid.UUID(resume_id))
            await save_compiled_profile(_uuid.UUID(resume_id), compiled.model_dump())
            logger.info(
                "profile_compiled",
                person_id=person_id,
                experience=len(compiled.experience),
                education=len(compiled.education),
            )
        except Exception as exc:
            logger.warning("profile_compile_failed", person_id=person_id, error=str(exc))

        # ── 8. Build full graph (single deferred write) ───────────────────────
        await update_resume_status(_uuid.UUID(resume_id), "graph_building")
        try:
            await build_full_graph(person_id, _uuid.UUID(resume_id))
            await mark_graph_built(_uuid.UUID(resume_id))
            logger.info("full_graph_built", person_id=person_id, resume_id=resume_id)
        except Exception as exc:
            logger.warning("full_graph_build_failed", person_id=person_id, error=str(exc))

        await update_resume_status(_uuid.UUID(resume_id), "enriched")

        # ── 9. Dispatch embedding ─────────────────────────────────────────────
        try:
            from firstknock.pipeline.embedding.tasks import dispatch_embedding
            resume = await get_resume_by_id(_uuid.UUID(resume_id))
            dispatch_embedding(person_id, resume_id, resume.extracted_json or {})
        except Exception as exc:
            logger.warning("embedding_dispatch_failed", person_id=person_id, error=str(exc))

        await close_driver()
        await dispose_engine()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
        # Drain lingering cleanup tasks (e.g. httpx connection pool teardown)
        # to avoid "Task exception was never retrieved" on Windows + Python 3.14.
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        logger.info("enrichment_complete", person_id=person_id, resume_id=resume_id)
        return {"status": "ok", "person_id": person_id}
    except Exception as exc:
        logger.warning("enrichment_task_failed", person_id=person_id, error=str(exc))
        raise self.retry(exc=exc)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def dispatch_enrichment(
    resume_id: str,
    person_id: str,
    github_url: str,
    linkedin_url: str,
    existing_projects: list[dict],
    company_names: list[str],
    institution_names: list[str],
    explicit_skills: list[str],
    company_hints: dict[str, str] | None = None,
) -> None:
    process_enrichment.apply_async(args=[
        resume_id, person_id, github_url, linkedin_url,
        existing_projects, company_names, institution_names, explicit_skills,
        company_hints or {},
    ])
    logger.info(
        "enrichment_dispatched",
        resume_id=resume_id,
        person_id=person_id,
        companies=company_names,
        institutions=institution_names,
        linkedin_url=linkedin_url,
    )
