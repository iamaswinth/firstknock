# Phase 2 — Core Ingestion Pipeline

**Goal:** PDF in → structured JSON saved to NeonDB. Five sequential stages, each signed off before the next is built.

**Test fixture:** `docs/AI Intern - Aswinthraj.pdf` (copy this to `tests/fixtures/sample_resumes/resume.pdf`)

**Ground rules:**
- Each stage is built in isolation and you test it before moving on
- No stage is wired to the next until you've confirmed its raw output
- If output doesn't match expectations below, stop and flag before continuing
- All expected outputs below are derived from Aswinthraj's actual resume

---

## Pre-flight checklist

Before Stage 1, confirm these are working:

```bash
# Memgraph + Redis running
docker-compose ps
# → firstknock-memgraph Running, firstknock-redis Running

# NeonDB reachable
python -c "
import asyncio, os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k,_,v = line.partition('=')
        os.environ.setdefault(k.strip(), v.strip())
import asyncpg
async def check():
    conn = await asyncpg.connect(os.environ['POSTGRES_DIRECT_URL'].replace('postgresql://', 'postgresql://'))
    r = await conn.fetchval('SELECT 1')
    print('NeonDB OK:', r)
    await conn.close()
asyncio.run(check())
"

# Python imports resolve
python -c "from firstknock.config import settings; print('Config OK, model:', settings.extraction_model)"
```

Copy the test resume:
```bash
copy "docs\AI Intern - Aswinthraj.pdf" "tests\fixtures\sample_resumes\resume.pdf"
```

---

## Stage 1 — Parsers

**Module:** `firstknock/pipeline/parsers/`

**What it does:** PDF bytes → clean raw text string. Uses `pdfplumber` as primary, `pymupdf` (fitz) as fallback if output < 100 chars.

### Files built

| File | Purpose |
|---|---|
| `parsers/pdf_parser.py` | `parse_pdf(file_bytes) → str` — pdfplumber with pymupdf fallback |
| `parsers/router.py` | `parse_file(file_bytes, file_type) → dict` — returns `{source_type, raw_text}` |

### Test command

```python
python -c "
import asyncio
from firstknock.pipeline.parsers.router import parse_file

with open('tests/fixtures/sample_resumes/resume.pdf', 'rb') as f:
    data = f.read()

result = asyncio.run(parse_file(data, 'pdf'))
print('Source type:', result['source_type'])
print('Total chars:', len(result['raw_text']))
print()
print('--- First 500 chars ---')
print(result['raw_text'][:500])
print()
print('--- Last 200 chars ---')
print(result['raw_text'][-200:])
"
```

### Expected output for Aswinthraj's resume

```
Source type: pdf
Total chars: >1500  (this resume is ~1800 chars of text content)

--- First 500 chars ---
ASWINTHRAJ DEVARAJ
iamaswinth@gmail.com  6369585965  Tirupur,TamilNadu
...
SUMMARY
Full Stack AI Engineer building production-grade AI systems...
```

**Pass criteria:**
- `source_type = "pdf"`
- `len(raw_text) > 1000` — single-page resume should produce ~1500–2000 chars
- Text contains "ASWINTHRAJ DEVARAJ" (his name)
- Text contains "TechKareer" (employer name)
- Text contains "iamaswinth@gmail.com" (email)
- No garbled unicode (`â€™`, `Ã©`, etc.) — if you see these, pdfplumber encoding is wrong

**Common failure modes:**
- `< 100 chars` → PDF is image-only, OCR needed (not Phase 2). This PDF is text-based so should work.
- Missing sections → column layout confused pdfplumber; pymupdf fallback should catch this

---

## Stage 2 — Normalization

**Module:** `firstknock/pipeline/normalization/`

**What it does:** Raw text → cleaned text + section map + extracted URLs.

### Files built

| File | Purpose |
|---|---|
| `normalization/text_cleaner.py` | `clean_text(raw) → str` — strip page numbers, fix encoding artifacts, normalize whitespace |
| `normalization/section_detector.py` | `detect_sections(text) → dict[str, str]` — returns `{section_name: section_content}` |
| `normalization/url_extractor.py` | `extract_urls(text) → dict` — returns `{github: [], linkedin: [], other: []}` |

### Test command

```python
python -c "
from firstknock.pipeline.normalization.text_cleaner import clean_text
from firstknock.pipeline.normalization.section_detector import detect_sections
from firstknock.pipeline.normalization.url_extractor import extract_urls

# First run Stage 1 to get raw text, or use this inline:
import asyncio
from firstknock.pipeline.parsers.router import parse_file
with open('tests/fixtures/sample_resumes/resume.pdf', 'rb') as f:
    raw = asyncio.run(parse_file(f.read(), 'pdf'))['raw_text']

cleaned = clean_text(raw)
sections = detect_sections(cleaned)
urls = extract_urls(raw)  # run on raw, not cleaned (URLs survive cleaning anyway)

print('=== SECTIONS DETECTED ===')
for name, content in sections.items():
    print(f'  [{name}] — {len(content)} chars')

print()
print('=== URLS EXTRACTED ===')
print('GitHub:', urls.get('github', []))
print('LinkedIn:', urls.get('linkedin', []))
print('Other:', urls.get('other', []))

print()
print('=== SIZE DELTA ===')
print(f'Raw: {len(raw)} chars → Cleaned: {len(cleaned)} chars ({len(raw)-len(cleaned):+d})')
"
```

### Expected output for Aswinthraj's resume

```
=== SECTIONS DETECTED ===
  [summary]     — ~180 chars
  [experience]  — ~900 chars
  [projects]    — ~500 chars
  [skills]      — ~350 chars
  [education]   — ~80 chars

=== URLS EXTRACTED ===
GitHub:   []  (PDF has [Github] text but URL is hyperlink, not plaintext)
LinkedIn: []  (same — embedded link, not raw URL text)
Other:    []

=== SIZE DELTA ===
Raw: ~1800 chars → Cleaned: ~1700 chars (-100)
```

**Pass criteria:**
- At least 4 sections detected: experience, projects, skills, education
- `summary` section detected (optional but present in this resume)
- Cleaned text is shorter than or equal to raw (artifacts removed, never inflated)
- URL extractor runs without error (empty lists are fine for this resume — PDFs with embedded links won't have plaintext URLs)

**Note:** If this resume has no plaintext URLs in the PDF, `urls.github = []` is correct. URLs in hyperlinks (not plaintext) are invisible to text extractors.

---

## Stage 3 — LLM Extraction

**Module:** `firstknock/pipeline/extraction/`

**What it does:** Cleaned resume text → strict `ResumeExtraction` Pydantic object, via Claude `claude-sonnet-4-6`.

**Requires:** `ANTHROPIC_API_KEY` set in `.env`

### Files built

| File | Purpose |
|---|---|
| `extraction/schemas.py` | `ResumeExtraction` Pydantic model — full schema definition |
| `extraction/prompts.py` | System prompt + user prompt template |
| `extraction/llm_client.py` | Async Anthropic client wrapper, logs token counts |
| `extraction/extractor.py` | `extract_resume(text) → ResumeExtraction` with tenacity retry (3 attempts, 2x backoff) |

### Extraction schema

```python
class Identity(BaseModel):
    name: str
    email: str | None
    phone: str | None
    location: str | None
    headline: str | None
    github_url: str | None
    linkedin_url: str | None

class ExperienceEntry(BaseModel):
    company: str
    title: str
    location: str | None
    start_date: str | None      # raw string as seen, e.g. "Jan 2026"
    end_date: str | None        # "Present" or "Dec 2025"
    is_current: bool
    description: list[str]      # bullet points
    tech_stack: list[str]       # technologies explicitly mentioned in this role

class ProjectEntry(BaseModel):
    name: str
    description: str
    tech_stack: list[str]
    url: str | None
    github_url: str | None

class SkillsBlock(BaseModel):
    languages: list[str]
    frameworks: list[str]
    ai_ml: list[str]
    databases: list[str]
    devops: list[str]
    other: list[str]

class EducationEntry(BaseModel):
    institution: str
    degree: str
    field: str
    start_year: str | None
    end_year: str | None

class ResumeExtraction(BaseModel):
    identity: Identity
    experience: list[ExperienceEntry]
    projects: list[ProjectEntry]
    skills: SkillsBlock
    education: list[EducationEntry]
    certifications: list[str]
    languages_spoken: list[str]
```

### Test command

```python
python -c "
import asyncio, json
from firstknock.pipeline.normalization.text_cleaner import clean_text
from firstknock.pipeline.normalization.section_detector import detect_sections
from firstknock.pipeline.parsers.router import parse_file
from firstknock.pipeline.extraction.extractor import extract_resume

async def run():
    with open('tests/fixtures/sample_resumes/resume.pdf', 'rb') as f:
        parsed = await parse_file(f.read(), 'pdf')
    cleaned = clean_text(parsed['raw_text'])

    result = await extract_resume(cleaned)

    print('=== IDENTITY ===')
    print(json.dumps(result.identity.model_dump(), indent=2))

    print()
    print('=== EXPERIENCE ===')
    for exp in result.experience:
        print(f'  {exp.title} @ {exp.company}')
        print(f'  Dates: {exp.start_date} → {exp.end_date} (current: {exp.is_current})')
        print(f'  Tech: {exp.tech_stack}')
        print()

    print('=== PROJECTS ===')
    for p in result.projects:
        print(f'  {p.name}')
        print(f'  Tech: {p.tech_stack}')
        print()

    print('=== SKILLS ===')
    print(json.dumps(result.skills.model_dump(), indent=2))

    print()
    print('=== EDUCATION ===')
    for e in result.education:
        print(f'  {e.degree} in {e.field} @ {e.institution} ({e.start_year} - {e.end_year})')

asyncio.run(run())
"
```

### Expected extraction output — Aswinthraj's resume

**Identity:**
```json
{
  "name": "Aswinthraj Devaraj",
  "email": "iamaswinth@gmail.com",
  "phone": "6369585965",
  "location": "Tirupur, Tamil Nadu",
  "headline": "Full Stack AI Engineer building production-grade AI systems and real-time voice/multimodal apps",
  "github_url": null,
  "linkedin_url": null
}
```

**Experience (2 entries):**
```
Software Engineering Intern @ TechKareer
  Dates: Jan 2026 → Present (current: True)
  Tech: [Google ADK, Next.js, FastAPI, Gemini Live API, LangGraph, Claude,
         browser-use, Playwright, Azure VPS, Crawl4AI, n8n, React Native,
         TanStack Query]

Software Engineering Intern @ Praskla Technology
  Dates: July 2025 → Dec 2025 (current: False)
  Tech: [Electron.js, React, Konva.js, AWS RDS, MySQL, Vite]
```

**Projects (2 entries):**
```
The Mind Surf - AI-Powered Document Chat & RAG App
  Tech: [FastAPI, Next.js 14, TypeScript, Pinecone, NeonDB, PostgreSQL,
         asyncpg, Unstructured.io, Tesseract OCR, GPT-4o Vision,
         BGE-Reranker-v2, Docker]

Syntax - Full-Stack Quiz & Competitive Programming Platform
  Tech: [React, Node.js, Express, Firebase, Redis, Judge API, JWT]
```

**Skills block:**
```json
{
  "languages": ["Python", "JavaScript", "SQL", "HTML5", "CSS3"],
  "frameworks": ["Next.js", "React", "FastAPI", "Node.js", "React Native",
                 "Tailwind CSS", "React Query", "LangGraph"],
  "ai_ml": ["Google ADK", "Gemini Live API", "Browser-use", "Browserbase",
             "RAG", "Pinecone"],
  "databases": ["NeonDB", "PostgreSQL", "Pinecone", "Prisma ORM", "MySQL"],
  "devops": ["Azure VPS", "DigitalOcean", "Docker", "GitHub Actions"],
  "other": ["WebSockets", "WebRTC", "n8n", "Clerk", "Postman", "Blender"]
}
```

**Education (1 entry):**
```
Bachelor in Computer Science and Engineering
  @ KSR College of Engineering, Tiruchengode
  2023 - Present
```

### Token cost verification

The llm_client logs token usage automatically. After running, you should see:
```
[extraction] tokens: ~1200 in / ~900 out | cost: ~$0.018–$0.025
```

If you see > 3000 input tokens, the prompt is too long — flag it.

**Pass criteria:**
- `identity.name = "Aswinthraj Devaraj"` — exact match
- `identity.email = "iamaswinth@gmail.com"` — exact match
- 2 experience entries with correct company names (TechKareer, Praskla Technology)
- TechKareer `is_current = True`, Praskla `is_current = False`
- 2 project entries (The Mind Surf, Syntax)
- `skills.ai_ml` contains at least: LangGraph, Google ADK, Gemini Live API, RAG
- Token usage printed — verify cost is in expected range
- No `ValidationError` thrown (Pydantic validates the JSON before returning)

**If identity.name is wrong or experience is missing:** the prompt needs adjustment. Do NOT move to Stage 4 until this is correct.

---

## Stage 4 — Resolution

**Module:** `firstknock/pipeline/resolution/`

**What it does:** Raw strings from Stage 3 → canonical forms. `reactjs` → `React`. `Jan 2026` → `2026-01`. No API calls.

### Files built

| File | Purpose |
|---|---|
| `resolution/aliases.py` | Loads `data/skill_aliases.json` + `SKILL_HIERARCHY` (parent skill mappings) |
| `resolution/skill_canonicalizer.py` | `canonicalize_skill(raw) → str`, `canonicalize_skill_list(list) → list` |
| `resolution/date_normalizer.py` | `normalize_date(raw) → "YYYY-MM" \| "YYYY" \| None`, `date_range_months(start, end) → int` |
| `resolution/company_matcher.py` | `match_company(raw) → str` — fuzzy match against `data/company_index.json` (empty now) |

### Skills to verify for Aswinthraj's resume

```python
python -c "
from firstknock.pipeline.resolution.skill_canonicalizer import canonicalize_skill, canonicalize_skill_list
from firstknock.pipeline.resolution.date_normalizer import normalize_date, date_range_months

# Generic alias tests
print('=== GENERIC ALIAS CHECKS ===')
print('py            →', canonicalize_skill('py'))            # → Python
print('JS            →', canonicalize_skill('JS'))            # → JavaScript
print('postgres      →', canonicalize_skill('postgres'))      # → PostgreSQL
print('react.js      →', canonicalize_skill('react.js'))      # → React
print('k8s           →', canonicalize_skill('k8s'))           # → Kubernetes

# Skills from Aswinthraj's actual resume
print()
print('=== FROM ASWINTHRAJ RESUME ===')
print('Next.js 14    →', canonicalize_skill('Next.js 14'))    # → Next.js
print('BGE-Reranker-v2→', canonicalize_skill('BGE-Reranker-v2')) # → BGE-Reranker
print('asyncpg       →', canonicalize_skill('asyncpg'))       # → asyncpg (no alias needed)
print('NeonDB        →', canonicalize_skill('NeonDB'))        # → NeonDB (or PostgreSQL)
print('Judge API     →', canonicalize_skill('Judge API'))     # → Judge0 API (if alias exists) or Judge API
print('HTML5/CSS3    →', canonicalize_skill('HTML5/CSS3'))    # → should split or keep

# Hierarchy expansion (compound skill → parent + self)
print()
print('=== HIERARCHY EXPANSION ===')
print('AWS RDS       →', canonicalize_skill_list(['AWS RDS']))  # → [AWS RDS, AWS]
print('GitHub Actions→', canonicalize_skill_list(['GitHub Actions'])) # → [GitHub Actions, CI/CD]
print('Azure VPS     →', canonicalize_skill_list(['Azure VPS'])) # → [Azure VPS, Azure]

# Date normalization
print()
print('=== DATE NORMALIZATION ===')
print('Jan 2026      →', normalize_date('Jan 2026'))          # → 2026-01
print('July 2025     →', normalize_date('July 2025'))         # → 2025-07
print('Dec 2025      →', normalize_date('Dec 2025'))          # → 2025-12
print('Present       →', normalize_date('Present'))           # → None
print('Sep 2023      →', normalize_date('Sep 2023'))          # → 2023-09

# Months calculation
print()
print('=== DURATION CALCULATION ===')
print('July 2025 to Dec 2025 →', date_range_months('2025-07', '2025-12'), 'months')  # → 5
print('Jan 2026 to Present   →', date_range_months('2026-01', None), 'months')       # → months since Jan 2026
print('Sep 2023 to Present   →', date_range_months('2023-09', None), 'months')       # → ~20+ months
"
```

### Expected canonicalization for this resume

After resolving Aswinthraj's full skill list, the canonical set should include:

| Raw (from extraction) | Canonical | Also adds |
|---|---|---|
| `Python` | `Python` | — |
| `JavaScript (ES6+)` | `JavaScript` | — |
| `Next.js 14` | `Next.js` | — |
| `Google ADK` | `Google ADK` | `Google Cloud` (hierarchy) |
| `Gemini Live API` | `Gemini Live API` | `Google Cloud` |
| `LangGraph` | `LangGraph` | `LangChain` (hierarchy, LangGraph is built on it) |
| `browser-use` | `browser-use` | `Playwright` (hierarchy, browser-use uses Playwright) |
| `AWS RDS` | `AWS RDS` | `AWS`, `MySQL` |
| `AWS RDS (MySQL)` | `AWS RDS` | `AWS`, `MySQL` |
| `BGE-Reranker-v2` | `BGE-Reranker` | `Information Retrieval` |
| `Pinecone (Dense + Sparse)` | `Pinecone` | `Vector Database`, `Hybrid Search` |
| `NeonDB (Postgres)` | `PostgreSQL` (or `NeonDB`) | — |
| `GitHub Actions (CI/CD)` | `GitHub Actions` | `CI/CD` |
| `Azure VPS` | `Azure VPS` | `Azure` |
| `asyncpg` | `asyncpg` | `PostgreSQL` (hierarchy) |
| `Prisma ORM` | `Prisma` | — |
| `TanStack Query` | `TanStack Query` | `React Query` (alias) |
| `React Query` | `TanStack Query` | — |
| `Electron.js` | `Electron` | — |

**Total expected canonical skills after resolution:** ~35–45 unique canonical skills

**Pass criteria:**
- `Next.js 14` → `Next.js` (version stripped)
- `Jan 2026` → `2026-01`
- `July 2025` → `2025-07`
- `Dec 2025` → `2025-12`
- `Present` → `None`
- `AWS RDS` produces `[AWS RDS, AWS]` from hierarchy
- Duration July 2025 → Dec 2025 = **5 months**
- No raw strings like `JavaScript (ES6+)` surviving into the final skill list

---

## Stage 5 — Persistence

**Module:** `firstknock/pipeline/persistence/`

**What it does:** Resolved extraction → NeonDB. Source of truth. Everything downstream is rebuilt from here.

**Requires:** `POSTGRES_URL` and `POSTGRES_DIRECT_URL` set in `.env`

### Files built

| File | Purpose |
|---|---|
| `persistence/models.py` | `User` + `Resume` SQLAlchemy async models (mirrors Alembic schema) |
| `persistence/postgres_writer.py` | `get_or_create_user()`, `save_extracted_resume()`, `update_resume_status()`, `save_enrichment_data()`, `mark_graph_built()` |
| `persistence/db.py` | Async engine + session factory |

### Test command

```python
python -c "
import asyncio
from firstknock.pipeline.persistence.postgres_writer import get_or_create_user, save_extracted_resume

async def test():
    # Create user for Aswinthraj
    user_id = await get_or_create_user('iamaswinth@gmail.com')
    print('User ID:', user_id)

    # Save a minimal extracted resume
    user_id, resume_id = await save_extracted_resume(
        user_email='iamaswinth@gmail.com',
        source_type='pdf',
        raw_text='ASWINTHRAJ DEVARAJ iamaswinth@gmail.com...',
        extracted_json={
            'identity': {'name': 'Aswinthraj Devaraj', 'email': 'iamaswinth@gmail.com'},
            'experience': [
                {'company': 'TechKareer', 'title': 'Software Engineering Intern',
                 'start_date': 'Jan 2026', 'end_date': 'Present', 'is_current': True}
            ],
            'skills': {'languages': ['Python', 'JavaScript'], 'ai_ml': ['LangGraph', 'Google ADK']}
        },
    )
    print('Resume ID:', resume_id)
    print('Status: extracted (should be)')

asyncio.run(test())
"
```

Then verify the row exists in NeonDB:
```python
python -c "
import asyncio
from firstknock.pipeline.persistence.postgres_writer import get_latest_resume_for_user

async def check():
    row = await get_latest_resume_for_user('iamaswinth@gmail.com')
    print('Resume ID:', row.resume_id)
    print('Status:', row.status)
    print('Source type:', row.source_type)
    print('extracted_json set:', row.extracted_json is not None)
    print('Name in JSON:', row.extracted_json['identity']['name'])

asyncio.run(check())
"
```

**Pass criteria:**
- User row created with `email = 'iamaswinth@gmail.com'`
- Resume row created with `status = 'extracted'`
- `extracted_json IS NOT NULL`
- `extracted_json['identity']['name'] = 'Aswinthraj Devaraj'`
- Running the command twice does NOT create a duplicate user (upsert behavior)
- Check in NeonDB dashboard → Tables → `users` and `resumes` tables

---

## Stage 6 — Orchestrator (wire stages 1–5)

**Module:** `firstknock/pipeline/orchestrator.py` + `scripts/test_ingestion.py`

**What it does:** `run_sync_ingestion(file_bytes, file_type, user_email)` chains all 5 stages in sequence and returns a summary.

### Files built

| File | Purpose |
|---|---|
| `pipeline/orchestrator.py` | Full `run_sync_ingestion()` implementation |
| `scripts/test_ingestion.py` | CLI: `python scripts/test_ingestion.py <pdf_path> <email>` |

### Test command (end-to-end Phase 2)

```bash
python scripts/test_ingestion.py "tests/fixtures/sample_resumes/resume.pdf" "iamaswinth@gmail.com"
```

### Expected output

```
FirstKnock — Resume Ingestion Test
═══════════════════════════════════════════════════════

[1/5] Parsing PDF...
      ✓  1847 chars extracted  (source: pdf)

[2/5] Normalizing text...
      ✓  sections: summary, experience, projects, skills, education
      ✓  cleaned: 1723 chars

[3/5] Extracting via LLM (claude-sonnet-4-6)...
      ✓  tokens: 1312 in / 891 out  (~$0.019)
      ✓  identity: Aswinthraj Devaraj <iamaswinth@gmail.com>
      ✓  experience: 2 entries  (TechKareer, Praskla Technology)
      ✓  projects: 2 entries   (The Mind Surf, Syntax)
      ✓  skills: 28 raw skills extracted

[4/5] Resolving entities...
      ✓  38 canonical skills  (28 raw → 38 after hierarchy expansion)
      ✓  dates: Jan 2026→2026-01, July 2025→2025-07, Dec 2025→2025-12
      ✓  companies: TechKareer (no alias), Praskla Technology (no alias)

[5/5] Saving to NeonDB...
      ✓  user_id:   <uuid>
      ✓  resume_id: <uuid>
      ✓  status:    extracted

═══════════════════════════════════════════════════════
Phase 2 complete. Resume saved to NeonDB.
View at: https://console.neon.tech → Tables → resumes
```

**Pass criteria:**
- Full run completes in < 20 seconds (LLM extraction is the bottleneck)
- `resume_id` UUID printed — copy it for Phase 3 graph write testing
- NeonDB shows the row in the `resumes` table
- ALL fields in expected output match — if experience count is 1 instead of 2, stop and fix Stage 3 prompt

---

## Tests written after sign-off

After you approve each stage, the corresponding test is written:

| Stage approved | Test file |
|---|---|
| Stage 1 | `tests/parsers/test_pdf_parser.py` |
| Stage 3 | `tests/extraction/test_extractor.py` |
| Stage 4 | `tests/resolution/test_canonicalization.py` |
| Stage 5 + 6 | `tests/integration/test_ingestion_pipeline.py` |

```bash
# Run all Phase 2 tests
pytest tests/parsers/ tests/extraction/ tests/resolution/ tests/integration/ -v
```

---

## What Phase 2 does NOT do yet

These are intentionally deferred:

| Feature | Added in |
|---|---|
| Memgraph graph write | Phase 3 |
| Async enrichment (GitHub, Crunchbase) | Phase 5 |
| Skill inference engine | Phase 4 |
| Vector embeddings | Phase 6 |
| DOCX / LinkedIn / OCR inputs | Phase 7 |
| Job matching API | Phase 8 |

**Phase 2 is done when:** you run `test_ingestion.py` on `docs/AI Intern - Aswinthraj.pdf`, read every field in the output, and it matches the expected values above exactly. Name, email, both companies, both projects, date formats, skill count.
