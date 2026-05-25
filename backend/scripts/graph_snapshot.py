import asyncio
from neo4j import AsyncGraphDatabase

PERSON_ID = "01e46dca-8d5a-434f-8550-009a601a8c67"

async def snapshot():
    driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
    async with driver.session(database="memgraph") as s:

        # Node counts
        r = await s.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC")
        rows = await r.values()
        print("=== NODE COUNTS ===")
        for row in rows:
            print(f"  {row[0]:<20} {row[1]}")

        # Relationship counts
        r = await s.run("MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS count ORDER BY count DESC")
        rows = await r.values()
        print("\n=== RELATIONSHIP COUNTS ===")
        for row in rows:
            print(f"  {row[0]:<30} {row[1]}")

        # Person
        r = await s.run("MATCH (p:Person {person_id: $pid}) RETURN p", pid=PERSON_ID)
        rows = await r.values()
        print("\n=== PERSON ===")
        p = rows[0][0]
        for k, v in p.items():
            print(f"  {k:<30} {v}")

        # Skills breakdown
        r = await s.run(
            "MATCH (p:Person {person_id: $pid})-[r:HAS_SKILL]->(s:Skill) "
            "RETURN r.source AS source, s.category AS category, count(s) AS count "
            "ORDER BY source, category",
            pid=PERSON_ID
        )
        rows = await r.values()
        print("\n=== SKILLS BREAKDOWN (source x category) ===")
        for row in rows:
            print(f"  source={row[0]:<12} category={row[1]:<12} count={row[2]}")

        # Explicit skills list
        r = await s.run(
            "MATCH (p:Person {person_id: $pid})-[:HAS_SKILL {source:'explicit'}]->(s:Skill) "
            "RETURN s.name AS name, s.category AS category ORDER BY s.category, s.name",
            pid=PERSON_ID
        )
        rows = await r.values()
        print("\n=== EXPLICIT SKILLS ===")
        for row in rows:
            print(f"  [{row[1]:<10}] {row[0]}")

        # Inferred skills
        r = await s.run(
            "MATCH (p:Person {person_id: $pid})-[r:HAS_SKILL {source:'inferred'}]->(s:Skill) "
            "RETURN s.name, r.confidence, r.inferred_by, r.reason "
            "ORDER BY r.confidence DESC",
            pid=PERSON_ID
        )
        rows = await r.values()
        print("\n=== INFERRED SKILLS (by confidence) ===")
        for row in rows:
            print(f"  {row[0]:<30} conf={row[1]:.2f}  because={row[2]}  ({row[3]})")

        # Work experience
        r = await s.run(
            "MATCH (p:Person {person_id: $pid})-[r:WORKED_AT]->(c:Company) "
            "RETURN c.name, r.title, r.start_date, r.end_date, r.months, r.is_current "
            "ORDER BY r.is_current DESC, r.start_date DESC",
            pid=PERSON_ID
        )
        rows = await r.values()
        print("\n=== WORK EXPERIENCE ===")
        for row in rows:
            current = " (current)" if row[5] else ""
            print(f"  {row[1]} @ {row[0]}{current}")
            print(f"    {row[2]} -> {row[3]}  |  {row[4]} months")

        # Skills per company
        r = await s.run(
            "MATCH (p:Person {person_id: $pid})-[:WORKED_AT]->(c:Company)-[:USED_SKILL]->(s:Skill) "
            "RETURN c.name AS company, collect(s.name) AS skills",
            pid=PERSON_ID
        )
        rows = await r.values()
        print("\n=== SKILLS PER COMPANY ===")
        for row in rows:
            print(f"  {row[0]}")
            for sk in row[1]:
                print(f"    - {sk}")

        # Projects
        r = await s.run(
            "MATCH (p:Person {person_id: $pid})-[:BUILT]->(proj:Project) "
            "OPTIONAL MATCH (proj)-[:USES]->(s:Skill) "
            "RETURN proj.name, proj.description, proj.url, proj.github_url, collect(s.name) AS stack",
            pid=PERSON_ID
        )
        rows = await r.values()
        print("\n=== PROJECTS ===")
        for row in rows:
            print(f"  {row[0]}")
            print(f"    {row[1][:80] if row[1] else 'no description'}...")
            if row[2]: print(f"    url:    {row[2]}")
            if row[3]: print(f"    github: {row[3]}")
            print(f"    stack:  {', '.join(row[4])}")

        # Education
        r = await s.run(
            "MATCH (p:Person {person_id: $pid})-[r:STUDIED_AT]->(i:Institution) "
            "RETURN i.name, r.degree, r.field, r.start_year, r.end_year",
            pid=PERSON_ID
        )
        rows = await r.values()
        print("\n=== EDUCATION ===")
        for row in rows:
            print(f"  {row[1]} in {row[2]} @ {row[0]}  ({row[3]} - {row[4]})")

        # SKILL_IMPLIES
        r = await s.run(
            "MATCH (s1:Skill)-[r:SKILL_IMPLIES]->(s2:Skill) "
            "RETURN s1.name, s2.name, r.confidence, r.count "
            "ORDER BY r.count DESC, r.confidence DESC LIMIT 15"
        )
        rows = await r.values()
        print("\n=== SKILL_IMPLIES (top 15) ===")
        for row in rows:
            print(f"  {row[0]:<25} → {row[1]:<25} conf={row[2]:.2f}  seen={row[3]}x")

        # CO_OCCURS_WITH
        r = await s.run(
            "MATCH (s1:Skill)-[r:CO_OCCURS_WITH]->(s2:Skill) "
            "RETURN count(r) AS total_edges, sum(r.coOccurrence) AS total_co_occurrences"
        )
        rows = await r.values()
        print("\n=== CO_OCCURS_WITH SUMMARY ===")
        print(f"  total edges:          {rows[0][0]}")
        print(f"  total co-occurrences: {rows[0][1]}")

    await driver.close()

asyncio.run(snapshot())
