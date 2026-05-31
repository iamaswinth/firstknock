# Handoff: FirstKnock — Candidate Dashboard ("Zentra" style)

## Overview
FirstKnock turns a candidate's résumé into a **knowledge graph**: it parses the
résumé, enriches it with public GitHub + company data, infers hidden skills, and
clusters everything into communities. This handoff covers the **candidate
self-view dashboard** — the screen a candidate lands on after their résumé has
been ingested.

The dashboard is laid out as a **bento grid of cards** on a light-grey canvas,
with an interactive skill graph as the hero. Two ingestion screens (Upload,
Processing) are included as **supplementary** references — see the note in
*Screens* about their visual style.

---

## About the Design Files
The files in this bundle are **design references created in HTML/CSS + React
(via in-browser Babel)** — prototypes showing the intended look and behaviour,
**not production code to ship as-is**. The in-browser Babel transform, CDN React,
and `window.DATA` global are prototype scaffolding only.

Your task is to **recreate these designs in the target codebase's environment**,
using its established patterns and libraries (e.g. a real React + bundler setup,
a component library, a data layer that calls the FirstKnock API). If no frontend
environment exists yet, pick an appropriate stack (React + Vite + TypeScript is a
safe default) and implement there. Wire the components to the real API documented
in `API_REFERENCE.md` instead of the bundled sample data.

## Fidelity
**High-fidelity.** Final colours, typography, spacing, and interactions are all
specified here and present in the prototype. Recreate the dashboard
pixel-faithfully using your codebase's libraries. Exact tokens are in *Design
Tokens* below.

---

## Screens / Views

### 1. Dashboard / Overview  ← primary deliverable
**File:** `FirstKnock Dashboard.html` → `overview-app.jsx`, `overview.css`,
`dashboard-graph.jsx`, `dashboard-data.js`

**Purpose:** The candidate reviews their parsed profile — skill graph, skill
composition, bridge skills, inferred skills with reasoning, pinned repos, career
timeline, and headline metrics.

**Layout (top → bottom):**
- **Top nav bar** (`.nav`, 56px tall): orange gradient logo mark + "FirstKnock"
  wordmark (left); centered horizontal links *Overview / Skills / Graph /
  Projects / Timeline / Documents* (active = solid black pill); right cluster of
  circular search button, bell (with orange ping dot), and a conic-gradient-ring
  avatar showing initials "AD".
- **Title bar** (`.titlebar`): big "Overview" heading (38px/600) + circular link
  icon; right-aligned pills — `Synced · May 29`, muted "from", `resume.pdf ▾`,
  `Export JSON`, and a solid-black `+ Add widget`.
- **Bento grid** (`.bento`, `display:grid; grid-template-columns:repeat(12,1fr); gap:16px`):
  | Row | Cards (column span) |
  |----|----|
  | 1 | **Skill Graph** (8) · right column (4) stacking **Skill Composition** + **Insight** |
  | 2 | **Bridge Skills** (4) · **Inferred Skills** (4) · **Commit Activity** (4) |
  | 3 | **Pinned Repositories** (7) · **Career Timeline** (5) |
  | 4 | **Skills Mapped** metric (6) · **GitHub Reach** metric (6) |
- **Footer** (`.foot`): mono micro-text — product line + `user_id · N skills · N edges`.

**Cards** (all `.card`: bg `--card` #fcfcfb, 1px `--line` border, radius 20px,
soft shadow, `card-head` with 18px/600 title + optional 13px `--ink-3` subtitle +
circular `⋯` menu):

- **Skill Graph** (hero): a filter bar of pill chips (type: All/Skills/Companies/
  Projects · source: All/Explicit/Inferred · communities), an SVG force-style
  graph, a counts strip, and an AI prompt bar (`.graph-prompt`) reading
  "Ask the graph — …". See *Interactions*.
- **Skill Composition** (Gross-Volume analog): huge number `23` (52px/700) +
  green "↑ 5 inferred" delta pill; subtitle "18 explicit · 5 inferred across 4
  communities"; three **striped horizontal bars** (Frameworks / Languages / Tools
  & infra) — bar track `--well`, fill is a solid colour + 45° white-stripe overlay,
  right-aligned count.
- **Insight** (`.insight`): full-bleed multi-stop gradient card, white text;
  pill "✦ Insight", giant `87%`, headline "FastAPI is your strongest bridge
  skill.", supporting copy.
- **Bridge Skills**: ranked rows — square rank badge, name + category + blue
  centrality value, striped blue progress bar (width = centrality×100%), note line.
- **Inferred Skills**: rows with a circular check (filled blue when confidence
  ≥ 0.85, else hollow), name + confidence % pill (green when high), reason
  sentence, and a `via [chip] → [chip]` reasoning chain ending in a dashed chip,
  with a mono method tag (`llm` / `graph_implies`) right-aligned.
- **Commit Activity** (Retention analog): pink **step area chart** (SVG), vertical
  hairline stripe fill, peak dot + floating "Peak · 60" bubble, month axis.
- **Pinned Repositories**: repo rows — repo icon, name, optional green "New" pill,
  language dot + label, ★ stars, summary line, stack chips.
- **Career Timeline**: entries with a coloured left bar, company + "Current" pill,
  role, mono date range + months + stage·industry, stack chips. Education entry
  has a grey bar.
- **Metric cards** (Skills Mapped, GitHub Reach): big number (44px/700) | centered
  **dot-matrix** column chart (peak column saturated, others faded) with a peak
  tag pill above | right-aligned delta.

### 2. Upload  *(supplementary)*
**File:** `FirstKnock Upload.html` → `app-shell.jsx`, `dashboard.css`, `flow.css`.
Drag-and-drop résumé upload + email field, maps to `POST /ingest`.

### 3. Processing  *(supplementary)*
**File:** `FirstKnock Processing.html`. Stage-by-stage ingestion progress, maps to
polling `GET /resume/{id}` until `status` reaches `enriched`.

> **⚠ Style note:** The Upload and Processing pages were built in an **earlier,
> warmer "bone / olive" palette** and have **not yet been migrated** to the Zentra
> style of the dashboard. Treat the dashboard as the source of truth for the
> visual system; when you build the ingestion screens, restyle them with the
> tokens below for consistency (the layout/flow is still valid).

---

## Interactions & Behavior

**Skill Graph (`dashboard-graph.jsx`):**
- **Hover a node** → that node + its direct neighbours stay full opacity;
  everything else dims to ~0.18; connected edges thicken/darken. (`onMouseEnter/Leave`)
- **Click a node** → opens a **right-side detail drawer** (`.drawer`, slides in
  from the right, ~320px). Drawer content varies by node kind:
  - *skill* → category · community · confidence; if inferred, a "Why we infer
    this" quote block + "Reached via" + method; co-occurs chips; implies chips.
  - *company* → title, mono date range, stage/industry chips, stack chips.
  - *project* → ★ stars · language, summary, stack chips, topic chips.
  - *person (YOU)* → explainer text.
  Click the same node again, or the drawer ×, to close.
- **Filter chips** (type / source / community): toggle visibility of node sets;
  active chip = solid black (`.gchip.is-active`). Selecting a community draws a
  dashed halo around that cluster.
- **Counts strip** updates live to reflect visible nodes/edges and current focus.

**Nav links** scroll to in-page sections via anchors (`#graph`, `#skills`,
`#projects`, `#timeline`); "Documents" links to the Upload page. In a real app,
wire these to routes.

**Buttons** (`Export JSON`, `Add widget`, `⋯` menus, search, bell) are visual in
the prototype — wire to real handlers.

**Animations:** drawer entrance `drawer-in` (translateX 16px + fade, 0.2s
ease-out). Hover opacity transitions 0.2s. Keep these subtle.

**Responsive:** full 12-col bento ≥ 821px wide. At ≤ 820px every card becomes
full-width (`grid-column: span 12`), nav links hide, title shrinks to 30px,
frame padding tightens. The app frame is `max-width:1500px`, centered.

---

## State Management
For a production build, the dashboard needs:
- `profile` — from `GET /profile/{user_id}` (identity, seniority, experience,
  github followers/repos).
- `skills` — from `GET /skills/{user_id}` (explicit + inferred, with
  `confidence`, `reason`, `via`, `inferred_by`).
- `graph` — from `GET /graph/{user_id}` (nodes, edges, communities).
- `analytics` — from `GET /analytics/{user_id}` (bridge_skills, career_timeline,
  inferred breakdown).
- Local UI state: `selectedNode` (drawer), `hoverNode`, `typeFilter`,
  `sourceFilter`, `communityFilter`.

See `dashboard-data.js` for the exact shapes the components expect (it mirrors the
API). `API_REFERENCE.md` is the backend contract.

---

## Design Tokens
*(authoritative copy lives in `overview.css` `:root`)*

**Surfaces**
| Token | Hex | Use |
|---|---|---|
| `--outer` | `#d4d3d1` | outermost page behind the app frame |
| `--page` | `#ececea` | app frame canvas (behind cards) |
| `--card` | `#fcfcfb` | card background |
| `--card-2` | `#f5f5f3` | chips, hover, dot-matrix empties |
| `--well` | `#f0f0ed` | progress-bar tracks |

**Ink (text)**
| Token | Hex |
|---|---|
| `--ink` | `#14161b` |
| `--ink-2` | `#43464d` |
| `--ink-3` | `#777a82` |
| `--ink-4` | `#a7aab1` |
| `--ink-5` | `#cdcfd4` |

**Lines:** `--line` `#eceae6`, `--line-2` `#e3e1dc`

**Brand / accent**
| Token | Hex | Use |
|---|---|---|
| `--brand` | `#ef7b2e` | logo gradient, ping dot, AI spark |
| `--primary` | `#14161b` | active nav, graph "YOU" node + edges-on-focus, dark buttons |
| `--green` / `--green-bg` | `#14a05a` / `#dcf3e4` | positive bars, high-confidence |
| `--blue` / `--blue-bg` | `#2f6af0` / `#dbe7ff` | bridge bars, centrality, info |
| `--pink` / `--pink-bg` | `#e6457f` / `#fcdfeb` | activity chart, accents |

**Graph node fills:** person/YOU `#14161b` · company `#14161b` · explicit skill
`#fff` (1.3px `#14161b` stroke) · inferred skill `#fff` (dashed stroke) · project
`#eef1f6` · institution `#e3e1dc`. Edges `#e3e1dc` (focused `#14161b`);
`IMPLIES` edges dashed.

**Radius:** `--radius` 14px · `--radius-lg` 20px (cards) · `--radius-xl` 24px
(app frame). Pills 999px.

**Shadow:** `--shadow` `0 1px 2px rgba(20,22,27,.04), 0 8px 24px rgba(20,22,27,.05)`;
`--shadow-sm` `0 1px 2px rgba(20,22,27,.05)`.

**Type:** body **Geist** (400/500/600/700); mono **Geist Mono** (`.fk-mono`,
dates/ids/method tags). Scale: title 38/600 · big numbers 44–64/700 · card title
18/600 · body 13–14 · subtitle/meta 12–13 (`--ink-3`) · mono micro 11–12.

**Spacing:** grid gap 16px · card body padding 18–22px · frame padding 18–26px.

---

## Assets
- **Fonts:** Geist + Geist Mono via Google Fonts (`<link>` in each HTML head).
  Swap for self-hosted in production.
- **Icons:** all inline SVG, hand-rolled in `overview-app.jsx` (object `I`) and
  `dashboard-graph.jsx`. No icon-font dependency — replace with your icon set if
  preferred (lucide/heroicons map cleanly).
- **Graph:** pure inline SVG, deterministic cluster layout — **no graph library**.
  In production you may keep the SVG approach or swap to d3-force / react-flow; the
  data shape in `dashboard-data.js` (`EDGES`, `SKILLS`, `COMMUNITIES`) is library-agnostic.
- **Images:** none. The avatar is initials on a gradient ring; the logo is an SVG
  hexagon on a CSS gradient.

---

## Files
**Dashboard (primary):**
- `FirstKnock Dashboard.html` — entry; loads fonts, React/Babel CDN, then the scripts below
- `overview.css` — all dashboard styling + tokens (`:root`)
- `overview-app.jsx` — nav, title bar, all cards, app composition (`OverviewApp`)
- `dashboard-graph.jsx` — `SkillGraph` (interactive SVG) + `NodeDrawer`
- `dashboard-data.js` — sample data on `window.DATA`, mirrors the API shapes

**Ingestion (supplementary, prior style):**
- `FirstKnock Upload.html`, `FirstKnock Processing.html`
- `app-shell.jsx`, `dashboard.css`, `flow.css`

**Reference:**
- `API_REFERENCE.md` — backend API contract
- `wireframes/` — earlier low-fi exploration (3 directions); historical context only

---

## Suggested build order
1. Scaffold the app + design tokens (port `overview.css` `:root` into your theme).
2. Build the card shell + the static cards (Composition, Insight, Bridge,
   Inferred, Projects, Timeline, Metrics) against `dashboard-data.js` shapes.
3. Build the Skill Graph (SVG or library) with hover-dim, click-drawer, filters.
4. Replace sample data with real API calls (`/profile`, `/skills`, `/graph`,
   `/analytics`); add loading/empty/error states.
5. Build/redress the Upload + Processing flow in the Zentra style; wire `/ingest`
   + polling.
