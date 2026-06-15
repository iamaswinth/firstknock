# FIRSTKNOCK — Backlog

## Planned: LLM Graph Curation (Phase 9 pipeline stage)

**Problem:** The ego graph query is a blunt instrument — it returns every node for every user regardless of resume shape. Dense resumes produce unreadable 150+ node blobs.

**Approach:** Add an LLM curation step at **ingest time** (after embedding, as a Celery task), not at request time.

The LLM receives the completed profile (explicit skills, inferred skills with confidence scores, companies, projects, community clusters) and writes a set of **display parameters** stored in Postgres:
- `featured_community_id` — which skill cluster is primary for this person
- `confidence_floor` — minimum confidence to show inferred skills (scales with resume density)
- `featured_node_ids` — up to 8 bridge/anchor skills worth pinning
- `max_inferred` — cap on inferred nodes to return

The `/graph/{user_id}` endpoint reads these params and parameterizes its Cypher query accordingly. Zero LLM latency at read time.

**Files to add/change:**
- `backend/firstknock/pipeline/graph/curator.py` — new Celery task
- `backend/firstknock/pipeline/persistence/models.py` — add `graph_display_params` JSONB column to Resume
- `backend/alembic/versions/003_graph_display_params.py` — migration
- `backend/firstknock/api/routes/graph.py` — read params when building Cypher
- `backend/firstknock/workers/celery_app.py` — register new task

**Prerequisite:** Graph clutter fix (frontend defaults) ships first as a stopgap.
