"""
Daily scraper — fetches all actively-hiring YC companies from workatastartup.com
and upserts them into Neon PostgreSQL.

Usage:
    # First time (or when session expires):
    python auth.py

    # Daily run:
    python main.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from client import SessionExpiredError, WaaSClient
from config import COOKIES_FILE, ALGOLIA_KEY_FILE, DATABASE_URL, FETCH_BATCH_SIZE
import notify
import pg_db


def _check_prerequisites() -> None:
    missing = [f for f in (COOKIES_FILE, ALGOLIA_KEY_FILE) if not Path(f).exists()]
    if missing:
        print(
            f"Missing auth files: {', '.join(missing)}\n"
            "Run  python auth.py  first to log in and capture your session."
        )
        sys.exit(1)
    if not DATABASE_URL:
        print("DATABASE_URL not set — add it to waas_scraper/.env and retry.")
        sys.exit(1)


async def run() -> None:
    _check_prerequisites()

    started_at = datetime.now(timezone.utc)
    print(f"=== waas_scraper  {started_at:%Y-%m-%d %H:%M UTC} ===\n")

    try:
        async with WaaSClient() as client:

            print("[1] Querying Algolia for company IDs...")
            company_ids = await client.get_all_company_ids()
            print(f"    -> {len(company_ids)} companies found\n")

            if not company_ids:
                raise RuntimeError("No companies returned from Algolia.")

            print(f"[2] Fetching details ({len(company_ids)} companies, "
                  f"batches of {FETCH_BATCH_SIZE})...")
            companies = await client.fetch_all_companies(company_ids)
            print(f"    -> {len(companies)} companies retrieved\n")

        print("[3] Writing to Neon PostgreSQL...")
        conn = pg_db.get_conn()
        stats = pg_db.upsert_run(conn, companies)
        conn.close()

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        summary = (
            f"Done in {elapsed:.0f}s\n"
            f"  New companies : {stats['new_companies']}\n"
            f"  New jobs      : {stats['new_jobs']}\n"
            f"  Closed jobs   : {stats['closed_jobs']}"
        )
        print(f"\n=== {summary} ===")

        notify.send(
            f"✅ <b>WaaS Scraper</b> — {started_at:%Y-%m-%d %H:%M UTC}\n\n"
            + summary
        )

    except Exception as e:
        msg = str(e) or type(e).__name__
        print(f"\n[error] {msg}")
        notify.send(
            f"❌ <b>WaaS Scraper FAILED</b> — {started_at:%Y-%m-%d %H:%M UTC}\n\n"
            + msg
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run())
