# FirstKnock — Resume Ingestion Pipeline Architecture

A conceptual architecture document for brainstorming. No code. Every layer is explained in terms of what it does, why it exists, what decisions it forces you to make, and what can go wrong.

---

## Part 1 — The big picture

### What FirstKnock is solving

Resumes are unstructured documents that lose information at every step of their lifecycle. A person spends 3 weeks at a cloud infrastructure company building backend services, and the only thing that ends up on the resume is "Software Engineer" with a few bullet points. Everything else — the cloud exposure, the CI/CD habits, the on-call experience, the working knowledge of containers — is lost.

FirstKnock's job is to reverse that information loss. Take a resume, recover what's missing, and use that recovered information to match people to the right jobs and write the right cold emails.

The ingestion pipeline is the foundation. It's the engine that takes raw, lossy resume data and produces a rich, queryable knowledge graph. Everything else FirstKnock does (job matching, email generation, "why matched" explanations) is downstream of this pipeline.

### Core architectural principles

These five principles drive every design decision in the pipeline. When you brainstorm changes later, check them against these:

**1. The resume is lossy. The graph should be lossless.**
The pipeline's job is to recover information that the resume format threw away. Every layer either extracts what's written, infers what's implied, or enriches what's missing.

**2. PostgreSQL is the source of truth. Memgraph is the query layer.**
Raw extracted data always goes to Postgres first. Memgraph is a queryable projection that can be rebuilt from Postgres at any time. This means Memgraph can be in-memory without losing user data on a restart.

**3. Synchronous stages return fast. Asynchronous stages take their time.**
The user uploads a resume and gets a response in under 3 seconds. Enrichment, inference, and embedding generation happen in the background. This isn't optional — it's the only way to keep the UX acceptable while doing expensive enrichment work.

**4. Inference confidence lives on the edge, not the node.**
A skill like "FastAPI" is the same node whether one user explicitly stated it or another user had it inferred. The user-specific confidence and reason live on the relationship between the person and the skill. This is what makes the graph efficient — shared nodes, user-specific edges.

**5. Every write is idempotent.**
Users re-upload resumes. Jobs retry on failure. Enrichment workers can run twice. The pipeline must produce the same graph state every time, regardless of how many times any stage runs.

### Data flow at a glance

```
Resume file uploaded by user
         │
         ▼
[Parse format-specific text]
         │
         ▼
[Clean and structure raw text]
         │
         ▼
[LLM extracts to JSON]                 ─── synchronous
         │                                  (returns to user in ~3s)
         ▼
[Resolve entities to canonical names]
         │
         ▼
[Save to PostgreSQL]
         │
   ┌─────┴─────┐
   ▼           ▼
[Async]    [User sees]
   │       "Processing..."
   ▼
[Fetch external data
 for every entity]                     ─── asynchronous
   │                                       (completes in 30-60s)
   ▼
[Inference engine runs
 over enriched data]
   │
   ▼
[Generate embeddings]
   │
   ▼
[Write graph to Memgraph]
   │
   ▼
User notified: graph ready
```

The dotted line between synchronous and asynchronous is the most important architectural boundary in the system. Get this wrong and either ingestion is slow (bad UX) or data is incomplete (bad matching).

---

## Part 2 — Layer-by-layer deep dive

Each layer below follows the same structure: what it does, what decisions you have to make, what can go wrong, and questions to think about.

---

### Layer 1 — Input ingestion

**What it does**
Accepts a resume in any format the user might have and produces clean raw text. This is the format normalization layer — its only job is to handle the messy reality of how people store their resumes.

**Input formats to support**
- PDF (the default for ~80% of users)
- DOCX (Microsoft Word, still common)
- LinkedIn URL (users who don't have a resume file)
- Image / scan (photographed resume, old scanned doc)
- Plain text (developer power users, paste from text editor)

**Key design decisions**

The most important decision in this layer is the OCR escalation strategy. Tesseract is free and fast but fails on complex layouts (multi-column resumes, decorative fonts, low-resolution scans). GPT-4o Vision is expensive but handles anything. You need a confidence threshold below which you escalate from Tesseract to Vision.

The second decision is whether to even support LinkedIn URLs. Pulling LinkedIn data via Proxycurl costs money per call and adds an external dependency, but LinkedIn data is structured and rich. The tradeoff is: do you want users to upload a PDF (free, lossy) or paste a URL (~$0.01 per ingestion, much richer data)?

The third decision is layout preservation. PDFs with multi-column layouts can be extracted as either "linear" (all left column, then all right column) or "spatial" (preserving visual layout). For resumes, spatial is almost always better — section headers stay with their content.

**What can go wrong**
- Password-protected PDFs (need to handle gracefully and ask user for password)
- Resumes with embedded fonts that break extraction
- Resumes where the entire content is actually an embedded image (scanned and saved as PDF)
- Right-to-left language resumes (Arabic, Hebrew) where text order gets reversed
- Multi-page resumes with headers/footers that bleed into the content extraction
- Tables used purely for layout (every cell becomes a separate text fragment)

**Questions to brainstorm**
- Do you want to support video resumes? (Some users in creative fields submit these.)
- What's your stance on resumes with images of the person? (Privacy/bias implications.)
- Do you store the original file or only the extracted text? (Storage cost vs. ability to re-extract.)
- Should you detect resume language and prompt the LLM in that language? (Affects extraction quality for non-English resumes.)
- How do you handle resumes that are actually CVs (academic, 10+ pages with publications)?
- Do you accept multiple file formats in one submission? (Cover letter + resume + portfolio doc.)

---

### Layer 2 — Text normalization

**What it does**
Takes raw text from Layer 1 and cleans it up before sending to the LLM. This layer exists because every dollar you save on LLM tokens is a dollar that scales with your user count.

**What it actually does**

Three things: strip artifacts that confuse the LLM, detect section boundaries to help the LLM, and extract URLs separately because LLMs are notoriously bad at preserving URLs in their output.

The artifact stripping handles things like page numbers, repeated headers/footers, page-break characters, and weird Unicode that PDFs sometimes inject. Without this, the LLM either wastes tokens or worse, hallucinates that "Page 3 of 5" is part of the person's job title.

The section detection is a fast regex pass that identifies SUMMARY, EXPERIENCE, EDUCATION, etc. This gives the LLM structural hints. You don't have to use it (the LLM will figure out sections on its own), but flagging boundaries explicitly improves extraction reliability and reduces edge cases.

URL extraction is the sneaky-important part. LLMs frequently truncate, paraphrase, or outright drop URLs from their output. By extracting all URLs with regex first, you can backfill them after LLM extraction.

**Key design decisions**

The biggest question is how aggressive to be with normalization. If you strip too much, you lose information (some resumes use bullet characters that signal hierarchy). If you strip too little, you waste LLM tokens on noise.

A related decision: do you preserve formatting hints (bold, italic) from the source document? Bold text in a resume often signals important information (job titles, company names). Stripping all formatting loses this signal. Keeping it means handling format-specific markup in every parser.

**What can go wrong**
- Stripping a page number that happened to also be the person's actual job ID
- Removing "headers" that were actually section dividers
- Section detection over-matching (e.g., a project named "Education Tracker" being detected as the Education section)
- URL extraction missing GitHub references written as "github.com/username" without protocol
- Section boundaries being wrong for resumes that don't use standard headers

**Questions to brainstorm**
- Should section detection be regex-based (fast but brittle) or LLM-based (smart but expensive)?
- How do you handle resumes with non-standard section names ("My Journey" instead of "Experience")?
- Do you preserve original character offsets so you can highlight extracted entities back in the source?
- Should you detect and handle multi-language resumes (some sections in English, some in another language)?

---

### Layer 3 — LLM structured extraction

**What it does**
The most critical layer. Takes the normalized text and asks an LLM to convert it into a strict JSON structure. This is where unstructured prose becomes queryable data.

**Why this is the most important layer**

Every downstream layer depends on this one's output. If the LLM mis-extracts a company name, the company enrichment will fail. If it merges two separate jobs into one entry, the inference engine will compute the wrong tenure. If it hallucinates a skill that wasn't on the resume, you'll match the user to wrong jobs.

The reliability of this layer determines the reliability of the entire system.

**The JSON schema decision**

You need to design a schema that:
1. Captures everything important from a resume
2. Has a consistent structure (so downstream layers can rely on it)
3. Uses null/empty arrays for missing data (never "Not specified" or other LLM creativity)
4. Forces dates into ISO format
5. Distinguishes between explicit skills and technologies mentioned in prose

The schema is essentially your data contract. Changes to it ripple through every downstream layer.

**Key design decisions**

**Single-pass extraction vs multi-pass.** Do you ask the LLM to extract everything in one shot, or split into multiple focused calls (identity in one call, experience in another, skills in a third)? Single-pass is faster and cheaper but more error-prone for long resumes. Multi-pass is more reliable but 3-4x the cost.

**Model selection.** Claude Sonnet for reliability and structured output, GPT-4o for speed, Haiku/mini models for cost. Test all three on your worst-case resumes (the ones with weird layouts) and pick based on extraction accuracy, not benchmark scores.

**Strict validation vs forgiving parsing.** Should the pipeline fail loudly when the LLM produces invalid JSON, or try to repair it? Strict is safer — invalid output usually means something is fundamentally wrong with the resume and you want a human to look at it.

**What can go wrong**

- LLM hallucinations — adding skills the resume doesn't mention, inferring job titles that aren't there
- Date mangling — "Summer 2023" becoming "2023-06-01" when it could be May, June, July, or August
- Bullet point summarization — the LLM compresses 5 detailed bullets into 2 vague ones, losing inference signal
- Section confusion — projects listed under work experience get treated as jobs
- URL truncation — `github.com/user/long-repo-name` becomes `github.com/user/long-repo`
- Splitting one job into multiple entries (or merging two into one) based on formatting cues
- Extracting fictional company names from project descriptions ("Built a tool used by Google" → adds Google as employer)

**Questions to brainstorm**

- How do you measure extraction quality? You need a labeled test set of resumes with known-correct extractions.
- Do you store the LLM's confidence per field? Some structured output APIs return this; others don't.
- When extraction partially fails, do you save the partial result or discard it entirely?
- Do you log every LLM call's input and output? (Yes — for debugging and prompt iteration.)
- Should there be a human review queue for low-confidence extractions?
- How do you handle resumes longer than the model's context window? (Truncate? Chunk?)
- Do you give the LLM a few-shot example or use zero-shot prompting?

---

### Layer 4 — Entity resolution

**What it does**
Takes the raw strings from the LLM extraction and converts them into canonical, deduplicated entities. Without this layer, your graph has "React", "ReactJS", "React.js", and "react" as four separate skill nodes.

**The three things it resolves**

**Skill canonicalization.** Maps every skill string variant to a single canonical name. Uses an alias dictionary as the primary mechanism, with fuzzy matching as a fallback for variants the dictionary doesn't have. This dictionary is a living document — every time you ingest a resume with a new variant, the dictionary grows.

**Company matching.** Maps every company name to a canonical entity, ideally a Crunchbase ID. This lets you enrich the company once and share it across all users who worked there. Without it, "Google" and "Google LLC" and "Google Inc." become three separate company nodes.

**Date normalization.** Converts every date string format the LLM might output ("Jan 2022", "01/2022", "January 2022", "1/22") to ISO 8601. Also handles "Present" / "Current" / "Now" — these all mean "no end date" but need consistent representation.

**Key design decisions**

**Aliasing strategy.** You can hardcode aliases (fast, predictable), use fuzzy matching (handles novel variants but produces false matches), or use an embedding-based approach (semantic similarity, expensive). Best is a hybrid: hardcoded dictionary first, fuzzy fallback for unknown strings, embedding similarity only when both fail.

**Parent-child relationships.** "AWS RDS" implies "AWS". Do you add both as skills? Probably yes — but with different confidence. The user explicitly knows RDS; AWS is implied at high confidence. This means the resolution layer is producing inference data, blurring the line with Layer 7.

**Match thresholds.** Fuzzy matching needs a similarity threshold. Set it too high and you miss real matches ("React JS" doesn't match "React"). Set it too low and you get false matches ("Reacta" matches "React"). The right threshold is found empirically by running through your test resumes.

**Company resolution rate.** Realistic expectation: maybe 50% of company names will match a Crunchbase entry on first try. The rest are tiny startups, regional companies, freelance clients, or companies that have been renamed. You need a graceful "stub node" path for unmatched companies — create the node, mark it as unenriched, queue a website scrape attempt.

**What can go wrong**

- "Apple" matching the fruit company instead of Apple Inc. (you need industry context)
- Skill consolidation that loses information — "React Native" should NOT collapse to "React"
- "Python" matching "Python (programming)" with low fuzzy score, creating both nodes
- Date normalization that picks the wrong interpretation ("3/4/2023" is March 4 in US, April 3 in EU)
- Company matching that maps a person's freelance client to a Fortune 500 with a similar name
- Skills that are actually job titles ("Data Engineer" appearing in the skills section)

**Questions to brainstorm**

- Do you let users correct entity resolution mistakes? (e.g., "this isn't the Apple I worked at")
- How do you handle company name evolution? (Facebook → Meta, Square → Block)
- Should canonicalization be cached? (It's stateless and slow if done per-call.)
- Do you maintain a "user-corrected aliases" table that overrides the global one?
- How do you handle internationalization? ("Tencent" in English vs. "腾讯" in Chinese)
- Do you separately track skills the LLM extracted vs skills you canonicalized? (For auditing.)

---

### Layer 5 — PostgreSQL persistence (source of truth)

**What it does**
Writes the cleaned, structured extraction to PostgreSQL as the system's source of truth. This happens before any enrichment or graph writing. Everything downstream can be rebuilt from this data.

**Why this layer exists at all**

The graph database is in-memory. It's fast but it's not where you bet your business data. PostgreSQL is the durable, reliable, well-understood store. If Memgraph dies catastrophically, the pipeline reads from PostgreSQL and rebuilds the graph. This separation is what lets you use an in-memory graph database in production without panic.

There's a second reason: PostgreSQL is queryable in ways the graph isn't. "How many resumes did we ingest yesterday?" is a 5-second query in Postgres. The same query in Memgraph requires traversing the entire person subgraph. Use each database for what it's good at.

**What gets stored**

The raw resume text (so you can re-extract with a better LLM later), the extracted JSON (the canonical structured representation), the enrichment results (so you don't re-call external APIs on graph rebuild), and metadata about the ingestion process (status, timestamps, error messages).

**Key design decisions**

**Schema rigidity vs JSONB flexibility.** You can either model every field of the extraction as a separate column (rigid, validated by Postgres, hard to evolve) or store the entire extraction as a JSONB blob (flexible, easy to evolve, weaker validation). JSONB is the right answer for this layer — the extraction schema will evolve as you add new fields, and Postgres JSONB indexing handles queries well enough.

**Multi-resume per user.** Should a user have one resume that gets updated, or a history of resumes? History is better — you can show "your resume from 6 months ago vs now", you can A/B test which version performs better in job matching. But it complicates queries: "the user's current skills" becomes "the skills from the user's most recent resume".

**Soft delete vs hard delete.** When a user deletes their account, do you actually delete the data or mark it deleted? GDPR requires actual deletion within 30 days. Other regulations have similar requirements. Build the deletion path from day one.

**Status field as a state machine.** Each resume moves through states: ingested → extracted → enriched → inferred → embedded → graphed. Encode this explicitly so you can find stuck resumes ("show me resumes in 'extracting' state for more than 5 minutes") and reason about partial failures.

**What can go wrong**

- The extraction succeeds but the Postgres write fails (and you've returned success to the user)
- Two simultaneous uploads of the same resume creating two entries (need idempotency keys)
- The status field getting out of sync with reality (Memgraph has the data but Postgres says "extracting")
- Disk filling up with raw text from large PDFs (need text size limits)
- Old enrichment data going stale (companies change, GitHub stats grow — when do you re-enrich?)

**Questions to brainstorm**

- How long do you keep raw resume text? (Storage cost vs ability to re-extract.)
- Do you encrypt the JSONB blob? (PII concerns — resumes contain emails, phones, addresses.)
- Do you store a hash of the raw resume to detect duplicate uploads?
- Should there be a "draft" resume state where the user previews extraction before committing?
- How do you handle the case where the same person uploads from two different emails?
- Do you keep an audit log of every modification to extracted data?

---

### Layer 6 — Asynchronous enrichment

**What it does**
After ingestion returns to the user, a fleet of background workers fetches external data about every entity in the resume — GitHub stats for the person, company data for every employer, README content for every project, ranking data for every school.

**Why it's asynchronous**

External APIs are slow and unreliable. The GitHub API rate limits at 5000 requests/hour. Crunchbase has its own limits. Web scraping can take 5-30 seconds per page. If any of this were synchronous, ingestion would take minutes instead of seconds.

The async model means the user sees their basic resume in the graph immediately, and the graph gets richer over the next minute as enrichment workers complete.

**The enrichment fan-out pattern**

When a resume is ingested, the orchestrator looks at the extracted JSON and spawns one enrichment task per entity. One for GitHub, one per company, one per project, one per school. These run in parallel. When they all complete, a single downstream task runs the inference engine and writes to the graph.

This is a classic fan-out/fan-in pattern. Celery + Redis handles it well. The key thing is that each individual enrichment task is independent — if GitHub is down, only the GitHub enrichment fails; everything else completes.

**Key design decisions**

**Sequential vs parallel within a worker.** When enriching one company, do you call Crunchbase and the website scraper sequentially or in parallel? Parallel is faster but harder to debug.

**Cache strategy.** Companies don't change daily. Once you've enriched Google, you don't need to re-enrich it next week. Cache enrichment results with a TTL — 30 days for companies, 7 days for GitHub stats, 1 day for live demo URL checks.

**Failure handling.** Some enrichments are mandatory (a person without a GitHub enrichment is fine; a resume without any company enrichment is broken). Define what's mandatory and what's best-effort. Failing best-effort enrichments shouldn't block downstream stages.

**Retry strategy.** Network failures should retry with exponential backoff. Rate limit failures should retry after the rate limit window. Permanent failures (404 on a GitHub user) shouldn't retry at all. The retry logic needs to distinguish these cases.

**Cost ceiling.** Crunchbase and Proxycurl cost real money per call. Set a per-user cost limit. If a user's resume has 50 work experiences (academic CVs do), don't enrich all 50.

**What can go wrong**

- A scraping target updates their HTML, breaking your scraper
- An external API changes their response format
- Rate limits being hit during peak ingestion times
- A slow enrichment task blocking the chord (fan-in) for minutes
- Enrichment results being too large to pass via Celery (need to pass via DB reference)
- Cached enrichment going stale and missing recent company changes (acquisition, pivot, rename)
- A GitHub user who has 10,000 repos (need pagination and limits)
- Personally-identifying information being scraped that shouldn't be in the graph (e.g., company founder's personal email)

**Questions to brainstorm**

- Do you let users manually trigger re-enrichment? (For when they notice stale data.)
- Should enrichment data be visible to users or hidden? (Transparency vs information overload.)
- How do you handle the case where a company appears on 10,000 resumes? (You're hitting Crunchbase a lot for the same company.)
- Do you enrich incrementally as new data is needed, or eagerly at ingestion time?
- What happens when an external API permanently goes away? (LinkedIn could shut down Proxycurl tomorrow.)
- Do you offer a "lite" mode that skips paid enrichment for cost-sensitive deployments?
- How do you debug an enrichment that produces wrong data? (Need observability into every external call.)

---

### Layer 7 — Implicit inference engine

**What it does**
The reason FirstKnock exists. Takes the extracted + enriched data and derives skills, domains, and seniority that weren't explicitly stated. A backend dev at a cloud infrastructure company has cloud exposure. A person who built a voice agent knows about audio pipelines. The inference engine codifies these implications.

**Why this is the differentiator**

Every other resume parser extracts what's written. FirstKnock extracts what's implied. This is the entire value proposition. A junior developer who built a sophisticated RAG system implicitly knows about hybrid search, reranking, and chunking strategies — even though they wrote none of those on their resume. Without inference, FirstKnock misses these signals and can't match this person to the right jobs.

**The architecture of the inference engine**

The engine is a rule-based system. Each rule has a condition (when does it apply?), an inference (what does it imply?), a confidence (how sure are we?), and a reason (how do we explain this to the user?). Rules run over the extracted + enriched data and produce a list of inferred skills, each with confidence and reason.

The "reason" is critical. When FirstKnock tells the user "we matched you to a Voice AI role", it has to explain why. The reason string from the inference rule becomes that explanation. "You worked at TechKareer (an AI tooling company) — implies exposure to AI ops" is what makes the matching trustworthy.

**Categories of inference rules**

**Domain exposure rules.** Based on company industry. Cloud infra company → cloud skills. Fintech → compliance knowledge. AI startup → MLOps. These have moderate confidence (0.5-0.7) because just working somewhere doesn't guarantee deep skill, but it's a real signal.

**Skill adjacency rules.** Based on explicit skills. FastAPI → asyncio. LangGraph → agent state machines. Kubernetes → container orchestration. Higher confidence (0.7-0.85) because if you use these technologies in production, you've encountered the adjacent concepts.

**Project implication rules.** Based on project descriptions and tech stacks. Voice agent → WebRTC, VAD. RAG platform → hybrid search, reranking. These can be very high confidence (0.8-0.9) because shipping a project demonstrates the skill.

**Seniority inference.** Based on titles, tenure, and project complexity. Combines explicit data (title, dates) with derived data (years of experience, did they ship solo, do they have leadership signals).

**Cross-rule patterns.** Some inferences require multiple signals. "Worked at a small AI startup AND has cloud skills" implies "comfortable deploying to production cloud environments" with higher confidence than either signal alone.

**Key design decisions**

**Rules vs models.** Hand-coded rules are explainable, testable, and editable. ML models can find patterns you didn't think of but lose explainability. Start with rules. Add ML when you have enough labeled data and rules are getting unwieldy.

**Confidence calibration.** Your confidence scores need to mean something. A 0.7 should be roughly twice as confident as a 0.35. This is hard to calibrate without ground truth. Build a test set of "we infer X with confidence Y" and validate against expert review.

**Conflict resolution.** Two rules might infer the same skill with different confidences. Take the higher? Average them? Treat them as independent evidence and combine probabilistically? The simplest answer (take the higher) is usually fine.

**Rule maintenance.** Rules will accumulate. You'll have hundreds within a year. Need a system for organizing them, testing them, and detecting when rules conflict or become outdated.

**Inference depth.** Should A → B → C inference be allowed? (Person knows X, X implies Y, Y implies Z, so person implicitly knows Z.) Tempting but dangerous — confidence compounds (decays) and you can infer absurd things.

**What can go wrong**

- Overfit rules — "anyone who lists React knows Redux" is too aggressive
- Outdated rules — "uses Python implies uses Django" was true in 2015, less so now
- Cultural assumptions — "worked at a US tech company implies English fluency" is mostly true but offensive when wrong
- Inferring skills from project descriptions that were aspirational (the person built a tiny prototype, the inference engine assumes deep expertise)
- Compounding errors — if extraction misidentified a company, every domain inference from that company is wrong
- User pushback — "I don't actually know what Voice Activity Detection is" — how do you let users correct inferences?

**Questions to brainstorm**

- Do you show users their inferred skills and let them confirm/deny?
- How do you A/B test new inference rules? You need a metric to optimize for.
- Should inference rules be community-contributed? (Risk: bad contributions degrade quality.)
- Do you weight inference rules by company prestige? (Senior engineer at FAANG implies more than at unknown startup.)
- How do you handle the cold-start problem when you have no data to validate confidence scores?
- Should rules be time-aware? (A skill listed 5 years ago might be stale.)
- Can inferences depreciate over time? (Skills you haven't touched in years.)
- How do you let domain experts add rules without engineering involvement?

---

### Layer 8 — Embedding generation

**What it does**
Generates vector embeddings for each significant piece of the resume — the full summary, each work experience, each project, each skill cluster. These embeddings power semantic search: finding jobs whose description is similar to your background even when there's no exact skill overlap.

**Why this layer is necessary alongside the graph**

The graph handles structural matching: "find jobs where this person has at least 5 required skills". Vector embeddings handle semantic matching: "find jobs that feel similar to what this person has done, even with different vocabulary".

These two approaches catch different matches. A graph match might miss a job that uses different terminology for the same concept. A vector match might miss a job that requires a specific certification or skill the user lacks. The combination — graph for precision, vectors for recall — produces better matches than either alone.

**What to embed**

Not the entire resume as one blob — that loses granularity. Better is to embed each meaningful chunk separately: the full summary (for overall fit), each work experience (for role-specific matching), each project (for technical depth matching), and skill clusters (the AI skills together, the backend skills together).

This gives you multiple ways to match. A job posting can be matched against the user's overall summary, their most recent role, their most relevant project, or their skill cluster — whichever has the highest similarity.

**Key design decisions**

**Embedding model selection.** Smaller models are cheaper and faster. Larger models capture more nuance. For resume matching, you don't need state-of-the-art models — text-embedding-3-small (1536 dimensions) is enough. Higher dimensions don't help much beyond a point and they cost more storage.

**Embedding granularity.** More chunks = more matching opportunities but more storage and slower queries. Fewer chunks = faster but coarser matching. The right balance depends on your job posting database — if jobs are 50-200 word descriptions, match against project-level embeddings. If they're 500+ words, match against full resume.

**Storage location.** Embeddings stored on the graph node (Memgraph vector index) means one query for graph + vector. Embeddings in a separate vector database means two queries but more specialized retrieval. For your scale (thousands of users), graph-native is fine.

**Regeneration triggers.** Embeddings should regenerate when source text changes. If a user re-uploads their resume, every embedding gets regenerated. If a project's enriched description gets updated, that project's embedding regenerates. This is straightforward but easy to forget — embeddings will silently go stale otherwise.

**What can go wrong**

- Embedding model deprecation (OpenAI deprecates models periodically — you need a re-embedding strategy)
- Drift between embedding models (text-embedding-3-small embeddings aren't comparable to text-embedding-ada-002 embeddings)
- Embeddings going stale after enrichment updates
- Storage bloat (10,000 users × 5 embeddings × 1536 floats × 4 bytes = 300MB; manageable but not free)
- Cost ballooning if you regenerate embeddings on every minor change
- Embeddings that don't actually capture what you want (semantic similarity in embedding space ≠ relevant for hiring)

**Questions to brainstorm**

- Do you embed the original LLM output or the canonicalized version?
- How do you handle multilingual embeddings? (Embedding a Mandarin resume with an English model gives bad results.)
- Should you fine-tune an embedding model on resume↔job pairs?
- Do you store embeddings only for current data or keep historical embeddings for comparison?
- How do you measure embedding quality? (Hard problem — need labeled relevance judgments.)
- Should you mix multiple embedding models for different use cases?

---

### Layer 9 — Memgraph graph write

**What it does**
The final stage. Takes everything — extracted data, enrichment results, inferred skills, embeddings — and writes it into Memgraph as a graph of interconnected nodes and relationships.

**The shared-node insight**

The most important architectural decision in this layer: skills, companies, and jobs are global nodes, shared across all users. Persons, projects, and education entries are per-user nodes. This means when 1000 users all know Python, there is ONE Python skill node with 1000 incoming relationships, not 1000 copies of the Python node.

This isn't just a storage optimization — it's what makes graph queries fast. "Find me other users who know Python" is one traversal from one node. "Find me jobs that require Python" is one traversal from the same node. The shared nodes are the connective tissue that lets the graph reason across users.

**Why MERGE, not CREATE**

Every write uses MERGE (Cypher's idempotent upsert). This handles every case: first-time user, re-upload of an updated resume, retry after partial failure, rebuild from PostgreSQL. The graph state is deterministic regardless of how many times the writes execute.

The price of MERGE is that you have to define what makes each node unique. Person is unique by email. Skill is unique by canonical name. Company is unique by name. Project is unique by (user_id, name) since two different users might both have a project called "Portfolio Site". Getting these unique keys wrong creates duplicate nodes.

**Indexes are mandatory**

Without indexes, every query scans the full graph. With 10,000 users this is fine. With 100,000 users it's catastrophic. Create indexes on every property you query by — Person.user_id, Person.email, Skill.name, Company.name, Project.user_id. Do this on day one, not when performance becomes a problem.

**Persistence configuration**

Memgraph is in-memory, but it has two persistence mechanisms: snapshots (full graph dump every N seconds) and WAL (write-ahead log of every change). Use both. Snapshots give you fast recovery; WAL gives you point-in-time recovery between snapshots.

The configuration tradeoff: more frequent snapshots = more disk I/O but less data lost on crash. WAL flushing more aggressively = more disk I/O but less data lost on crash. For a resume app, losing the last 5 minutes of writes on a crash is acceptable. For a payment system it wouldn't be.

**Key design decisions**

**Vector index inside or outside the graph.** Memgraph supports vector indexes natively. Pinecone supports them as a dedicated service. Native is simpler (one database, one connection) but limited to Memgraph's vector capabilities. Pinecone is more sophisticated but is another moving part.

**Relationship direction.** Person —HAS_SKILL→ Skill, or Skill —KNOWN_BY→ Person? Both work for queries. Convention is to write the relationship in the direction of the action ("Person has skill"). Stick to one convention or your queries become confusing.

**Edge property normalization.** The HAS_SKILL edge has properties: confidence, source, reason. These are the inference metadata. The temptation is to put them on the Skill node instead. Resist it — the skill itself isn't inferred (Python is Python), but the person's knowledge of it might be.

**What can go wrong**

- Memgraph runs out of memory and crashes (RAM is a hard constraint)
- WAL files growing unbounded if snapshots aren't running (disk fills up)
- Index creation failing silently and queries getting slow over weeks
- A poorly-written query locking the database for everyone
- The recovery process from PostgreSQL being slower than expected (1M resumes takes hours to rebuild)
- Schema evolution breaking existing data (you renamed a property but old data has the old name)
- Two users with the same email creating conflicts at the Person node MERGE

**Questions to brainstorm**

- Do you support multiple graph environments (production, staging, dev) or one with namespacing?
- How do you migrate graph schema changes? (Cypher doesn't have built-in migrations like SQL.)
- Should the graph be read-replicated for query scaling?
- Do you back up the WAL files separately for point-in-time recovery?
- How do you monitor graph health? (Number of nodes, average query time, index hit rate.)
- What's your strategy when Memgraph itself gets deprecated or you need to migrate to a different graph DB?

---

## Part 3 — Cross-cutting concerns

These are decisions that don't belong to any single layer but affect every layer.

### Persistence and recovery strategy

The pipeline has two distinct persistence layers with different purposes. PostgreSQL is the durable source of truth — everything we write here we keep. Memgraph is the queryable projection — anything we put here we can rebuild from Postgres.

This separation gives you operational flexibility. You can upgrade Memgraph versions, change your graph schema, run experimental queries against a copy of the graph — all without risk of data loss.

The recovery flow is: PostgreSQL holds raw_text + extracted_json + enriched_json for every user. On Memgraph cold start, a script reads all "graphed" resumes from Postgres and replays them through the graph writer. The MERGE-based writes ensure no duplicates regardless of how many times rebuild runs.

**Open question to brainstorm:** How long does recovery take at scale? If rebuilding 1M resumes takes 8 hours, is that acceptable? If not, you need to either keep an off-graph backup of Memgraph snapshots (faster recovery but more storage), or shard the graph for parallel rebuild.

### Async vs sync boundaries

The most architecturally important line in the system is "what runs synchronously in the API request vs asynchronously in the background".

**Sync stages: 1-5** (parsing through Postgres write). These need to complete before returning to the user because they produce the user-facing artifact (extracted JSON visible in the UI immediately).

**Async stages: 6-9** (enrichment through graph write). These can take 30-60 seconds and the user can wait while seeing a "processing" status.

The sync stages are bounded by LLM latency (extraction is the slow step, ~2 seconds). The async stages are bounded by external API latency (enrichment can take 30+ seconds with parallel workers).

**Open question to brainstorm:** Is there a hybrid mode where the user gets a partial result faster? E.g., return basic extraction in 1 second, push richer data via websocket as it completes. This is better UX but more complex.

### Multi-tenancy and isolation

A single Memgraph instance holds all users' data. Multi-tenancy is enforced by user_id properties on Person nodes and all queries filtering by user_id. Shared nodes (Skill, Company, Job) are global by design — that's the whole benefit of the graph approach.

There's no instance-level isolation. If you needed strict tenant isolation (enterprise customers with strict data residency requirements), you'd need separate Memgraph instances per tenant. For consumer/B2C use cases, shared instance is fine.

**Open question to brainstorm:** When does shared-graph become a liability rather than an asset? If FirstKnock goes B2B and a recruiter wants to upload 10,000 candidate resumes that should be private from other recruiters, the shared-graph model breaks. Plan for this case before it arrives.

### Failure modes

Every layer can fail. The pipeline needs explicit handling for each failure mode:

**Layer 1-3 failures** (parsing, normalization, extraction): Mark resume as "failed" with error message, return error to user, no async stages fire.

**Layer 4-5 failures** (resolution, Postgres): Same as above. These shouldn't fail except for infrastructure issues.

**Layer 6 failures** (enrichment): Individual enrichments can fail independently. Partial enrichment is fine — downstream stages get whatever completed. A resume can have "graph_built=true" with partial enrichment data.

**Layer 7-8 failures** (inference, embedding): Should not fail except for infrastructure issues. If they do, the graph still gets explicit data; inferred data is added later when retried.

**Layer 9 failures** (graph write): If Memgraph is down, retry queue holds the writes. When Memgraph comes back, queued writes execute.

The key principle: failures should be visible (logged, monitored) but should not block the entire pipeline. A user uploading a resume during a 2-minute Memgraph outage should still get their PostgreSQL write and have the graph backfilled when Memgraph recovers.

### Observability

You need to be able to answer questions like:
- How many resumes are stuck in "extracting" state for more than 5 minutes?
- What's the average time from ingestion to graphed?
- Which inference rules fire most often?
- Which enrichment APIs are failing most?
- What's the graph node count over time?

These require structured logging at every stage, metrics for every external call, and dashboards for the key counts. Build this from day one — debugging a pipeline without observability is impossible at any scale.

---

## Part 4 — Critical design decisions explained

The big "why" questions that drove the architecture.

### Why graph database (vs SQL or vector-only)

The implicit inference makes natural graph data. "Person has skill (explicitly) that is implied by other skill (which the person has explicitly)" is a multi-hop traversal. In SQL this is a recursive CTE that's painful to write and slow to execute. In Cypher it's three lines.

The "why matched" explanation paths are graph traversals. Finding "the shortest chain of evidence connecting this person to this job" is the textbook example of what graphs are good at.

The shared-node memory optimization (one Skill node, many edges) doesn't have a direct equivalent in SQL or vector databases. SQL with foreign keys is the closest, but the queries become joins of joins of joins for any non-trivial traversal.

Vector databases alone can't capture explicit-vs-inferred distinction with reasoning. They give you "similar to" but not "implied by".

### Why Memgraph (vs Neo4j)

Cost: Memgraph's MAGE library has all the graph algorithms in the open source edition. Neo4j requires enterprise license ($$$$) for the same.

Speed: Memgraph is in-memory, so query latency is consistently low. Neo4j has memory + disk and performance varies.

Vector index: Memgraph has native vector indexes since 2.15, removing the need for Pinecone in the basic case.

Cypher compatibility: 95% of Cypher works identically. The 5% that doesn't is minor procedure name differences.

Tradeoff: Memgraph is in-memory, so total graph size is capped by your server RAM. Neo4j can hold larger graphs on disk. For FirstKnock's scale (hundreds of MB of graph data even at 100k users), this isn't a constraint.

### Why PostgreSQL as source of truth (not the graph)

Memgraph being in-memory means a server crash could lose data. PostgreSQL is durable by design. You don't want raw user-submitted data living only in a database that loses state on restart.

PostgreSQL is also the right tool for the queries you'll inevitably want: counts, aggregations, time-series of ingestion volume, audit logs. The graph isn't optimized for these.

PostgreSQL is universally understood. Every backend engineer knows how to debug it, back it up, scale it. The same isn't true of graph databases. By keeping the source of truth in Postgres, you make the operational burden manageable for any team.

### Why store inference confidence on the edge

The shared-node model is the answer. The Skill "Python" is the same Python whether you explicitly listed it or we inferred it from your job at a Python shop. What differs is the *relationship* between you and Python — the confidence, the source, the reason.

If you put confidence on the Skill node, you can't represent that one user knows Python at confidence 1.0 (explicit) and another user knows it at confidence 0.7 (inferred). You'd need separate "Python_Explicit" and "Python_Inferred" nodes, which defeats the shared-node model.

The edge-property approach is also what makes the explanation paths work. The "reason" property on the HAS_SKILL edge is the building block of "why we matched you to this job".

### Why async enrichment

Synchronous enrichment would mean the user waits 30-60 seconds for an upload. That's terrible UX. The alternative — return immediately with a "processing" status and update via polling or websocket — is the standard pattern for any operation that involves external API calls.

The cost is complexity: you need a task queue (Celery + Redis), worker processes, and a way for the frontend to know when enrichment is complete. But this complexity is the price of acceptable latency.

The other benefit of async: failures are isolated. If GitHub's API is down, only GitHub enrichment fails. The user still has their basic graph. They get richer data later when GitHub recovers.

---

## Part 5 — What we're explicitly NOT building

Architectural decisions are as much about what you don't build as what you do.

**Not building: real-time graph updates.** The graph is updated when a resume is ingested or re-ingested. We're not building a live update system where the graph reflects every external change in real-time. If Aswinthraj's GitHub star count goes from 14 to 15, the graph doesn't know until the next re-enrichment. This is fine for the use case — job matching doesn't need second-precision freshness.

**Not building: full historical versioning.** PostgreSQL keeps the latest extracted JSON. We're not building a system where you can query "what did Aswinthraj's resume look like 6 months ago". If users want versioning, they upload multiple resumes (which we'd treat as separate resume records).

**Not building: graph federation.** Each FirstKnock instance has its own graph. We're not federating across instances or syncing graphs between deployments. If you need a single global graph, you run a single global instance.

**Not building: ML-based extraction.** All extraction goes through the LLM. We're not training custom models. The LLM is "good enough" and the engineering cost of custom models isn't worth it until we have millions of resumes for training data.

**Not building: automatic skill discovery from job postings.** The skill ontology grows manually (via the SKILL_ALIASES dictionary). We're not running NER on job postings to discover new skills automatically. This is a future enhancement when manual maintenance becomes painful.

**Not building: a recommendation explanation that's better than a graph path.** When we say "you were matched because X → Y → Z", that's the explanation. We're not generating natural-language explanations with another LLM call on top. The path is the explanation. Simpler is better.

---

## Part 6 — Open questions for future brainstorming

These are questions that don't have right answers yet. They'll need to be resolved at some point, but they're not blocking initial development.

**On extraction quality:**
- How do we evaluate extraction quality at scale? We need a labeled test set, but who labels it?
- Do we expose extraction confidence to users? If so, how?
- What's our policy when extraction is clearly wrong? Auto-retry with different model? Human review queue?

**On inference rules:**
- Do we let users add their own inference rules? Powerful but dangerous.
- How do we deprecate inference rules that become outdated? (Things change — "Twitter" is now "X", "Facebook" is "Meta".)
- Should rules have effective date ranges? "From 2010-2020, knowing Hadoop implied big data skills. After 2020, less so."

**On the graph:**
- When does the shared-graph model break down? At what user scale or with what use case?
- Do we need a separate "private" graph for sensitive employer data (job postings under NDA)?
- How do we handle the case where the graph schema needs to evolve? Migration story.

**On enrichment:**
- What's the cost ceiling per user? At what point does an extremely well-traveled person become economically infeasible to enrich?
- Should users be able to manually trigger re-enrichment? (When they notice stale data.)
- Do we offer different enrichment tiers? (Basic free, premium with deeper enrichment.)

**On privacy:**
- Where do we draw the line on inferring personal information? (Inferring that someone has a family from career gaps might cross a line.)
- Do we let users see and edit their inferred data?
- How do we comply with right-to-explanation regulations? (Aspects of GDPR.)
- What's our data retention policy after account deletion?

**On the pipeline itself:**
- Do we need real-time observability into pipeline performance, or is daily aggregation enough?
- Should the pipeline be event-driven (Kafka) or task-queue driven (Celery)? Tradeoffs at scale differ.
- How do we test the pipeline end-to-end without burning LLM/enrichment costs in tests?

---

## Part 7 — Evolution path

The current architecture is sized for FirstKnock at launch through about 10,000 users. The system will naturally evolve as scale increases.

**Phase 1 — Launch (0 to 10K users)**
Everything as described. Single Memgraph instance, single Postgres, single Celery worker pool. All running on a modest VPS. Operational complexity is low because there's one of everything.

**Phase 2 — Growth (10K to 100K users)**
Memgraph gets more RAM (16-32GB). Postgres might need a read replica for analytics queries that shouldn't compete with operational reads. Celery worker pool scales horizontally. Add CDN for static frontend assets. Still one logical instance of everything.

**Phase 3 — Scale (100K to 1M users)**
Memgraph might need to shard by user cohort. Postgres definitely needs read replicas and possibly partitioning by date. Enrichment workers fan out across multiple regions. Consider hot/cold storage for old enrichment data. Move to dedicated infrastructure rather than shared cloud.

**Phase 4 — Hyper-scale (1M+ users)**
Architecture changes meaningfully. Graph might need to move to a distributed graph database. Multi-region deployment for latency. Custom-trained models for extraction and inference. At this scale, you're rewriting parts of the system anyway.

Most likely you'll never reach Phase 4. Building for it now is wasted effort. Build for Phase 1, and trust that Phase 2 transitions are linear scale-ups of the same architecture.

---

## End of document

This document covers the architecture, the design decisions, and the open questions. It's a starting point for brainstorming, not a final answer. As you think through the system and start building, you'll discover problems and tradeoffs this document didn't anticipate — that's the point. Use this as the framework for thinking, and update it as you learn.

The most important things to remember:

1. **PostgreSQL is the source of truth.** Everything else is a projection.
2. **Sync vs async is the most important architectural boundary.** Get the user a response fast; do expensive work in the background.
3. **The graph's value is the shared-node model.** One Python node, thousands of edges.
4. **Inference confidence lives on the edge.** Skills are skills; what differs is how strongly each person knows each skill.
5. **The pipeline must be idempotent.** Users re-upload; tasks retry; everything must produce the same result.

Everything else is implementation detail.
