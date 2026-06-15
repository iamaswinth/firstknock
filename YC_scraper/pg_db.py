"""
PostgreSQL (Neon) database layer — batch-optimised.

Strategy: two bulk SELECTs to find existing IDs, then execute_values for
batch upserts. Total round-trips: ~6 regardless of how many rows there are.
"""
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values, Json

from config import DATABASE_URL

# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS companies (
        id                 INTEGER PRIMARY KEY,
        name               TEXT,
        slug               TEXT UNIQUE,
        batch              TEXT,
        website            TEXT,
        one_liner          TEXT,
        description        TEXT,
        hiring_description TEXT,
        tech_description   TEXT,
        primary_vertical   TEXT,
        parent_sector      TEXT,
        child_sector       TEXT,
        team_size          INTEGER,
        location           TEXT,
        country            TEXT,
        twitter_url        TEXT,
        fb_url             TEXT,
        is_hiring          BOOLEAN DEFAULT TRUE,
        first_seen_at      TIMESTAMPTZ NOT NULL,
        last_seen_at       TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id                        INTEGER PRIMARY KEY,
        company_id                INTEGER NOT NULL REFERENCES companies(id),
        title                     TEXT,
        description               TEXT,
        job_type                  TEXT,
        role                      TEXT,
        salary_min                INTEGER,
        salary_max                INTEGER,
        equity_min                DOUBLE PRECISION,
        equity_max                DOUBLE PRECISION,
        remote                    TEXT,
        visa                      TEXT,
        locations                 JSONB,
        skills                    JSONB,
        show_path                 TEXT,
        interview_process         TEXT,
        min_experience            INTEGER,
        pretty_salary_range       TEXT,
        pretty_location_or_remote TEXT,
        is_active                 BOOLEAN DEFAULT TRUE,
        first_seen_at             TIMESTAMPTZ NOT NULL,
        last_seen_at              TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS founders (
        id            INTEGER PRIMARY KEY,
        company_id    INTEGER NOT NULL REFERENCES companies(id),
        full_name     TEXT,
        founder_bio   TEXT,
        linkedin      TEXT,
        first_seen_at TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_jobs_company     ON jobs(company_id)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_active      ON jobs(is_active)",
    "CREATE INDEX IF NOT EXISTS idx_founders_company ON founders(company_id)",
]


# ── Connection ────────────────────────────────────────────────────────────────

def get_conn() -> "psycopg2.extensions.connection":
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        for stmt in _SCHEMA:
            cur.execute(stmt)
    conn.commit()
    return conn


# ── Upsert ────────────────────────────────────────────────────────────────────

def upsert_run(conn: "psycopg2.extensions.connection", companies: list[dict]) -> dict:
    """
    Upsert all companies, jobs, and founders in ~6 round-trips regardless of
    how many rows there are (bulk SELECT + execute_values batch INSERT).

    first_seen_at is set on insert and never overwritten on conflict.
    """
    now = datetime.now(timezone.utc)
    stats = {"new_companies": 0, "new_jobs": 0, "closed_jobs": 0}

    # Flatten all jobs and founders once so we don't re-iterate per table
    all_jobs: list[tuple[int, dict]] = [
        (c["id"], job)
        for c in companies
        for job in c.get("jobs", [])
    ]
    all_founders: list[tuple[int, dict]] = [
        (c["id"], founder)
        for c in companies
        for founder in c.get("founders", [])
        if founder.get("id")
    ]
    seen_job_ids: list[int] = [job["id"] for _, job in all_jobs]

    with conn.cursor() as cur:

        # ── Companies ────────────────────────────────────────────────────────
        company_ids = [c["id"] for c in companies]
        cur.execute("SELECT id FROM companies WHERE id = ANY(%s)", (company_ids,))
        existing_companies = {row[0] for row in cur.fetchall()}
        stats["new_companies"] = len(company_ids) - len(existing_companies)

        if companies:
            execute_values(
                cur,
                """
                INSERT INTO companies
                    (id, name, slug, batch, website, one_liner, description,
                     hiring_description, tech_description, primary_vertical,
                     parent_sector, child_sector, team_size, location, country,
                     twitter_url, fb_url, is_hiring, first_seen_at, last_seen_at)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    name               = EXCLUDED.name,
                    slug               = EXCLUDED.slug,
                    batch              = EXCLUDED.batch,
                    website            = EXCLUDED.website,
                    one_liner          = EXCLUDED.one_liner,
                    description        = EXCLUDED.description,
                    hiring_description = EXCLUDED.hiring_description,
                    tech_description   = EXCLUDED.tech_description,
                    primary_vertical   = EXCLUDED.primary_vertical,
                    parent_sector      = EXCLUDED.parent_sector,
                    child_sector       = EXCLUDED.child_sector,
                    team_size          = EXCLUDED.team_size,
                    location           = EXCLUDED.location,
                    country            = EXCLUDED.country,
                    twitter_url        = EXCLUDED.twitter_url,
                    fb_url             = EXCLUDED.fb_url,
                    is_hiring          = EXCLUDED.is_hiring,
                    last_seen_at       = EXCLUDED.last_seen_at
                """,
                [
                    (
                        c["id"], c.get("name"), c.get("slug"), c.get("batch"),
                        c.get("website"), c.get("one_liner"), c.get("description"),
                        c.get("hiring_description"), c.get("tech_description"),
                        c.get("primary_vertical"), c.get("parent_sector"),
                        c.get("child_sector"), c.get("team_size"),
                        c.get("pretty_location"), c.get("country"),
                        c.get("twitter_url"), c.get("fb_url"),
                        bool(c.get("is_hiring")),
                        now, now,
                    )
                    for c in companies
                ],
                page_size=200,
            )

        # ── Jobs ─────────────────────────────────────────────────────────────
        if seen_job_ids:
            cur.execute("SELECT id FROM jobs WHERE id = ANY(%s)", (seen_job_ids,))
            existing_jobs = {row[0] for row in cur.fetchall()}
            stats["new_jobs"] = len(seen_job_ids) - len(existing_jobs)

            execute_values(
                cur,
                """
                INSERT INTO jobs
                    (id, company_id, title, description, job_type, role,
                     salary_min, salary_max, equity_min, equity_max,
                     remote, visa, locations, skills, show_path,
                     interview_process, min_experience,
                     pretty_salary_range, pretty_location_or_remote,
                     is_active, first_seen_at, last_seen_at)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    title                     = EXCLUDED.title,
                    description               = EXCLUDED.description,
                    job_type                  = EXCLUDED.job_type,
                    role                      = EXCLUDED.role,
                    salary_min                = EXCLUDED.salary_min,
                    salary_max                = EXCLUDED.salary_max,
                    equity_min                = EXCLUDED.equity_min,
                    equity_max                = EXCLUDED.equity_max,
                    remote                    = EXCLUDED.remote,
                    visa                      = EXCLUDED.visa,
                    locations                 = EXCLUDED.locations,
                    skills                    = EXCLUDED.skills,
                    show_path                 = EXCLUDED.show_path,
                    interview_process         = EXCLUDED.interview_process,
                    min_experience            = EXCLUDED.min_experience,
                    pretty_salary_range       = EXCLUDED.pretty_salary_range,
                    pretty_location_or_remote = EXCLUDED.pretty_location_or_remote,
                    is_active                 = TRUE,
                    last_seen_at              = EXCLUDED.last_seen_at
                """,
                [
                    (
                        job["id"], cid,
                        job.get("title"), job.get("description"),
                        job.get("job_type"), job.get("pretty_role"),
                        job.get("salary_min"), job.get("salary_max"),
                        job.get("equity_min"), job.get("equity_max"),
                        job.get("remote"), job.get("visa"),
                        Json(job.get("locations") or []),
                        Json([s["name"] for s in job.get("skills") or []]),
                        job.get("show_path"), job.get("interview_process"),
                        job.get("min_experience"),
                        job.get("pretty_salary_range"),
                        job.get("pretty_location_or_remote"),
                        True,  # is_active
                        now, now,
                    )
                    for cid, job in all_jobs
                ],
                page_size=200,
            )

            # Mark jobs absent from this run as closed (one UPDATE, no loop)
            cur.execute(
                """
                UPDATE jobs
                SET    is_active = FALSE, last_seen_at = %s
                WHERE  is_active = TRUE
                AND    id != ALL(%s)
                """,
                (now, seen_job_ids),
            )
            stats["closed_jobs"] = cur.rowcount

        # ── Founders ─────────────────────────────────────────────────────────
        if all_founders:
            execute_values(
                cur,
                """
                INSERT INTO founders
                    (id, company_id, full_name, founder_bio, linkedin, first_seen_at)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    full_name   = EXCLUDED.full_name,
                    founder_bio = EXCLUDED.founder_bio,
                    linkedin    = EXCLUDED.linkedin
                """,
                [
                    (
                        founder["id"], cid,
                        founder.get("full_name"), founder.get("founder_bio"),
                        founder.get("linkedin"),
                        now,
                    )
                    for cid, founder in all_founders
                ],
                page_size=200,
            )

    conn.commit()
    return stats
