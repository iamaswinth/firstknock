import structlog
from firstknock.pipeline.parsers.router import parse_file
from firstknock.pipeline.normalization.text_cleaner import clean_text
from firstknock.pipeline.normalization.section_detector import detect_sections
from firstknock.pipeline.extraction.extractor import extract_resume
from firstknock.pipeline.resolution.skill_canonicalizer import canonicalize_skill_list
from firstknock.pipeline.resolution.date_normalizer import normalize_date, date_range_months
from firstknock.pipeline.resolution.company_matcher import match_company
from firstknock.pipeline.persistence.postgres_writer import save_extracted_resume, mark_graph_built
from firstknock.pipeline.graph.writers import write_resume_graph

logger = structlog.get_logger()


async def run_sync_ingestion(
    file_bytes: bytes,
    file_type: str,
    user_email: str,
) -> dict:
    # Stage 1 — Parse
    parsed = await parse_file(file_bytes, file_type)
    raw_text = parsed["raw_text"]
    embedded_links = parsed.get("embedded_links", [])

    # Stage 2 — Normalize
    cleaned = clean_text(raw_text)
    sections = detect_sections(cleaned)

    # Stage 3 — LLM Extraction
    extraction = await extract_resume(cleaned, embedded_links=embedded_links)

    # Stage 4 — Resolution: apply transforms and build resolved dict
    raw_dump = extraction.model_dump()

    # Canonicalize all skill categories
    skills = raw_dump["skills"]
    raw_skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))
    for category in ("languages", "frameworks", "ai_ml", "databases", "devops", "other"):
        skills[category] = canonicalize_skill_list(skills.get(category, []))
    canonical_skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))

    # Normalize experience dates and calculate durations
    for exp in raw_dump["experience"]:
        norm_start = normalize_date(exp.get("start_date"))
        norm_end = normalize_date(exp.get("end_date"))
        exp["start_date"] = norm_start
        exp["end_date"] = norm_end
        exp["months"] = date_range_months(norm_start, norm_end)
        exp["company"] = match_company(exp["company"])
        exp["tech_stack"] = canonicalize_skill_list(exp.get("tech_stack", []))

    # Canonicalize project tech stacks
    for proj in raw_dump["projects"]:
        proj["tech_stack"] = canonicalize_skill_list(proj.get("tech_stack", []))

    # Stage 5 — Persist to Postgres (source of truth)
    user_id, resume_id = await save_extracted_resume(
        user_email=user_email,
        source_type=parsed["source_type"],
        raw_text=raw_text,
        extracted_json=raw_dump,
    )

    # Stage 6 — Write graph to Memgraph (non-fatal if Memgraph is down)
    graph_written = False
    try:
        await write_resume_graph(str(user_id), raw_dump)
        await mark_graph_built(resume_id)
        graph_written = True
    except Exception as exc:
        logger.warning("graph_write_failed", resume_id=str(resume_id), error=str(exc))

    # Stage 7 — Inference Engine: compute inferred skills + save to Postgres (non-fatal)
    inferred_count = 0
    inferred_json: dict | None = None
    if graph_written:
        try:
            from firstknock.pipeline.inference.engine import run_inference
            from firstknock.pipeline.inference.seniority import compute_seniority, compute_total_experience_months
            from firstknock.pipeline.persistence.postgres_writer import save_inferred_data

            inferred_result = await run_inference(str(user_id))
            total_months = compute_total_experience_months(raw_dump.get("experience", []))
            seniority = compute_seniority(total_months)
            inferred_json = {
                **inferred_result,
                "seniority": seniority,
                "total_experience_months": total_months,
            }
            await save_inferred_data(resume_id, inferred_json)
            inferred_count = len(inferred_json.get("skills", []))
            logger.info("inference_complete", person_id=str(user_id), inferred=inferred_count, seniority=seniority)
        except Exception as exc:
            logger.warning("inference_failed", person_id=str(user_id), error=str(exc))

    # Stage 8 — Async Enrichment: dispatch Celery tasks (non-blocking, non-fatal)
    enrichment_dispatched = False
    if graph_written:
        try:
            from firstknock.pipeline.enrichment.tasks import dispatch_enrichment

            # Collect inputs for each enricher
            identity = raw_dump.get("identity", {})
            github_url = identity.get("github_url", "")
            linkedin_url = identity.get("linkedin_url", "")

            company_names = [e["company"] for e in raw_dump.get("experience", []) if e.get("company")]
            institution_names = [e["institution"] for e in raw_dump.get("education", []) if e.get("institution")]

            existing_projects = [
                {"project_id": str(__import__("uuid").uuid5(__import__("uuid").NAMESPACE_URL, f"{user_id}:{p['name']}")),
                 "name": p["name"],
                 "github_url": p.get("github_url", "")}
                for p in raw_dump.get("projects", [])
            ]

            all_skills = [
                s for cat in raw_dump.get("skills", {}).values()
                if isinstance(cat, list) for s in cat
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

            dispatch_enrichment(
                resume_id=str(resume_id),
                person_id=str(user_id),
                github_url=github_url,
                linkedin_url=linkedin_url,
                existing_projects=existing_projects,
                company_names=company_names,
                institution_names=institution_names,
                explicit_skills=all_skills,
                company_hints=company_hints,
            )
            enrichment_dispatched = True
        except Exception as exc:
            logger.warning("enrichment_dispatch_failed", resume_id=str(resume_id), error=str(exc))
            if inferred_json:
                try:
                    from firstknock.pipeline.graph.writers import write_graph_final_layer
                    await write_graph_final_layer(str(user_id), inferred_json, None)
                    logger.info("fallback_graph_final_layer_written", person_id=str(user_id))
                except Exception as inner_exc:
                    logger.warning("fallback_graph_write_failed", person_id=str(user_id), error=str(inner_exc))

    # Stage 9 — Async Embedding: generate + write vectors (non-blocking, non-fatal)
    embedding_dispatched = False
    if graph_written:
        try:
            from firstknock.pipeline.embedding.tasks import dispatch_embedding
            dispatch_embedding(str(user_id), str(resume_id), raw_dump)
            embedding_dispatched = True
        except Exception as exc:
            logger.warning("embedding_dispatch_failed", resume_id=str(resume_id), error=str(exc))

    return {
        "user_id": user_id,
        "resume_id": resume_id,
        "source_type": parsed["source_type"],
        "char_count": len(raw_text),
        "sections": list(sections.keys()),
        "identity": {
            "name": extraction.identity.name,
            "email": extraction.identity.email,
        },
        "experience_count": len(extraction.experience),
        "companies": [e.company for e in extraction.experience],
        "project_count": len(extraction.projects),
        "projects": [p.name for p in extraction.projects],
        "raw_skill_count": raw_skill_count,
        "canonical_skill_count": canonical_skill_count,
        "status": "extracted",
        "graph_written": graph_written,
        "inferred_skills": inferred_count,
        "enrichment_dispatched": enrichment_dispatched,
        "embedding_dispatched": embedding_dispatched,
    }
