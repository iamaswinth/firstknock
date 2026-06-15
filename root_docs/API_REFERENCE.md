# FirstKnock — Backend API Reference

Base URL: `http://localhost:8000`  
All responses are JSON. No authentication required (dev mode).  
CORS is open to all origins.  
Interactive docs: `http://localhost:8000/docs`

---

## Table of Contents
- [POST /ingest](#post-ingest)
- [GET /health](#get-health)
- [GET /health/deep](#get-healthdeep)
- [GET /resume/{resume_id}](#get-resumeresume_id)
- [GET /profile/{user_id}](#get-profileuser_id)
- [GET /skills/{user_id}](#get-skillsuser_id)
- [GET /graph/{user_id}](#get-graphuser_id)
- [GET /analytics/{user_id}](#get-analyticsuser_id)
- [TypeScript Types](#typescript-types)
- [Frontend Flow](#frontend-flow)

---

## POST /ingest

Upload a PDF or DOCX resume. Triggers the full ingestion pipeline synchronously (parse → extract → graph) and dispatches enrichment + embeddings async in background.

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | Yes | `.pdf` or `.docx` resume |
| `email` | string | Yes | User's email — used to create/link the user account |

**Response `200`**
```json
{
  "resume_id": "eba00ecc-36a7-4f8c-beb4-e8ac71d044a4",
  "user_id": "01e46dca-8d5a-434f-8550-009a601a8c67",
  "status": "extracted",
  "stages_complete": ["parse", "normalize", "extract", "resolve", "persist", "graph"],
  "stages_pending": ["enrichment", "inference", "embedding"]
}
```

**Errors**
- `400` — unsupported file type (not pdf/docx)
- `500` — extraction failed

**Notes for frontend:**
- Save both `resume_id` and `user_id` — you'll need them for all other endpoints.
- `stages_pending` always contains `["enrichment", "inference", "embedding"]` — these run async. Poll `/resume/{resume_id}` to track status.
- Typical response time: **8–20 seconds** (LLM extraction is synchronous).

---

## GET /health

Basic liveness check.

**Response `200`**
```json
{ "status": "ok" }
```

---

## GET /health/deep

Checks all three services: NeonDB, Memgraph, Redis.

**Response `200`**
```json
{
  "overall": "ok",
  "services": [
    { "name": "neondb",   "status": "ok",    "latency_ms": 42.1,  "detail": null },
    { "name": "memgraph", "status": "ok",    "latency_ms": 3.2,   "detail": null },
    { "name": "redis",    "status": "error", "latency_ms": null,  "detail": "Connection refused" }
  ]
}
```

`overall` values: `"ok"` | `"degraded"` | `"error"`

---

## GET /resume/{resume_id}

Status polling endpoint + full extracted resume data. Call this after `/ingest` to check if enrichment is done and to get all profile data.

**Path param:** `resume_id` — UUID from `/ingest` response

**Response `200`**
```json
{
  "resume_id": "eba00ecc-36a7-4f8c-beb4-e8ac71d044a4",
  "user_id": "01e46dca-8d5a-434f-8550-009a601a8c67",
  "status": "enriched",
  "graph_built": true,
  "ingested_at": "2026-05-27T10:30:00",
  "updated_at": "2026-05-27T10:30:45",
  "identity": {
    "name": "Aswinthraj Devaraj",
    "email": "iamaswinth@gmail.com",
    "phone": "6369585965",
    "location": "Tirupur, TamilNadu",
    "headline": "Full Stack AI Engineer",
    "github_url": "https://github.com/iamaswinth",
    "linkedin_url": "https://www.linkedin.com/in/aswinthraj-d-362a18291/"
  },
  "experience": [
    {
      "company": "TechKareer",
      "title": "Software Engineering Intern",
      "location": "Remote",
      "start_date": "2026-01",
      "end_date": null,
      "is_current": true,
      "months": 5,
      "description": ["Built AI agent workflows using Google ADK"],
      "tech_stack": ["Google ADK", "FastAPI", "Next.js", "LangGraph"]
    }
  ],
  "projects": [
    {
      "name": "The Mind Surf",
      "description": "RAG-based knowledge management app",
      "tech_stack": ["Next.js", "Pinecone", "FastAPI"],
      "url": null,
      "github_url": "https://github.com/iamaswinth/the-mind-surf"
    }
  ],
  "skills": {
    "languages":  ["Python", "JavaScript", "SQL"],
    "frameworks": ["Next.js", "React", "FastAPI"],
    "ai_ml":      ["LangGraph", "Google ADK", "Gemini Live API", "RAG"],
    "databases":  ["PostgreSQL", "Pinecone", "Neon"],
    "devops":     ["Docker", "GitHub Actions", "Azure"],
    "other":      ["Blender"]
  },
  "education": [
    {
      "institution": "KSR College of Engineering, Tiruchengode",
      "degree": "B.E.",
      "field": "Computer Science Engineering",
      "start_year": "2022",
      "end_year": "2026"
    }
  ],
  "certifications": [],
  "enriched": {
    "github": {
      "profile": { "followers": 12, "public_repos": 18, "bio": "Building AI stuff" },
      "pinned_repos": [
        {
          "name": "the-mind-surf",
          "stars": 4,
          "forks": 1,
          "primary_language": "TypeScript",
          "topics": ["rag", "nextjs", "pinecone"],
          "readme_summary": "AI-powered knowledge management tool using RAG...",
          "extracted_skills": ["Next.js", "Pinecone", "FastAPI"],
          "is_new": false
        }
      ]
    },
    "companies": {
      "TechKareer": { "stage": "seed", "industry": "EdTech", "headcount": 15, "founded": 2023, "headquarters": "India" }
    },
    "institutions": {
      "KSR College of Engineering, Tiruchengode": { "ranking_tier": "other" }
    }
  }
}
```

**Status lifecycle:** `"extracted"` → `"enriched"` (after Celery enrichment completes, ~10–30s)

**Errors**
- `400` — invalid UUID format
- `404` — resume not found

**Polling pattern:**
```js
// Poll every 3s until status === "enriched"
const poll = setInterval(async () => {
  const res = await fetch(`/resume/${resumeId}`)
  const data = await res.json()
  if (data.status === "enriched") clearInterval(poll)
}, 3000)
```

---

## GET /profile/{user_id}

Merged profile: Postgres resume data + Memgraph node properties (seniority, GitHub stats).

**Path param:** `user_id` — UUID from `/ingest` response

**Response `200`**
```json
{
  "user_id": "01e46dca-8d5a-434f-8550-009a601a8c67",
  "name": "Aswinthraj Devaraj",
  "email": "iamaswinth@gmail.com",
  "headline": "Full Stack AI Engineer",
  "github_url": "https://github.com/iamaswinth",
  "linkedin_url": "https://www.linkedin.com/in/aswinthraj-d-362a18291/",
  "location": "Tirupur, TamilNadu",
  "seniority": "mid",
  "total_experience_months": 18,
  "github_followers": 12,
  "public_repos": 18,
  "experience": [ /* same as /resume */ ],
  "projects": [ /* same as /resume */ ],
  "education": [ /* same as /resume */ ],
  "skills_summary": {
    "explicit_count": 32,
    "inferred_count": 0,
    "total": 32
  }
}
```

`seniority` values: `"junior"` | `"mid"` | `"senior"` | `"staff"` | `null` (if graph not built yet)

**Errors**
- `400` — invalid UUID
- `404` — user not found

---

## GET /skills/{user_id}

All skills from the graph with confidence scores and inference explanations.

**Response `200`**
```json
{
  "user_id": "01e46dca-8d5a-434f-8550-009a601a8c67",
  "explicit": [
    { "name": "Python",    "category": "language",  "source": "explicit", "confidence": 1.0, "inferred_by": null, "reason": null },
    { "name": "FastAPI",   "category": "framework", "source": "explicit", "confidence": 1.0, "inferred_by": null, "reason": null },
    { "name": "LangGraph", "category": "framework", "source": "explicit", "confidence": 1.0, "inferred_by": null, "reason": null }
  ],
  "inferred": [
    {
      "name": "WebRTC",
      "category": "tool",
      "source": "inferred",
      "confidence": 0.85,
      "inferred_by": "llm",
      "reason": "Gemini Live API requires WebRTC for real-time audio streaming"
    },
    {
      "name": "Agent State Machines",
      "category": "concept",
      "source": "inferred",
      "confidence": 0.9,
      "inferred_by": "graph_implies",
      "reason": "LangGraph is built on agent state machine architecture"
    }
  ],
  "total": 47
}
```

`source` values: `"explicit"` | `"inferred"` | `"graph_algo"`  
`inferred_by` values: `"llm"` | `"graph_implies"` | `"adamic_adar"` | `null`

**Errors**
- `404` — no skills found (graph may not be built yet)
- `503` — Memgraph unavailable

---

## GET /graph/{user_id}

Full graph visualization data in **react-force-graph** format. Pass the response directly to `<ForceGraph2D graphData={data} />`.

**Response `200`**
```json
{
  "nodes": [
    {
      "id": "01e46dca-8d5a-434f-8550-009a601a8c67",
      "name": "Aswinthraj Devaraj",
      "type": "Person",
      "val": 20,
      "community_id": null,
      "confidence": null,
      "source_type": null,
      "properties": { "seniority": "mid", "total_experience_months": 18 }
    },
    {
      "id": "skill-Python",
      "name": "Python",
      "type": "Skill",
      "val": 10,
      "community_id": 2,
      "confidence": 1.0,
      "source_type": "explicit",
      "properties": { "category": "language" }
    },
    {
      "id": "skill-WebRTC",
      "name": "WebRTC",
      "type": "Skill",
      "val": 5,
      "community_id": 1,
      "confidence": 0.85,
      "source_type": "inferred",
      "properties": { "category": "tool" }
    },
    {
      "id": "company-TechKareer",
      "name": "TechKareer",
      "type": "Company",
      "val": 8,
      "properties": { "stage": "seed", "industry": "EdTech" }
    },
    {
      "id": "proj-uuid",
      "name": "The Mind Surf",
      "type": "Project",
      "val": 8,
      "properties": { "stars": 4, "primary_language": "TypeScript" }
    }
  ],
  "links": [
    {
      "source": "01e46dca-...",
      "target": "skill-Python",
      "type": "HAS_SKILL",
      "confidence": 1.0,
      "source_type": "explicit",
      "co_occurrence": null,
      "properties": {}
    },
    {
      "source": "01e46dca-...",
      "target": "company-TechKareer",
      "type": "WORKED_AT",
      "properties": { "title": "Software Engineering Intern", "months": 5, "is_current": true }
    },
    {
      "source": "skill-Python",
      "target": "skill-FastAPI",
      "type": "CO_OCCURS_WITH",
      "co_occurrence": 8,
      "properties": {}
    }
  ],
  "communities": [
    {
      "id": 1,
      "name": "LangGraph + Google ADK",
      "color": "#7C3AED",
      "skills": ["LangGraph", "Google ADK", "RAG", "Gemini Live API", "browser-use"]
    },
    {
      "id": 2,
      "name": "React + Next.js",
      "color": "#0EA5E9",
      "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS"]
    }
  ]
}
```

**Node types:** `"Person"` | `"Skill"` | `"Company"` | `"Project"` | `"Institution"`  
**Link types:** `"HAS_SKILL"` | `"WORKED_AT"` | `"BUILT"` | `"USES"` | `"STUDIED_AT"` | `"CO_OCCURS_WITH"`  

**`val` (node size guide):**
| Node type | val |
|---|---|
| Person | 20 |
| Explicit Skill | 10 |
| Company / Project | 8 |
| Institution | 6 |
| Inferred Skill | 5 |
| Graph-algo Skill | 3 |

**`communities`:** `null` if Memgraph MAGE not installed — handle gracefully in UI.

**Errors**
- `404` — no graph data (graph not built yet)
- `503` — Memgraph unavailable

---

## GET /analytics/{user_id}

Career analytics: timeline, skill communities, bridge skills, inferred skill explanations.
MAGE-dependent fields (`skill_communities`, `bridge_skills`) return `null` if MAGE not installed.

**Response `200`**
```json
{
  "user_id": "01e46dca-8d5a-434f-8550-009a601a8c67",
  "seniority": "mid",
  "total_experience_months": 18,
  "career_timeline": [
    {
      "company": "TechKareer",
      "title": "Software Engineering Intern",
      "start_date": "2026-01",
      "end_date": null,
      "months": 5,
      "is_current": true
    },
    {
      "company": "Praskla Technology",
      "title": "Software Engineering Intern",
      "start_date": "2025-07",
      "end_date": "2025-12",
      "months": 6,
      "is_current": false
    }
  ],
  "skill_communities": [
    {
      "id": 1,
      "name": "LangGraph + Google ADK",
      "skills": ["LangGraph", "Google ADK", "RAG", "Gemini Live API"]
    },
    {
      "id": 2,
      "name": "React + Next.js",
      "skills": ["React", "Next.js", "Tailwind CSS", "TypeScript"]
    }
  ],
  "bridge_skills": [
    { "name": "FastAPI",   "centrality": 0.8712, "category": "framework" },
    { "name": "Python",    "centrality": 0.7430, "category": "language" },
    { "name": "Docker",    "centrality": 0.4210, "category": "tool" }
  ],
  "inferred_skills": [
    {
      "name": "WebRTC",
      "category": "tool",
      "source": "inferred",
      "confidence": 0.85,
      "inferred_by": "llm",
      "reason": "Gemini Live API requires WebRTC for real-time audio streaming"
    },
    {
      "name": "Pydantic",
      "category": "framework",
      "source": "inferred",
      "confidence": 0.9,
      "inferred_by": "graph_implies",
      "reason": "FastAPI is built on Pydantic for data validation"
    }
  ]
}
```

**Errors**
- `400` — invalid UUID
- `404` — user not found

---

## TypeScript Types

Copy-paste ready for your Next.js project:

```typescript
// POST /ingest
interface IngestResponse {
  resume_id: string
  user_id: string
  status: string
  stages_complete: string[]
  stages_pending: string[]
}

// GET /resume/{resume_id}
interface ResumeStatusResponse {
  resume_id: string
  user_id: string
  status: 'extracted' | 'enriched' | 'ingested'
  graph_built: boolean
  ingested_at: string
  updated_at: string
  identity: {
    name: string
    email: string | null
    phone: string | null
    location: string | null
    headline: string | null
    github_url: string | null
    linkedin_url: string | null
  }
  experience: ExperienceEntry[]
  projects: ProjectEntry[]
  skills: {
    languages: string[]
    frameworks: string[]
    ai_ml: string[]
    databases: string[]
    devops: string[]
    other: string[]
  }
  education: EducationEntry[]
  certifications: string[]
  enriched: EnrichedData | null
}

interface ExperienceEntry {
  company: string
  title: string
  location: string | null
  start_date: string | null
  end_date: string | null
  is_current: boolean
  months: number | null
  description: string[]
  tech_stack: string[]
}

interface ProjectEntry {
  name: string
  description: string
  tech_stack: string[]
  url: string | null
  github_url: string | null
}

interface EducationEntry {
  institution: string
  degree: string
  field: string
  start_year: string | null
  end_year: string | null
}

interface EnrichedData {
  github?: {
    profile: { followers: number; public_repos: number; bio: string }
    pinned_repos: PinnedRepo[]
  }
  companies: Record<string, CompanyData>
  institutions: Record<string, { ranking_tier: string }>
}

interface PinnedRepo {
  name: string
  stars: number
  forks: number
  primary_language: string
  topics: string[]
  readme_summary: string
  extracted_skills: string[]
  is_new: boolean
}

interface CompanyData {
  stage: string | null
  industry: string | null
  headcount: number | null
  founded: number | null
  headquarters: string | null
}

// GET /profile/{user_id}
interface ProfileResponse {
  user_id: string
  name: string
  email: string
  headline: string | null
  github_url: string | null
  linkedin_url: string | null
  location: string | null
  seniority: 'junior' | 'mid' | 'senior' | 'staff' | null
  total_experience_months: number | null
  github_followers: number | null
  public_repos: number | null
  experience: ExperienceEntry[]
  projects: ProjectEntry[]
  education: EducationEntry[]
  skills_summary: { explicit_count: number; inferred_count: number; total: number }
}

// GET /skills/{user_id}
interface SkillItem {
  name: string
  category: string
  source: 'explicit' | 'inferred' | 'graph_algo'
  confidence: number
  inferred_by: string | null
  reason: string | null
}

interface SkillsResponse {
  user_id: string
  explicit: SkillItem[]
  inferred: SkillItem[]
  total: number
}

// GET /graph/{user_id}
interface GraphNode {
  id: string
  name: string
  type: 'Person' | 'Skill' | 'Company' | 'Project' | 'Institution'
  val: number
  community_id: number | null
  confidence: number | null
  source_type: 'explicit' | 'inferred' | 'graph_algo' | null
  properties: Record<string, unknown>
}

interface GraphLink {
  source: string
  target: string
  type: string
  confidence: number | null
  source_type: string | null
  co_occurrence: number | null
  properties: Record<string, unknown>
}

interface GraphCommunity {
  id: number
  name: string
  color: string
  skills: string[]
}

interface GraphResponse {
  nodes: GraphNode[]
  links: GraphLink[]
  communities: GraphCommunity[]
}

// GET /analytics/{user_id}
interface CareerEntry {
  company: string
  title: string
  start_date: string | null
  end_date: string | null
  months: number | null
  is_current: boolean
}

interface BridgeSkill {
  name: string
  centrality: number
  category: string | null
}

interface InferredSkillDetail {
  name: string
  category: string
  source: string
  confidence: number
  inferred_by: string | null
  reason: string | null
}

interface SkillCommunity {
  id: number
  name: string
  skills: string[]
}

interface AnalyticsResponse {
  user_id: string
  seniority: string | null
  total_experience_months: number | null
  career_timeline: CareerEntry[]
  skill_communities: SkillCommunity[] | null
  bridge_skills: BridgeSkill[] | null
  inferred_skills: InferredSkillDetail[]
}
```

---

## Frontend Flow

### Recommended page structure

```
/                     → Upload page (drag & drop PDF)
/profile/{user_id}    → Main profile + graph visualization
```

### Step-by-step data loading

```typescript
// 1. Upload resume → get resume_id + user_id
const upload = await fetch('/ingest', { method: 'POST', body: formData })
const { resume_id, user_id } = await upload.json()

// 2. Poll until enrichment completes (~10-30s)
const pollStatus = () => fetch(`/resume/${resume_id}`)
  .then(r => r.json())
  .then(d => d.status)

// 3. Load all profile data in parallel
const [profile, skills, graph, analytics] = await Promise.all([
  fetch(`/profile/${user_id}`).then(r => r.json()),
  fetch(`/skills/${user_id}`).then(r => r.json()),
  fetch(`/graph/${user_id}`).then(r => r.json()),
  fetch(`/analytics/${user_id}`).then(r => r.json()),
])

// 4. Pass graph data directly to react-force-graph
// <ForceGraph2D graphData={{ nodes: graph.nodes, links: graph.links }} />
```

### Color coding for graph nodes

```typescript
const NODE_COLORS: Record<string, string> = {
  Person: '#F59E0B',
  Company: '#3B82F6',
  Project: '#10B981',
  Institution: '#8B5CF6',
}

// For Skill nodes: use community color if available
const getSkillColor = (node: GraphNode, communities: GraphCommunity[]) => {
  if (node.type !== 'Skill') return NODE_COLORS[node.type]
  const community = communities.find(c => c.id === node.community_id)
  if (community) return community.color
  // Fallback: dim inferred skills
  return node.source_type === 'explicit' ? '#6B7280' : '#D1D5DB'
}
```

### Recommended npm packages

```bash
npm install react-force-graph       # 3D/2D force graph
npm install @tanstack/react-query   # data fetching + polling
npm install framer-motion           # animations
npm install recharts                # career timeline chart
```
