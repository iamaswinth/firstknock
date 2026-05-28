"""
Reset script — wipes Memgraph and recreates Postgres schema from scratch.
Run from the backend directory:
    .venv/Scripts/python.exe scripts/reset_db.py
"""
import asyncio
import subprocess
import sys


async def wipe_memgraph():
    from firstknock.pipeline.graph.client import get_driver
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        await (await session.run("MATCH (n) DETACH DELETE n")).consume()
        result = await session.run("MATCH (n) RETURN count(n) as n")
        record = await result.single()
        print(f"  Memgraph wiped. Remaining nodes: {record['n']}")


def reset_postgres():
    alembic = ".venv/Scripts/alembic.exe"
    print("  Running: alembic downgrade base")
    r = subprocess.run([alembic, "downgrade", "base"], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    print("  Running: alembic upgrade head")
    r = subprocess.run([alembic, "upgrade", "head"], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    for line in r.stdout.splitlines():
        if "Running upgrade" in line:
            print(f"  {line.strip()}")


if __name__ == "__main__":
    print("=== Wiping Memgraph ===")
    asyncio.run(wipe_memgraph())

    print("=== Resetting Postgres ===")
    reset_postgres()

    print("Done.")
