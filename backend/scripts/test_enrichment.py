"""
Test each enricher independently + verify enriched data in Memgraph.

Usage:
    python scripts/test_enrichment.py [--github] [--company] [--institution] [--graph]
    python scripts/test_enrichment.py          # runs all four
"""
import asyncio
import sys
import argparse
from firstknock.pipeline.enrichment.github import enrich_github
from firstknock.pipeline.enrichment.company import enrich_companies
from firstknock.pipeline.enrichment.institution import enrich_institutions


# ── Test data (matches Aswinth's resume) ─────────────────────────────────────
GITHUB_URL = "https://github.com/iamaswinth"
PERSON_ID = "test-person-01"
EXISTING_PROJECTS = []  # empty → all pinned repos treated as new

COMPANIES = ["TechKareer", "Praskla Technology"]
INSTITUTIONS = ["KSR College of Engineering, Tiruchengode"]


# ── Individual enricher tests ─────────────────────────────────────────────────

async def test_github():
    print("\n" + "=" * 60)
    print("GITHUB ENRICHMENT")
    print("=" * 60)
    result = await enrich_github(PERSON_ID, GITHUB_URL, EXISTING_PROJECTS)

    if not result:
        print("  FAIL — empty result (token missing or API error)")
        return

    profile = result.get("profile", {})
    print(f"\n  Profile:")
    print(f"    followers:    {profile.get('followers')}")
    print(f"    public_repos: {profile.get('public_repos')}")
    print(f"    bio:          {profile.get('bio', '')[:80]}")

    repos = result.get("pinned_repos", [])
    print(f"\n  Pinned repos: {len(repos)}")
    for repo in repos:
        status = "NEW" if repo["is_new"] else "MATCHED"
        print(f"\n    [{status}] {repo['name']}")
        print(f"      stars:     {repo['stars']}  forks: {repo['forks']}")
        print(f"      language:  {repo['primary_language']}")
        print(f"      topics:    {repo['topics']}")
        if repo.get("readme_summary"):
            print(f"      summary:   {repo['readme_summary'][:120]}...")
        if repo.get("extracted_skills"):
            print(f"      skills:    {repo['extracted_skills']}")

    ok = len(repos) > 0
    print(f"\n  {'OK' if ok else 'FAIL'}  pinned repos returned: {len(repos)}")
    ok2 = profile.get("followers") is not None
    print(f"  {'OK' if ok2 else 'FAIL'}  profile fetched")


async def test_company():
    print("\n" + "=" * 60)
    print("COMPANY ENRICHMENT  (Perplexity AI)")
    print("=" * 60)
    result = await enrich_companies(COMPANIES)

    for company, data in result.items():
        print(f"\n  {company}:")
        for k, v in data.items():
            print(f"    {k:<15} {v}")

    non_empty = sum(
        1 for d in result.values() if any(v is not None for v in d.values())
    )
    print(f"\n  {'OK' if non_empty > 0 else 'WARN'}  {non_empty}/{len(COMPANIES)} companies enriched")


def test_institution():
    print("\n" + "=" * 60)
    print("INSTITUTION ENRICHMENT  (static lookup)")
    print("=" * 60)
    result = enrich_institutions(INSTITUTIONS)

    for name, data in result.items():
        tier = data.get("ranking_tier", "???")
        print(f"\n  {name}")
        print(f"    ranking_tier: {tier}")

    ok = len(result) == len(INSTITUTIONS)
    print(f"\n  {'OK' if ok else 'FAIL'}  all institutions returned a tier")

    # Bonus: check known universities
    known = {
        "MIT": "top10",
        "Stanford University": "top10",
        "IIT Madras": "top50",
    }
    print("\n  Known-university checks:")
    spot = enrich_institutions(list(known.keys()))
    for name, expected in known.items():
        actual = spot.get(name, {}).get("ranking_tier", "?")
        ok = actual == expected
        print(f"    {'OK' if ok else 'FAIL'}  {name} → {actual}  (expected {expected})")


async def test_graph():
    """Query Memgraph and show enriched properties on nodes."""
    from firstknock.pipeline.graph.client import get_driver, close_driver

    print("\n" + "=" * 60)
    print("MEMGRAPH — enriched node properties")
    print("=" * 60)

    driver = await get_driver()
    async with driver.session(database="memgraph") as s:

        # Projects
        r = await s.run(
            "MATCH (proj:Project) "
            "RETURN proj.name AS name, proj.stars AS stars, "
            "proj.primary_language AS lang, proj.description AS desc "
            "ORDER BY proj.stars DESC NULLS LAST LIMIT 10"
        )
        rows = await r.values()
        print("\n  Projects (top 10 by stars):")
        if rows:
            for name, stars, lang, desc in rows:
                desc_short = (desc or "")[:60]
                print(f"    {name:<30} stars={stars}  lang={lang}  desc={bool(desc_short)}")
        else:
            print("    (none found — run ingestion first)")

        # Companies
        r = await s.run(
            "MATCH (c:Company) "
            "RETURN c.name AS name, c.stage AS stage, c.industry AS industry, "
            "c.headcount AS headcount LIMIT 20"
        )
        rows = await r.values()
        print("\n  Companies:")
        if rows:
            for name, stage, industry, headcount in rows:
                print(f"    {name:<30} stage={stage}  industry={industry}  headcount={headcount}")
        else:
            print("    (none found)")

        # Institutions
        r = await s.run(
            "MATCH (i:Institution) RETURN i.name AS name, i.ranking_tier AS tier"
        )
        rows = await r.values()
        print("\n  Institutions:")
        if rows:
            for name, tier in rows:
                print(f"    {name:<40} tier={tier}")
        else:
            print("    (none found)")

        # Person github stats
        r = await s.run(
            "MATCH (p:Person) WHERE p.github_followers IS NOT NULL "
            "RETURN p.name AS name, p.github_followers AS followers, p.public_repos AS repos"
        )
        rows = await r.values()
        print("\n  Person GitHub stats:")
        if rows:
            for name, followers, repos in rows:
                print(f"    {name:<30} followers={followers}  public_repos={repos}")
        else:
            print("    (none enriched yet — run ingestion + wait 10s)")

    await close_driver()


# ── Entry point ───────────────────────────────────────────────────────────────

async def main(args):
    run_all = not any([args.github, args.company, args.institution, args.graph])

    if run_all or args.github:
        await test_github()

    if run_all or args.company:
        await test_company()

    if run_all or args.institution:
        test_institution()

    if run_all or args.graph:
        await test_graph()

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--github",      action="store_true", help="Test GitHub enricher only")
    parser.add_argument("--company",     action="store_true", help="Test company enricher only")
    parser.add_argument("--institution", action="store_true", help="Test institution enricher only")
    parser.add_argument("--graph",       action="store_true", help="Query Memgraph for enriched data")
    args = parser.parse_args()
    asyncio.run(main(args))
