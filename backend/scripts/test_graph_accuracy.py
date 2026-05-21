"""
Graph accuracy tests for Phase 3.

Loads ground truth from NeonDB (extracted_json) and checks that
every entity was written correctly to Memgraph.

Usage:
    python scripts/test_graph_accuracy.py iamaswinth@gmail.com

Each test prints PASS / FAIL with detail so you can see exactly
what is wrong or missing.
"""

import asyncio
import sys
from firstknock.pipeline.persistence.postgres_writer import get_latest_resume_for_user
from firstknock.pipeline.graph.client import get_driver, close_driver

PASS = "[PASS]"
FAIL = "[FAIL]"

_pass_count = 0
_fail_count = 0


def ok(label: str, detail: str = "") -> None:
    global _pass_count
    _pass_count += 1
    suffix = f"  {detail}" if detail else ""
    print(f"  {PASS} {label}{suffix}")


def fail(label: str, detail: str = "") -> None:
    global _fail_count
    _fail_count += 1
    suffix = f"\n         {detail}" if detail else ""
    print(f"  {FAIL} {label}{suffix}")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def one(session, query: str, **params):
    r = await session.run(query, **params)
    return await r.single()


async def many(session, query: str, **params):
    r = await session.run(query, **params)
    return await r.values()


# ---------------------------------------------------------------------------
# individual test groups
# ---------------------------------------------------------------------------

async def test_person(session, user_id: str, identity: dict) -> None:
    print("\n[1] Person node")
    row = await one(
        session,
        "MATCH (p:Person {person_id: $pid}) RETURN p.name AS name, p.email AS email, p.headline AS headline",
        pid=user_id,
    )
    if row is None:
        fail("Person node exists", "NOT FOUND")
        return

    ok("Person node exists")

    name_ok = row["name"] == identity["name"]
    ok("name correct", row["name"]) if name_ok else fail("name wrong", f"got '{row['name']}' expected '{identity['name']}'")

    email_ok = row["email"] == identity.get("email")
    ok("email correct", row["email"]) if email_ok else fail("email wrong", f"got '{row['email']}' expected '{identity.get('email')}'")

    headline_ok = row["headline"] == identity.get("headline")
    ok("headline correct") if headline_ok else fail("headline wrong", f"got '{row['headline']}'")


async def test_skills(session, user_id: str, skills_block: dict, experience: list) -> None:
    print("\n[2] HAS_SKILL edges (skills block + experience tech_stack)")

    rows = await many(
        session,
        "MATCH (p:Person {person_id: $pid})-[r:HAS_SKILL]->(s:Skill) "
        "RETURN s.name AS name, r.confidence AS conf, r.source AS src, s.category AS cat",
        pid=user_id,
    )
    graph_skills = {row[0]: {"conf": row[1], "src": row[2], "cat": row[3]} for row in rows}

    # expected = main skills block + experience tech_stack (mirrors _collect_skills logic)
    expected: set[str] = set()
    for names in skills_block.values():
        expected.update(n for n in (names or []) if n)
    for exp in experience:
        expected.update(n for n in exp.get("tech_stack", []) if n)

    missing = [s for s in expected if s not in graph_skills]
    extra   = [s for s in graph_skills if s not in expected]

    ok(f"{len(expected)} skills expected, {len(graph_skills)} in graph")

    if missing:
        fail(f"{len(missing)} skills missing from graph", ", ".join(sorted(missing)))
    else:
        ok("all expected skills present")

    if extra:
        fail(f"{len(extra)} unexpected skills in graph", ", ".join(sorted(extra)))
    else:
        ok("no unexpected skills")

    # check confidence + source on all graph skills
    bad_conf  = [s for s, v in graph_skills.items() if v["conf"] != 1.0]
    bad_src   = [s for s, v in graph_skills.items() if v["src"] != "explicit"]
    ok("all HAS_SKILL.confidence = 1.0") if not bad_conf else fail("wrong confidence", ", ".join(bad_conf))
    ok("all HAS_SKILL.source = 'explicit'") if not bad_src else fail("wrong source", ", ".join(bad_src))

    # check categories are set
    no_cat = [s for s, v in graph_skills.items() if not v["cat"]]
    ok("all skills have category") if not no_cat else fail("missing category", ", ".join(no_cat))


async def test_experience(session, user_id: str, experience: list) -> None:
    print("\n[3] WORKED_AT edges (experience)")
    for exp in experience:
        company = exp["company"]
        row = await one(
            session,
            "MATCH (p:Person {person_id: $pid})-[r:WORKED_AT]->(c:Company {name: $company}) "
            "RETURN r.title AS title, r.start_date AS start, r.end_date AS end, "
            "r.months AS months, r.is_current AS is_current, "
            "r.location AS location, r.description AS description, r.skills_used AS skills_used",
            pid=user_id,
            company=company,
        )
        if row is None:
            fail(f"WORKED_AT -> {company}", "edge NOT FOUND")
            continue

        ok(f"WORKED_AT -> {company} exists")

        if row["title"] != exp["title"]:
            fail(f"  title", f"got '{row['title']}' expected '{exp['title']}'")
        else:
            ok(f"  title correct", row["title"])

        if row["start"] != exp.get("start_date"):
            fail(f"  start_date", f"got '{row['start']}' expected '{exp.get('start_date')}'")
        else:
            ok(f"  start_date correct", str(row["start"]))

        if row["end"] != exp.get("end_date"):
            fail(f"  end_date", f"got '{row['end']}' expected '{exp.get('end_date')}'")
        else:
            ok(f"  end_date correct", str(row["end"]))

        if row["months"] != exp.get("months"):
            fail(f"  months", f"got {row['months']} expected {exp.get('months')}")
        else:
            ok(f"  months correct", str(row["months"]))

        if row["is_current"] != exp.get("is_current", False):
            fail(f"  is_current", f"got {row['is_current']} expected {exp.get('is_current')}")
        else:
            ok(f"  is_current correct", str(row["is_current"]))

        if row["location"] != exp.get("location"):
            fail(f"  location", f"got '{row['location']}' expected '{exp.get('location')}'")
        else:
            ok(f"  location correct", str(row["location"]))

        expected_desc = exp.get("description", [])
        got_desc = row["description"] or []
        if not got_desc:
            fail(f"  description", "empty — work bullets not stored")
        elif len(got_desc) != len(expected_desc):
            fail(f"  description length", f"got {len(got_desc)} bullets, expected {len(expected_desc)}")
        else:
            ok(f"  description correct", f"{len(got_desc)} bullets stored")

        expected_skills = set(exp.get("tech_stack", []))
        got_skills = set(row["skills_used"] or [])
        missing_used = expected_skills - got_skills
        if missing_used:
            fail(f"  skills_used missing", ", ".join(sorted(missing_used)))
        else:
            ok(f"  skills_used correct", f"{len(got_skills)} skills")


async def test_experience_tech_stack(session, user_id: str, experience: list) -> None:
    print("\n[4] Experience tech_stack skills -> HAS_SKILL (gap check)")
    rows = await many(
        session,
        "MATCH (p:Person {person_id: $pid})-[r:HAS_SKILL]->(s:Skill) RETURN s.name",
        pid=user_id,
    )
    graph_skill_names = {row[0] for row in rows}

    all_exp_skills = set()
    for exp in experience:
        for skill in exp.get("tech_stack", []):
            if skill:
                all_exp_skills.add(skill)

    missing_exp_skills = all_exp_skills - graph_skill_names
    if missing_exp_skills:
        fail(
            f"{len(missing_exp_skills)} experience tech_stack skills NOT in HAS_SKILL",
            ", ".join(sorted(missing_exp_skills)),
        )
    else:
        ok("all experience tech_stack skills present in graph")


async def test_projects(session, user_id: str, projects: list) -> None:
    print("\n[5] BUILT + USES edges (projects)")
    import uuid as _uuid
    for proj in projects:
        project_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"{user_id}:{proj['name']}"))
        row = await one(
            session,
            "MATCH (p:Person {person_id: $pid})-[:BUILT]->(proj:Project {project_id: $projid}) "
            "RETURN proj.name AS name, proj.description AS desc, proj.url AS url",
            pid=user_id,
            projid=project_id,
        )
        if row is None:
            fail(f"Project '{proj['name']}'", "NOT FOUND in graph")
            continue

        ok(f"Project '{proj['name']}' exists")

        if row["name"] != proj["name"]:
            fail("  name mismatch", f"got '{row['name']}'")
        else:
            ok("  name correct")

        expected_url = proj.get("url") or proj.get("github_url")
        if row["url"] != expected_url:
            fail("  url", f"got '{row['url']}' expected '{expected_url}'")
        else:
            ok("  url correct", str(row["url"]))

        # check tech_stack via USES edges
        uses_rows = await many(
            session,
            "MATCH (proj:Project {project_id: $projid})-[:USES]->(s:Skill) RETURN s.name",
            projid=project_id,
        )
        graph_uses = {row[0] for row in uses_rows}
        expected_uses = set(proj.get("tech_stack", []))
        missing_uses = expected_uses - graph_uses

        ok(f"  {len(graph_uses)}/{len(expected_uses)} USES edges present")
        if missing_uses:
            fail(f"  missing USES skills", ", ".join(sorted(missing_uses)))
        else:
            ok("  all tech_stack skills linked via USES")


async def test_education(session, user_id: str, education: list) -> None:
    print("\n[6] STUDIED_AT edges (education)")
    for edu in education:
        row = await one(
            session,
            "MATCH (p:Person {person_id: $pid})-[r:STUDIED_AT]->(i:Institution {name: $inst}) "
            "RETURN r.degree AS degree, r.field AS field, r.start_year AS start, r.end_year AS end",
            pid=user_id,
            inst=edu["institution"],
        )
        if row is None:
            fail(f"STUDIED_AT -> {edu['institution']}", "edge NOT FOUND")
            continue

        ok(f"STUDIED_AT -> {edu['institution']} exists")

        if row["degree"] != edu.get("degree"):
            fail("  degree", f"got '{row['degree']}' expected '{edu.get('degree')}'")
        else:
            ok("  degree correct", row["degree"])

        if row["field"] != edu.get("field"):
            fail("  field", f"got '{row['field']}' expected '{edu.get('field')}'")
        else:
            ok("  field correct", row["field"])


async def test_co_occurs(session, skills_block: dict) -> None:
    print("\n[7] CO_OCCURS_WITH edges")
    row = await one(session, "MATCH (s1)-[r:CO_OCCURS_WITH]->(s2) RETURN count(r) AS total")
    total = row["total"] if row else 0

    all_skills = []
    for names in skills_block.values():
        all_skills.extend(n for n in (names or []) if n)
    unique = sorted(set(all_skills))
    expected_pairs = len(unique) * (len(unique) - 1) // 2

    ok(f"{total} CO_OCCURS_WITH edges in graph")
    if total < expected_pairs:
        fail(f"expected >= {expected_pairs} pairs for {len(unique)} skills", f"got {total}")
    else:
        ok(f"pair count correct (>= {expected_pairs})")

    # spot-check: two known skills that must co-occur
    row2 = await one(
        session,
        "MATCH (s1:Skill {name: 'Python'})-[r:CO_OCCURS_WITH]-(s2:Skill {name: 'FastAPI'}) "
        "RETURN r.coOccurrence AS count",
    )
    if row2 and row2["count"] and row2["count"] > 0:
        ok("Python <-> FastAPI co-occurrence exists", f"count={row2['count']}")
    else:
        fail("Python <-> FastAPI co-occurrence missing or zero")


async def test_missing_person_properties(session, user_id: str, identity: dict) -> None:
    print("\n[8] Person node — optional properties (known gaps)")
    row = await one(
        session,
        "MATCH (p:Person {person_id: $pid}) "
        "RETURN p.github_url AS gh, p.linkedin_url AS li, p.location AS loc",
        pid=user_id,
    )
    val = row["gh"] if row else None
    ok("github_url stored") if val else fail("github_url NOT stored", f"expected '{identity.get('github_url')}'")

    val = row["li"] if row else None
    ok("linkedin_url stored") if val else fail("linkedin_url NOT stored", f"expected '{identity.get('linkedin_url')}'")

    val = row["loc"] if row else None
    ok("location stored") if val else fail("location NOT stored", f"expected '{identity.get('location')}'")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

async def main(email: str) -> None:
    print("FirstKnock - Graph Accuracy Tests")
    print("=" * 55)

    resume = await get_latest_resume_for_user(email)
    user_id = str(resume.user_id)
    data = resume.extracted_json

    print(f"\nGround truth: resume {resume.resume_id}")
    print(f"Person: {data['identity']['name']} ({user_id})")

    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        await test_person(session, user_id, data["identity"])
        await test_skills(session, user_id, data["skills"], data["experience"])
        await test_experience(session, user_id, data["experience"])
        await test_experience_tech_stack(session, user_id, data["experience"])
        await test_projects(session, user_id, data["projects"])
        await test_education(session, user_id, data["education"])
        await test_co_occurs(session, data["skills"])
        await test_missing_person_properties(session, user_id, data["identity"])

    await close_driver()

    print()
    print("=" * 55)
    print(f"Results: {_pass_count} passed, {_fail_count} failed")
    if _fail_count:
        print("Review the FAIL lines above to see what needs fixing.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_graph_accuracy.py <email>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
