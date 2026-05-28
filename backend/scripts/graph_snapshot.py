"""
Full Memgraph graph snapshot — all nodes, relationships, and enrichment data.
Dynamically discovers all Person nodes; no hardcoded IDs.
"""
import asyncio
from neo4j import AsyncGraphDatabase


async def snapshot():
    driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
    async with driver.session(database="memgraph") as s:

        # ── Node counts ───────────────────────────────────────────────────────
        r = await s.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS c ORDER BY c DESC")
        rows = await r.values()
        print("=" * 60)
        print("  NODE COUNTS")
        print("=" * 60)
        for row in rows:
            print(f"  {row[0]:<20} {row[1]}")

        # ── Relationship counts ───────────────────────────────────────────────
        r = await s.run("MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c ORDER BY c DESC")
        rows = await r.values()
        print()
        print("=" * 60)
        print("  RELATIONSHIP COUNTS")
        print("=" * 60)
        for row in rows:
            print(f"  [{row[0]:<25}]  x{row[1]}")

        # ── Get all persons ───────────────────────────────────────────────────
        r = await s.run("MATCH (p:Person) RETURN p.person_id AS pid ORDER BY p.name")
        pids = [row[0] for row in await r.values()]

        for pid in pids:

            # Person node
            r = await s.run("MATCH (p:Person {person_id: $pid}) RETURN p", pid=pid)
            rows = await r.values()
            if not rows:
                continue
            p = rows[0][0]

            print()
            print("=" * 60)
            print(f"  PERSON: {p.get('name', '?')}")
            print("=" * 60)
            for k, v in sorted(p.items()):
                if k == "embedding":
                    print(f"  {'embedding':<35} [dim={len(v)}]")
                elif v is not None and v != "":
                    print(f"  {k:<35} {v}")

            # ── Skills breakdown ──────────────────────────────────────────────
            r = await s.run(
                "MATCH (p:Person {person_id: $pid})-[r:HAS_SKILL]->(s:Skill) "
                "RETURN r.source AS src, s.category AS cat, count(s) AS c "
                "ORDER BY src, cat", pid=pid
            )
            rows = await r.values()
            print()
            print("  SKILLS BREAKDOWN")
            print("  " + "-" * 56)
            for row in rows:
                cat = str(row[1]) if row[1] is not None else "none"
                print(f"  source={str(row[0]):<12} category={cat:<12} count={row[2]}")

            # ── Explicit skills ───────────────────────────────────────────────
            r = await s.run(
                "MATCH (p:Person {person_id: $pid})-[:HAS_SKILL {source:'explicit'}]->(s:Skill) "
                "RETURN s.name AS n, s.category AS c ORDER BY s.category, s.name", pid=pid
            )
            rows = await r.values()
            print()
            print("  EXPLICIT SKILLS")
            print("  " + "-" * 56)
            by_cat = {}
            for row in rows:
                by_cat.setdefault(row[1], []).append(row[0])
            for cat, names in sorted(by_cat.items()):
                print(f"  [{cat}]")
                for n in names:
                    print(f"    - {n}")

            # ── Inferred skills ───────────────────────────────────────────────
            r = await s.run(
                "MATCH (p:Person {person_id: $pid})-[r:HAS_SKILL {source:'inferred'}]->(s:Skill) "
                "RETURN s.name, r.confidence, r.inferred_by, r.reason "
                "ORDER BY r.confidence DESC", pid=pid
            )
            rows = await r.values()
            print()
            print("  INFERRED SKILLS (by confidence)")
            print("  " + "-" * 56)
            for row in rows:
                conf = row[1] or 0.0
                bar = "#" * int(conf * 20)
                print(f"  {str(row[0]):<30} {conf:.2f}  [{bar:<20}]  via {row[2]}")

            # ── Work experience ───────────────────────────────────────────────
            r = await s.run(
                "MATCH (p:Person {person_id: $pid})-[r:WORKED_AT]->(c:Company) "
                "RETURN c.name, r.title, r.start_date, r.end_date, r.months, r.is_current, r.source "
                "ORDER BY r.is_current DESC, r.start_date DESC", pid=pid
            )
            rows = await r.values()
            print()
            print("  WORK EXPERIENCE")
            print("  " + "-" * 56)
            for row in rows:
                cur = " [current]" if row[5] else ""
                src = f"  source={row[6]}" if row[6] else ""
                print(f"  {row[1]} @ {row[0]}{cur}{src}")
                print(f"    {row[2]} -> {row[3] or 'present'}  |  {row[4] or '?'} months")

            # ── Skills per company ────────────────────────────────────────────
            r = await s.run(
                "MATCH (p:Person {person_id: $pid})-[:WORKED_AT]->(c:Company)-[:USED_SKILL]->(s:Skill) "
                "RETURN c.name, collect(s.name) AS skills", pid=pid
            )
            rows = await r.values()
            if rows:
                print()
                print("  SKILLS PER COMPANY")
                print("  " + "-" * 56)
                for row in rows:
                    print(f"  {row[0]}")
                    for sk in sorted(row[1]):
                        print(f"    - {sk}")

            # ── Projects ─────────────────────────────────────────────────────
            r = await s.run(
                "MATCH (p:Person {person_id: $pid})-[:BUILT]->(proj:Project) "
                "OPTIONAL MATCH (proj)-[:USES]->(s:Skill) "
                "RETURN proj.name, proj.description, proj.github_url, proj.stars, "
                "proj.primary_language, proj.source, collect(s.name) AS stack", pid=pid
            )
            rows = await r.values()
            print()
            print("  PROJECTS")
            print("  " + "-" * 56)
            for row in rows:
                src = f"  [{row[5]}]" if row[5] else ""
                print(f"  {row[0]}{src}  stars={row[3]}  lang={row[4]}")
                if row[1]:
                    print(f"    desc:   {row[1][:100]}")
                if row[2]:
                    print(f"    github: {row[2]}")
                if row[6]:
                    print(f"    stack:  {', '.join(sorted(row[6]))}")

            # ── Education ─────────────────────────────────────────────────────
            r = await s.run(
                "MATCH (p:Person {person_id: $pid})-[r:STUDIED_AT]->(i:Institution) "
                "RETURN i.name, i.ranking_tier, r.degree, r.field, r.start_year, r.end_year",
                pid=pid
            )
            rows = await r.values()
            print()
            print("  EDUCATION")
            print("  " + "-" * 56)
            for row in rows:
                print(f"  {row[2]} in {row[3]} @ {row[0]}")
                print(f"    years: {row[4]} - {row[5]}  |  tier={row[1]}")

        # ── Company enrichment (all) ──────────────────────────────────────────
        r = await s.run(
            "MATCH (c:Company) RETURN c ORDER BY c.name"
        )
        rows = await r.values()
        print()
        print("=" * 60)
        print("  COMPANY INTELLIGENCE")
        print("=" * 60)
        for row in rows:
            c = row[0]
            print(f"\n  {c.get('name', '?')}")
            print("  " + "-" * 40)
            for k in ["stage", "industry", "business_model", "website", "linkedin_url",
                      "description", "founded", "headquarters", "headcount",
                      "total_funding_usd", "last_round_type", "last_round_amount_usd",
                      "last_round_date", "ceo", "founders", "key_investors"]:
                v = c.get(k)
                if v is not None and v != [] and v != "":
                    print(f"  {k:<25} {v}")

        # ── Institution enrichment ────────────────────────────────────────────
        r = await s.run("MATCH (i:Institution) RETURN i.name, i.ranking_tier ORDER BY i.name")
        rows = await r.values()
        print()
        print("=" * 60)
        print("  INSTITUTIONS")
        print("=" * 60)
        for row in rows:
            print(f"  {row[0]:<45} tier={row[1]}")

        # ── SKILL_IMPLIES ─────────────────────────────────────────────────────
        r = await s.run(
            "MATCH (s1:Skill)-[r:SKILL_IMPLIES]->(s2:Skill) "
            "RETURN s1.name, s2.name, r.confidence, r.count "
            "ORDER BY r.count DESC, r.confidence DESC LIMIT 20"
        )
        rows = await r.values()
        print()
        print("=" * 60)
        print("  SKILL_IMPLIES (top 20 by frequency)")
        print("=" * 60)
        for row in rows:
            print(f"  {row[0]:<25} -> {row[1]:<25} conf={row[2]:.2f}  seen={row[3]}x")

        # ── CO_OCCURS_WITH summary ────────────────────────────────────────────
        r = await s.run(
            "MATCH (s1:Skill)-[r:CO_OCCURS_WITH]->(s2:Skill) "
            "RETURN count(r) AS edges, sum(r.coOccurrence) AS total "
        )
        rows = await r.values()
        print()
        print("=" * 60)
        print("  CO_OCCURS_WITH SUMMARY")
        print("=" * 60)
        print(f"  total pair edges:     {rows[0][0]}")
        print(f"  total co-occurrences: {rows[0][1]}")

        # ── Top co-occurring pairs ────────────────────────────────────────────
        r = await s.run(
            "MATCH (s1:Skill)-[r:CO_OCCURS_WITH]->(s2:Skill) "
            "RETURN s1.name, s2.name, r.coOccurrence "
            "ORDER BY r.coOccurrence DESC LIMIT 10"
        )
        rows = await r.values()
        print()
        print("  TOP CO-OCCURRING PAIRS")
        for row in rows:
            print(f"  {row[0]:<25} <-> {row[1]:<25}  x{row[2]}")

    await driver.close()


asyncio.run(snapshot())
