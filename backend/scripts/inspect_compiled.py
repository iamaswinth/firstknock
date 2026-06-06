"""
Usage:
    python scripts/inspect_compiled.py                    # latest resume
    python scripts/inspect_compiled.py <email>            # latest resume for email
    python scripts/inspect_compiled.py <resume_id>        # specific resume by UUID
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    from firstknock.pipeline.persistence.db import get_session
    from firstknock.pipeline.persistence.models import Resume, User
    from sqlalchemy import select

    arg = sys.argv[1] if len(sys.argv) > 1 else None

    async with get_session() as session:
        if arg is None:
            # Latest resume overall
            stmt = select(Resume).order_by(Resume.ingested_at.desc()).limit(1)
            result = await session.execute(stmt)
            resume = result.scalar_one_or_none()
        elif "@" in arg:
            # By email
            stmt = (
                select(Resume)
                .join(User, Resume.user_id == User.user_id)
                .where(User.email == arg)
                .order_by(Resume.ingested_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            resume = result.scalar_one_or_none()
        else:
            # By resume UUID
            import uuid
            stmt = select(Resume).where(Resume.resume_id == uuid.UUID(arg))
            result = await session.execute(stmt)
            resume = result.scalar_one_or_none()

    if not resume:
        print("No resume found.")
        return

    print(f"\n{'='*60}")
    print(f"Resume ID : {resume.resume_id}")
    print(f"Status    : {resume.status}  |  graph_built={resume.graph_built}")
    print(f"Ingested  : {resume.ingested_at}")
    print(f"{'='*60}\n")

    compiled = resume.compiled_json
    if not compiled:
        print("compiled_json is NULL — compilation has not run yet or failed.\n")
        print("Current status is:", resume.status)
        return

    experience = compiled.get("experience", [])
    education = compiled.get("education", [])

    print(f"EXPERIENCE  ({len(experience)} entries)")
    print("-" * 60)
    for i, exp in enumerate(experience, 1):
        company_meta = exp.get("company_meta")
        print(f"\n[{i}] {exp.get('company')}  |{exp.get('title')}")
        print(f"    Period  : {exp.get('start_date')} -> {exp.get('end_date')}  ({exp.get('months')} months)")
        print(f"    Source  : {exp.get('source')}")
        print(f"    Location: {exp.get('location')}")
        tech = exp.get("tech_stack", [])
        if tech:
            print(f"    Tech    : {', '.join(tech[:8])}{'...' if len(tech) > 8 else ''}")
        li_skills = exp.get("linkedin_job_skills", [])
        if li_skills:
            print(f"    LI skills: {', '.join(li_skills[:8])}{'...' if len(li_skills) > 8 else ''}")
        if exp.get("linkedin_title"):
            print(f"    LI title : {exp.get('linkedin_title')}  (start: {exp.get('linkedin_start_date')})")
        if company_meta:
            print(f"    Company meta [OK]")
            print(f"      industry  : {company_meta.get('industry')}")
            print(f"      stage     : {company_meta.get('stage')}")
            print(f"      headcount : {company_meta.get('headcount')}")
            print(f"      HQ        : {company_meta.get('headquarters')}")
            print(f"      website   : {company_meta.get('website')}")
            if company_meta.get("founders"):
                print(f"      founders  : {company_meta.get('founders')}")
        else:
            print(f"    Company meta [none] (not enriched or discarded)")

    print(f"\n\nEDUCATION  ({len(education)} entries)")
    print("-" * 60)
    for i, edu in enumerate(education, 1):
        print(f"\n[{i}] {edu.get('institution')}")
        print(f"    {edu.get('degree')} in {edu.get('field')}")
        print(f"    {edu.get('start_year')} -> {edu.get('end_year')}")
        print(f"    Tier   : {edu.get('ranking_tier')}")
        print(f"    Source : {edu.get('source')}")

    print(f"\n\nRAW JSON (full compiled_json):")
    print("-" * 60)
    print(json.dumps(compiled, indent=2, default=str))


asyncio.run(main())
