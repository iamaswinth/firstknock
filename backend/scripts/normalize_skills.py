"""
One-time skill normalization script.

Fixes:
  1. Case duplicates (e.g. 'prompt engineering' vs 'Prompt engineering')
  2. Synonym duplicates (e.g. 'CI/CD' vs 'CI/CD pipelines') via LLM
  3. Removes low-quality inferred HAS_SKILL edges (no inferred_by, conf < 0.6)

Run once after Phase 4 is complete, then re-ingest resumes for a clean graph.
"""
import asyncio
import json
import anthropic
from collections import defaultdict
from neo4j import AsyncGraphDatabase
from firstknock.config import settings

BOLT_URI = "bolt://localhost:7687"


# ── Merge helpers ─────────────────────────────────────────────────────────────

async def _rel_count(session, name: str) -> int:
    r = await session.run(
        "MATCH (s:Skill {name: $name})-[r]-() RETURN count(r) AS n", name=name
    )
    row = await r.single()
    return row["n"] if row else 0


async def merge_skill_nodes(session, canonical: str, duplicate: str) -> None:
    """Move all relationships from duplicate Skill to canonical, then delete duplicate."""

    # HAS_SKILL (Person → Skill)
    r = await session.run(
        "MATCH (p:Person)-[r:HAS_SKILL]->(s:Skill {name: $dup}) "
        "RETURN p.person_id, r.source, r.confidence, r.inferred_by, r.reason",
        dup=duplicate,
    )
    for row in await r.values():
        await session.run(
            "MATCH (p:Person {person_id: $pid}), (s:Skill {name: $can}) "
            "MERGE (p)-[r:HAS_SKILL {source: $src}]->(s) "
            "ON CREATE SET r.confidence=$conf, r.inferred_by=$ib, r.reason=$reason "
            "ON MATCH SET  r.confidence=$conf, r.inferred_by=$ib, r.reason=$reason",
            pid=row[0], can=canonical, src=row[1],
            conf=row[2], ib=row[3] or "", reason=row[4] or "",
        )

    # USES (Project → Skill)
    r = await session.run(
        "MATCH (proj:Project)-[:USES]->(s:Skill {name: $dup}) RETURN proj.project_id",
        dup=duplicate,
    )
    for row in await r.values():
        await session.run(
            "MATCH (proj:Project {project_id: $pid}), (s:Skill {name: $can}) "
            "MERGE (proj)-[:USES]->(s)",
            pid=row[0], can=canonical,
        )

    # USED_SKILL (Company → Skill)
    r = await session.run(
        "MATCH (c:Company)-[:USED_SKILL]->(s:Skill {name: $dup}) RETURN c.name",
        dup=duplicate,
    )
    for row in await r.values():
        await session.run(
            "MATCH (c:Company {name: $cname}), (s:Skill {name: $can}) "
            "MERGE (c)-[:USED_SKILL]->(s)",
            cname=row[0], can=canonical,
        )

    # CO_OCCURS_WITH outbound (dup → other): sum coOccurrence
    r = await session.run(
        "MATCH (s:Skill {name: $dup})-[r:CO_OCCURS_WITH]->(other:Skill) "
        "RETURN other.name, r.coOccurrence",
        dup=duplicate,
    )
    for row in await r.values():
        if row[0] == canonical:
            continue
        await session.run(
            "MATCH (s1:Skill {name: $can}), (s2:Skill {name: $other}) "
            "MERGE (s1)-[r:CO_OCCURS_WITH]->(s2) "
            "ON CREATE SET r.coOccurrence = $n "
            "ON MATCH SET  r.coOccurrence = r.coOccurrence + $n",
            can=canonical, other=row[0], n=row[1],
        )

    # CO_OCCURS_WITH inbound (other → dup): sum coOccurrence
    r = await session.run(
        "MATCH (other:Skill)-[r:CO_OCCURS_WITH]->(s:Skill {name: $dup}) "
        "RETURN other.name, r.coOccurrence",
        dup=duplicate,
    )
    for row in await r.values():
        if row[0] == canonical:
            continue
        await session.run(
            "MATCH (s1:Skill {name: $other}), (s2:Skill {name: $can}) "
            "MERGE (s1)-[r:CO_OCCURS_WITH]->(s2) "
            "ON CREATE SET r.coOccurrence = $n "
            "ON MATCH SET  r.coOccurrence = r.coOccurrence + $n",
            other=row[0], can=canonical, n=row[1],
        )

    # SKILL_IMPLIES outbound (dup → other)
    r = await session.run(
        "MATCH (s:Skill {name: $dup})-[r:SKILL_IMPLIES]->(other:Skill) "
        "RETURN other.name, r.confidence, r.reason, r.count",
        dup=duplicate,
    )
    for row in await r.values():
        if row[0] == canonical:
            continue
        await session.run(
            "MATCH (s1:Skill {name: $can}), (s2:Skill {name: $other}) "
            "MERGE (s1)-[r:SKILL_IMPLIES]->(s2) "
            "ON CREATE SET r.confidence=$conf, r.reason=$reason, r.count=$cnt "
            "ON MATCH SET  r.confidence=(r.confidence*r.count+$conf)/(r.count+$cnt), r.count=r.count+$cnt",
            can=canonical, other=row[0], conf=row[1], reason=row[2] or "", cnt=row[3] or 1,
        )

    # SKILL_IMPLIES inbound (other → dup)
    r = await session.run(
        "MATCH (other:Skill)-[r:SKILL_IMPLIES]->(s:Skill {name: $dup}) "
        "RETURN other.name, r.confidence, r.reason, r.count",
        dup=duplicate,
    )
    for row in await r.values():
        if row[0] == canonical:
            continue
        await session.run(
            "MATCH (s1:Skill {name: $other}), (s2:Skill {name: $can}) "
            "MERGE (s1)-[r:SKILL_IMPLIES]->(s2) "
            "ON CREATE SET r.confidence=$conf, r.reason=$reason, r.count=$cnt "
            "ON MATCH SET  r.confidence=(r.confidence*r.count+$conf)/(r.count+$cnt), r.count=r.count+$cnt",
            other=row[0], can=canonical, conf=row[1], reason=row[2] or "", cnt=row[3] or 1,
        )

    # Delete duplicate
    await session.run("MATCH (s:Skill {name: $dup}) DETACH DELETE s", dup=duplicate)


# ── LLM synonym detection ─────────────────────────────────────────────────────

async def find_synonym_groups(skill_names: list[str]) -> list[dict]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    skill_list = "\n".join(f"- {n}" for n in sorted(skill_names))
    prompt = f"""You are a skill deduplication engine for a resume graph database.

Given these skill node names:
{skill_list}

Find groups of skills that are clearly the same concept under different names.
Examples of valid groups: 'CI/CD' + 'CI/CD pipelines', 'npm/yarn' + 'npm', 'JavaScript' + 'JS'
Examples of INVALID groups (related but NOT the same): 'Docker' + 'Containerization', 'PostgreSQL' + 'asyncpg'

Rules:
- Only group skills that are genuinely synonymous (same thing, different label)
- The canonical name should be the cleaner, more widely-used version
- If unsure, do NOT group them
- Return JSON array of groups that have at least 2 members

Return ONLY valid JSON in this format (empty array [] if no synonyms found):
[{{"canonical": "CI/CD", "synonyms": ["CI/CD pipelines", "CI/CD Pipeline"]}}]"""

    response = await client.messages.create(
        model=settings.inference_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print(f"  [warn] LLM synonym parse failed: {raw[:100]}")
        return []


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    driver = AsyncGraphDatabase.driver(BOLT_URI, auth=("", ""))
    async with driver.session(database="memgraph") as session:

        # Fetch all skill names + relationship counts
        r = await session.run(
            "MATCH (s:Skill) "
            "OPTIONAL MATCH (s)-[r]-() "
            "RETURN s.name AS name, count(r) AS rels"
        )
        rows = await r.values()
        all_skills = {row[0]: row[1] for row in rows}
        print(f"Total skill nodes: {len(all_skills)}")

        # ── Step 1: Case duplicates ──────────────────────────────────────────
        groups: dict[str, list[str]] = defaultdict(list)
        for name in all_skills:
            groups[name.lower()].append(name)

        case_pairs: list[tuple[str, str]] = []
        for key, members in groups.items():
            if len(members) < 2:
                continue
            # Pick most-connected as canonical
            canonical = max(members, key=lambda n: all_skills.get(n, 0))
            for dup in members:
                if dup != canonical:
                    case_pairs.append((canonical, dup))

        if case_pairs:
            print(f"\nCase duplicates found ({len(case_pairs)}):")
            for canonical, dup in case_pairs:
                print(f"  MERGE '{dup}' -> '{canonical}'")
            for canonical, dup in case_pairs:
                await merge_skill_nodes(session, canonical, dup)
                del all_skills[dup]
            print(f"  Done. {len(case_pairs)} duplicate(s) removed.")
        else:
            print("\nNo case duplicates found.")

        # ── Step 2: LLM synonym detection ────────────────────────────────────
        remaining = list(all_skills.keys())
        print(f"\nSending {len(remaining)} skills to LLM for synonym detection...")
        synonym_groups = await find_synonym_groups(remaining)

        if synonym_groups:
            print(f"Synonym groups found ({len(synonym_groups)}):")
            for group in synonym_groups:
                canonical = group.get("canonical", "").strip()
                synonyms = [s.strip() for s in group.get("synonyms", [])]
                valid_synonyms = [s for s in synonyms if s in all_skills and s != canonical]
                if not canonical or not valid_synonyms:
                    continue
                if canonical not in all_skills:
                    print(f"  [skip] canonical '{canonical}' not in graph")
                    continue
                print(f"  MERGE {valid_synonyms} -> '{canonical}'")
                for dup in valid_synonyms:
                    await merge_skill_nodes(session, canonical, dup)
                    del all_skills[dup]
            print("  Done.")
        else:
            print("No synonym groups found.")

        # ── Step 3: Remove low-quality inferred edges ────────────────────────
        r = await session.run(
            "MATCH (p:Person)-[r:HAS_SKILL {source:'inferred'}]->(s:Skill) "
            "WHERE r.confidence < 0.6 AND (r.inferred_by IS NULL OR r.inferred_by = '') "
            "DELETE r "
            "RETURN count(r) AS removed"
        )
        row = await r.single()
        removed = row["removed"] if row else 0
        print(f"\nLow-quality inferred edges removed: {removed}")

        # ── Final count ──────────────────────────────────────────────────────
        r = await session.run("MATCH (s:Skill) RETURN count(s) AS n")
        row = await r.single()
        print(f"\nSkill nodes after normalization: {row['n']}")

    await driver.close()
    print("\nDone. Re-ingest resumes to rebuild CO_OCCURS_WITH from clean names.")


asyncio.run(main())
