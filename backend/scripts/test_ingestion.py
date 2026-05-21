import asyncio
import sys
import time
from pathlib import Path
from firstknock.pipeline.parsers.router import parse_file
from firstknock.pipeline.normalization.text_cleaner import clean_text
from firstknock.pipeline.normalization.section_detector import detect_sections
from firstknock.pipeline.extraction.extractor import extract_resume
from firstknock.pipeline.resolution.skill_canonicalizer import canonicalize_skill_list
from firstknock.pipeline.resolution.date_normalizer import normalize_date
from firstknock.pipeline.resolution.company_matcher import match_company
from firstknock.pipeline.persistence.postgres_writer import save_extracted_resume


async def main(pdf_path: str, email: str) -> None:
    print("FirstKnock - Resume Ingestion Test")
    print("=" * 55)
    print()

    start = time.time()

    # Stage 1
    print("[1/5] Parsing PDF...")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    parsed = await parse_file(file_bytes, "pdf")
    raw_text = parsed["raw_text"]
    embedded_links = parsed.get("embedded_links", [])
    print(f"      source: {parsed['source_type']} | chars: {len(raw_text)}")
    print(f"      embedded links: {len(embedded_links)} found")

    # Stage 2
    print()
    print("[2/5] Normalizing text...")
    cleaned = clean_text(raw_text)
    sections = detect_sections(cleaned)
    print(f"      sections: {', '.join(sections.keys())}")
    print(f"      cleaned: {len(cleaned)} chars")

    # Stage 3
    print()
    print("[3/5] Extracting via LLM (claude-sonnet-4-6)...")
    extraction = await extract_resume(cleaned, embedded_links=embedded_links)
    raw_dump = extraction.model_dump()
    raw_skill_count = sum(len(v) for v in raw_dump["skills"].values() if isinstance(v, list))
    companies = [e.company for e in extraction.experience]
    projects = [p.name for p in extraction.projects]
    print(f"      identity:   {extraction.identity.name} <{extraction.identity.email}>")
    print(f"      experience: {len(extraction.experience)} entries ({', '.join(companies)})")
    print(f"      projects:   {len(extraction.projects)} entries ({', '.join(projects)})")
    print(f"      skills:     {raw_skill_count} raw skills extracted")

    # Stage 4
    print()
    print("[4/5] Resolving entities...")
    for category in ("languages", "frameworks", "ai_ml", "databases", "devops", "other"):
        raw_dump["skills"][category] = canonicalize_skill_list(raw_dump["skills"].get(category, []))
    canonical_skill_count = sum(len(v) for v in raw_dump["skills"].values() if isinstance(v, list))

    date_summary = []
    for exp in raw_dump["experience"]:
        norm_start = normalize_date(exp.get("start_date"))
        norm_end = normalize_date(exp.get("end_date"))
        if exp.get("start_date") and norm_start:
            date_summary.append(f"{exp['start_date']}->{norm_start}")
        exp["start_date"] = norm_start
        exp["end_date"] = norm_end
        exp["company"] = match_company(exp["company"])
        exp["tech_stack"] = canonicalize_skill_list(exp.get("tech_stack", []))

    for proj in raw_dump["projects"]:
        proj["tech_stack"] = canonicalize_skill_list(proj.get("tech_stack", []))

    print(f"      {raw_skill_count} raw -> {canonical_skill_count} canonical skills")
    if date_summary:
        print(f"      dates: {', '.join(date_summary)}")

    # Stage 5
    print()
    print("[5/5] Saving to NeonDB...")
    user_id, resume_id = await save_extracted_resume(
        user_email=email,
        source_type=parsed["source_type"],
        raw_text=raw_text,
        extracted_json=raw_dump,
    )
    print(f"      user_id:   {user_id}")
    print(f"      resume_id: {resume_id}")
    print(f"      status:    extracted")

    elapsed = time.time() - start
    print()
    print("=" * 55)
    print(f"Phase 2 complete in {elapsed:.1f}s. Resume saved to NeonDB.")
    print("View at: https://console.neon.tech -> Tables -> resumes")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/test_ingestion.py <pdf_path> <email>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
