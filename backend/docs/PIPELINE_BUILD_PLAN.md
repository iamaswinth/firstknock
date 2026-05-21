# FirstKnock — Pipeline Build Plan

## What we're building

A Graph RAG resume ingestion pipeline. Users upload a PDF → the system parses it, infers implicit skills the user never wrote down, enriches every entity with external data (GitHub, Crunchbase), stores everything in NeonDB (source of truth) AND Memgraph (query layer), then uses graph algorithms to match users to jobs and generate personalized cold emails.

**Current state (Phase 1 complete):**
- `pyproject.toml` — all dependencies installed
- `docker-compose.yml` — Memgraph + Redis only (NeonDB replaces local Postgres)
- `alembic/` — migration ran, `users` + `resumes` tables exist in NeonDB
- `firstknock/config.py`, `firstknock/main.py` — stubs
- `data/skill_aliases.json` — 100+ alias mappings seeded

---

## Directory layout (flat, no src/)

```
backend/
├── firstknock/               ← Python package (flat layout, no src/ nesting)
│   ├── config.py
│   ├── main.py
│   ├── api/
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── ingest.py
│   │       ├── matches.py
│   │       ├── email.py
│   │       └── graph.py
│   ├── pipeline/
│   │   ├── orchestrator.py
│   │   ├── parsers/          ← Stage 1: PDF, DOCX, OCR, LinkedIn
│   │   ├── normalization/    ← Stage 2: text cleaner, section detector, URL extractor
│   │   ├── extraction/       ← Stage 3: Claude LLM, Pydantic schemas, prompts
│   │   ├── resolution/       ← Stage 4: skill aliases, company matcher, date normalizer
│   │   ├── persistence/      ← Stage 5: SQLAlchemy models, NeonDB writer
│   │   ├── enrichment/       ← Stage 6: Celery tasks, GitHub, Crunchbase, graph updater
│   │   ├── inference/        ← Stage 7: rule engine, domain/skill/project rules, seniority
│   │   ├── embedding/        ← Stage 8: OpenAI embeddings, batch calls
│   │   └── graph/            ← Stage 9: Memgraph client, schema setup, MERGE writers
│   ├── workers/
│   │   └── celery_app.py
│   └── utils/
├── alembic/
├── data/
│   ├── skill_aliases.json    ← 100+ mappings (seeded)
│   ├── company_index.json    ← empty now, populated by enrichment
│   └── institution_rankings.json
├── tests/
├── scripts/
└── docs/
```

**Module names are by function, never by execution order.** No `stage1_`, `stage2_` prefixes.

---

## Infrastructure

| Service | Where | Purpose |
|---|---|---|
| PostgreSQL | **NeonDB (cloud)** | Source of truth — write here first, always |
| Memgraph | Docker (`localhost:7687`) | Graph query layer — rebuilt from Postgres on cold start |
| Redis | Docker (`localhost:6379`) | Celery broker + result backend |

```bash
# Start local services
docker-compose up -d        # starts Memgraph + Redis
# Postgres lives in NeonDB — no local container needed
```

---

## Graph Data Model

Full schema for Memgraph. Every stage that writes to the graph uses this.

### Node types

| Label | Key properties | Set by |
|---|---|---|
| `:Person` | `person_id` (UUID), `name`, `email`, `seniority_level`, `headline`, `embedding` (1536-float vector) | Phase 3, Phase 4 (seniority), Phase 6 (embedding) |
| `:Skill` | `name` (canonical), `category` (`language`/`framework`/`tool`/`cloud`/`concept`) | Phase 3 — shared globally, no user_id |
| `:Company` | `name` (canonical), `industry`, `stage`, `headcount`, `github_url` | Phase 3 (name), Phase 5 enrichment (industry/stage/headcount) |
| `:Project` | `project_id`, `name`, `description`, `url`, `stars`, `primary_language`, `embedding` | Phase 3 (core), Phase 5 GitHub enrichment |
| `:Institution` | `name` (canonical), `ranking_tier` | Phase 3 |
| `:Job` | `job_id`, `title`, `company_name`, `required_skills[]`, `embedding` | Phase 8+ (job matching target) |

### Relationship types

| Relationship | From → To | Key properties |
|---|---|---|
| `HAS_SKILL` | Person → Skill | `confidence` (0–1), `source` (`explicit`/`inferred`/`graph_algo`), `years_used` |
| `WORKED_AT` | Person → Company | `title`, `start_date`, `end_date`, `months`, `is_current` |
| `BUILT` | Person → Project | `role`, `start_date`, `end_date` |
| `USES` | Project → Skill | `confidence` (1.0 for explicit) |
| `STUDIED_AT` | Person → Institution | `degree`, `field`, `start_year`, `end_year` |
| `CO_OCCURS_WITH` | Skill ↔ Skill | `coOccurrence` (count) — powers Louvain community detection |
| `IMPLIES` | Skill → Skill | `confidence` — from inference rules (e.g., LangGraph → Agent State Machines) |

**Rules:**
- `:Skill` and `:Company` are shared globally — NEVER add `person_id` to them
- Always `MERGE`, never `CREATE`
- Postgres write MUST happen before any Memgraph write

---

## Enrichment → Graph Flow

Enrichment writes to **both** Postgres and Memgraph. After each Celery task completes, it calls `enrichment/graph_updater.py` to update Memgraph nodes.

```
PDF → parse → normalize → extract → resolve
                                        ↓
                                  [Postgres write]  ← source of truth
                                        ↓
                                  [Memgraph write]  ← Phase 3 graph (basic nodes/edges)
                                        ↓ (Celery, async — does not block API response)
                              ┌─────────────────────┐
                              │ GitHub enrichment   │─→ Postgres update
                              │ Crunchbase enrichment│─→ + Memgraph update (Company/Project props)
                              │ Institution lookup  │─→ + Memgraph update (Institution.ranking_tier)
                              └─────────────────────┘
                                        ↓
                              [Inference engine]  → new HAS_SKILL {source:"inferred"} edges
                              [Embedding]         → vectors on Person/Project nodes
                              [Adamic-Adar algo]  → new HAS_SKILL {source:"graph_algo"} edges
```

| Enricher | Postgres write | Memgraph update |
|---|---|---|
| `github.py` | `enriched_json.github` | `SET proj.stars, proj.primary_language`; adds language `:Skill` nodes |
| `company.py` | `enriched_json.companies` | `SET c.stage, c.industry, c.headcount` |
| `institution.py` | `enriched_json.institutions` | `SET i.ranking_tier` |

---

## Graph Algorithms (Memgraph MAGE)

> **Critical:** The spec HTML uses Neo4j GDS syntax (`gds.pageRank.stream()`). Memgraph uses MAGE procedures — different names, same concepts. Never use `gds.*` calls in Memgraph.

### Core algorithms

| Algorithm | Purpose | Memgraph MAGE call | Runs when |
|---|---|---|---|
| **Personalized PageRank** | From a Person node, score every other node by proximity weighted by `confidence`. Surfaces job/company matches even if person never wrote those words. | `CALL pagerank.get()` | On match request (API) |
| **Node Similarity (Jaccard)** | Compares Person's `HAS_SKILL` edges against Job's required skills. Works on both explicit AND inferred edges. | `CALL node_similarity.jaccard()` | On match request (API) |
| **Louvain community detection** | Discovers skill clusters automatically (e.g., {LangGraph, ADK, Tool calling} → "Agentic AI cluster"). Run on `CO_OCCURS_WITH` edges. Cluster IDs become domain tags for cold email targeting. | `CALL community_detection.get()` | Nightly batch |
| **Dijkstra shortest path** | Powers "why did we recommend this?" explanation. Finds path Person → Job via confidence-weighted edges. The path is the explanation shown to the user. | `shortestPath()` or `CALL path.dijkstra()` | On match request (API) |
| **Adamic-Adar link prediction** | Discovers inferred skills that rule-based inference missed. Scores missing Person→Skill edges by shared graph neighbors. Writes new `HAS_SKILL {source:"graph_algo"}` edges above threshold. | `CALL link_prediction.adamic_adar()` | After inference (Phase 4+) |

### Secondary algorithms

| Algorithm | Purpose | Memgraph MAGE call | Runs when |
|---|---|---|---|
| **Betweenness centrality** | Finds "bridge skills" connecting multiple clusters. High-betweenness skills = rare cross-domain value → cold email hook. | `CALL betweenness_centrality.get()` | Nightly batch |
| **Weakly connected components** | Graph health check. If Person node is isolated after ingestion, enrichment broke. Detects orphan Skill nodes too. | `CALL weakly_connected_components.get()` | After every ingestion |
| **KNN (embedding space)** | Semantic job matching via OpenAI vectors. "Multimodal AI engineer" and "voice systems developer" are close in embedding space even with no shared skill strings. Combined with Jaccard for hybrid ranking. | Memgraph vector index + `CALL vector_search.search_nodes()` | Phase 6+ |

---

## Build Phases

### Phase 1 — Foundation ✅ COMPLETE

- `pyproject.toml`, `docker-compose.yml` (Memgraph + Redis), `Dockerfile`
- `.env.example` + `.env` (NeonDB credentials set)
- `firstknock/config.py` — Pydantic Settings
- `alembic/` + migration `001_initial_schema.py` — ran against NeonDB
- `data/skill_aliases.json` — 100+ aliases seeded
- All `__init__.py` stubs created

**Verify:** `docker-compose ps` (Memgraph + Redis running) · NeonDB has `users` + `resumes` tables · `python -c "from firstknock.config import settings; print('OK')"` passes.

---

### Phase 2 — Core Ingestion (Stages 1–5)

**Goal:** PDF in → structured JSON saved to NeonDB. No graph, no async enrichment yet.

> See `docs/PHASE2_CORE_INGESTION.md` for full detail with expected outputs for Aswinthraj's resume.

**Stage 1 — Parsers** (`pipeline/parsers/`)
- `pdf_parser.py` — pdfplumber primary, pymupdf fallback
- `router.py` — dispatches by file type
- **Pass:** `raw_text > 1000 chars`, contains "ASWINTHRAJ DEVARAJ" and "TechKareer"

**Stage 2 — Normalization** (`pipeline/normalization/`)
- `text_cleaner.py`, `section_detector.py`, `url_extractor.py`
- **Pass:** 4+ sections detected (summary, experience, projects, skills, education)

**Stage 3 — Extraction** (`pipeline/extraction/`)
- `schemas.py`, `prompts.py`, `llm_client.py`, `extractor.py`
- Model: `claude-sonnet-4-6` · Cost: ~$0.017–$0.030/resume
- **Pass:** name=Aswinthraj Devaraj, email=iamaswinth@gmail.com, 2 experience entries, 2 projects

**Stage 4 — Resolution** (`pipeline/resolution/`)
- `aliases.py`, `skill_canonicalizer.py`, `date_normalizer.py`, `company_matcher.py`
- **Pass:** `Next.js 14→Next.js`, `Jan 2026→2026-01`, `AWS RDS→[AWS RDS, AWS]`

**Stage 5 — Persistence** (`pipeline/persistence/`)
- `models.py`, `postgres_writer.py`, `db.py`
- **Pass:** NeonDB row with `status=extracted`, `extracted_json IS NOT NULL`

**Stage 6 — Orchestrator + test script**
- `pipeline/orchestrator.py::run_sync_ingestion()` chains stages 1–5
- `scripts/test_ingestion.py` — CLI smoke test
- **Pass:** Full run <20s, resume_id printed, all fields match expected

---

### Phase 3 — Graph Write (Stage 9)

**Goal:** After Postgres write, full graph schema written to Memgraph.

Files: `pipeline/graph/client.py`, `schema_setup.py`, `writers.py`, `queries.py`

`write_resume_graph()` writes:
1. `MERGE (:Person)` — name, email, headline
2. Per skill → `MERGE (:Skill)` + `MERGE (p)-[:HAS_SKILL {confidence:1.0, source:"explicit"}]->(s)`
3. Per experience → `MERGE (:Company)` + `MERGE (p)-[:WORKED_AT]->(c)`
4. Per project → `CREATE (:Project)` + `MERGE (p)-[:BUILT]->(proj)` + skills → `MERGE (proj)-[:USES]->(s)`
5. Per education → `MERGE (:Institution)` + `MERGE (p)-[:STUDIED_AT]->(i)`
6. Per skill co-occurrence pair → `MERGE (s1)-[:CO_OCCURS_WITH]-(s2)` + increment count
7. WCC health check — log warning if Person node isolated

Also: `main.py` with FastAPI lifespan + `api/routes/ingest.py` (POST /ingest)

**Verify:**
```cypher
-- Memgraph Lab at http://localhost:3000
MATCH (p:Person)-[r:HAS_SKILL]->(s:Skill) RETURN p,r,s LIMIT 25
MATCH (p:Person)-[:WORKED_AT]->(c:Company) RETURN p.name, c.name
MATCH (p:Person)-[:BUILT]->(proj:Project)-[:USES]->(s:Skill) RETURN proj.name, s.name
```

---

### Phase 4 — Inference Engine (Stage 7)

**Goal:** `HAS_SKILL` edges with `source="inferred"` and `confidence < 1.0` appear in Memgraph.

Files: `pipeline/inference/engine.py`, `domain_rules.py`, `skill_rules.py`, `project_rules.py`, `seniority.py`

**Inference rules for Aswinthraj's resume specifically:**
- `Gemini Live API` → infers: WebRTC, VAD (Voice Activity Detection), Streaming UX, Real-time audio
- `LangGraph` → infers: Agent State Machines, Tool calling, Workflow orchestration, LangChain
- `Google ADK` → infers: Multi-agent systems, Agent framework
- `browser-use` (project) → infers: Playwright (it uses Playwright internally)
- `Pinecone (Dense + Sparse)` → infers: Hybrid Search, BM25, Vector Database
- `BGE-Reranker-v2` → infers: Cross-encoder reranking, Information Retrieval
- `Azure VPS` → infers: Linux administration, Cloud infrastructure
- `AWS RDS` → infers: AWS, Database administration
- `asyncpg` → infers: PostgreSQL (confirmed proficiency, not just awareness)
- TechKareer company (AI tooling space) → infers: AI domain exposure

After inference, run Adamic-Adar to find additional missing skill edges the rules didn't cover.

**Verify:**
```bash
pytest tests/inference/ -v
# test_gemini_live_infers_webrtc → passes
# test_langgraph_infers_agent_state_machines → passes
```

---

### Phase 5 — Async Enrichment Workers (Stage 6)

**Goal:** Within 30s of ingestion, `enriched_json` updated in Postgres AND graph nodes updated in Memgraph.

Files:
- `workers/celery_app.py`
- `pipeline/enrichment/tasks.py` — Celery chord: `github | crunchbase | institution → graph_update`
- `pipeline/enrichment/github.py` — repo stars, languages, README
- `pipeline/enrichment/company.py` — Crunchbase: stage, industry, headcount
- `pipeline/enrichment/institution.py` — ranking tier lookup
- `pipeline/enrichment/graph_updater.py` — **writes enriched data back to Memgraph nodes**

**What graph_updater does:**
```python
# After GitHub enrichment completes:
SET proj.stars = 342, proj.primary_language = "Python"
MERGE (:Skill {name: "Python"})  # language detected in repo → new skill node

# After Crunchbase enrichment completes:
SET c.stage = "seed", c.industry = "AI Infrastructure", c.headcount = 12

# After institution lookup:
SET i.ranking_tier = "other"  # KSR College → not top-50
```

**Verify:**
```bash
# Terminal 1
celery -A firstknock.workers.celery_app worker --loglevel=info
# Terminal 2 — ingest resume
curl -F "file=@tests/fixtures/sample_resumes/resume.pdf" http://localhost:8000/ingest
# Wait 30s, then check:
# Postgres: SELECT status, enriched_json IS NOT NULL FROM resumes ORDER BY ingested_at DESC LIMIT 1;
# → enriched | true
# Memgraph: MATCH (c:Company) WHERE c.stage IS NOT NULL RETURN c.name, c.stage
# → TechKareer with stage populated (if Crunchbase finds it)
```

---

### Phase 6 — Embeddings + Vector Index (Stage 8)

**Goal:** Person + Project nodes have embedding vectors; KNN semantic search works.

Files: `pipeline/embedding/embedder.py`, update `graph/schema_setup.py` (vector index), `scripts/backfill_embeddings.py`

Resume summary for embedding (combines headline + skills + experience titles):
```
"Full Stack AI Engineer. Skills: Python, FastAPI, LangGraph, Google ADK, Gemini Live API,
 React, Next.js, Pinecone, PostgreSQL, Docker. Roles: Software Engineering Intern at TechKareer,
 Software Engineering Intern at Praskla Technology. Projects: The Mind Surf (RAG), Syntax (competitive programming)."
```

**Verify:**
```cypher
CALL vector_search.search_nodes("person_embedding", 5, [/* any 1536-float vector */])
YIELD node, score
RETURN node.name, score;
```

---

### Phase 7 — Additional Input Formats

**Goal:** DOCX, LinkedIn URL, image/OCR produce same graph result as PDF.

- Wire `parsers/docx_parser.py`, `parsers/linkedin_fetcher.py` (Proxycurl), `parsers/ocr_parser.py`
- Test MERGE idempotency: same person via PDF then DOCX → single `:Person` node

---

### Phase 8 — API Hardening + Full Test Suite

Files:
- `api/routes/matches.py`, `email.py`, `graph.py`
- `GET /health/deep` — checks NeonDB + Memgraph
- `utils/logging.py` (structlog), `utils/retry.py` (tenacity)
- `scripts/rebuild_graph_from_postgres.py` — cold-start recovery (Postgres → Memgraph rebuild)

Full test suite:
```bash
pytest tests/ -v --cov=firstknock
# tests/parsers/test_pdf_parser.py     → extracted text > 1000 chars
# tests/extraction/test_extractor.py   → correct name/email/skills
# tests/resolution/test_canonicalization.py → React variants → "React"
# tests/inference/test_engine.py       → voice project → audio stack inferred
# tests/integration/test_full_pipeline.py → PDF in → Postgres + Memgraph both written
```

---

## Verification checkpoints

| Phase | Command | Expected |
|---|---|---|
| 1 ✅ | `docker-compose ps` | Memgraph + Redis running; NeonDB tables exist |
| 2 | `python scripts/test_ingestion.py resume.pdf iamaswinth@gmail.com` | NeonDB row, status=extracted |
| 3 | `curl -F file=@resume.pdf localhost:8000/ingest` + Memgraph Lab | Person + Skill + Company nodes visible |
| 4 | `pytest tests/inference/ -v` | Inferred HAS_SKILL edges on graph |
| 5 | Ingest + wait 30s | enriched_json in Postgres + Company.stage in Memgraph |
| 6 | Cypher vector search | Returns ranked Person nodes by semantic similarity |
| 7 | Ingest DOCX of same person | Same Person node (MERGE idempotent) |
| 8 | `pytest tests/ -v --cov` | All tests pass |

---

## Design constraints (non-negotiable)

- Always `MERGE` in Cypher — never `CREATE`
- NeonDB write MUST happen before Celery dispatch AND before Memgraph write
- Shared nodes (`:Skill`, `:Company`) have no `person_id` — user data lives on the edge
- API returns in <3 seconds — enrichment is async and never blocks
- Enrichment writes to BOTH Postgres AND Memgraph — they must stay in sync
- Graph algorithms use Memgraph MAGE procedures — never `gds.*` (Neo4j GDS syntax, won't work)
- All LLM output is validated by Pydantic before reaching resolution
