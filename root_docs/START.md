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

**Celery workers** — each queue in its own terminal

Ingestion (LLM-heavy — parse, extract, infer):
```bash
.venv/Scripts/python.exe -m celery -A firstknock.workers.celery_app worker -Q ingestion -n ingestion@%h -c 4 --loglevel=info --pool=solo
```

Enrichment (GitHub, LinkedIn, company data):
```bash
.venv/Scripts/python.exe -m celery -A firstknock.workers.celery_app worker -Q enrichment -n enrichment@%h -c 2 --loglevel=info --pool=solo
```

Embedding (OpenAI vectors):
```bash
.venv/Scripts/python.exe -m celery -A firstknock.workers.celery_app worker -Q embedding -n embedding@%h -c 4 --loglevel=info --pool=solo
```

> **Quick start (single worker, all queues)** — fine for local dev:
> ```bash
> .venv/Scripts/python.exe -m celery -A firstknock.workers.celery_app worker -Q ingestion,enrichment,embedding -n dev@%h --loglevel=info --pool=solo
> ```

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

---

## Ingestion flow (what happens after upload)

`POST /ingest` returns `202 Accepted` in <200ms with `{ resume_id, status: "queued" }`.
The frontend polls `GET /resume/{resume_id}` every 3 s and tracks status through:

```
queued → parsing → extracting → resolving → persisting → graph_building → inferring → enriching → enriched
```

`failed` is set if any unrecoverable error occurs — the frontend returns the user to the upload screen.
