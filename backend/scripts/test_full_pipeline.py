"""
Full pipeline smoke test — runs all 9 stages in-process (no Celery needed).
Usage:
    python scripts/test_full_pipeline.py <path_to_resume.pdf> <email>
    python scripts/test_full_pipeline.py                          # uses bundled sample
"""
import asyncio
import sys
import time
import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── pretty print helpers ──────────────────────────────────────────────────────

def banner(stage: int, total: int, title: str) -> None:
    print()
    print(f"{'='*60}")
    print(f"  STAGE {stage}/{total} — {title}")
    print(f"{'='*60}")

def field(label: str, value) -> None:
    if isinstance(value, list):
        print(f"  {label:<30} {len(value)} items")
        for item in value[:5]:
            print(f"    {'':30} - {item}")
        if len(value) > 5:
            print(f"    {'':30} ... +{len(value) - 5} more")
    elif isinstance(value, dict):
        print(f"  {label:<30}")
        for k, v in list(value.items())[:8]:
            print(f"    {k:<28} {v}")
    else:
        print(f"  {label:<30} {value}")

def ok(msg: str, elapsed: float | None = None) -> None:
    suffix = f"  [{elapsed:.1f}s]" if elapsed else ""
    print(f"  OK  {msg}{suffix}")

def warn(msg: str) -> None:
    print(f"  WARN  {msg}")

def section_break() -> None:
    print(f"  {'-'*56}")


# ── main pipeline ─────────────────────────────────────────────────────────────

async def run(pdf_path: str, email: str) -> None:
    TOTAL = 9

    print()
    print("FIRSTKNOCK — Full Pipeline Test")
    print(f"Resume : {pdf_path}")
    print(f"Email  : {email}")
    pipeline_start = time.time()

    # ── Stage 1: Parse ────────────────────────────────────────────────────────
    banner(1, TOTAL, "Parse")
    t = time.time()
    from firstknock.pipeline.parsers.router import parse_file
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    ext = Path(pdf_path).suffix.lstrip(".").lower()
    parsed = await parse_file(file_bytes, ext)
    raw_text = parsed["raw_text"]
    embedded_links = parsed.get("embedded_links", [])
    ok(f"source_type={parsed['source_type']}  chars={len(raw_text)}", time.time() - t)
    field("embedded_links_found", embedded_links)
    print()
    print("  --- raw text preview (first 300 chars) ---")
    print("  " + raw_text[:300].replace("\n", "\n  "))

    # ── Stage 2: Normalize ────────────────────────────────────────────────────
    banner(2, TOTAL, "Normalize + Section Detection")
    t = time.time()
    from firstknock.pipeline.normalization.text_cleaner import clean_text
    from firstknock.pipeline.normalization.section_detector import detect_sections
    cleaned = clean_text(raw_text)
    sections = detect_sections(cleaned)
    ok(f"cleaned chars={len(cleaned)}  sections={len(sections)}", time.time() - t)
    field("sections_detected", list(sections.keys()))

    # ── Stage 3: LLM Extraction ───────────────────────────────────────────────
    banner(3, TOTAL, "LLM Extraction (Claude)")
    t = time.time()
    from firstknock.pipeline.extraction.extractor import extract_resume
    extraction = await extract_resume(cleaned, embedded_links=embedded_links)
    raw_dump = extraction.model_dump()
    elapsed_3 = time.time() - t
    ok(f"extracted in {elapsed_3:.1f}s")

    section_break()
    print("  IDENTITY")
    field("  name", extraction.identity.name)
    field("  email", extraction.identity.email)
    field("  github_url", extraction.identity.github_url)
    field("  linkedin_url", extraction.identity.linkedin_url)
    field("  location", extraction.identity.location)

    section_break()
    print("  EXPERIENCE")
    for exp in extraction.experience:
        print(f"    {exp.title} @ {exp.company}  ({exp.start_date} - {exp.end_date or 'present'})")
        if exp.tech_stack:
            print(f"      stack: {', '.join(exp.tech_stack[:6])}")

    section_break()
    print("  PROJECTS")
    for proj in extraction.projects:
        print(f"    {proj.name}")
        if proj.tech_stack:
            print(f"      stack: {', '.join(proj.tech_stack[:6])}")

    section_break()
    print("  EDUCATION")
    for edu in extraction.education:
        print(f"    {edu.degree} — {edu.institution}  ({edu.start_year}-{edu.end_year})")

    section_break()
    print("  SKILLS")
    skills = raw_dump["skills"]
    raw_skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))
    for cat, names in skills.items():
        if names:
            print(f"    {cat:<12} {names}")

    # ── Stage 4: Resolution ───────────────────────────────────────────────────
    banner(4, TOTAL, "Resolution (canonicalize, normalize dates, match companies)")
    t = time.time()
    from firstknock.pipeline.resolution.skill_canonicalizer import canonicalize_skill_list
    from firstknock.pipeline.resolution.date_normalizer import normalize_date, date_range_months
    from firstknock.pipeline.resolution.company_matcher import match_company

    print("  Skills:")
    for cat in ("languages", "frameworks", "ai_ml", "databases", "devops", "other"):
        before = raw_dump["skills"].get(cat, [])
        after = canonicalize_skill_list(before)
        raw_dump["skills"][cat] = after
        if before != after:
            print(f"    {cat}: {before} -> {after}")
        elif after:
            print(f"    {cat}: {after}  (unchanged)")

    canonical_skill_count = sum(len(v) for v in raw_dump["skills"].values() if isinstance(v, list))

    print()
    print("  Experience dates + company matching:")
    for exp in raw_dump["experience"]:
        orig_company = exp["company"]
        norm_start = normalize_date(exp.get("start_date"))
        norm_end = normalize_date(exp.get("end_date"))
        months = date_range_months(norm_start, norm_end)
        matched = match_company(orig_company)
        exp["start_date"] = norm_start
        exp["end_date"] = norm_end
        exp["months"] = months
        exp["company"] = matched
        exp["tech_stack"] = canonicalize_skill_list(exp.get("tech_stack", []))
        company_note = f"-> {matched}" if matched != orig_company else ""
        print(f"    {orig_company} {company_note}  |  {norm_start} to {norm_end or 'present'}  ({months or '?'} mo)")

    for proj in raw_dump["projects"]:
        proj["tech_stack"] = canonicalize_skill_list(proj.get("tech_stack", []))

    ok(f"skills: {raw_skill_count} raw -> {canonical_skill_count} canonical", time.time() - t)

    # ── Stage 5: Postgres ─────────────────────────────────────────────────────
    banner(5, TOTAL, "Persist to Postgres (NeonDB)")
    t = time.time()
    from firstknock.pipeline.persistence.postgres_writer import save_extracted_resume, mark_graph_built
    user_id, resume_id = await save_extracted_resume(
        user_email=email,
        source_type=parsed["source_type"],
        raw_text=raw_text,
        extracted_json=raw_dump,
    )
    ok(f"saved", time.time() - t)
    field("user_id", str(user_id))
    field("resume_id", str(resume_id))

    # ── Stage 6: Memgraph (initial graph) ─────────────────────────────────────
    banner(6, TOTAL, "Write Resume Graph to Memgraph")
    t = time.time()
    from firstknock.pipeline.graph.writers import write_resume_graph
    from firstknock.pipeline.graph.queries import COUNT_PERSON_RELS
    from firstknock.pipeline.graph.client import get_driver
    graph_written = False
    try:
        await write_resume_graph(str(user_id), raw_dump)
        await mark_graph_built(resume_id)
        graph_written = True

        driver = await get_driver()
        async with driver.session(database="memgraph") as s:
            r = await s.run(COUNT_PERSON_RELS, person_id=str(user_id))
            rec = await r.single()
            rel_count = rec["rel_count"] if rec else 0
        ok(f"graph written  relationships={rel_count}", time.time() - t)
    except Exception as exc:
        warn(f"Memgraph write failed: {exc}")
        warn("Is Memgraph running? Try: docker start memgraph")

    # ── Stage 7: Inference Engine ─────────────────────────────────────────────
    banner(7, TOTAL, "Inference Engine (inferred skills + seniority)")
    t = time.time()
    inferred_json = None
    if graph_written:
        try:
            from firstknock.pipeline.inference.engine import run_inference
            from firstknock.pipeline.inference.seniority import compute_seniority, compute_total_experience_months
            from firstknock.pipeline.persistence.postgres_writer import save_inferred_data

            inferred_result = await run_inference(str(user_id))
            total_months = compute_total_experience_months(raw_dump.get("experience", []))
            seniority = compute_seniority(total_months)
            inferred_json = {**inferred_result, "seniority": seniority, "total_experience_months": total_months}
            await save_inferred_data(resume_id, inferred_json)

            ok(f"seniority={seniority}  total_experience={total_months}mo  inferred_skills={len(inferred_json.get('skills', []))}", time.time() - t)
            print()
            print("  Inferred skills (top 10):")
            for skill in sorted(inferred_json.get("skills", []), key=lambda s: -s.get("confidence", 0))[:10]:
                bar = int(skill.get("confidence", 0) * 20) * "#"
                print(f"    {skill['name']:<25} conf={skill.get('confidence', 0):.2f}  [{bar:<20}]  via {skill.get('inferred_by', '')}")
        except Exception as exc:
            warn(f"Inference failed: {exc}")
    else:
        warn("Skipped — graph write failed")

    # ── Stage 8a: GitHub Enrichment ───────────────────────────────────────────
    banner(8, TOTAL, "Enrichment — 8a: GitHub")
    t = time.time()
    github_data = {}
    identity = raw_dump.get("identity", {})
    github_url = identity.get("github_url", "")
    linkedin_url = identity.get("linkedin_url", "")
    company_names = [e["company"] for e in raw_dump.get("experience", []) if e.get("company")]
    institution_names = [e["institution"] for e in raw_dump.get("education", []) if e.get("institution")]
    existing_projects = [
        {"project_id": str(__import__("uuid").uuid5(__import__("uuid").NAMESPACE_URL, f"{user_id}:{p['name']}")),
         "name": p["name"], "github_url": p.get("github_url", "")}
        for p in raw_dump.get("projects", [])
    ]
    all_explicit_skills = [s for cat in raw_dump.get("skills", {}).values() if isinstance(cat, list) for s in cat]

    if github_url:
        try:
            from firstknock.pipeline.enrichment.github import enrich_github
            github_data = await enrich_github(str(user_id), github_url, existing_projects)
            profile = github_data.get("profile", {})
            repos = github_data.get("pinned_repos", [])
            ok(f"github enriched  followers={profile.get('followers')}  pinned_repos={len(repos)}", time.time() - t)
            for repo in repos:
                new_tag = " [NEW]" if repo.get("is_new") else ""
                print(f"    {repo['name']:<30} stars={repo.get('stars',0)}  lang={repo.get('primary_language','')}  skills={repo.get('extracted_skills', [])[:3]}{new_tag}")
        except Exception as exc:
            warn(f"GitHub enrichment failed: {exc}")
    else:
        warn("No github_url found in resume — skipping")

    # ── Stage 8b: Company Enrichment (Perplexity) ─────────────────────────────
    print()
    print(f"  --- 8b: Company Enrichment (Perplexity) ---")
    t = time.time()
    company_data = {}
    if company_names:
        try:
            from firstknock.pipeline.enrichment.company import enrich_companies
            company_data = await enrich_companies(company_names)
            ok(f"enriched {len(company_data)} companies", time.time() - t)
            for name, data in company_data.items():
                print(f"    {name}")
                print(f"      stage={data.get('stage')}  funding=${data.get('total_funding_usd')}  ceo={data.get('ceo')}")
                print(f"      investors={data.get('key_investors', [])[:3]}  founders={data.get('founders', [])[:2]}")
        except Exception as exc:
            warn(f"Company enrichment failed: {exc}")
    else:
        warn("No companies found")

    # ── Stage 8c: Institution Enrichment ─────────────────────────────────────
    print()
    print(f"  --- 8c: Institution Enrichment ---")
    t = time.time()
    institution_data = {}
    if institution_names:
        from firstknock.pipeline.enrichment.institution import enrich_institutions
        institution_data = enrich_institutions(institution_names)
        ok(f"enriched {len(institution_data)} institutions", time.time() - t)
        for name, data in institution_data.items():
            print(f"    {name:<40} tier={data.get('ranking_tier')}")
    else:
        warn("No institutions found")

    # ── Stage 8d: LinkedIn Enrichment (Apify) ────────────────────────────────
    print()
    print(f"  --- 8d: LinkedIn Enrichment (Apify) ---")
    t = time.time()
    linkedin_data = {}
    if linkedin_url:
        try:
            from firstknock.pipeline.enrichment.linkedin import enrich_linkedin
            li_profile = await enrich_linkedin(linkedin_url)
            linkedin_data = li_profile.model_dump()
            ok(f"linkedin enriched  positions={len(li_profile.experience)}  skills={len(li_profile.skills)}  connections={li_profile.connections}", time.time() - t)
            print(f"    headline:     {li_profile.headline}")
            print(f"    location:     {li_profile.location}")
            print(f"    followers:    {li_profile.followers}")
            print()
            print(f"    Experience from LinkedIn:")
            for exp in li_profile.experience:
                current = " [current]" if exp.is_current else ""
                print(f"      {exp.title} @ {exp.company}  ({exp.start_date} to {exp.end_date or 'present'}){current}")
        except Exception as exc:
            warn(f"LinkedIn enrichment failed: {exc}")
    else:
        warn("No linkedin_url found in resume — skipping")

    # ── Stage 8e: Enrich LinkedIn-only companies ──────────────────────────────
    print()
    print(f"  --- 8e: LinkedIn-only Company Enrichment ---")
    t = time.time()
    linkedin_experience = linkedin_data.get("experience", [])
    if linkedin_experience:
        resume_company_set = {c.lower() for c in company_names if c}
        new_li_companies = list({
            exp["company"] for exp in linkedin_experience
            if exp.get("company") and exp["company"].lower() not in resume_company_set
        })
        if new_li_companies:
            print(f"  New companies found on LinkedIn (not in resume): {new_li_companies}")
            try:
                from firstknock.pipeline.enrichment.company import enrich_companies
                new_enriched = await enrich_companies(new_li_companies)
                ok(f"enriched {len(new_enriched)} new companies", time.time() - t)
                for name, data in new_enriched.items():
                    print(f"    {name}")
                    print(f"      stage={data.get('stage')}  funding=${data.get('total_funding_usd')}  ceo={data.get('ceo')}")
                    company_data[name] = data
            except Exception as exc:
                warn(f"LinkedIn company enrichment failed: {exc}")
        else:
            ok("No new companies found on LinkedIn — all already in resume")
    else:
        warn("No LinkedIn experience to diff")

    # ── Stage 8f: Write Final Graph Layer ─────────────────────────────────────
    banner(8, TOTAL, "Enrichment — 8f: Write Final Layer to Memgraph")
    t = time.time()
    if graph_written:
        try:
            from firstknock.pipeline.graph.writers import write_graph_final_layer
            enriched_payload = {
                "github": github_data,
                "companies": company_data,
                "institutions": institution_data,
                "linkedin": linkedin_data,
            }
            await write_graph_final_layer(
                str(user_id),
                inferred_json,
                enriched_payload,
                set(s.lower() for s in all_explicit_skills),
            )
            driver = await get_driver()
            async with driver.session(database="memgraph") as s:
                r = await s.run(COUNT_PERSON_RELS, person_id=str(user_id))
                rec = await r.single()
                final_rel_count = rec["rel_count"] if rec else 0
            ok(f"final graph written  total_relationships={final_rel_count}", time.time() - t)
        except Exception as exc:
            warn(f"Final graph write failed: {exc}")
    else:
        warn("Skipped — initial graph write failed")

    # ── Stage 9: Embedding ────────────────────────────────────────────────────
    banner(9, TOTAL, "Embeddings (OpenAI text-embedding-3-small)")
    t = time.time()
    try:
        from firstknock.pipeline.embedding.writer import embed_and_write
        result = await embed_and_write(str(user_id), str(resume_id), raw_dump)
        ok(f"embeddings written  person_dim={result.get('person_embedding_dim')}  projects={result.get('project_count')}", time.time() - t)
        for k, v in result.items():
            print(f"    {k:<30} {v}")
    except Exception as exc:
        warn(f"Embedding failed: {exc}")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_elapsed = time.time() - pipeline_start
    print()
    print(f"{'='*60}")
    print(f"  PIPELINE COMPLETE  ({total_elapsed:.1f}s total)")
    print(f"{'='*60}")
    print(f"  user_id     : {user_id}")
    print(f"  resume_id   : {resume_id}")
    print(f"  experience  : {len(raw_dump.get('experience', []))} entries")
    print(f"  skills      : {canonical_skill_count} canonical ({raw_skill_count} raw)")
    print(f"  inferred    : {len(inferred_json.get('skills', [])) if inferred_json else 0} skills")
    print(f"  companies   : {len(company_data)} enriched")
    print(f"  institutions: {len(institution_data)} enriched")
    print(f"  linkedin    : {len(linkedin_data.get('experience', []))} positions")
    print()
    from firstknock.pipeline.persistence.db import dispose_engine
    await dispose_engine()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        pdf_path = sys.argv[1]
        email = sys.argv[2]
    elif len(sys.argv) == 1:
        # default to bundled sample
        pdf_path = str(Path(__file__).parent.parent.parent / "docs" / "AI Intern - Aswinthraj.pdf")
        email = "test@firstknock.ai"
        print(f"No args given — using default: {pdf_path}")
    else:
        print("Usage: python scripts/test_full_pipeline.py <resume.pdf> <email>")
        sys.exit(1)

    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    asyncio.run(run(pdf_path, email))
