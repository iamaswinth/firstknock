# FirstKnock — Resume Ingestion Pipeline

**Build specification for Claude Code**

This document is the complete spec for building the FirstKnock resume ingestion pipeline — a Graph RAG system that parses resumes, infers implicit skills, enriches with external data, and stores everything in Memgraph for job matching and personalized cold email generation.

Read this entire document before starting. The build order at the end is non-negotiable — earlier stages are dependencies for later ones.

---

## 0. Project context

**What FirstKnock does**: Users upload their resume. The system parses it, enriches every entity (companies, projects, skills, education) with external data, runs an inference engine that derives implicit skills from explicit ones (e.g., "built a voice agent with Gemini Live API" → infers WebRTC, VAD, streaming UX), stores everything in a graph, and uses that graph to match users to relevant jobs and generate personalized cold outreach emails to founders/CTOs.

**The differentiator**: The implicit inference engine. Most resume parsers extract what's written. FirstKnock extracts what's implied. A backend engineer at a cloud-infra company has cloud exposure even if AWS isn't on their resume — we capture that.

**Build philosophy**:
- PostgreSQL is the source of truth — always write there first
- Memgraph is the query layer — rebuilt from PostgreSQL on cold start
- Enrichment is async — never blocks ingestion
- Inference rules live in code, are easy to add, and store confidence + reason on the edge
- Every relationship is idempotent (use `MERGE`, never `CREATE`)

---

## 1. Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT: PDF · DOCX · LinkedIn URL · Image · Plain text          │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Format parsers → raw text                             │
│  Stage 2: Normalization → clean text + section boundaries       │
│  Stage 3: LLM extraction → structured JSON                      │
│  Stage 4: Entity resolution → canonical names                   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
                  ┌──────────┴──────────┐
                  ▼                     ▼
        ┌─────────────────┐   ┌──────────────────────┐
        │ Stage 5:        │   │ Stage 6: Async       │
        │ PostgreSQL save │   │ enrichment (Celery)  │
        │ (source of      │   │ - GitHub API         │
        │  truth)         │   │ - Crunchbase         │
        └─────────────────┘   │ - Company scraper    │
                              │ - Project NLP        │
                              └──────────┬───────────┘
                                         ▼
                  ┌──────────────────────┴───────────┐
                  │ Stage 7: Inference engine        │
                  │ - Domain exposure rules          │
                  │ - Skill adjacency rules          │
                  │ - Project implication rules      │
                  │ - Seniority inference            │
                  └──────────────────┬───────────────┘
                                     ▼
                  ┌──────────────────┴───────────────┐
                  │ Stage 8: Embedding generation    │
                  └──────────────────┬───────────────┘
                                     ▼
                  ┌──────────────────┴───────────────┐
                  │ Stage 9: Memgraph write          │
                  │ - MERGE nodes + relationships    │
                  │ - WAL + snapshot persistence     │
                  └──────────────────────────────────┘
```

---

## 2. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | Async-first, rich ecosystem |
| API framework | FastAPI | Async-native, auto-generated docs |
| LLM | Claude Sonnet 4.6 via Anthropic API | Best structured output reliability |
| PDF parsing | `pdfplumber` + `pymupdf` (fitz) | Column detection + speed |
| DOCX parsing | `python-docx` | Standard library |
| OCR | Tesseract (fast) → GPT-4o Vision (fallback) | Two-tier for cost optimization |
| Fuzzy matching | `rapidfuzz` | Faster than fuzzywuzzy |
| Date parsing | `dateparser` | Handles "Jan 22 – Present" style |
| Task queue | Celery + Redis | Mature, well-documented |
| Source of truth | PostgreSQL 15 + JSONB | Reliable, queryable raw data |
| Graph store | Memgraph | Free Cypher + GDS, in-memory speed |
| Vector index | Memgraph native vector index | No separate Pinecone needed |
| Embeddings | OpenAI `text-embedding-3-small` | $0.02 / 1M tokens |
| Browser scraping | Playwright | Handles JS-heavy sites |
| LinkedIn data | Proxycurl API | Reliable, ToS-compliant |
| Company data | Crunchbase API + custom scraper | Comprehensive coverage |
| Container | Docker + docker-compose | Standard for multi-service |

---

## 3. Project structure

```
firstknock/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── README.md
├── alembic.ini
├── alembic/
│   └── versions/
│       └── 001_initial_schema.py
├── src/
│   └── firstknock/
│       ├── __init__.py
│       ├── main.py                          # FastAPI entry
│       ├── config.py                        # Pydantic settings
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes/
│       │   │   ├── ingest.py                # POST /ingest
│       │   │   ├── matches.py               # GET /matches/{id}
│       │   │   ├── email.py                 # POST /email/draft
│       │   │   └── graph.py                 # GET /graph/{id}
│       │   └── schemas.py                   # Pydantic request/response
│       │
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── orchestrator.py              # Coordinates all stages
│       │   │
│       │   ├── stage1_input/
│       │   │   ├── __init__.py
│       │   │   ├── pdf_parser.py
│       │   │   ├── docx_parser.py
│       │   │   ├── linkedin_fetcher.py
│       │   │   ├── ocr_parser.py
│       │   │   └── router.py                # Dispatches to right parser
│       │   │
│       │   ├── stage2_normalize/
│       │   │   ├── __init__.py
│       │   │   ├── text_cleaner.py
│       │   │   ├── section_detector.py
│       │   │   └── url_extractor.py
│       │   │
│       │   ├── stage3_extract/
│       │   │   ├── __init__.py
│       │   │   ├── llm_client.py            # Claude API wrapper
│       │   │   ├── prompts.py               # Extraction prompt
│       │   │   ├── schemas.py               # Pydantic JSON schema
│       │   │   └── extractor.py             # Main extraction logic
│       │   │
│       │   ├── stage4_resolve/
│       │   │   ├── __init__.py
│       │   │   ├── skill_canonicalizer.py
│       │   │   ├── company_matcher.py
│       │   │   ├── date_normalizer.py
│       │   │   └── aliases.py               # SKILL_ALIASES dict
│       │   │
│       │   ├── stage5_persist/
│       │   │   ├── __init__.py
│       │   │   ├── postgres_writer.py
│       │   │   └── models.py                # SQLAlchemy models
│       │   │
│       │   ├── stage6_enrich/
│       │   │   ├── __init__.py
│       │   │   ├── tasks.py                 # Celery task definitions
│       │   │   ├── github_enricher.py
│       │   │   ├── company_enricher.py
│       │   │   ├── project_enricher.py
│       │   │   └── institution_enricher.py
│       │   │
│       │   ├── stage7_infer/
│       │   │   ├── __init__.py
│       │   │   ├── engine.py                # Rule executor
│       │   │   ├── domain_rules.py          # Domain exposure rules
│       │   │   ├── skill_rules.py           # Adjacency rules
│       │   │   ├── project_rules.py         # Project implication rules
│       │   │   └── seniority_inference.py
│       │   │
│       │   ├── stage8_embed/
│       │   │   ├── __init__.py
│       │   │   └── embedder.py
│       │   │
│       │   └── stage9_graph/
│       │       ├── __init__.py
│       │       ├── memgraph_client.py
│       │       ├── schema_setup.py          # Indexes + vector index
│       │       ├── writers.py               # MERGE statements
│       │       └── queries.py               # Read queries
│       │
│       ├── workers/
│       │   ├── __init__.py
│       │   ├── celery_app.py
│       │   └── tasks.py                     # Routes to stage6_enrich
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           └── retry.py
│
├── data/
│   ├── skill_aliases.json                   # Canonical skill mapping
│   ├── company_index.json                   # Cached Crunchbase index
│   └── institution_rankings.json
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   └── sample_resumes/
│   │       ├── aswinthraj.pdf
│   │       └── ...
│   ├── stage1/
│   ├── stage3/
│   ├── stage7/
│   └── integration/
│
└── scripts/
    ├── rebuild_graph_from_postgres.py       # Cold-start recovery
    ├── seed_skill_aliases.py
    └── test_ingestion.py
```

---

## 4. Environment setup

### `pyproject.toml`

```toml
[project]
name = "firstknock"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Web framework
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    
    # LLM clients
    "anthropic>=0.34.0",
    "openai>=1.30.0",  # for embeddings only
    
    # PDF/DOCX parsing
    "pdfplumber>=0.11.0",
    "pymupdf>=1.24.0",
    "python-docx>=1.1.0",
    "pillow>=10.0.0",
    "pytesseract>=0.3.10",
    
    # Text processing
    "rapidfuzz>=3.6.0",
    "dateparser>=1.2.0",
    "langdetect>=1.0.9",
    
    # Database
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    
    # Graph database
    "gqlalchemy>=1.5.0",  # Memgraph Python client (or use neo4j driver)
    "neo4j>=5.18.0",      # Works with Memgraph via Bolt
    
    # Task queue
    "celery[redis]>=5.3.0",
    "redis>=5.0.0",
    
    # External APIs
    "httpx>=0.27.0",
    "playwright>=1.42.0",
    
    # Utilities
    "structlog>=24.1.0",
    "tenacity>=8.2.0",  # retries
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
]
```

### `.env.example`

```bash
# LLM APIs
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# External data
PROXYCURL_API_KEY=...
CRUNCHBASE_API_KEY=...
GITHUB_TOKEN=ghp_...

# Database
POSTGRES_URL=postgresql+asyncpg://firstknock:firstknock@localhost:5432/firstknock

# Graph database (Memgraph speaks Bolt protocol, same as Neo4j)
MEMGRAPH_URL=bolt://localhost:7687
MEMGRAPH_USER=
MEMGRAPH_PASSWORD=

# Task queue
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# App config
LOG_LEVEL=INFO
ENV=development
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: firstknock
      POSTGRES_PASSWORD: firstknock
      POSTGRES_DB: firstknock
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data

  memgraph:
    image: memgraph/memgraph-mage:latest
    ports:
      - "7687:7687"   # Bolt protocol
      - "7444:7444"   # Monitoring
      - "3000:3000"   # Memgraph Lab UI
    volumes:
      - memgraph-data:/var/lib/memgraph
      - memgraph-log:/var/log/memgraph
    command: >
      --storage-snapshot-interval-sec=300
      --storage-snapshot-retention-count=3
      --storage-wal-enabled=true
      --storage-wal-file-flush-every-n-tx=100
      --data-directory=/var/lib/memgraph
      --log-level=WARNING
      --bolt-server-name-for-init=Neo4j/5.11.0

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      POSTGRES_URL: postgresql+asyncpg://firstknock:firstknock@postgres:5432/firstknock
      MEMGRAPH_URL: bolt://memgraph:7687
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
    env_file: .env
    depends_on: [postgres, memgraph, redis]
    command: uvicorn firstknock.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./src:/app/src

  worker:
    build: .
    environment:
      POSTGRES_URL: postgresql+asyncpg://firstknock:firstknock@postgres:5432/firstknock
      MEMGRAPH_URL: bolt://memgraph:7687
      CELERY_BROKER_URL: redis://redis:6379/1
    env_file: .env
    depends_on: [postgres, memgraph, redis]
    command: celery -A firstknock.workers.celery_app worker --loglevel=info --concurrency=4

volumes:
  postgres-data:
  memgraph-data:
  memgraph-log:
  redis-data:
```

### `src/firstknock/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    # LLM APIs
    anthropic_api_key: str
    openai_api_key: str
    
    # External data
    proxycurl_api_key: str = ""
    crunchbase_api_key: str = ""
    github_token: str = ""
    
    # Databases
    postgres_url: str
    memgraph_url: str = "bolt://localhost:7687"
    memgraph_user: str = ""
    memgraph_password: str = ""
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # App
    env: str = "development"
    log_level: str = "INFO"
    
    # Pipeline tuning
    extraction_model: str = "claude-sonnet-4-6"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    skill_alias_match_threshold: int = 92
    company_match_threshold: int = 88


settings = Settings()
```

---

## 5. Stage 1 — Input ingestion

**Purpose**: Accept resumes in any format, return clean raw text.

**Files**: `src/firstknock/pipeline/stage1_input/`

### Router

```python
# stage1_input/router.py
from enum import Enum
from pathlib import Path
from typing import Union

from .pdf_parser import extract_pdf_text
from .docx_parser import extract_docx_text
from .linkedin_fetcher import fetch_linkedin_profile
from .ocr_parser import extract_image_text


class InputType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    LINKEDIN_URL = "linkedin_url"
    IMAGE = "image"
    PLAIN_TEXT = "plain_text"


async def ingest_input(
    source: Union[bytes, str, Path],
    input_type: InputType,
) -> dict:
    """
    Returns: {
        "raw_text": str,
        "source_type": str,
        "metadata": {"page_count": int, "language": str, ...}
    }
    """
    if input_type == InputType.PDF:
        return await extract_pdf_text(source)
    if input_type == InputType.DOCX:
        return await extract_docx_text(source)
    if input_type == InputType.LINKEDIN_URL:
        return await fetch_linkedin_profile(source)
    if input_type == InputType.IMAGE:
        return await extract_image_text(source)
    if input_type == InputType.PLAIN_TEXT:
        return {"raw_text": str(source), "source_type": "plain_text", "metadata": {}}
    raise ValueError(f"Unsupported input type: {input_type}")
```

### PDF parser

```python
# stage1_input/pdf_parser.py
import io
from typing import Union
import pdfplumber


async def extract_pdf_text(source: Union[bytes, str]) -> dict:
    """
    pdfplumber handles column detection automatically.
    Falls back to pymupdf if pdfplumber returns suspiciously short text
    (likely a scanned PDF that needs OCR).
    """
    if isinstance(source, bytes):
        fileobj = io.BytesIO(source)
    else:
        fileobj = source  # path
    
    text_parts = []
    page_count = 0
    
    with pdfplumber.open(fileobj) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text(layout=True) or ""
            text_parts.append(page_text)
    
    raw_text = "\n".join(text_parts).strip()
    
    # If pdfplumber returned very little text, it's likely a scanned PDF
    if len(raw_text) < 100:
        # Fallback: this is an image-based PDF, route to OCR
        from .ocr_parser import extract_pdf_via_ocr
        return await extract_pdf_via_ocr(source)
    
    return {
        "raw_text": raw_text,
        "source_type": "pdf",
        "metadata": {"page_count": page_count},
    }
```

### DOCX parser

```python
# stage1_input/docx_parser.py
import io
from typing import Union
from docx import Document


async def extract_docx_text(source: Union[bytes, str]) -> dict:
    if isinstance(source, bytes):
        fileobj = io.BytesIO(source)
    else:
        fileobj = source
    
    doc = Document(fileobj)
    
    text_parts = []
    for para in doc.paragraphs:
        text_parts.append(para.text)
    
    # Also extract from tables (resumes often use tables for layout)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text_parts.append(cell.text)
    
    raw_text = "\n".join(t for t in text_parts if t.strip())
    
    return {
        "raw_text": raw_text,
        "source_type": "docx",
        "metadata": {"paragraph_count": len(doc.paragraphs)},
    }
```

### LinkedIn fetcher

```python
# stage1_input/linkedin_fetcher.py
import httpx
from firstknock.config import settings


async def fetch_linkedin_profile(url: str) -> dict:
    """Uses Proxycurl API for ToS-compliant LinkedIn data."""
    api_url = "https://nubela.co/proxycurl/api/v2/linkedin"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            params={"url": url, "use_cache": "if-recent"},
            headers={"Authorization": f"Bearer {settings.proxycurl_api_key}"},
        )
        response.raise_for_status()
        data = response.json()
    
    # Reconstruct as resume-like text for downstream LLM extraction
    raw_text = _linkedin_json_to_text(data)
    
    return {
        "raw_text": raw_text,
        "source_type": "linkedin",
        "metadata": {"linkedin_data": data},  # keep structured for direct use
    }


def _linkedin_json_to_text(data: dict) -> str:
    """Convert Proxycurl JSON into resume-like text format."""
    parts = []
    parts.append(f"{data.get('full_name', '')}")
    parts.append(f"{data.get('headline', '')}")
    parts.append(f"{data.get('city', '')}, {data.get('country', '')}")
    parts.append(f"\nSUMMARY\n{data.get('summary', '')}")
    
    if data.get("experiences"):
        parts.append("\nWORK EXPERIENCE")
        for exp in data["experiences"]:
            parts.append(f"{exp.get('title')} - {exp.get('company')}")
            parts.append(f"{exp.get('starts_at', {}).get('year', '')} - {exp.get('ends_at', {}).get('year', 'Present')}")
            parts.append(exp.get("description", ""))
    
    if data.get("education"):
        parts.append("\nEDUCATION")
        for edu in data["education"]:
            parts.append(f"{edu.get('degree_name')} - {edu.get('school')}")
    
    return "\n".join(parts)
```

### OCR parser

```python
# stage1_input/ocr_parser.py
import io
import base64
from typing import Union

import pytesseract
from PIL import Image
import fitz  # pymupdf for rasterizing PDFs
from anthropic import AsyncAnthropic

from firstknock.config import settings


async def extract_image_text(source: Union[bytes, str]) -> dict:
    """Two-tier OCR: try Tesseract first (free, fast), escalate to Claude vision if confidence low."""
    if isinstance(source, bytes):
        img = Image.open(io.BytesIO(source))
    else:
        img = Image.open(source)
    
    # Try Tesseract first
    tesseract_text = pytesseract.image_to_string(img)
    
    # Measure confidence — Tesseract returns per-word confidence
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    confidences = [int(c) for c in data["conf"] if c != "-1"]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    if avg_confidence >= 70 and len(tesseract_text) > 200:
        return {
            "raw_text": tesseract_text,
            "source_type": "image_ocr",
            "metadata": {"ocr_method": "tesseract", "confidence": avg_confidence},
        }
    
    # Escalate to vision LLM
    return await _claude_vision_ocr(source)


async def _claude_vision_ocr(source: Union[bytes, str]) -> dict:
    """Use Claude's vision capability for complex layouts."""
    if isinstance(source, str):
        with open(source, "rb") as f:
            image_bytes = f.read()
    else:
        image_bytes = source
    
    image_b64 = base64.standard_b64encode(image_bytes).decode()
    
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.extraction_model,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
                },
                {
                    "type": "text",
                    "text": "Extract ALL text from this resume image exactly as written. Preserve section headers, bullet points, and structure. Output as plain text only.",
                },
            ],
        }],
    )
    
    return {
        "raw_text": message.content[0].text,
        "source_type": "image_vision",
        "metadata": {"ocr_method": "claude_vision"},
    }


async def extract_pdf_via_ocr(source: Union[bytes, str]) -> dict:
    """For scanned PDFs — rasterize each page and OCR."""
    if isinstance(source, bytes):
        doc = fitz.open(stream=source, filetype="pdf")
    else:
        doc = fitz.open(source)
    
    text_parts = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        result = await extract_image_text(img_bytes)
        text_parts.append(result["raw_text"])
    
    return {
        "raw_text": "\n".join(text_parts),
        "source_type": "pdf_ocr",
        "metadata": {"page_count": len(doc), "ocr_method": "page-by-page"},
    }
```

---

## 6. Stage 2 — Text normalization

**Purpose**: Clean text and detect section boundaries before LLM extraction. Saves LLM tokens and improves extraction reliability.

**Files**: `src/firstknock/pipeline/stage2_normalize/`

### Text cleaner

```python
# stage2_normalize/text_cleaner.py
import re
import unicodedata


def clean_text(raw_text: str) -> str:
    """Normalize whitespace, fix encoding, strip artifacts."""
    text = unicodedata.normalize("NFKC", raw_text)
    
    # Remove page-break artifacts
    text = re.sub(r"\f", "\n", text)
    
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Strip page numbers (lines containing only a number, possibly with "Page" prefix)
    text = re.sub(r"^(?:Page\s+)?\d+(?:\s+of\s+\d+)?\s*$", "", text, flags=re.MULTILINE)
    
    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r"[ \t]+", " ", text)
    
    # Trim each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    
    return text.strip()
```

### Section detector

```python
# stage2_normalize/section_detector.py
import re
from typing import Dict, Tuple


SECTION_PATTERNS = {
    "summary":      r"^(SUMMARY|OBJECTIVE|PROFILE|ABOUT)\b",
    "experience":   r"^(WORK\s+EXPERIENCE|EXPERIENCE|EMPLOYMENT|PROFESSIONAL\s+EXPERIENCE|WORK\s+HISTORY)\b",
    "education":    r"^(EDUCATION|ACADEMIC\s+BACKGROUND|QUALIFICATIONS)\b",
    "skills":       r"^(SKILLS|TECHNICAL\s+SKILLS|CORE\s+COMPETENCIES|EXPERTISE)\b",
    "projects":     r"^(PROJECTS|PERSONAL\s+PROJECTS|SIDE\s+PROJECTS)\b",
    "certifications": r"^(CERTIFICATIONS|CERTIFICATES|LICENSES)\b",
    "publications": r"^(PUBLICATIONS|RESEARCH|PAPERS)\b",
    "awards":       r"^(AWARDS|HONORS|ACHIEVEMENTS|RECOGNITION)\b",
    "languages":    r"^(LANGUAGES)\b",
    "interests":    r"^(INTERESTS|HOBBIES)\b",
    "volunteer":    r"^(VOLUNTEER|VOLUNTEERING|COMMUNITY)\b",
}


def detect_sections(text: str) -> Dict[str, Tuple[int, int]]:
    """
    Returns: {"experience": (start_char, end_char), ...}
    Sections that aren't found are absent from the dict.
    """
    matches = []
    for section_name, pattern in SECTION_PATTERNS.items():
        for m in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            matches.append((m.start(), section_name))
    
    # Sort by position
    matches.sort()
    
    sections = {}
    for i, (start, name) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        sections[name] = (start, end)
    
    return sections
```

### URL extractor

```python
# stage2_normalize/url_extractor.py
import re
from typing import Dict, List

URL_PATTERN = re.compile(
    r"(https?://[^\s\[\]]+|"
    r"github\.com/[\w\-]+(?:/[\w\-]+)?|"
    r"linkedin\.com/in/[\w\-]+)"
)

GITHUB_PATTERN = re.compile(r"github\.com/([\w\-]+)(?:/([\w\-]+))?")
LINKEDIN_PATTERN = re.compile(r"linkedin\.com/in/([\w\-]+)")


def extract_urls(text: str) -> Dict[str, List[str]]:
    """LLMs often drop URLs in extraction — extract and store separately."""
    urls = URL_PATTERN.findall(text)
    
    github_urls = []
    linkedin_urls = []
    other_urls = []
    
    for url in urls:
        if "github.com" in url:
            github_urls.append(url if url.startswith("http") else f"https://{url}")
        elif "linkedin.com" in url:
            linkedin_urls.append(url if url.startswith("http") else f"https://{url}")
        else:
            other_urls.append(url)
    
    return {
        "github": list(set(github_urls)),
        "linkedin": list(set(linkedin_urls)),
        "other": list(set(other_urls)),
    }


def infer_github_from_email(email: str) -> str:
    """Fallback: many resumes have GitHub as text 'github' with no URL.
    Try constructing from email prefix."""
    if "@" not in email:
        return ""
    username = email.split("@")[0]
    return f"https://github.com/{username}"
```

---

## 7. Stage 3 — LLM structured extraction

**Purpose**: Convert raw text → strict JSON schema using Claude. This is the most critical stage — every downstream stage depends on this output's structure.

**Files**: `src/firstknock/pipeline/stage3_extract/`

### Pydantic schema

```python
# stage3_extract/schemas.py
from typing import Optional, List
from pydantic import BaseModel, Field


class Identity(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website: Optional[str] = None


class Experience(BaseModel):
    company: str
    title: str
    location: Optional[str] = None
    start_date: str = Field(..., description="ISO format YYYY-MM or YYYY")
    end_date: Optional[str] = Field(None, description="ISO format or 'Present'")
    description: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    technologies_mentioned: List[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    gpa: Optional[str] = None
    activities: List[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str
    tech_stack: List[str] = Field(default_factory=list)
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    role: Optional[str] = None  # "solo" or "team"


class Skills(BaseModel):
    languages: List[str] = Field(default_factory=list)
    ai_ml: List[str] = Field(default_factory=list)
    frontend: List[str] = Field(default_factory=list)
    backend: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    devops: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    expiry: Optional[str] = None


class Language(BaseModel):
    language: str
    proficiency: Optional[str] = None  # "native", "fluent", "conversational", "basic"


class ResumeExtraction(BaseModel):
    identity: Identity
    summary: Optional[str] = None
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    certifications: List[Certification] = Field(default_factory=list)
    languages: List[Language] = Field(default_factory=list)
```

### Extraction prompt

```python
# stage3_extract/prompts.py

EXTRACTION_SYSTEM_PROMPT = """You are a resume parser that outputs strict JSON matching the provided schema.

Rules you MUST follow:
1. Output ONLY valid JSON, no preamble, no markdown fences, no commentary.
2. If a field is missing from the resume, use null (for single values) or [] (for lists).
3. NEVER hallucinate. If you cannot find a value, return null. Do not guess.
4. Dates MUST be ISO 8601: "YYYY-MM" for month-year, "YYYY" for year only, "Present" for current.
5. Extract technologies even from prose ("optimized the Postgres queries" → add "PostgreSQL" to technologies_mentioned).
6. Preserve URLs exactly as written. Never paraphrase or shorten URLs.
7. For bullet points, keep the original wording — do not summarize or rewrite.
8. Split skills into the correct category. If unsure, put in "tools".
9. For experience, infer location only if it's explicitly stated.
"""


EXTRACTION_USER_PROMPT_TEMPLATE = """Extract the following resume into JSON matching this exact schema:

{schema_json}

Resume text:
---
{resume_text}
---

Output the JSON object only."""
```

### Extractor

```python
# stage3_extract/extractor.py
import json
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from firstknock.config import settings
from .schemas import ResumeExtraction
from .prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE


_client = AsyncAnthropic(api_key=settings.anthropic_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def extract_resume(raw_text: str) -> ResumeExtraction:
    """Run LLM extraction with automatic retry on transient failures."""
    schema_json = json.dumps(ResumeExtraction.model_json_schema(), indent=2)
    
    user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
        schema_json=schema_json,
        resume_text=raw_text,
    )
    
    message = await _client.messages.create(
        model=settings.extraction_model,
        max_tokens=4096,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    
    response_text = message.content[0].text.strip()
    
    # Defensive: strip markdown fences if model added them despite instructions
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    response_text = response_text.strip()
    
    data = json.loads(response_text)
    return ResumeExtraction(**data)
```

---

## 8. Stage 4 — Entity resolution

**Purpose**: Normalize all extracted strings into canonical forms so the graph doesn't fragment with "React", "ReactJS", and "react.js" as separate nodes.

**Files**: `src/firstknock/pipeline/stage4_resolve/`

### Skill canonicalizer

```python
# stage4_resolve/aliases.py
# Living document — add entries as you encounter new variants

SKILL_ALIASES = {
    # Languages
    "py": "Python",
    "python3": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "es6": "JavaScript (ES6+)",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    
    # Frontend
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "nuxtjs": "Nuxt.js",
    "vuejs": "Vue.js",
    "tailwindcss": "Tailwind CSS",
    
    # Backend
    "nodejs": "Node.js",
    "node": "Node.js",
    "fastapi": "FastAPI",
    "django rest framework": "Django REST Framework",
    "drf": "Django REST Framework",
    
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "redis": "Redis",
    "neondb": "Neon (PostgreSQL)",
    
    # DevOps
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "gha": "GitHub Actions",
    "github actions": "GitHub Actions",
    "ci/cd": "CI/CD",
    
    # Cloud
    "aws": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    
    # AI/ML
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "openai api": "OpenAI API",
    "claude api": "Anthropic Claude API",
    "rag": "RAG",
    "llm": "LLM",
}


# Skills that should be marked as parents of others
SKILL_HIERARCHY = {
    "AWS RDS": ["AWS"],
    "AWS S3": ["AWS"],
    "AWS Lambda": ["AWS"],
    "Google Cloud Run": ["Google Cloud Platform"],
}
```

```python
# stage4_resolve/skill_canonicalizer.py
from typing import List, Tuple
from rapidfuzz import process, fuzz

from .aliases import SKILL_ALIASES, SKILL_HIERARCHY
from firstknock.config import settings


def canonicalize_skill(raw: str) -> str:
    """Normalize a raw skill string to its canonical form."""
    if not raw:
        return raw
    
    cleaned = raw.strip().lower()
    
    # Direct alias match
    if cleaned in SKILL_ALIASES:
        return SKILL_ALIASES[cleaned]
    
    # Fuzzy match against known aliases
    match = process.extractOne(
        cleaned,
        list(SKILL_ALIASES.keys()),
        scorer=fuzz.ratio,
        score_cutoff=settings.skill_alias_match_threshold,
    )
    if match:
        return SKILL_ALIASES[match[0]]
    
    # No match — return title-cased original
    return raw.strip()


def expand_with_parents(skill: str) -> List[str]:
    """Return skill + any parent skills (e.g. AWS RDS → [AWS RDS, AWS])."""
    result = [skill]
    if skill in SKILL_HIERARCHY:
        result.extend(SKILL_HIERARCHY[skill])
    return result


def canonicalize_skill_list(raw_skills: List[str]) -> List[str]:
    """Apply canonicalization + parent expansion + dedup."""
    result = set()
    for raw in raw_skills:
        canonical = canonicalize_skill(raw)
        for skill in expand_with_parents(canonical):
            result.add(skill)
    return sorted(result)
```

### Company matcher

```python
# stage4_resolve/company_matcher.py
import json
from pathlib import Path
from typing import Optional, Tuple
from rapidfuzz import process, fuzz
from firstknock.config import settings


# Load Crunchbase index once at import (or use redis cache in production)
_company_index = None


def _load_company_index():
    global _company_index
    if _company_index is None:
        try:
            path = Path("data/company_index.json")
            _company_index = json.loads(path.read_text())
        except FileNotFoundError:
            _company_index = {}
    return _company_index


def match_company(raw_name: str) -> Tuple[Optional[str], Optional[str], int]:
    """
    Returns: (canonical_name, crunchbase_id, confidence_score)
    If no match found, returns the cleaned raw name as canonical.
    """
    index = _load_company_index()
    if not index:
        return raw_name.strip(), None, 0
    
    cleaned = raw_name.strip()
    
    # Direct match
    if cleaned in index:
        return cleaned, index[cleaned]["id"], 100
    
    # Fuzzy match
    match = process.extractOne(
        cleaned,
        list(index.keys()),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=settings.company_match_threshold,
    )
    if match:
        matched_name = match[0]
        return matched_name, index[matched_name]["id"], int(match[1])
    
    return cleaned, None, 0
```

### Date normalizer

```python
# stage4_resolve/date_normalizer.py
import re
from typing import Optional
import dateparser


def normalize_date(raw: Optional[str]) -> Optional[str]:
    """Convert any date string to ISO 'YYYY-MM' or 'YYYY'. None for null/Present."""
    if not raw:
        return None
    
    raw = raw.strip()
    if raw.lower() in {"present", "current", "now", "ongoing"}:
        return None  # null = currently ongoing
    
    # Year only
    if re.fullmatch(r"\d{4}", raw):
        return raw
    
    parsed = dateparser.parse(raw)
    if parsed is None:
        return None
    
    # Return as YYYY-MM
    return f"{parsed.year:04d}-{parsed.month:02d}"


def date_range_months(start: Optional[str], end: Optional[str]) -> int:
    """Compute tenure in months. None end = present."""
    from datetime import date
    
    if not start:
        return 0
    
    parsed_start = dateparser.parse(start)
    if not parsed_start:
        return 0
    
    parsed_end = dateparser.parse(end) if end else None
    if not parsed_end:
        parsed_end = date.today()
    
    if hasattr(parsed_end, "year"):
        years_diff = parsed_end.year - parsed_start.year
        months_diff = parsed_end.month - parsed_start.month
        return years_diff * 12 + months_diff
    return 0
```

---

## 9. Stage 5 — PostgreSQL persistence (source of truth)

**Purpose**: Always write raw extracted JSON to Postgres before any further processing. This is the recovery layer — if Memgraph corrupts, rebuild from here.

**Files**: `src/firstknock/pipeline/stage5_persist/`

### Schema

```python
# stage5_persist/models.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resumes = relationship("Resume", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"
    
    resume_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    
    source_type = Column(String, nullable=False)  # pdf, docx, linkedin, ...
    raw_text = Column(Text)
    extracted_json = Column(JSONB)
    enriched_json = Column(JSONB)  # populated after enrichment workers finish
    
    status = Column(String, default="ingested", index=True)
    # statuses: ingested, extracted, enriched, inferred, embedded, graphed, failed
    
    graph_built = Column(Boolean, default=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    error_message = Column(Text)
    
    user = relationship("User", back_populates="resumes")
```

### Writer

```python
# stage5_persist/postgres_writer.py
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from firstknock.config import settings
from .models import Base, User, Resume


_engine = create_async_engine(settings.postgres_url, echo=False, future=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with _session_factory() as session:
        yield session


async def get_or_create_user(email: str) -> uuid.UUID:
    async with _session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            return user.user_id
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.user_id


async def save_extracted_resume(
    user_email: str,
    source_type: str,
    raw_text: str,
    extracted_json: dict,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Returns (user_id, resume_id). Always called BEFORE enrichment."""
    user_id = await get_or_create_user(user_email)
    
    async with _session_factory() as session:
        resume = Resume(
            user_id=user_id,
            source_type=source_type,
            raw_text=raw_text,
            extracted_json=extracted_json,
            status="extracted",
        )
        session.add(resume)
        await session.commit()
        await session.refresh(resume)
        return user_id, resume.resume_id


async def update_resume_status(resume_id: uuid.UUID, status: str, error: Optional[str] = None):
    async with _session_factory() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.status = status
        if error:
            resume.error_message = error
        await session.commit()


async def save_enrichment_data(resume_id: uuid.UUID, enriched_json: dict):
    async with _session_factory() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.enriched_json = enriched_json
        resume.status = "enriched"
        await session.commit()


async def mark_graph_built(resume_id: uuid.UUID):
    async with _session_factory() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        resume.graph_built = True
        resume.status = "graphed"
        await session.commit()
```

### Alembic migration

```python
# alembic/versions/001_initial_schema.py
"""initial schema

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    
    op.create_table(
        "resumes",
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("raw_text", sa.Text()),
        sa.Column("extracted_json", postgresql.JSONB()),
        sa.Column("enriched_json", postgresql.JSONB()),
        sa.Column("status", sa.String(), nullable=False, server_default="ingested"),
        sa.Column("graph_built", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_index("ix_resumes_status", "resumes", ["status"])
    op.create_index("ix_resumes_ingested_at", "resumes", ["ingested_at"])


def downgrade():
    op.drop_table("resumes")
    op.drop_table("users")
```

---

## 10. Stage 6 — Async enrichment workers

**Purpose**: Fetch external data about every entity (companies, projects, education) without blocking ingestion. Each enrichment is a separate Celery task — fail independently, retry independently.

**Files**: `src/firstknock/pipeline/stage6_enrich/` and `src/firstknock/workers/`

### Celery setup

```python
# workers/celery_app.py
from celery import Celery
from firstknock.config import settings

celery_app = Celery(
    "firstknock",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["firstknock.pipeline.stage6_enrich.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=2,
    task_default_retry_delay=60,
    task_max_retries=3,
)
```

### Enrichment task router

```python
# stage6_enrich/tasks.py
import asyncio
from uuid import UUID
from celery import group, chord
from firstknock.workers.celery_app import celery_app
from .github_enricher import enrich_github
from .company_enricher import enrich_company
from .project_enricher import enrich_project
from .institution_enricher import enrich_institution


@celery_app.task(name="enrich.dispatch", bind=True)
def dispatch_enrichment(self, resume_id: str, extracted_json: dict):
    """Fan out enrichment tasks. When all complete, trigger inference + graph write."""
    user_id = extracted_json.get("user_id")
    tasks = []
    
    # GitHub
    github_url = extracted_json.get("identity", {}).get("github_url")
    if github_url:
        tasks.append(github_enrich_task.s(resume_id, github_url))
    
    # Companies
    for exp in extracted_json.get("experience", []):
        tasks.append(company_enrich_task.s(resume_id, exp["company"]))
    
    # Projects (only if they have URLs)
    for proj in extracted_json.get("projects", []):
        if proj.get("github_url") or proj.get("demo_url"):
            tasks.append(project_enrich_task.s(resume_id, proj))
    
    # Education
    for edu in extracted_json.get("education", []):
        tasks.append(institution_enrich_task.s(resume_id, edu["institution"]))
    
    # When all enrichment done, trigger downstream
    chord(group(tasks))(downstream_pipeline.s(resume_id))


@celery_app.task(name="enrich.github", bind=True, max_retries=3)
def github_enrich_task(self, resume_id: str, github_url: str):
    try:
        return asyncio.run(enrich_github(github_url))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="enrich.company", bind=True, max_retries=3)
def company_enrich_task(self, resume_id: str, company_name: str):
    try:
        return asyncio.run(enrich_company(company_name))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="enrich.project", bind=True, max_retries=3)
def project_enrich_task(self, resume_id: str, project: dict):
    try:
        return asyncio.run(enrich_project(project))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="enrich.institution", bind=True, max_retries=3)
def institution_enrich_task(self, resume_id: str, institution_name: str):
    try:
        return asyncio.run(enrich_institution(institution_name))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="pipeline.downstream", bind=True)
def downstream_pipeline(self, enrichment_results: list, resume_id: str):
    """Runs after all enrichment tasks complete. Triggers inference + embedding + graph write."""
    from firstknock.pipeline.orchestrator import run_downstream_pipeline
    asyncio.run(run_downstream_pipeline(resume_id, enrichment_results))
```

### GitHub enricher

```python
# stage6_enrich/github_enricher.py
import re
from typing import Optional
import httpx
from firstknock.config import settings


GITHUB_API = "https://api.github.com"


async def enrich_github(github_url: str) -> dict:
    """Fetch repos, top languages, README signals for a GitHub user."""
    username = _extract_username(github_url)
    if not username:
        return {"error": "invalid_url"}
    
    headers = {"Authorization": f"token {settings.github_token}"} if settings.github_token else {}
    
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        # User profile
        user_resp = await client.get(f"{GITHUB_API}/users/{username}")
        if user_resp.status_code != 200:
            return {"error": f"user not found: {user_resp.status_code}"}
        user_data = user_resp.json()
        
        # Top repos by stars
        repos_resp = await client.get(
            f"{GITHUB_API}/users/{username}/repos",
            params={"sort": "updated", "per_page": 30},
        )
        repos = repos_resp.json() if repos_resp.status_code == 200 else []
        
        # Aggregate language stats from top 10 repos
        top_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:10]
        language_totals = {}
        for repo in top_repos:
            lang_resp = await client.get(f"{GITHUB_API}/repos/{username}/{repo['name']}/languages")
            if lang_resp.status_code == 200:
                for lang, bytes_count in lang_resp.json().items():
                    language_totals[lang] = language_totals.get(lang, 0) + bytes_count
        
        total_bytes = sum(language_totals.values()) or 1
        language_percentages = {
            lang: round(b / total_bytes * 100, 1)
            for lang, b in sorted(language_totals.items(), key=lambda x: -x[1])
        }
    
    return {
        "username": username,
        "followers": user_data.get("followers", 0),
        "public_repos": user_data.get("public_repos", 0),
        "bio": user_data.get("bio"),
        "top_repos": [
            {
                "name": r["name"],
                "stars": r.get("stargazers_count", 0),
                "language": r.get("language"),
                "description": r.get("description"),
                "url": r.get("html_url"),
            }
            for r in top_repos
        ],
        "language_breakdown": language_percentages,
    }


def _extract_username(url: str) -> Optional[str]:
    match = re.search(r"github\.com/([\w\-]+)", url)
    return match.group(1) if match else None
```

### Company enricher

```python
# stage6_enrich/company_enricher.py
import httpx
from firstknock.config import settings


async def enrich_company(company_name: str) -> dict:
    """
    Pipeline:
    1. Look up in Crunchbase (if API key available)
    2. Find company website
    3. Scrape job postings page to infer tech stack
    """
    crunchbase_data = await _crunchbase_lookup(company_name) if settings.crunchbase_api_key else {}
    
    website = crunchbase_data.get("homepage_url")
    tech_stack = []
    if website:
        tech_stack = await _scrape_tech_stack(website)
    
    return {
        "name": company_name,
        "website": website,
        "size": crunchbase_data.get("num_employees_enum"),
        "industry": crunchbase_data.get("category_list", []),
        "stage": crunchbase_data.get("funding_stage"),
        "location": crunchbase_data.get("city"),
        "tech_stack": tech_stack,
        "description": crunchbase_data.get("short_description"),
    }


async def _crunchbase_lookup(name: str) -> dict:
    """Crunchbase API v4 search."""
    if not settings.crunchbase_api_key:
        return {}
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://api.crunchbase.com/api/v4/searches/organizations",
            params={"query": name, "user_key": settings.crunchbase_api_key},
        )
        if response.status_code != 200:
            return {}
        results = response.json().get("entities", [])
        return results[0]["properties"] if results else {}


async def _scrape_tech_stack(website: str) -> list:
    """Best-effort: visit /careers or /jobs page, regex out tech names from job descriptions."""
    from playwright.async_api import async_playwright
    
    tech_keywords = {
        "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "Kotlin",
        "React", "Vue", "Angular", "Next.js", "Svelte",
        "FastAPI", "Django", "Flask", "Node.js", "Express",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform",
    }
    
    found = set()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            for path in ["/careers", "/jobs", "/about"]:
                try:
                    await page.goto(f"{website.rstrip('/')}{path}", timeout=10000)
                    content = await page.content()
                    for tech in tech_keywords:
                        if tech.lower() in content.lower():
                            found.add(tech)
                except Exception:
                    continue
            await browser.close()
    except Exception:
        pass
    
    return sorted(found)
```

### Project enricher

```python
# stage6_enrich/project_enricher.py
import re
import httpx
from firstknock.config import settings


async def enrich_project(project: dict) -> dict:
    enrichment = {"name": project["name"]}
    
    if github_url := project.get("github_url"):
        enrichment.update(await _enrich_github_repo(github_url))
    
    if demo_url := project.get("demo_url"):
        enrichment["live"] = await _check_url_alive(demo_url)
    
    return enrichment


async def _enrich_github_repo(repo_url: str) -> dict:
    match = re.search(r"github\.com/([\w\-]+)/([\w\-\.]+)", repo_url)
    if not match:
        return {}
    
    owner, repo = match.group(1), match.group(2).rstrip(".git")
    headers = {"Authorization": f"token {settings.github_token}"} if settings.github_token else {}
    
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        repo_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if repo_resp.status_code != 200:
            return {}
        repo_data = repo_resp.json()
        
        readme_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}/readme")
        readme_text = ""
        if readme_resp.status_code == 200:
            import base64
            content = readme_resp.json().get("content", "")
            readme_text = base64.b64decode(content).decode("utf-8", errors="ignore")[:5000]
    
    return {
        "stars": repo_data.get("stargazers_count", 0),
        "forks": repo_data.get("forks_count", 0),
        "language": repo_data.get("language"),
        "readme_excerpt": readme_text,
        "last_updated": repo_data.get("updated_at"),
    }


async def _check_url_alive(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.head(url)
            return resp.status_code < 400
    except Exception:
        return False
```

---

## 11. Stage 7 — Implicit inference engine

**Purpose**: Derive skills, domains, and seniority that aren't explicitly stated. The differentiator of FirstKnock.

**Files**: `src/firstknock/pipeline/stage7_infer/`

### Rule structure

```python
# stage7_infer/engine.py
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class InferredSkill:
    name: str
    confidence: float  # 0.0–1.0
    source: str        # "explicit", "domain_rule", "skill_adjacency", "project_implication"
    reason: str        # human-readable explanation, stored on the edge


@dataclass
class InferenceRule:
    name: str
    applies_to: str  # "company", "project", "skill", "title"
    condition: Callable[[dict], bool]
    infers: List[str]
    confidence: float
    reason_template: str
    
    def evaluate(self, entity: dict) -> List[InferredSkill]:
        if not self.condition(entity):
            return []
        return [
            InferredSkill(
                name=skill,
                confidence=self.confidence,
                source=self.applies_to,
                reason=self.reason_template.format(**entity),
            )
            for skill in self.infers
        ]


class InferenceEngine:
    def __init__(self, rules: List[InferenceRule]):
        self.rules = rules
    
    def run(self, extracted: dict, enriched: dict) -> List[InferredSkill]:
        """Run all rules over the extracted + enriched resume data."""
        inferred = []
        
        # Company-based rules
        for exp in extracted.get("experience", []):
            company_data = enriched.get("companies", {}).get(exp["company"], {})
            combined = {**exp, **company_data}
            for rule in [r for r in self.rules if r.applies_to == "company"]:
                inferred.extend(rule.evaluate(combined))
        
        # Project-based rules
        for proj in extracted.get("projects", []):
            for rule in [r for r in self.rules if r.applies_to == "project"]:
                inferred.extend(rule.evaluate(proj))
        
        # Skill-based rules (adjacency)
        all_skills = set()
        for category in extracted.get("skills", {}).values():
            all_skills.update(category)
        for skill in all_skills:
            for rule in [r for r in self.rules if r.applies_to == "skill"]:
                inferred.extend(rule.evaluate({"skill_name": skill}))
        
        # Dedup — keep highest confidence per skill name
        deduped = {}
        for inf in inferred:
            existing = deduped.get(inf.name)
            if not existing or inf.confidence > existing.confidence:
                deduped[inf.name] = inf
        
        return list(deduped.values())
```

### Domain rules

```python
# stage7_infer/domain_rules.py
from .engine import InferenceRule


DOMAIN_RULES = [
    InferenceRule(
        name="cloud_infra_company_exposure",
        applies_to="company",
        condition=lambda c: any(
            kw in str(c.get("industry", [])).lower() or kw in str(c.get("description", "")).lower()
            for kw in ["cloud", "infrastructure", "devops", "platform"]
        ),
        infers=["AWS", "Kubernetes", "Infrastructure as Code", "CI/CD", "Docker"],
        confidence=0.65,
        reason_template="worked at a cloud/infra company ({company}) — implies cloud exposure",
    ),
    InferenceRule(
        name="fintech_compliance_exposure",
        applies_to="company",
        condition=lambda c: any(
            kw in str(c.get("industry", [])).lower()
            for kw in ["fintech", "banking", "payments", "lending"]
        ),
        infers=["PCI-DSS", "KYC", "AML", "Financial Compliance"],
        confidence=0.55,
        reason_template="worked at a fintech company ({company}) — implies compliance exposure",
    ),
    InferenceRule(
        name="ai_company_exposure",
        applies_to="company",
        condition=lambda c: any(
            kw in str(c.get("industry", [])).lower() or kw in str(c.get("description", "")).lower()
            for kw in ["ai", "machine learning", "llm", "artificial intelligence"]
        ),
        infers=["MLOps", "Model Deployment", "Prompt Engineering"],
        confidence=0.60,
        reason_template="worked at an AI company ({company}) — implies ML ops exposure",
    ),
]
```

### Skill adjacency rules

```python
# stage7_infer/skill_rules.py
from .engine import InferenceRule


SKILL_ADJACENCY_RULES = [
    InferenceRule(
        name="fastapi_implies_async",
        applies_to="skill",
        condition=lambda e: e.get("skill_name") == "FastAPI",
        infers=["asyncio", "Pydantic", "ASGI"],
        confidence=0.70,
        reason_template="uses FastAPI — implies async Python patterns",
    ),
    InferenceRule(
        name="langgraph_implies_agents",
        applies_to="skill",
        condition=lambda e: e.get("skill_name") == "LangGraph",
        infers=["Agent State Machines", "Tool Calling", "Prompt Chaining"],
        confidence=0.80,
        reason_template="uses LangGraph — implies explicit agent state machine design",
    ),
    InferenceRule(
        name="gemini_live_implies_voice",
        applies_to="skill",
        condition=lambda e: "Gemini Live" in e.get("skill_name", ""),
        infers=["WebSocket Session Management", "Voice Activity Detection", "Real-time Audio Pipeline", "Streaming UX"],
        confidence=0.70,
        reason_template="uses Gemini Live API — implies real-time voice stack",
    ),
    InferenceRule(
        name="pinecone_implies_hybrid_search",
        applies_to="skill",
        condition=lambda e: e.get("skill_name") == "Pinecone",
        infers=["Vector Search", "Embedding Models"],
        confidence=0.85,
        reason_template="uses Pinecone — implies vector search knowledge",
    ),
    InferenceRule(
        name="kubernetes_implies_orchestration",
        applies_to="skill",
        condition=lambda e: e.get("skill_name") == "Kubernetes",
        infers=["Container Orchestration", "Helm", "Service Mesh", "YAML Configuration"],
        confidence=0.75,
        reason_template="uses Kubernetes — implies orchestration knowledge",
    ),
]
```

### Project implication rules

```python
# stage7_infer/project_rules.py
from .engine import InferenceRule


def _contains(haystack: str, needles: list) -> bool:
    return any(n.lower() in (haystack or "").lower() for n in needles)


PROJECT_RULES = [
    InferenceRule(
        name="voice_agent_implies_audio_stack",
        applies_to="project",
        condition=lambda p: _contains(p.get("description", ""), ["voice", "audio", "speech", "STT", "TTS"]),
        infers=["WebRTC", "Voice Activity Detection", "Audio Streaming", "Multimodal Data"],
        confidence=0.65,
        reason_template="built '{name}' (voice/audio project) — implies audio stack",
    ),
    InferenceRule(
        name="rag_platform_implies_retrieval_stack",
        applies_to="project",
        condition=lambda p: _contains(p.get("description", ""), ["RAG", "retrieval", "document search"]),
        infers=["Hybrid Search Fusion", "Reranker Pipeline", "BM25", "Chunking Strategies"],
        confidence=0.80,
        reason_template="built '{name}' (RAG platform) — implies retrieval expertise",
    ),
    InferenceRule(
        name="reranker_implies_advanced_rag",
        applies_to="project",
        condition=lambda p: any(
            "reranker" in t.lower() or "bge-" in t.lower() or "cross-encoder" in t.lower()
            for t in p.get("tech_stack", [])
        ),
        infers=["Cross-Encoder Reranking", "Hybrid Search Fusion", "Recall vs Precision Tuning"],
        confidence=0.85,
        reason_template="built '{name}' using reranker — implies advanced retrieval pipeline",
    ),
    InferenceRule(
        name="self_hosted_implies_devops",
        applies_to="project",
        condition=lambda p: any(
            kw in str(p.get("description", "")).lower() + str(p.get("tech_stack", [])).lower()
            for kw in ["vps", "self-host", "deployed", "production"]
        ),
        infers=["Linux Server Administration", "Reverse Proxy Config", "Process Management"],
        confidence=0.60,
        reason_template="self-deployed '{name}' — implies basic devops",
    ),
    InferenceRule(
        name="async_python_signal",
        applies_to="project",
        condition=lambda p: "asyncpg" in [t.lower() for t in p.get("tech_stack", [])],
        infers=["Async Connection Pooling", "High-Performance Backend Design"],
        confidence=0.80,
        reason_template="uses asyncpg in '{name}' — implies deliberate async backend choice",
    ),
]
```

### Seniority inference

```python
# stage7_infer/seniority_inference.py
from typing import Literal
from firstknock.pipeline.stage4_resolve.date_normalizer import date_range_months


SeniorityLevel = Literal["junior", "mid", "senior", "staff", "intern"]


def infer_seniority(extracted: dict) -> SeniorityLevel:
    """Heuristic seniority inference from titles, tenure, and project complexity."""
    experiences = extracted.get("experience", [])
    
    # Compute total tenure
    total_months = sum(
        date_range_months(exp.get("start_date"), exp.get("end_date"))
        for exp in experiences
    )
    total_years = total_months / 12
    
    # Inspect titles
    all_titles = " ".join(exp.get("title", "").lower() for exp in experiences)
    
    if "intern" in all_titles and total_years < 2:
        return "intern"
    if any(kw in all_titles for kw in ["staff", "principal", "distinguished"]):
        return "staff"
    if any(kw in all_titles for kw in ["senior", "sr.", "lead", "head of"]):
        return "senior"
    if total_years >= 5:
        return "senior"
    if total_years >= 2:
        return "mid"
    return "junior"
```

### Build the engine

```python
# stage7_infer/__init__.py
from .engine import InferenceEngine
from .domain_rules import DOMAIN_RULES
from .skill_rules import SKILL_ADJACENCY_RULES
from .project_rules import PROJECT_RULES

# Single global engine instance
inference_engine = InferenceEngine(
    rules=DOMAIN_RULES + SKILL_ADJACENCY_RULES + PROJECT_RULES,
)
```

---

## 12. Stage 8 — Embedding generation

**Purpose**: Generate vector embeddings for semantic search. Store directly on graph nodes (no separate Pinecone).

**Files**: `src/firstknock/pipeline/stage8_embed/`

```python
# stage8_embed/embedder.py
from typing import List
from openai import AsyncOpenAI
from firstknock.config import settings


_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_text(text: str) -> List[float]:
    """Single text → embedding vector."""
    response = await _client.embeddings.create(
        model=settings.embedding_model,
        input=text,
        dimensions=settings.embedding_dimension,
    )
    return response.data[0].embedding


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Batch embedding for efficiency. OpenAI allows up to 2048 inputs per call."""
    response = await _client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
        dimensions=settings.embedding_dimension,
    )
    return [d.embedding for d in response.data]


async def embed_resume(extracted: dict, inferred_skills: list) -> dict:
    """Generate all embeddings needed for the graph in one batch call."""
    texts = []
    keys = []
    
    # Full resume summary embedding
    summary_text = _build_resume_summary(extracted, inferred_skills)
    texts.append(summary_text)
    keys.append("resume_summary")
    
    # Per-project embeddings
    for i, proj in enumerate(extracted.get("projects", [])):
        proj_text = f"{proj['name']}: {proj.get('description', '')} Tech: {', '.join(proj.get('tech_stack', []))}"
        texts.append(proj_text)
        keys.append(f"project_{i}")
    
    embeddings_list = await embed_batch(texts)
    
    return dict(zip(keys, embeddings_list))


def _build_resume_summary(extracted: dict, inferred_skills: list) -> str:
    parts = []
    if summary := extracted.get("summary"):
        parts.append(summary)
    
    # Aggregate all skills (explicit + inferred)
    all_skills = []
    for cat in extracted.get("skills", {}).values():
        all_skills.extend(cat)
    all_skills.extend(s.name for s in inferred_skills)
    parts.append(f"Skills: {', '.join(set(all_skills))}")
    
    # Recent experience
    for exp in extracted.get("experience", [])[:2]:
        parts.append(f"{exp['title']} at {exp['company']}: {exp.get('description', '')}")
    
    return "\n".join(parts)
```

---

## 13. Stage 9 — Memgraph graph write

**Purpose**: Write all nodes and relationships using `MERGE` (idempotent). Set up indexes and vector index on first run.

**Files**: `src/firstknock/pipeline/stage9_graph/`

### Memgraph client

```python
# stage9_graph/memgraph_client.py
from neo4j import AsyncGraphDatabase
from firstknock.config import settings


_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.memgraph_url,
            auth=(settings.memgraph_user, settings.memgraph_password) if settings.memgraph_user else None,
        )
    return _driver


async def execute_query(cypher: str, params: dict | None = None):
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(cypher, params or {})
        return [record async for record in result]


async def execute_write(cypher: str, params: dict | None = None):
    return await execute_query(cypher, params)
```

### Schema setup

```python
# stage9_graph/schema_setup.py
from .memgraph_client import execute_write
from firstknock.config import settings


INDEXES = [
    "CREATE INDEX ON :Person(user_id);",
    "CREATE INDEX ON :Person(email);",
    "CREATE INDEX ON :Skill(name);",
    "CREATE INDEX ON :Company(name);",
    "CREATE INDEX ON :Project(user_id);",
    "CREATE INDEX ON :Education(user_id);",
    "CREATE INDEX ON :Domain(name);",
    "CREATE INDEX ON :Job(id);",
]


async def setup_schema():
    """Run on app startup. Indexes are idempotent in Memgraph."""
    for stmt in INDEXES:
        try:
            await execute_write(stmt)
        except Exception as e:
            print(f"Index already exists or failed: {stmt}: {e}")
    
    # Vector indexes for embeddings
    try:
        await execute_write(f"""
            CREATE VECTOR INDEX person_embedding ON :Person(embedding)
            WITH CONFIG {{"dimension": {settings.embedding_dimension}, "capacity": 100000, "metric": "cos"}};
        """)
    except Exception as e:
        print(f"person_embedding vector index: {e}")
    
    try:
        await execute_write(f"""
            CREATE VECTOR INDEX project_embedding ON :Project(embedding)
            WITH CONFIG {{"dimension": {settings.embedding_dimension}, "capacity": 500000, "metric": "cos"}};
        """)
    except Exception as e:
        print(f"project_embedding vector index: {e}")
```

### Graph writers

```python
# stage9_graph/writers.py
import uuid
from typing import List
from .memgraph_client import execute_write
from firstknock.pipeline.stage4_resolve.skill_canonicalizer import canonicalize_skill_list
from firstknock.pipeline.stage4_resolve.date_normalizer import normalize_date, date_range_months
from firstknock.pipeline.stage7_infer.engine import InferredSkill


async def write_resume_to_graph(
    user_id: uuid.UUID,
    extracted: dict,
    enriched: dict,
    inferred_skills: List[InferredSkill],
    embeddings: dict,
    seniority: str,
):
    """Main entry point. Writes all nodes and relationships for a resume."""
    user_id_str = str(user_id)
    identity = extracted["identity"]
    
    # 1. Person node
    await _write_person(user_id_str, identity, extracted.get("summary"), seniority, embeddings.get("resume_summary"))
    
    # 2. Explicit skills
    all_explicit_skills = []
    for cat_name, cat_skills in extracted.get("skills", {}).items():
        for skill in canonicalize_skill_list(cat_skills):
            all_explicit_skills.append((skill, cat_name))
    
    for skill, category in all_explicit_skills:
        await _write_skill_node(skill, category)
        await _write_has_skill_edge(user_id_str, skill, confidence=1.0, source="explicit",
                                    reason=f"listed in {category} section")
    
    # 3. Inferred skills
    for inf in inferred_skills:
        await _write_skill_node(inf.name, category="inferred")
        await _write_has_skill_edge(user_id_str, inf.name,
                                    confidence=inf.confidence,
                                    source=inf.source,
                                    reason=inf.reason)
    
    # 4. Experience → Company nodes
    for exp in extracted.get("experience", []):
        company_data = enriched.get("companies", {}).get(exp["company"], {})
        await _write_company_node(exp["company"], company_data)
        await _write_worked_at_edge(user_id_str, exp, company_data)
    
    # 5. Projects
    for i, proj in enumerate(extracted.get("projects", [])):
        proj_embedding = embeddings.get(f"project_{i}")
        await _write_project_node(user_id_str, proj, enriched.get("projects", {}).get(proj["name"], {}), proj_embedding)
        await _write_built_edge(user_id_str, proj["name"])
    
    # 6. Education
    for edu in extracted.get("education", []):
        edu_data = enriched.get("institutions", {}).get(edu["institution"], {})
        await _write_education_node(user_id_str, edu, edu_data)
        await _write_studied_at_edge(user_id_str, edu["institution"])


async def _write_person(user_id: str, identity: dict, summary: str | None, seniority: str, embedding: list | None):
    await execute_write(
        """
        MERGE (p:Person {email: $email})
        SET p.user_id = $user_id,
            p.name = $name,
            p.phone = $phone,
            p.location = $location,
            p.github_url = $github_url,
            p.linkedin_url = $linkedin_url,
            p.summary = $summary,
            p.seniority = $seniority,
            p.embedding = $embedding,
            p.ingested_at = timestamp()
        """,
        {
            "email": identity["email"],
            "user_id": user_id,
            "name": identity["name"],
            "phone": identity.get("phone"),
            "location": identity.get("location"),
            "github_url": identity.get("github_url"),
            "linkedin_url": identity.get("linkedin_url"),
            "summary": summary,
            "seniority": seniority,
            "embedding": embedding,
        },
    )


async def _write_skill_node(skill_name: str, category: str):
    await execute_write(
        "MERGE (s:Skill {name: $name}) ON CREATE SET s.category = $category",
        {"name": skill_name, "category": category},
    )


async def _write_has_skill_edge(user_id: str, skill_name: str, confidence: float, source: str, reason: str):
    await execute_write(
        """
        MATCH (p:Person {user_id: $user_id}), (s:Skill {name: $skill_name})
        MERGE (p)-[r:HAS_SKILL]->(s)
        SET r.confidence = $confidence,
            r.source = $source,
            r.reason = $reason,
            r.updated_at = timestamp()
        """,
        {
            "user_id": user_id,
            "skill_name": skill_name,
            "confidence": confidence,
            "source": source,
            "reason": reason,
        },
    )


async def _write_company_node(name: str, enriched: dict):
    await execute_write(
        """
        MERGE (c:Company {name: $name})
        SET c.website   = $website,
            c.industry  = $industry,
            c.size      = $size,
            c.stage     = $stage,
            c.location  = $location,
            c.tech_stack = $tech_stack,
            c.enriched_at = timestamp()
        """,
        {
            "name": name,
            "website": enriched.get("website"),
            "industry": enriched.get("industry") or [],
            "size": enriched.get("size"),
            "stage": enriched.get("stage"),
            "location": enriched.get("location"),
            "tech_stack": enriched.get("tech_stack") or [],
        },
    )


async def _write_worked_at_edge(user_id: str, exp: dict, company_data: dict):
    tenure = date_range_months(exp.get("start_date"), exp.get("end_date"))
    await execute_write(
        """
        MATCH (p:Person {user_id: $user_id}), (c:Company {name: $company})
        MERGE (p)-[r:WORKED_AT {start_date: $start_date}]->(c)
        SET r.title = $title,
            r.end_date = $end_date,
            r.location = $location,
            r.bullets = $bullets,
            r.tech_used = $tech_used,
            r.tenure_months = $tenure
        """,
        {
            "user_id": user_id,
            "company": exp["company"],
            "title": exp["title"],
            "start_date": normalize_date(exp.get("start_date")),
            "end_date": normalize_date(exp.get("end_date")),
            "location": exp.get("location"),
            "bullets": exp.get("bullets") or [],
            "tech_used": exp.get("technologies_mentioned") or [],
            "tenure": tenure,
        },
    )


async def _write_project_node(user_id: str, proj: dict, enriched: dict, embedding: list | None):
    await execute_write(
        """
        MERGE (p:Project {user_id: $user_id, name: $name})
        SET p.description = $description,
            p.tech_stack  = $tech_stack,
            p.github_url  = $github_url,
            p.demo_url    = $demo_url,
            p.stars       = $stars,
            p.language    = $language,
            p.live        = $live,
            p.embedding   = $embedding
        """,
        {
            "user_id": user_id,
            "name": proj["name"],
            "description": proj.get("description"),
            "tech_stack": proj.get("tech_stack") or [],
            "github_url": proj.get("github_url"),
            "demo_url": proj.get("demo_url"),
            "stars": enriched.get("stars", 0),
            "language": enriched.get("language"),
            "live": enriched.get("live"),
            "embedding": embedding,
        },
    )


async def _write_built_edge(user_id: str, project_name: str):
    await execute_write(
        """
        MATCH (p:Person {user_id: $user_id}), (proj:Project {user_id: $user_id, name: $name})
        MERGE (p)-[:BUILT]->(proj)
        """,
        {"user_id": user_id, "name": project_name},
    )


async def _write_education_node(user_id: str, edu: dict, enriched: dict):
    await execute_write(
        """
        MERGE (e:Education {user_id: $user_id, institution: $institution})
        SET e.degree = $degree,
            e.field = $field,
            e.start = $start,
            e.end = $end,
            e.gpa = $gpa,
            e.affiliation = $affiliation,
            e.ranking = $ranking
        """,
        {
            "user_id": user_id,
            "institution": edu["institution"],
            "degree": edu.get("degree"),
            "field": edu.get("field"),
            "start": normalize_date(edu.get("start")),
            "end": normalize_date(edu.get("end")),
            "gpa": edu.get("gpa"),
            "affiliation": enriched.get("affiliation"),
            "ranking": enriched.get("ranking"),
        },
    )


async def _write_studied_at_edge(user_id: str, institution: str):
    await execute_write(
        """
        MATCH (p:Person {user_id: $user_id}), (e:Education {user_id: $user_id, institution: $inst})
        MERGE (p)-[:STUDIED_AT]->(e)
        """,
        {"user_id": user_id, "inst": institution},
    )
```

---

## 14. Orchestrator

The orchestrator wires all stages together. Sync stages run in the API request; async stages dispatch to Celery.

```python
# pipeline/orchestrator.py
import uuid
from typing import Union

from .stage1_input.router import ingest_input, InputType
from .stage2_normalize.text_cleaner import clean_text
from .stage2_normalize.section_detector import detect_sections
from .stage2_normalize.url_extractor import extract_urls, infer_github_from_email
from .stage3_extract.extractor import extract_resume
from .stage4_resolve.skill_canonicalizer import canonicalize_skill_list
from .stage5_persist.postgres_writer import save_extracted_resume, save_enrichment_data, mark_graph_built
from .stage7_infer import inference_engine
from .stage7_infer.seniority_inference import infer_seniority
from .stage8_embed.embedder import embed_resume
from .stage9_graph.writers import write_resume_to_graph
from firstknock.workers.celery_app import celery_app


async def run_sync_ingestion(source: Union[bytes, str], input_type: InputType) -> dict:
    """
    Stages 1–5: complete in <3 seconds, return to API caller.
    Then fires async enrichment task and returns.
    """
    # 1. Input
    result = await ingest_input(source, input_type)
    raw_text = result["raw_text"]
    
    # 2. Normalize
    cleaned = clean_text(raw_text)
    sections = detect_sections(cleaned)
    urls = extract_urls(raw_text)
    
    # 3. Extract via LLM
    extracted = await extract_resume(cleaned)
    extracted_dict = extracted.model_dump()
    
    # Backfill missing URLs from regex extraction
    if not extracted_dict["identity"].get("github_url") and urls["github"]:
        extracted_dict["identity"]["github_url"] = urls["github"][0]
    if not extracted_dict["identity"].get("github_url") and extracted_dict["identity"].get("email"):
        extracted_dict["identity"]["github_url"] = infer_github_from_email(extracted_dict["identity"]["email"])
    
    # 4. Resolve (canonicalize all skills in place)
    for cat in extracted_dict["skills"]:
        extracted_dict["skills"][cat] = canonicalize_skill_list(extracted_dict["skills"][cat])
    
    # 5. Persist to PostgreSQL (source of truth)
    user_id, resume_id = await save_extracted_resume(
        user_email=extracted_dict["identity"]["email"],
        source_type=result["source_type"],
        raw_text=raw_text,
        extracted_json=extracted_dict,
    )
    
    # Fire async enrichment
    celery_app.send_task(
        "enrich.dispatch",
        args=[str(resume_id), {**extracted_dict, "user_id": str(user_id)}],
    )
    
    return {
        "resume_id": str(resume_id),
        "user_id": str(user_id),
        "status": "processing",
        "stages_complete": ["input", "normalize", "extract", "resolve", "persist"],
        "stages_pending": ["enrich", "infer", "embed", "graph"],
    }


async def run_downstream_pipeline(resume_id: str, enrichment_results: list):
    """
    Called by Celery chord after all enrichment tasks complete.
    Stages 7-9: inference, embedding, graph write.
    """
    from firstknock.pipeline.stage5_persist.postgres_writer import _session_factory
    from firstknock.pipeline.stage5_persist.models import Resume
    from sqlalchemy import select
    
    # Load extracted JSON from Postgres
    async with _session_factory() as session:
        result = await session.execute(select(Resume).where(Resume.resume_id == resume_id))
        resume = result.scalar_one()
        extracted = resume.extracted_json
    
    # Restructure enrichment results into expected shape
    enriched = _structure_enrichment(enrichment_results)
    
    # Save enriched data
    await save_enrichment_data(uuid.UUID(resume_id), enriched)
    
    # 7. Inference
    inferred_skills = inference_engine.run(extracted, enriched)
    seniority = infer_seniority(extracted)
    
    # 8. Embeddings
    embeddings = await embed_resume(extracted, inferred_skills)
    
    # 9. Graph write
    await write_resume_to_graph(
        user_id=uuid.UUID(extracted.get("user_id", str(uuid.uuid4()))),
        extracted=extracted,
        enriched=enriched,
        inferred_skills=inferred_skills,
        embeddings=embeddings,
        seniority=seniority,
    )
    
    await mark_graph_built(uuid.UUID(resume_id))


def _structure_enrichment(results: list) -> dict:
    """Convert flat enrichment results into {companies: {...}, projects: {...}, institutions: {...}}."""
    structured = {"companies": {}, "projects": {}, "institutions": {}, "github": None}
    for result in results:
        if not result:
            continue
        if "username" in result:
            structured["github"] = result
        elif "name" in result and "industry" in result:
            structured["companies"][result["name"]] = result
        elif "name" in result and ("stars" in result or "live" in result):
            structured["projects"][result["name"]] = result
        elif "affiliation" in result:
            structured["institutions"][result["name"]] = result
    return structured
```

---

## 15. API layer

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from firstknock.api.routes import ingest, matches, email, graph
from firstknock.pipeline.stage9_graph.schema_setup import setup_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_schema()
    yield


app = FastAPI(title="FirstKnock", lifespan=lifespan)

app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(matches.router, prefix="/matches", tags=["matching"])
app.include_router(email.router, prefix="/email", tags=["email"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])


@app.get("/health")
async def health():
    return {"status": "ok"}
```

```python
# api/routes/ingest.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from firstknock.pipeline.orchestrator import run_sync_ingestion
from firstknock.pipeline.stage1_input.router import InputType


router = APIRouter()


@router.post("")
async def ingest_resume(file: UploadFile = File(...)):
    """Upload a resume file. Returns immediately with processing status."""
    content = await file.read()
    
    if file.filename.endswith(".pdf"):
        input_type = InputType.PDF
    elif file.filename.endswith(".docx"):
        input_type = InputType.DOCX
    elif file.filename.endswith((".png", ".jpg", ".jpeg")):
        input_type = InputType.IMAGE
    else:
        raise HTTPException(400, "Unsupported file type")
    
    try:
        result = await run_sync_ingestion(content, input_type)
        return result
    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {e}")


@router.post("/linkedin")
async def ingest_linkedin(url: str = Form(...)):
    try:
        return await run_sync_ingestion(url, InputType.LINKEDIN_URL)
    except Exception as e:
        raise HTTPException(500, f"LinkedIn fetch failed: {e}")
```

---

## 16. Build order — non-negotiable

Build in this exact sequence. Each phase is testable on its own.

### Phase 1 — Foundation (Day 1-2)
1. Project scaffold: `pyproject.toml`, `docker-compose.yml`, `.env.example`
2. `config.py` with Pydantic settings
3. Start postgres + memgraph + redis containers
4. Alembic schema for Postgres
5. Verify: `docker-compose up` runs cleanly, Memgraph accessible at `bolt://localhost:7687`

### Phase 2 — Core ingestion (Day 3-5)
1. Stage 1: PDF parser only (`pdf_parser.py`)
2. Stage 2: Text cleaner + section detector + URL extractor
3. Stage 3: LLM extractor with Pydantic schema
4. Stage 4: Skill canonicalizer + date normalizer (skip company matcher initially)
5. Stage 5: PostgreSQL writer
6. Wire stages 1–5 into orchestrator
7. Verify: PDF in → JSON in Postgres

### Phase 3 — Graph write (Day 6-7)
1. Stage 9: Memgraph schema setup, writers
2. Skip embeddings initially — pass `None` for embedding fields
3. Skip inference initially — write only explicit data
4. Verify: After ingestion, open Memgraph Lab (localhost:3000), see Person + Skill + Company nodes

### Phase 4 — Inference engine (Day 8-9)
1. Stage 7: Engine + first 3 rule files (domain, skill, project)
2. Add inferred skills to graph write
3. Verify: HAS_SKILL edges with `source="inferred"` appear in graph

### Phase 5 — Enrichment workers (Day 10-12)
1. Celery setup + Redis connection
2. Stage 6: GitHub enricher first (highest signal)
3. Wire enrichment dispatch into orchestrator
4. Add company enricher, project enricher last
5. Verify: After ingestion, check Postgres `enriched_json` populates within 30s

### Phase 6 — Embeddings + vector index (Day 13)
1. Stage 8: Embedder with OpenAI
2. Add vector index creation to schema setup
3. Backfill embeddings on existing nodes via script
4. Verify: `CALL vector_search.search_nodes(...)` returns results

### Phase 7 — Additional input formats (Day 14)
1. DOCX parser
2. LinkedIn fetcher
3. OCR parser (Tesseract + Claude vision fallback)
4. Verify: Each format produces equivalent output for the same person

### Phase 8 — API hardening (Day 15)
1. All 4 endpoints (`/ingest`, `/matches`, `/email`, `/graph`)
2. Rate limiting, auth (JWT)
3. Request/response validation
4. Error handling + structured logging

---

## 17. Testing strategy

### Unit tests per stage

```python
# tests/stage3/test_extractor.py
import pytest
from firstknock.pipeline.stage3_extract.extractor import extract_resume


@pytest.mark.asyncio
async def test_extract_aswinthraj_resume():
    raw_text = open("tests/fixtures/sample_resumes/aswinthraj.txt").read()
    result = await extract_resume(raw_text)
    
    assert result.identity.name == "Aswinthraj Devaraj"
    assert result.identity.email == "iamaswinth@gmail.com"
    assert len(result.experience) == 2
    assert len(result.projects) == 2
    assert "FastAPI" in result.skills.backend
    assert "LangGraph" in result.skills.ai_ml
```

```python
# tests/stage4/test_skill_canonicalization.py
from firstknock.pipeline.stage4_resolve.skill_canonicalizer import canonicalize_skill


def test_react_variants_canonicalize():
    assert canonicalize_skill("reactjs") == "React"
    assert canonicalize_skill("react.js") == "React"
    assert canonicalize_skill("React JS") == "React"


def test_aws_parent_expansion():
    from firstknock.pipeline.stage4_resolve.skill_canonicalizer import canonicalize_skill_list
    result = canonicalize_skill_list(["AWS RDS"])
    assert "AWS RDS" in result
    assert "AWS" in result
```

```python
# tests/stage7/test_inference_engine.py
import pytest
from firstknock.pipeline.stage7_infer import inference_engine


def test_voice_agent_infers_audio_stack():
    extracted = {
        "experience": [],
        "projects": [{
            "name": "AI Interviewer",
            "description": "Built a voice-based AI interviewer using Gemini Live",
            "tech_stack": ["Google ADK", "Gemini Live API"],
        }],
        "skills": {"ai_ml": ["LangGraph", "Gemini Live API"]},
    }
    enriched = {"companies": {}}
    
    inferred = inference_engine.run(extracted, enriched)
    inferred_names = {s.name for s in inferred}
    
    assert "Voice Activity Detection" in inferred_names
    assert "Agent State Machines" in inferred_names
```

### Integration tests

```python
# tests/integration/test_full_pipeline.py
import pytest
from firstknock.pipeline.orchestrator import run_sync_ingestion
from firstknock.pipeline.stage1_input.router import InputType


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_ingestion_pdf():
    with open("tests/fixtures/sample_resumes/aswinthraj.pdf", "rb") as f:
        content = f.read()
    
    result = await run_sync_ingestion(content, InputType.PDF)
    
    assert result["status"] == "processing"
    assert "resume_id" in result
    # Wait for async stages... (use polling or fixed delay in test)
```

---

## 18. Production deployment

### Memgraph persistence checklist

In `docker-compose.yml`, these flags are non-negotiable for production:

```yaml
command: >
  --storage-snapshot-interval-sec=300
  --storage-snapshot-retention-count=3
  --storage-wal-enabled=true
  --storage-wal-file-flush-every-n-tx=100
  --data-directory=/var/lib/memgraph
```

Mounted volume `memgraph-data:/var/lib/memgraph` survives container restarts.

### Cold-start recovery script

```python
# scripts/rebuild_graph_from_postgres.py
"""
Run this if Memgraph data directory is lost.
Rebuilds the entire graph from PostgreSQL extracted_json.
"""
import asyncio
from sqlalchemy import select
from firstknock.pipeline.stage5_persist.postgres_writer import _session_factory
from firstknock.pipeline.stage5_persist.models import Resume
from firstknock.pipeline.stage9_graph.schema_setup import setup_schema
from firstknock.pipeline.orchestrator import run_downstream_pipeline


async def rebuild():
    await setup_schema()
    
    async with _session_factory() as session:
        result = await session.execute(
            select(Resume).where(Resume.status.in_(["enriched", "graphed"]))
        )
        resumes = result.scalars().all()
    
    print(f"Rebuilding {len(resumes)} resumes into Memgraph...")
    
    for resume in resumes:
        try:
            # Reuse enrichment from cache, re-run inference + graph write
            await run_downstream_pipeline(
                resume_id=str(resume.resume_id),
                enrichment_results=resume.enriched_json or {},
            )
            print(f"✓ {resume.resume_id}")
        except Exception as e:
            print(f"✗ {resume.resume_id}: {e}")


if __name__ == "__main__":
    asyncio.run(rebuild())
```

### Monitoring

Add `prometheus-client` to dependencies. Expose metrics at `/metrics`:

```python
from prometheus_client import Counter, Histogram, make_asgi_app

ingestion_total = Counter("firstknock_ingestion_total", "Total resume ingestions", ["status"])
ingestion_duration = Histogram("firstknock_ingestion_duration_seconds", "Ingestion duration")
inference_skills_inferred = Histogram("firstknock_inferred_skills_per_resume", "Skills inferred per resume")
graph_node_count = Counter("firstknock_graph_nodes_created", "Total nodes created in graph", ["label"])

app.mount("/metrics", make_asgi_app())
```

### Health checks

```python
@app.get("/health/deep")
async def deep_health():
    """Verify all dependencies are reachable."""
    health = {"status": "ok", "checks": {}}
    
    try:
        from firstknock.pipeline.stage5_persist.postgres_writer import _session_factory
        async with _session_factory() as session:
            await session.execute(text("SELECT 1"))
        health["checks"]["postgres"] = "ok"
    except Exception as e:
        health["checks"]["postgres"] = f"error: {e}"
        health["status"] = "degraded"
    
    try:
        from firstknock.pipeline.stage9_graph.memgraph_client import execute_query
        await execute_query("RETURN 1")
        health["checks"]["memgraph"] = "ok"
    except Exception as e:
        health["checks"]["memgraph"] = f"error: {e}"
        health["status"] = "degraded"
    
    return health
```

---

## 19. What to defer until later

Things that are tempting to build now but should wait until you have real usage:

- Authentication (build with magic links via Resend, don't overthink)
- Multi-resume per user (just take latest for v1)
- Public API rate limiting (Cloudflare handles this for free)
- A frontend (test with curl / Postman / your existing FirstKnock UI)
- The cold email generator (separate document — covered after ingestion is stable)
- Job matching queries (only valuable once you have jobs in the graph)
- The graph visualization UI

The ingestion pipeline is the entire foundation. Everything else is downstream from a solid graph. Get this right, then the rest of FirstKnock becomes much easier.

---

## 20. Common pitfalls to avoid

1. **Don't use `CREATE` in Cypher writes — always `MERGE`.** The pipeline must be idempotent. Users will re-upload the same resume.

2. **Don't put `user_id` on shared nodes (`:Skill`, `:Company`).** They're global. The user-specific data lives on the edge.

3. **Don't block ingestion on enrichment.** Always return to the caller in <3 seconds. Enrichment is async.

4. **Don't trust LLM output blindly.** Always validate with Pydantic. Use `tenacity` for retries with exponential backoff.

5. **Don't skip Postgres.** Always write raw extracted JSON to Postgres BEFORE Memgraph. If Memgraph dies, you can rebuild. If you skipped Postgres, you've lost user data.

6. **Don't hardcode prompts in business logic.** Keep all LLM prompts in `prompts.py` files so they're easy to version and test.

7. **Don't forget indexes.** Without `CREATE INDEX ON :Person(user_id)`, every query scans the full graph. Add indexes on day one.

8. **Don't reinvent the alias table.** Start with the `SKILL_ALIASES` dict in this spec, grow it as you encounter new variants in real resumes.

9. **Don't combine inference rules into giant if/else blocks.** Keep them as separate `InferenceRule` objects so each is testable in isolation.

10. **Don't forget the `ingested_at` timestamp.** You'll need it for analytics and debugging within the first week.

---

## End of spec

This document is everything you need to build the FirstKnock ingestion pipeline. Hand it to Claude Code, follow the build order in section 16, and you'll have a working Graph RAG resume system.

When you complete each phase, run the validation step described in section 16 — don't move to the next phase until the current one is verified.
