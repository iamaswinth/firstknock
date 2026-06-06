import asyncio
import uuid
import structlog
from firstknock.workers.celery_app import app

logger = structlog.get_logger()


@app.task(
    bind=True,
    max_retries=0,
    name="ingestion.process",
    queue="ingestion",
)
def process_ingestion(self, resume_id: str, user_email: str, file_type: str) -> dict:
    """
    Full ingestion pipeline for one resume. Runs async work inside a dedicated event loop.

    Key invariant: dispose_engine() is ALWAYS called inside _run()'s finally block.
    This drains the asyncpg connection pool before the loop closes so the next task's
    event loop gets fresh connections (avoids 'Event loop is closed' on pool ping).

    Graph write is NOT done here — it is deferred to the enrichment task after all
    enrichment data is available. This eliminates incremental graph merge conflicts.
    """
    logger.info("ingestion_started", resume_id=resume_id, email=user_email)

    async def _run() -> dict:
        import uuid as _uuid
        from firstknock.pipeline.ingestion.file_store import fetch_file, delete_file
        from firstknock.pipeline.persistence.postgres_writer import (
            update_resume_status,
            save_extracted_resume,
        )
        from firstknock.pipeline.parsers.router import parse_file
        from firstknock.pipeline.normalization.text_cleaner import clean_text
        from firstknock.pipeline.normalization.section_detector import detect_sections
        from firstknock.pipeline.extraction.extractor import extract_resume
        from firstknock.pipeline.resolution.skill_canonicalizer import canonicalize_skill_list
        from firstknock.pipeline.resolution.date_normalizer import normalize_date, date_range_months
        from firstknock.pipeline.resolution.company_matcher import match_company
        from firstknock.pipeline.persistence.db import dispose_engine

        rid = _uuid.UUID(resume_id)
        pipeline_error: Exception | None = None
        result: dict = {}

        try:
            # ── Stage 1: Parse ───────────────────────────────────────────────
            await update_resume_status(rid, "parsing")
            file_bytes = await fetch_file(resume_id)
            parsed = await parse_file(file_bytes, file_type)
            raw_text = parsed["raw_text"]
            embedded_links = parsed.get("embedded_links", [])
            await delete_file(resume_id)

            # ── Stage 2: Normalize ───────────────────────────────────────────
            cleaned = clean_text(raw_text)
            detect_sections(cleaned)

            # ── Stage 3: LLM Extraction (Claude Sonnet) ──────────────────────
            await update_resume_status(rid, "extracting")
            extraction = await extract_resume(cleaned, embedded_links=embedded_links)
            raw_dump = extraction.model_dump()

            # ── Stage 4: Resolution ──────────────────────────────────────────
            await update_resume_status(rid, "resolving")
            skills = raw_dump["skills"]
            raw_skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))
            for category in ("languages", "frameworks", "ai_ml", "databases", "devops", "other"):
                skills[category] = canonicalize_skill_list(skills.get(category, []))
            canonical_skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))

            for exp in raw_dump["experience"]:
                norm_start = normalize_date(exp.get("start_date"))
                norm_end = normalize_date(exp.get("end_date"))
                exp["start_date"] = norm_start
                exp["end_date"] = norm_end
                exp["months"] = date_range_months(norm_start, norm_end)
                exp["company"] = match_company(exp["company"])
                exp["tech_stack"] = canonicalize_skill_list(exp.get("tech_stack", []))

            for proj in raw_dump["projects"]:
                proj["tech_stack"] = canonicalize_skill_list(proj.get("tech_stack", []))

            # ── Stage 5: Persist to Postgres ─────────────────────────────────
            await update_resume_status(rid, "persisting")
            user_id, db_resume_id = await save_extracted_resume(
                user_email=user_email,
                source_type=parsed["source_type"],
                raw_text=raw_text,
                extracted_json=raw_dump,
                resume_id=rid,
            )

            # ── Stage 6: Inference (Claude Haiku) ────────────────────────────
            # Runs from extracted_json directly — no graph write needed first.
            await update_resume_status(rid, "inferring")
            inferred_count = 0
            try:
                from firstknock.pipeline.inference.engine import run_inference
                from firstknock.pipeline.inference.seniority import (
                    compute_seniority,
                    compute_total_experience_months,
                )
                from firstknock.pipeline.persistence.postgres_writer import save_inferred_data
                from firstknock.pipeline.graph.writers import _collect_skills

                explicit_for_inference = [
                    {"name": name, "category": category}
                    for name, category in _collect_skills(raw_dump)
                ]
                inferred_result = await run_inference(str(user_id), explicit_for_inference)
                total_months = compute_total_experience_months(raw_dump.get("experience", []))
                seniority = compute_seniority(total_months)
                inferred_json = {
                    **inferred_result,
                    "seniority": seniority,
                    "total_experience_months": total_months,
                }
                await save_inferred_data(db_resume_id, inferred_json)
                inferred_count = len(inferred_json.get("skills", []))
                logger.info("inference_complete", resume_id=resume_id, inferred=inferred_count)
            except Exception as exc:
                logger.warning("inference_failed", resume_id=resume_id, error=str(exc))

            # ── Stage 7: Dispatch enrichment ─────────────────────────────────
            # Always dispatches — graph write is no longer a prerequisite.
            await update_resume_status(rid, "enriching")
            try:
                from firstknock.pipeline.enrichment.tasks import dispatch_enrichment

                identity = raw_dump.get("identity", {})
                company_names = [
                    e["company"] for e in raw_dump.get("experience", []) if e.get("company")
                ]
                person_location = identity.get("location", "")
                company_hints: dict[str, str] = {}
                for e in raw_dump.get("experience", []):
                    if not e.get("company"):
                        continue
                    parts: list[str] = []
                    if e.get("company_url"):
                        parts.append(f"website: {e['company_url']}")
                    loc = e.get("location") or person_location
                    if loc:
                        parts.append(loc)
                    if e.get("title"):
                        parts.append(f"role: {e['title']}")
                    desc = e.get("description") or []
                    if desc and isinstance(desc, list) and desc[0]:
                        parts.append(f"context: {str(desc[0])[:150]}")
                    company_hints[e["company"]] = " | ".join(parts)

                institution_names = [
                    e["institution"]
                    for e in raw_dump.get("education", [])
                    if e.get("institution")
                ]
                existing_projects = [
                    {
                        "project_id": str(
                            _uuid.uuid5(_uuid.NAMESPACE_URL, f"{user_id}:{p['name']}")
                        ),
                        "name": p["name"],
                        "github_url": p.get("github_url") or "",
                    }
                    for p in raw_dump.get("projects", [])
                ]
                all_skills = [
                    s
                    for cat in raw_dump.get("skills", {}).values()
                    if isinstance(cat, list)
                    for s in cat
                ]
                dispatch_enrichment(
                    resume_id=str(db_resume_id),
                    person_id=str(user_id),
                    github_url=identity.get("github_url", ""),
                    linkedin_url=identity.get("linkedin_url", ""),
                    existing_projects=existing_projects,
                    company_names=company_names,
                    company_hints=company_hints,
                    institution_names=institution_names,
                    explicit_skills=all_skills,
                )
            except Exception as exc:
                logger.warning("enrichment_dispatch_failed", resume_id=resume_id, error=str(exc))

            logger.info(
                "ingestion_complete",
                resume_id=resume_id,
                raw_skills=raw_skill_count,
                canonical_skills=canonical_skill_count,
                inferred=inferred_count,
            )
            result = {"resume_id": str(db_resume_id), "user_id": str(user_id), "status": "enriching"}

        except Exception as exc:
            pipeline_error = exc
            logger.error("ingestion_pipeline_failed", resume_id=resume_id, error=str(exc))
            try:
                await update_resume_status(rid, "failed", error_message=str(exc))
            except Exception:
                pass

        finally:
            try:
                await dispose_engine()
            except Exception:
                pass

        if pipeline_error is not None:
            raise pipeline_error
        return result

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run())
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        return result
    except Exception as exc:
        logger.error("ingestion_task_failed", resume_id=resume_id, error=str(exc))
        raise
    finally:
        loop.close()
        asyncio.set_event_loop(None)
