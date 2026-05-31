# FIRSTKNOCK — Start Commands

All commands assume you're in the repo root (`FIRSTKNOCK/`).

---

## Infrastructure (must be running first)

**Memgraph**
```bash
docker run -it -p 7687:7687 -p 7444:7444 memgraph/memgraph
```

**Redis**
```bash
docker run -p 6379:6379 redis
```

---

## Backend

```bash
cd backend
```

**API server**
```bash
.venv/Scripts/python.exe -m uvicorn firstknock.main:app --host 0.0.0.0 --port 8000 --reload
```

**Celery worker** (enrichment + embeddings — run in a separate terminal)
```bash
.venv/Scripts/python.exe -m celery -A firstknock.workers.celery_app worker --loglevel=info --pool=solo
```

---

## Frontend

```bash
cd firstknock
npm run dev
```

Runs on `http://localhost:3000`

---

## Database

**Apply migrations** (first time or after schema changes)
```bash
cd backend
.venv/Scripts/alembic.exe upgrade head
```

**Wipe everything and reset** (Memgraph + Postgres in one command)
```bash
cd backend
.venv/Scripts/python.exe scripts/reset_db.py
```
