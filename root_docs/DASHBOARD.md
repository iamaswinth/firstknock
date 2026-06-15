# FIRSTKNOCK — Dashboard Build Plan

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Framework | Next.js 16 (App Router) | already scaffolded in `firstknock/` |
| Styling | Tailwind CSS v4 + CSS vars | design tokens live in `globals.css` |
| Components | shadcn/ui | install via CLI, drop into `components/ui/` |
| Graph | `@memgraph/orb` | canvas-based, replaces the prototype's inline SVG |
| Data fetching | `@tanstack/react-query` | caching, polling, parallel loads |
| Animations | `framer-motion` | drawer entrance, hover transitions |
| Types | TypeScript | all API shapes in `lib/api/types.ts` |

### Install commands (run from `firstknock/`)
```bash
npx shadcn@latest init
npx shadcn@latest add card badge button progress separator sheet

npm install @memgraph/orb @tanstack/react-query framer-motion
```

---

## Routes

```
/                           Upload page — drag & drop PDF + email field
/processing/[resume_id]     Polling page — stage-by-stage progress until status=enriched
/profile/[user_id]          Main dashboard
```

---

## Folder Structure

```
firstknock/
├── app/
│   ├── globals.css                   # ← ALL design tokens as CSS vars (see tokens section)
│   ├── layout.tsx                    # root layout: fonts + QueryProvider
│   ├── page.tsx                      # Upload page
│   ├── processing/
│   │   └── [resume_id]/page.tsx      # Polling / processing screen
│   └── profile/
│       └── [user_id]/page.tsx        # Dashboard page — fetches all data, renders grid
│
├── components/
│   ├── ui/                           # shadcn output — do not hand-edit
│   │
│   ├── layout/
│   │   ├── nav.tsx                   # top nav bar (56px): logo, links, search/bell/avatar
│   │   ├── title-bar.tsx             # "Overview" heading + sync pill + export buttons
│   │   └── footer.tsx                # mono micro-text: product line + user_id · N skills · N edges
│   │
│   ├── graph/
│   │   ├── skill-graph.tsx           # orb canvas: physics, node styling, filter wiring
│   │   ├── node-drawer.tsx           # slide-in panel (320px) — content varies by node type
│   │   └── graph-filters.tsx         # pill chips: type / source / community toggles
│   │
│   ├── cards/
│   │   ├── card-shell.tsx            # base: bg --card, border, radius-lg, shadow, card-head + ⋯ menu
│   │   ├── skill-composition.tsx     # big count + striped bars (Frameworks / Languages / Tools)
│   │   ├── insight.tsx               # full-bleed gradient, white text, "✦ Insight" pill, big %
│   │   ├── bridge-skills.tsx         # ranked rows: badge + name + centrality + blue progress bar
│   │   ├── inferred-skills.tsx       # confidence rows: check circle + % pill + reasoning chain chips
│   │   ├── role-fit.tsx              # 3 role recommendation rows with LLM reason text
│   │   ├── pinned-repos.tsx          # repo rows: icon + name + language + stars + stack chips
│   │   ├── career-timeline.tsx       # entries with coloured left bar + stage/industry chips
│   │   ├── profile-completeness.tsx  # big % score + 6 section bars + enrichment status dots
│   │   └── metric-card.tsx           # reusable: big number + dot-matrix column chart + delta
│   │
│   ├── upload/
│   │   ├── dropzone.tsx              # drag-and-drop zone + email input → POST /ingest
│   │   └── processing-status.tsx     # stage progress list (parse → enrich → embed)
│   │
│   └── shared/
│       ├── striped-bar.tsx           # reused in Composition + Bridge Skills
│       └── dot-matrix.tsx            # reused in Skills Mapped + GitHub Reach metric cards
│
├── lib/
│   ├── api/
│   │   ├── client.ts                 # base fetch: BASE_URL, error handling, JSON parse
│   │   ├── types.ts                  # all TypeScript interfaces (see API types section)
│   │   └── hooks/
│   │       ├── use-resume-poll.ts    # polls GET /resume/{id} every 3s until status=enriched
│   │       ├── use-profile.ts        # GET /profile/{user_id}
│   │       ├── use-skills.ts         # GET /skills/{user_id}
│   │       ├── use-graph.ts          # GET /graph/{user_id}
│   │       ├── use-analytics.ts      # GET /analytics/{user_id}
│   │       ├── use-roles.ts          # GET /profile/{user_id}/roles
│   │       └── use-completeness.ts   # GET /profile/{user_id}/completeness
│   │
│   └── utils.ts                      # cn() (clsx + twMerge), formatMonths(), initials()
│
└── providers/
    └── query-provider.tsx            # <QueryClientProvider> wrapper for layout.tsx
```

---

## Dashboard Grid

12-column bento grid. Gap 16px. Max-width 1500px centered.

```
Row 1:  [ Skill Graph ×8        ] [ Skill Composition ×4 ]
                                   [ Insight            ×4 ]

Row 2:  [ Bridge Skills ×4 ] [ Inferred Skills ×4 ] [ Role Fit ×4 ]

Row 3:  [ Pinned Repositories ×7 ] [ Career Timeline ×5 ]

Row 4:  [ Profile Completeness ×6 ] [ Skills Mapped ×3 ] [ GitHub Reach ×3 ]
```

Responsive (≤ 820px): every card spans all 12 columns, nav links hidden.

---

## Cards — Data Sources & Key Content

### Skill Graph (hero · row 1 · ×8)
- **Data:** `GET /graph/{user_id}` → nodes, links, communities
- **Library:** `@memgraph/orb` (canvas)
- **Node types / colours:**
  - Person `#14161b` filled
  - Explicit Skill `#fff` + 1.3px `#14161b` stroke
  - Inferred Skill `#fff` + dashed stroke
  - Company `#14161b` filled
  - Project `#eef1f6` filled
  - Institution `#e3e1dc` filled
  - Edges `#e3e1dc`; focused edges `#14161b`; IMPLIES edges dashed
  - Skill nodes in a community use that community's `color` from the response
- **Interactions:**
  - Hover node → neighbours stay full opacity, rest dims to 0.18, connected edges thicken
  - Click node → opens `NodeDrawer` (slide-in, 320px right)
  - Filter chips toggle node visibility by type / source / community
  - Counts strip updates live
  - AI prompt bar (visual placeholder for now)
- **NodeDrawer content by type:**
  - `Skill` → category · community · confidence; if inferred: "Why we infer this" + `via` chain + `inferred_by` method tag
  - `Company` → title, date range, stage/industry chips, stack chips, funding if available
  - `Project` → ★ stars · language, summary, stack + topic chips
  - `Person` → explainer text

### Skill Composition (row 1 · ×4)
- **Data:** `GET /skills/{user_id}` + `GET /analytics/{user_id}`
- **Content:** big total count + "↑ N inferred" delta pill; "N explicit · N inferred across N communities" subtitle; 3 striped horizontal bars — Frameworks / Languages / Tools & Infra

### Insight (row 1 · ×4)
- **Data:** `GET /analytics/{user_id}` → bridge_skills[0]
- **Content:** full-bleed gradient card, white text; "✦ Insight" pill; giant `87%`; headline "FastAPI is your strongest bridge skill." + copy
- **Fallback:** if bridge_skills is null, show a generic "Graph analysis pending" state

### Bridge Skills (row 2 · ×4)
- **Data:** `GET /analytics/{user_id}` → bridge_skills
- **Content:** ranked rows — square rank badge, name + category + blue centrality value, striped blue progress bar (width = centrality × 100%), note line
- **Null state:** "MAGE not installed — community analysis unavailable"

### Inferred Skills (row 2 · ×4)
- **Data:** `GET /analytics/{user_id}` → inferred_skills (or `GET /skills/{user_id}` → inferred)
- **Content:** rows with circular check (filled blue if confidence ≥ 0.85, hollow otherwise), name + confidence % pill (green if high), reason sentence, `via [chip] → [chip]` chain + dashed endpoint chip, mono `llm` / `graph_implies` method tag right-aligned

### Role Fit (row 2 · ×4) ← new
- **Data:** `GET /profile/{user_id}/roles`
- **Content:** up to 3 rows — role title (bold) + LLM reason sentence (muted); numbered rank badge left; subtle divider between rows
- **Empty state:** "Role analysis pending — try re-ingesting"

### Pinned Repositories (row 3 · ×7)
- **Data:** `GET /resume/{resume_id}` → enriched.github.pinned_repos
- **Content:** repo rows — repo icon, name + optional "New" green pill, language dot + label, ★ stars, one-line summary, stack chips

### Career Timeline (row 3 · ×5)
- **Data:** `GET /analytics/{user_id}` → career_timeline; company stage/industry from `GET /profile/{user_id}` → experience
- **Content:** entries with coloured left bar (brand colour for current, muted for past, grey for education), company name + "Current" pill, role title, mono date range + months, stage · industry chips, stack chips

### Profile Completeness (row 4 · ×6) ← new
- **Data:** `GET /profile/{user_id}/completeness`
- **Content:**
  - Left: big `overall_score%` (44px/700) + label + `top_suggestion` callout
  - Right: 6 mini progress bars (Identity / Experience / Skills / Projects / Education / Enrichment) each with `pct` fill + missing items on hover/expand
  - Bottom strip: enrichment status dots — GitHub ✓/✗, LinkedIn ✓/✗, Company ✓/✗, Institution ✓/✗

### Skills Mapped (row 4 · ×3)
- **Data:** `GET /skills/{user_id}` → total
- **Content:** big number + dot-matrix column chart + delta vs explicit baseline

### GitHub Reach (row 4 · ×3)
- **Data:** `GET /profile/{user_id}` → github_followers, public_repos
- **Content:** big number (followers) + dot-matrix chart + public_repos as secondary stat

---

## API Hooks Pattern

Each hook follows the same shape:

```typescript
// lib/api/hooks/use-profile.ts
export function useProfile(userId: string) {
  return useQuery({
    queryKey: ['profile', userId],
    queryFn: () => apiClient.get<ProfileResponse>(`/profile/${userId}`),
    staleTime: 5 * 60 * 1000,
  })
}
```

Dashboard page loads all 6 in parallel:
```typescript
const profile      = useProfile(userId)
const skills       = useSkills(userId)
const graph        = useGraph(userId)
const analytics    = useAnalytics(userId)
const roles        = useRoles(userId)
const completeness = useCompleteness(userId)
```

Polling hook for the processing page:
```typescript
export function useResumePoll(resumeId: string) {
  return useQuery({
    queryKey: ['resume', resumeId],
    queryFn: () => apiClient.get<ResumeStatusResponse>(`/resume/${resumeId}`),
    refetchInterval: (query) =>
      query.state.data?.status === 'enriched' ? false : 3000,
  })
}
```

---

## Design Tokens

Port these into `app/globals.css` `:root`. shadcn CSS vars coexist in the same block.

```css
:root {
  /* Surfaces */
  --outer:    #d4d3d1;
  --page:     #ececea;
  --card:     #fcfcfb;
  --card-2:   #f5f5f3;
  --well:     #f0f0ed;

  /* Ink */
  --ink:   #14161b;
  --ink-2: #43464d;
  --ink-3: #777a82;
  --ink-4: #a7aab1;
  --ink-5: #cdcfd4;

  /* Lines */
  --line:   #eceae6;
  --line-2: #e3e1dc;

  /* Brand */
  --brand:    #ef7b2e;
  --primary:  #14161b;

  /* Accent */
  --green:    #14a05a;
  --green-bg: #dcf3e4;
  --blue:     #2f6af0;
  --blue-bg:  #dbe7ff;
  --pink:     #e6457f;
  --pink-bg:  #fcdfeb;

  /* Radius */
  --radius:    14px;
  --radius-lg: 20px;
  --radius-xl: 24px;

  /* Shadow */
  --shadow:    0 1px 2px rgba(20,22,27,.04), 0 8px 24px rgba(20,22,27,.05);
  --shadow-sm: 0 1px 2px rgba(20,22,27,.05);
}
```

**Typography:** Geist + Geist Mono via Google Fonts (swap to `next/font` in production).

```
Title: 38px / 600
Big numbers: 44–64px / 700
Card title: 18px / 600
Body: 13–14px
Subtitle / meta: 12–13px (--ink-3)
Mono micro: 11–12px (.fk-mono = Geist Mono)
```

---

## Orb Integration Notes

`@memgraph/orb` renders to a `<canvas>`. Use the `useOrb` hook or manual instantiation inside a `useEffect`:

```typescript
// components/graph/skill-graph.tsx (skeleton)
useEffect(() => {
  if (!containerRef.current) return
  const orb = new Orb(containerRef.current)
  orb.data.setup({ nodes, edges })
  orb.view.setSettings({ render: { ... } })
  orb.events.on(OrbEventType.NODE_CLICK, (e) => setSelectedNode(e.node))
  orb.events.on(OrbEventType.NODE_HOVER, (e) => setHoverNode(e.node))
  orb.render.rerender()
  return () => orb.destroy()
}, [nodes, edges])
```

Transform the API response before passing to Orb:
- `GraphNode` → Orb node (`id`, `label`, custom `data` for type/community/confidence)
- `GraphLink` → Orb edge (`id`, `start`, `end`, custom `data` for type/co_occurrence)
- Apply node fill/stroke colours based on `type` and `source_type`
- Dashed stroke for inferred skills (Orb supports custom canvas draw functions)

---

## Build Order

1. **Setup** — install deps, init shadcn, port tokens into `globals.css`, scaffold folder structure, `QueryProvider`
2. **Base shell** — `nav.tsx`, `title-bar.tsx`, `footer.tsx`, `card-shell.tsx`
3. **Upload + Processing** — `dropzone.tsx` → POST /ingest, `processing-status.tsx` → poll /resume
4. **Static cards** (mock data first, then wire API):
   - `skill-composition.tsx`
   - `insight.tsx`
   - `bridge-skills.tsx`
   - `inferred-skills.tsx`
   - `role-fit.tsx`
   - `pinned-repos.tsx`
   - `career-timeline.tsx`
   - `profile-completeness.tsx`
   - `metric-card.tsx` (×2: Skills Mapped, GitHub Reach)
5. **Skill Graph** — Orb canvas, hover/click/filter interactions, `node-drawer.tsx`
6. **API wiring** — create all 6 hooks, replace mock data, add loading + error + empty states
7. **Polish** — framer-motion drawer animation, responsive breakpoints, null-state handling (MAGE unavailable)

---

## Future-proofing Notes

- **Phase 9 (LLM Graph Curation):** `GET /graph/{user_id}` will eventually accept display params from Postgres (`confidence_floor`, `max_inferred`, `featured_node_ids`). The Orb filter layer is already in `graph-filters.tsx` — just pass the params through when the backend ships it.
- **Job recommendations** (from `chore.txt` — planned): a new `/jobs/{user_id}` endpoint + a new card in row 4 replacing or extending the metric cards. Reserve the grid space.
- **LinkedIn data** (`SET_PERSON_LINKEDIN_STATS`): linkedin_headline, connections, followers will eventually populate — add to the Profile header in `title-bar.tsx` or the Career Timeline card without layout surgery.
- **Company funding detail** (`SET_COMPANY_ENRICHMENT`): total_funding_usd, last_round_type, key_investors, founders are stored on Company nodes — expose them in the `NodeDrawer` company view as an expandable section.
- **Multi-resume support:** the backend already models one user → many resumes (always queries `ORDER BY ingested_at DESC LIMIT 1`). When multi-resume UI is needed, the `resume_id` selector can slot into the `title-bar.tsx` dropdown (the "resume.pdf ▾" pill) without touching any card.
