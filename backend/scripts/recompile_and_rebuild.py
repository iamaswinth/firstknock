"""
Recompile a resume's compiled_json and rebuild the graph from scratch.
Use this when the prompt has changed and you need fresh graph data
without running the full ingestion pipeline again.

Usage:
    python scripts/recompile_and_rebuild.py <resume_id>
    python scripts/recompile_and_rebuild.py  # uses latest resume
"""
import asyncio
import sys
import uuid as _uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    from firstknock.pipeline.persistence.postgres_writer import (
        get_resume_by_id, save_compiled_profile,
    )
    from firstknock.pipeline.persistence.db import dispose_engine
    from firstknock.pipeline.graph.client import get_driver, close_driver
    from firstknock.pipeline.graph.queries import DELETE_PERSON_AND_RELS
    from firstknock.pipeline.graph.writers import build_full_graph
    from firstknock.pipeline.compilation.compiler import compile_profile

    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg:
        resume_id = _uuid.UUID(arg)
    else:
        from sqlalchemy import select
        from firstknock.pipeline.persistence.models import Resume
        from firstknock.pipeline.persistence.db import get_session
        async with get_session() as session:
            result = await session.execute(
                select(Resume).order_by(Resume.ingested_at.desc()).limit(1)
            )
            r = result.scalar_one()
            resume_id = r.resume_id

    resume = await get_resume_by_id(resume_id)
    person_id = str(resume.user_id)

    print(f"Resume : {resume_id}")
    print(f"Person : {person_id}")
    print(f"Status : {resume.status}")
    print()

    # Step 1: Recompile
    print("Step 1: Recompiling profile with updated prompt...")
    compiled = await compile_profile(resume_id)
    await save_compiled_profile(resume_id, compiled.model_dump())
    print(f"  Compiled: {len(compiled.experience)} experience, {len(compiled.education)} education")
    vertscend = [e for e in compiled.experience if "Vertscend" in e.company]
    for e in vertscend:
        print(f"    [{e.source}] {e.company} | {e.title} | {e.start_date} -> {e.end_date}")
    print()

    # Step 2: Delete existing graph for this person
    print("Step 2: Deleting existing Memgraph data for this person...")
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        await session.run(DELETE_PERSON_AND_RELS, person_id=person_id)
    print(f"  Deleted Person node and all relationships for {person_id}")
    print()

    # Step 3: Rebuild graph from new compiled_json
    print("Step 3: Rebuilding graph from new compiled_json...")
    await build_full_graph(person_id, resume_id)
    print("  Graph rebuilt successfully")
    print()

    # Step 4: Verify
    from firstknock.pipeline.graph.queries import GET_CAREER_WORKED_AT
    print("Step 4: Verifying WORKED_AT edges...")
    async with driver.session(database="memgraph") as session:
        result = await session.run(GET_CAREER_WORKED_AT, person_id=person_id)
        rows = await result.values()
    for row in rows:
        company, title, start, end, months, is_current = row[0], row[1], row[2], row[3], row[4], row[5]
        print(f"  {company} | {title} | {start} -> {end} ({months} months)")

    await close_driver()
    await dispose_engine()
    print("\nDone.")


asyncio.run(main())
