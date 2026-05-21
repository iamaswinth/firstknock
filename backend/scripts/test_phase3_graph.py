import asyncio
import sys
import time
from pathlib import Path
from firstknock.pipeline.orchestrator import run_sync_ingestion
from firstknock.pipeline.graph.client import get_driver, close_driver


async def main(pdf_path: str, email: str) -> None:
    print("FirstKnock - Phase 3 Graph Write Test")
    print("=" * 55)
    print()

    start = time.time()

    # Run full ingestion (stages 1-5 + graph write)
    print("[1/2] Running full ingestion pipeline...")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    result = await run_sync_ingestion(file_bytes, "pdf", email)
    user_id = str(result["user_id"])

    print(f"      user_id:      {user_id}")
    print(f"      resume_id:    {result['resume_id']}")
    print(f"      graph_written: {result['graph_written']}")

    if not result["graph_written"]:
        print()
        print("ERROR: graph write failed — is Memgraph running? (docker-compose up -d)")
        return

    print()
    print("[2/2] Verifying graph in Memgraph...")

    driver = await get_driver()
    async with driver.session(database="memgraph") as session:

        # Check Person + skills
        r = await session.run(
            "MATCH (p:Person {person_id: $pid})-[:HAS_SKILL]->(s:Skill) RETURN p.name AS name, count(s) AS skill_count",
            pid=user_id,
        )
        row = await r.single()
        if row:
            print(f"      Person:  {row['name']} | skills: {row['skill_count']}")
        else:
            print("      WARN: No Person→Skill edges found")

        # Check companies
        r = await session.run(
            "MATCH (p:Person {person_id: $pid})-[:WORKED_AT]->(c:Company) RETURN c.name AS company",
            pid=user_id,
        )
        records = await r.values()
        companies = [row[0] for row in records]
        print(f"      Companies: {companies}")

        # Check projects + skills
        r = await session.run(
            "MATCH (p:Person {person_id: $pid})-[:BUILT]->(proj:Project)-[:USES]->(s:Skill) "
            "RETURN proj.name AS project, s.name AS skill LIMIT 10",
            pid=user_id,
        )
        records = await r.values()
        if records:
            print(f"      Project->Skill samples:")
            seen = set()
            for proj, skill in records:
                if proj not in seen:
                    print(f"        {proj}")
                    seen.add(proj)
                print(f"            - {skill}")
        else:
            print("      WARN: No Project→Skill edges found")

        # Check co-occurrence edges
        r = await session.run(
            "MATCH (s1:Skill)-[r:CO_OCCURS_WITH]->(s2:Skill) RETURN count(r) AS pairs"
        )
        row = await r.single()
        pair_count = row["pairs"] if row else 0
        print(f"      CO_OCCURS_WITH edges: {pair_count}")

    await close_driver()

    elapsed = time.time() - start
    print()
    print("=" * 55)
    print(f"Phase 3 complete in {elapsed:.1f}s.")
    print("Verify visually at http://localhost:3000 (Memgraph Lab)")
    print()
    print("Cypher to run in Lab:")
    print(f"  MATCH (p:Person {{person_id: '{user_id}'}})-[r:HAS_SKILL]->(s) RETURN p,r,s LIMIT 25")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/test_phase3_graph.py <pdf_path> <email>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
