import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id                INTEGER PRIMARY KEY,
    name              TEXT,
    slug              TEXT UNIQUE,
    batch             TEXT,
    website           TEXT,
    one_liner         TEXT,
    description       TEXT,
    hiring_description TEXT,
    tech_description  TEXT,
    primary_vertical  TEXT,
    parent_sector     TEXT,
    child_sector      TEXT,
    team_size         INTEGER,
    location          TEXT,
    country           TEXT,
    twitter_url       TEXT,
    fb_url            TEXT,
    is_hiring         INTEGER DEFAULT 1,
    first_seen_at     TEXT NOT NULL,
    last_seen_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id                       INTEGER PRIMARY KEY,
    company_id               INTEGER NOT NULL REFERENCES companies(id),
    title                    TEXT,
    description              TEXT,
    job_type                 TEXT,
    role                     TEXT,
    salary_min               INTEGER,
    salary_max               INTEGER,
    equity_min               REAL,
    equity_max               REAL,
    remote                   TEXT,
    visa                     TEXT,
    locations                TEXT,   -- JSON array of strings
    skills                   TEXT,   -- JSON array of skill names
    show_path                TEXT,
    interview_process        TEXT,
    min_experience           INTEGER,
    pretty_salary_range      TEXT,
    pretty_location_or_remote TEXT,
    is_active                INTEGER DEFAULT 1,
    first_seen_at            TEXT NOT NULL,
    last_seen_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS founders (
    id            INTEGER PRIMARY KEY,
    company_id    INTEGER NOT NULL REFERENCES companies(id),
    full_name     TEXT,
    founder_bio   TEXT,
    linkedin      TEXT,
    first_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_company   ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_active    ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_founders_company ON founders(company_id);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def upsert_run(conn: sqlite3.Connection, companies: list[dict]) -> dict:
    """
    Upsert all companies, jobs, and founders from one daily run.
    Returns stats: new_companies, new_jobs, closed_jobs.
    """
    now = datetime.now(timezone.utc).isoformat()
    seen_job_ids: set[int] = set()
    stats = {"new_companies": 0, "new_jobs": 0, "closed_jobs": 0}

    for c in companies:
        cid = c["id"]

        existing = conn.execute(
            "SELECT first_seen_at FROM companies WHERE id = ?", (cid,)
        ).fetchone()
        first_seen = existing["first_seen_at"] if existing else now
        if not existing:
            stats["new_companies"] += 1

        conn.execute(
            """
            INSERT INTO companies
                (id, name, slug, batch, website, one_liner, description,
                 hiring_description, tech_description, primary_vertical,
                 parent_sector, child_sector, team_size, location, country,
                 twitter_url, fb_url, is_hiring, first_seen_at, last_seen_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, slug=excluded.slug, batch=excluded.batch,
                website=excluded.website, one_liner=excluded.one_liner,
                description=excluded.description,
                hiring_description=excluded.hiring_description,
                tech_description=excluded.tech_description,
                primary_vertical=excluded.primary_vertical,
                parent_sector=excluded.parent_sector,
                child_sector=excluded.child_sector,
                team_size=excluded.team_size, location=excluded.location,
                country=excluded.country, twitter_url=excluded.twitter_url,
                fb_url=excluded.fb_url, is_hiring=excluded.is_hiring,
                last_seen_at=excluded.last_seen_at
            """,
            (
                cid, c.get("name"), c.get("slug"), c.get("batch"),
                c.get("website"), c.get("one_liner"), c.get("description"),
                c.get("hiring_description"), c.get("tech_description"),
                c.get("primary_vertical"), c.get("parent_sector"),
                c.get("child_sector"), c.get("team_size"),
                c.get("pretty_location"), c.get("country"),
                c.get("twitter_url"), c.get("fb_url"),
                1 if c.get("is_hiring") else 0,
                first_seen, now,
            ),
        )

        for job in c.get("jobs", []):
            jid = job["id"]
            seen_job_ids.add(jid)

            job_existing = conn.execute(
                "SELECT first_seen_at FROM jobs WHERE id = ?", (jid,)
            ).fetchone()
            job_first = job_existing["first_seen_at"] if job_existing else now
            if not job_existing:
                stats["new_jobs"] += 1

            conn.execute(
                """
                INSERT INTO jobs
                    (id, company_id, title, description, job_type, role,
                     salary_min, salary_max, equity_min, equity_max,
                     remote, visa, locations, skills, show_path,
                     interview_process, min_experience,
                     pretty_salary_range, pretty_location_or_remote,
                     is_active, first_seen_at, last_seen_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, description=excluded.description,
                    job_type=excluded.job_type, role=excluded.role,
                    salary_min=excluded.salary_min, salary_max=excluded.salary_max,
                    equity_min=excluded.equity_min, equity_max=excluded.equity_max,
                    remote=excluded.remote, visa=excluded.visa,
                    locations=excluded.locations, skills=excluded.skills,
                    show_path=excluded.show_path,
                    interview_process=excluded.interview_process,
                    min_experience=excluded.min_experience,
                    pretty_salary_range=excluded.pretty_salary_range,
                    pretty_location_or_remote=excluded.pretty_location_or_remote,
                    is_active=1, last_seen_at=excluded.last_seen_at
                """,
                (
                    jid, cid,
                    job.get("title"), job.get("description"),
                    job.get("job_type"), job.get("pretty_role"),
                    job.get("salary_min"), job.get("salary_max"),
                    job.get("equity_min"), job.get("equity_max"),
                    job.get("remote"), job.get("visa"),
                    json.dumps(job.get("locations") or []),
                    json.dumps([s["name"] for s in job.get("skills") or []]),
                    job.get("show_path"), job.get("interview_process"),
                    job.get("min_experience"),
                    job.get("pretty_salary_range"),
                    job.get("pretty_location_or_remote"),
                    job_first, now,
                ),
            )

        for founder in c.get("founders", []):
            fid = founder.get("id")
            if not fid:
                continue
            f_existing = conn.execute(
                "SELECT first_seen_at FROM founders WHERE id = ?", (fid,)
            ).fetchone()
            conn.execute(
                """
                INSERT INTO founders (id, company_id, full_name, founder_bio, linkedin, first_seen_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    full_name=excluded.full_name,
                    founder_bio=excluded.founder_bio,
                    linkedin=excluded.linkedin
                """,
                (
                    fid, cid,
                    founder.get("full_name"), founder.get("founder_bio"),
                    founder.get("linkedin"),
                    f_existing["first_seen_at"] if f_existing else now,
                ),
            )

    # Mark jobs not returned in this run as closed (full scan = safe to do this)
    if seen_job_ids:
        placeholders = ",".join("?" * len(seen_job_ids))
        result = conn.execute(
            f"UPDATE jobs SET is_active=0, last_seen_at=? "
            f"WHERE is_active=1 AND id NOT IN ({placeholders})",
            [now, *seen_job_ids],
        )
        stats["closed_jobs"] = result.rowcount

    conn.commit()
    return stats
