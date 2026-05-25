import asyncio
from neo4j import AsyncGraphDatabase


async def check():
    driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
    async with driver.session(database="memgraph") as s:
        r1 = await s.run(
            "MATCH (s1:Skill)-[r:SKILL_IMPLIES]->(s2:Skill) "
            "RETURN s1.name AS from_skill, s2.name AS to_skill, r.confidence, r.count "
            "ORDER BY r.count DESC LIMIT 10"
        )
        rows1 = await r1.values()
        print("=== SKILL_IMPLIES edges (top 10 by count) ===")
        for row in rows1:
            print(f"  {row[0]} -> {row[1]}  conf={row[2]:.2f}  count={row[3]}")

        r2 = await s.run(
            "MATCH (p:Person)-[r:HAS_SKILL {source: 'inferred'}]->(s:Skill) "
            "RETURN s.name, r.inferred_by, r.confidence, r.reason "
            "ORDER BY r.confidence DESC LIMIT 10"
        )
        rows2 = await r2.values()
        print("\n=== HAS_SKILL inferred edges (top 10 by confidence) ===")
        for row in rows2:
            print(f"  {row[0]}  inferred_by={row[1]}  conf={row[2]:.2f}  reason={row[3]}")

    await driver.close()


asyncio.run(check())
