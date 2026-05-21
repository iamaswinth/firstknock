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
    }
