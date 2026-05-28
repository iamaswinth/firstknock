"""
Test Phase 6 embeddings end-to-end.

Usage:
    python scripts/test_embeddings.py [--embed] [--graph] [--postgres] [--search]
    python scripts/test_embeddings.py          # runs all four
"""
import asyncio
import argparse
from firstknock.pipeline.embedding.embedder import embed_text, build_person_text


# ── Sample person data (matches Aswinth's resume) ─────────────────────────────
SAMPLE_PERSON = {
    "identity": {
        "name": "Aswinthraj Devaraj",
        "headline": "Full Stack AI Engineer",
        "github_url": "https://github.com/iamaswinth",
    },
    "skills": {
        "languages": ["Python", "JavaScript", "SQL"],
        "frameworks": ["FastAPI", "Next.js", "React"],
        "ai_ml": ["LangGraph", "Google ADK", "Gemini Live API", "RAG"],
        "databases": ["PostgreSQL", "Pinecone"],
        "devops": ["Docker", "GitHub Actions"],
        "other": [],
    },
    "experience": [
        {"title": "Software Engineering Intern", "company": "TechKareer"},
        {"title": "Software Engineering Intern", "company": "Praskla Technology"},
    ],
    "projects": [
        {"name": "The Mind Surf"},
        {"name": "Syntax"},
    ],
}


async def test_embed():
    print("\n" + "=" * 60)
    print("EMBEDDER — OpenAI API call")
    print("=" * 60)

    person_text = build_person_text(SAMPLE_PERSON)
    print(f"\n  Input text:\n    {person_text[:200]}...")

    vector = await embed_text(person_text)
    ok_len = len(vector) == 1536
    ok_vals = all(isinstance(v, float) for v in vector[:5])

    print(f"\n  Vector length: {len(vector)}")
    print(f"  First 5 values: {[round(v, 5) for v in vector[:5]]}")
    print(f"\n  {'OK' if ok_len else 'FAIL'}  length == 1536")
    print(f"  {'OK' if ok_vals else 'FAIL'}  values are floats")


async def test_graph():
    from firstknock.pipeline.graph.client import get_driver, close_driver

    print("\n" + "=" * 60)
    print("MEMGRAPH — Person.embedding property")
    print("=" * 60)

    driver = await get_driver()
    async with driver.session(database="memgraph") as s:
        r = await s.run(
            "MATCH (p:Person) WHERE p.embedding IS NOT NULL "
            "RETURN p.name AS name, size(p.embedding) AS dims LIMIT 10"
        )
        rows = await r.values()

    if rows:
        for name, dims in rows:
            ok = dims == 1536
            print(f"  {'OK' if ok else 'FAIL'}  {name}  dims={dims}")
    else:
        print("  (no Person nodes with embeddings yet — run ingestion first)")

    print()
    r2 = None
    async with driver.session(database="memgraph") as s:
        r2 = await s.run(
            "MATCH (proj:Project) WHERE proj.embedding IS NOT NULL "
            "RETURN proj.name AS name, size(proj.embedding) AS dims LIMIT 10"
        )
        proj_rows = await r2.values()

    if proj_rows:
        print("  Projects with embeddings:")
        for name, dims in proj_rows:
            print(f"    OK  {name}  dims={dims}")
    else:
        print("  (no Project nodes with embeddings yet)")

    await close_driver()


async def test_postgres():
    from sqlalchemy import text
    from firstknock.pipeline.persistence.db import get_session

    print("\n" + "=" * 60)
    print("NEONDB — users.embedding column")
    print("=" * 60)

    async with get_session() as session:
        result = await session.execute(
            text("SELECT email, array_length(embedding::real[], 1) AS dims "
                 "FROM users WHERE embedding IS NOT NULL LIMIT 10")
        )
        rows = result.fetchall()

    if rows:
        for email, dims in rows:
            ok = dims == 1536
            print(f"  {'OK' if ok else 'FAIL'}  {email}  dims={dims}")
    else:
        print("  (no users with embeddings yet — run ingestion first)")
        print("  Also check: did you run 'alembic upgrade head'?")


async def test_search():
    from firstknock.pipeline.graph.client import get_driver, close_driver

    print("\n" + "=" * 60)
    print("MEMGRAPH — vector_search semantic query")
    print("=" * 60)

    query_text = "Full Stack AI Engineer with LangGraph and FastAPI"
    print(f"  Query: \"{query_text}\"")

    query_vector = await embed_text(query_text)
    if not query_vector:
        print("  FAIL  could not embed query text")
        return

    driver = await get_driver()
    try:
        async with driver.session(database="memgraph") as s:
            r = await s.run(
                'CALL vector_search.search_nodes("person_embedding", 5, $vec) '
                "YIELD node, score "
                "RETURN node.name AS name, score",
                vec=query_vector,
            )
            rows = await r.values()

        if rows:
            print(f"\n  Top matches:")
            for name, score in rows:
                print(f"    {name:<30} score={score:.4f}")
        else:
            print("  (no results — Person.embedding may not be set yet)")
    except Exception as exc:
        print(f"  FAIL  {exc}")
        print("  (vector_search MAGE module may not be installed in this Memgraph build)")

    await close_driver()


async def main(args):
    run_all = not any([args.embed, args.graph, args.postgres, args.search])

    if run_all or args.embed:
        await test_embed()
    if run_all or args.graph:
        await test_graph()
    if run_all or args.postgres:
        await test_postgres()
    if run_all or args.search:
        await test_search()

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed",    action="store_true", help="Test OpenAI embed call")
    parser.add_argument("--graph",    action="store_true", help="Check Memgraph Person.embedding")
    parser.add_argument("--postgres", action="store_true", help="Check NeonDB users.embedding")
    parser.add_argument("--search",   action="store_true", help="Run vector_search similarity query")
    args = parser.parse_args()
    asyncio.run(main(args))
