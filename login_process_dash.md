# FirstKnock — Login → Upload Modal → Dashboard: Build Plan

## What's Already Built

| Layer | Status |
|---|---|
| Design tokens (`--fk-*` CSS vars) | ✅ done |
| shadcn/ui + Tailwind v4 | ✅ done |
| All dashboard cards (10 cards) | ✅ done |
| Nav, TitleBar, Footer | ✅ done |
| All API hooks (React Query) | ✅ done |
| `/profile/[user_id]/page.tsx` (full dashboard) | ✅ done |
| Dropzone component | ✅ done |
| ProcessingStatus component | ✅ done |
| Processing page (`/processing/[resume_id]`) | ✅ done (will be deprecated) |

**What this plan adds:** Login, email-based auth layer, `/dashboard` route, upload modal (replaces standalone upload + processing pages), and empty-state handling.

---

## Product Flow (Target)

```
/                   ──redirect──▶  /login          (if not authed)
                    ──redirect──▶  /dashboard       (if authed)

/login              ──submit──▶   /dashboard        (stores userId in auth)

/dashboard          ──no resume──▶  empty state with Upload CTA
                    ──has resume──▶  full bento grid with data

Upload CTA          ──click──▶   UploadModal opens
UploadModal         ──step 1──▶  file + email → POST /ingest
                    ──step 2──▶  live polling progress (inside modal)
                    ──step 3──▶  success → modal closes → dashboard refreshes
```

---

## Route Architecture

| Route | Purpose | Auth required |
|---|---|---|
| `/` | Redirect → `/login` or `/dashboard` | — |
| `/login` | Email sign-in form | No |
| `/dashboard` | Full profile dashboard | Yes — reads userId from auth |
| `/profile/[user_id]` | Shareable public profile link | No — keep as-is |

The current `/processing/[resume_id]` page becomes a fallback-only route. Processing now happens inside the upload modal.

---

## Auth Strategy

**No backend auth needed.** The backend creates a user on first ingest. We persist the mapping on the client.

### Storage shape
```ts
// localStorage key: "fk_users"
type FKUserStore = {
  current: string            // email of the active "session"
  users: Record<string, {    // keyed by email
    userId: string
    name: string
    resumeId: string
    ingestedAt: string
  }>
}
```

### Login flow
1. User enters email on `/login`
2. Check `fk_users.users[email]`:
   - **Found** → set `fk_users.current = email` → redirect to `/dashboard`
   - **Not found** → set `fk_users.current = email` (with no userId yet) → redirect to `/dashboard`
3. On `/dashboard`, if `userId` is missing → show empty state with Upload CTA
4. After successful ingest, write `userId + resumeId + name` into `fk_users.users[email]`

### Logout
Clear `fk_users.current` → redirect to `/login`.

### Hook: `useAuth`
```ts
const { email, userId, name, login, logout, saveResume } = useAuth()
```

---

## State Architecture

### AuthProvider (wraps the whole app)

```
RootLayout
  └── QueryProvider           (react-query)
        └── AuthProvider      (email + userId context)
              └── page content
```

**AuthProvider** reads from localStorage on mount, exposes:
- `email: string | null`
- `userId: string | null`
- `name: string | null`
- `isAuthed: boolean` (email is set, doesn't require userId)
- `hasResume: boolean` (userId exists)
- `login(email)` — sets current user
- `logout()` — clears current user
- `saveResume({ userId, resumeId, name })` — called after ingest

### Dashboard data flow

```
/dashboard
  └── useAuth() → userId
        ├── useProfile(userId)
        ├── useSkills(userId)
        ├── useGraph(userId)
        ├── useAnalytics(userId)
        ├── useRoles(userId)
        └── useCompleteness(userId)
```

All hooks already exist. No changes needed there.

---

## Component Plan

### New: `lib/auth/index.ts`
Client-side auth store — read/write localStorage with the FKUserStore shape.

```ts
export function getAuth(): FKUserStore
export function setCurrentUser(email: string): void
export function saveResume(email: string, data: { userId, resumeId, name }): void
export function clearCurrentUser(): void
```

### New: `providers/auth-provider.tsx`
React context + `useAuth` hook. `'use client'`. Reads from `lib/auth` on mount.

### New: `app/login/page.tsx`
```
Design:
  - Same background as upload page: var(--fk-outer)
  - Centered card (max-w-sm) using var(--fk-card) surface
  - FK logo + hexagon mark at top
  - Headline: "Sign in to FirstKnock"
  - Sub: "Use the email you registered with, or enter a new one to get started."
  - Single email input + "Continue" button
  - No password — email-based identification only
  - On submit: calls login(email) → router.push('/dashboard')
  - If email already exists in store: "Welcome back, [name]" message before redirect
```

### New: `app/page.tsx` (redirect)
```ts
// Server component — reads nothing, just redirects
import { redirect } from 'next/navigation'
export default function Root() {
  redirect('/login')
}
```
(Actual auth-based conditional redirect is handled client-side by AuthProvider on mount.)

### New: `app/dashboard/page.tsx`
- `'use client'`
- Reads `useAuth()` for userId + email
- If not authed (no email): redirect to `/login`
- If authed but no resume (no userId): renders `EmptyDashboard`
- If has userId: renders the full bento grid (same as current `/profile/[user_id]`)

Factor the full dashboard grid into a shared `DashboardContent` component so both `/dashboard` and `/profile/[user_id]` can use it.

```
app/dashboard/page.tsx
  └── DashboardContent (userId from auth context)

app/profile/[user_id]/page.tsx
  └── DashboardContent (userId from URL)
```

### New: `components/dashboard/empty-dashboard.tsx`
Shown when authed but no resume yet.
```
Design:
  - Full bento grid layout — exact same Nav + TitleBar + Footer
  - All card slots are greyed-out skeletons (faint dotted borders, no content)
  - Centered overlay on the grid: icon + "Your knowledge graph lives here." + 
    "Upload your résumé to get started." + "Upload résumé" button
  - Button click → opens UploadModal
  - Style: the overlay floats above the ghost grid, backdrop blur on the grid itself
```

### New: `components/upload/upload-modal.tsx`
shadcn `Dialog` component. Multi-step. `'use client'`.

**Step 1 — Upload**
```
- Dialog title: "Analyse your résumé"
- Dropzone (existing component, reuse)
- Email input: pre-filled + disabled (from useAuth)
- "Analyse" button → disabled until file selected
- On submit: calls POST /ingest → transitions to Step 2
- Error state: inline below the button
```

**Step 2 — Processing**
```
- Dialog title: "Building your graph"
- Same stages checklist as existing ProcessingStatus component
- Polls GET /resume/{resumeId} every 3s
- Live checkmarks as stages complete
- Pulsing orange dot + "Processing…" label
- No cancel button (intentional — let it finish)
```

**Step 3 — Done**
```
- Dialog title: "Your graph is ready"
- Green checkmark animation
- "View your profile" button (or auto-closes after 1.5s)
- On close/button: calls saveResume() in auth context → modal closes → dashboard re-fetches
```

**Internal state:**
```ts
type ModalStep = 'upload' | 'processing' | 'done'
const [step, setStep] = useState<ModalStep>('upload')
const [resumeId, setResumeId] = useState<string | null>(null)
```

**Trigger:** Exposed via `useUploadModal()` context or passed as a prop to EmptyDashboard and the TitleBar "+ Add widget" button.

---

## File Tree (new files only)

```
firstknock/
├── lib/
│   └── auth/
│       └── index.ts                    ← localStorage store helpers
│
├── providers/
│   ├── query-provider.tsx              ← exists
│   └── auth-provider.tsx               ← NEW: AuthProvider + useAuth
│
├── app/
│   ├── page.tsx                        ← CHANGE: redirect to /login
│   ├── login/
│   │   └── page.tsx                    ← NEW: email login form
│   ├── dashboard/
│   │   └── page.tsx                    ← NEW: auth-gated dashboard
│   └── profile/[user_id]/
│       └── page.tsx                    ← KEEP: shareable link (no changes)
│
├── components/
│   ├── dashboard/
│   │   ├── dashboard-content.tsx       ← NEW: extracted from profile page
│   │   └── empty-dashboard.tsx         ← NEW: ghost grid + upload CTA
│   └── upload/
│       ├── dropzone.tsx                ← exists
│       ├── processing-status.tsx       ← exists
│       └── upload-modal.tsx            ← NEW: multi-step Dialog
```

---

## Build Order

### Phase 1 — Auth layer (no UI changes yet)
1. `lib/auth/index.ts` — localStorage helpers
2. `providers/auth-provider.tsx` — AuthProvider + useAuth hook
3. Wire AuthProvider into `app/layout.tsx` (alongside QueryProvider)

### Phase 2 — Login page
4. `app/login/page.tsx` — email form, calls `login()`, redirects to `/dashboard`
5. `app/page.tsx` — simple redirect

### Phase 3 — Upload modal
6. `components/upload/upload-modal.tsx` — Dialog with 3 steps, reuses Dropzone + ProcessingStatus
7. Test: open modal from a button, complete upload flow, verify `saveResume()` is called

### Phase 4 — Dashboard shell refactor
8. Extract `components/dashboard/dashboard-content.tsx` from `/profile/[user_id]/page.tsx`
9. `components/dashboard/empty-dashboard.tsx` — ghost grid + Upload CTA
10. `app/dashboard/page.tsx` — reads auth, branches empty vs full state
11. Update `/profile/[user_id]/page.tsx` to use `DashboardContent`

### Phase 5 — Polish
12. Add redirect in `AuthProvider` (on mount, if no email → push to `/login`)
13. Nav: add logout button (small "Sign out" link in right cluster)
14. TitleBar: wire the "+ Add widget" button to open UploadModal
15. Empty state: test the full "new user" journey end-to-end

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Auth backend | None — localStorage only | Backend has no auth endpoints; adds no backend work |
| Session persistence | localStorage (survives refresh) | Simple; suits a demo-to-product trajectory |
| Processing location | Inside modal (not separate page) | Better UX — user stays in context |
| Modal close on done | Auto-close after 1.5s + manual button | Gives feedback without trapping the user |
| Empty state | Ghost grid (not blank page) | Shows the product's potential even before data |
| `/profile/[user_id]` | Keep unchanged | Shareable link; let it coexist with `/dashboard` |
| `DashboardContent` extraction | Required | Both `/dashboard` and `/profile/[user_id]` need it |
| Logout | Clear `fk_users.current` only | Keeps resume data stored; re-login restores it |

---

## What Does NOT Change

- All 10 dashboard cards — no modifications
- All API hooks — no modifications
- All design tokens — no modifications
- The `/profile/[user_id]` route — keep as-is for sharing
- The processing page at `/processing/[resume_id]` — keep as fallback, just don't navigate to it anymore

---

## UI Reference File

**Canonical source:** `design_handoff_firstknock_dashboard/FirstKnock Dashboard.html`

This is the pixel-authoritative reference for the entire product. It loads:
- `overview.css` — all tokens and component styles
- `overview-app.jsx` — nav, title bar, all cards, app shell
- `dashboard-graph.jsx` — interactive skill graph + node drawer
- `dashboard-data.js` — sample data mirroring the API shapes

Open `FirstKnock Dashboard.html` in a browser to see the exact target. **Every pixel in the dashboard must match this reference.** When in doubt about spacing, colour, font size, or interaction — open the HTML file.

---

## Canonical Design Tokens (from `overview.css`)

These are the authoritative values. They are already mapped into `globals.css` as `--fk-*` vars. Never hardcode hex values in components — always use the CSS variable.

### Surfaces
| CSS var | Hex | Use |
|---|---|---|
| `--fk-outer` | `#d4d3d1` | outermost page canvas behind the app frame |
| `--fk-page` | `#ececea` | app frame background (behind cards) |
| `--fk-card` | `#fcfcfb` | card background |
| `--fk-card-2` | `#f5f5f3` | chips, hover states, dot-matrix empties |
| `--fk-well` | `#f0f0ed` | progress bar tracks |

### Ink (text hierarchy)
| CSS var | Hex | Level |
|---|---|---|
| `--fk-ink` | `#14161b` | Primary — headings, active elements |
| `--fk-ink-2` | `#43464d` | Secondary — body text |
| `--fk-ink-3` | `#777a82` | Tertiary — subtitles, captions |
| `--fk-ink-4` | `#a7aab1` | Muted — disabled, placeholders |
| `--fk-ink-5` | `#cdcfd4` | Ghost — separators, very faint text |

### Lines
| CSS var | Hex |
|---|---|
| `--fk-line` | `#eceae6` — card borders |
| `--fk-line-2` | `#e3e1dc` — inner dividers |

### Brand & Accent
| CSS var | Hex | Use |
|---|---|---|
| `--fk-brand` | `#ef7b2e` | orange — logo mark, ping dot, AI spark icon |
| `--fk-green` | `#14a05a` | positive deltas, high-confidence badges |
| `--fk-green-bg` | `#dcf3e4` | green pill background |
| `--fk-blue` | `#2f6af0` | bridge skills, centrality, info |
| `--fk-blue-bg` | `#dbe7ff` | blue pill background |
| `--fk-pink` | `#e6457f` | activity chart, accents |
| `--fk-pink-bg` | `#fcdfeb` | pink pill background |

### Radius
| CSS var | Value | Use |
|---|---|---|
| `--fk-radius` | `14px` | chips, inner elements |
| `--fk-radius-lg` | `20px` | cards |
| `--fk-radius-xl` | `24px` | app frame |

### Shadows
```css
--fk-shadow:    0 1px 2px rgba(20,22,27,.04), 0 8px 24px rgba(20,22,27,.05);
--fk-shadow-sm: 0 1px 2px rgba(20,22,27,.05);
```

### Typography
- **Body font:** Geist (400/500/600/700) — loaded via Google Fonts
- **Mono font:** Geist Mono — used for dates, IDs, method tags (class `.fk-mono`)
- **Font smoothing:** `-webkit-font-smoothing: antialiased` on body

---

## Component Pixel Specs (from `overview-app.jsx` + `overview.css`)

### Nav bar (56px tall)
```
height: 56px
display: flex, align-items: center, gap: 18px

Logo mark (.nav-mark):
  width: 30px, height: 30px, border-radius: 9px
  background: linear-gradient(150deg, #f7943f, #ec6a1e)
  box-shadow: 0 2px 6px rgba(236,106,30,0.35)
  icon: hex SVG in white

Wordmark (.nav-name):
  font-size: 18px, font-weight: 600, letter-spacing: -0.01em

Nav links (.nav-link):
  padding: 8px 14px, border-radius: 9px
  font-size: 14px, font-weight: 500, color: var(--fk-ink-3)
  Active (.is-active): background var(--fk-ink), color #fff

Icon buttons (.nav-circle):
  width: 40px, height: 40px, border-radius: 50%
  border: 1px solid var(--fk-line-2), background: var(--fk-card)

Bell ping dot (.ping):
  position: absolute, top: 9px, right: 10px
  width: 7px, height: 7px, border-radius: 50%
  background: var(--fk-brand), border: 1.5px solid var(--fk-card)

Avatar (.nav-avatar):
  width: 42px, height: 42px, border-radius: 50%, padding: 2px
  background: conic-gradient(from 200deg, #f7943f, #e6457f, #2f6af0, #14a05a, #f7943f)
  Inner: background var(--fk-ink), color #fff, font-weight: 700, font-size: 13px
```

### Title bar
```
margin: 22px 0 18px, display: flex, align-items: center, gap: 16px

Heading (h1):
  font-size: 38px, font-weight: 600, letter-spacing: -0.025em

Pills (.tb-pill):
  height: 38px, padding: 0 13px, border-radius: 11px
  font-size: 13px, font-weight: 500, color: var(--fk-ink-2)
  background: var(--fk-card), border: 1px solid var(--fk-line-2)

"+ Add widget" pill (.tb-add):
  background: var(--fk-ink), color: #fff, border-color: var(--fk-ink)
```

### Card shell
```
background: var(--fk-card)
border: 1px solid var(--fk-line)
border-radius: 20px  (var(--fk-radius-lg))
box-shadow: var(--fk-shadow)
display: flex, flex-direction: column
overflow: hidden

Card header (.card-head):
  padding: 20px 22px 0
  display: flex, align-items: center, gap: 10px

Card title (.card-title):
  font-size: 18px, font-weight: 600, letter-spacing: -0.01em

Card subtitle (.card-sub):
  font-size: 13px, color: var(--fk-ink-3), margin-top: 2px

Menu button (.card-menu):
  width: 34px, height: 34px, border-radius: 50%
  border: 1px solid var(--fk-line-2), color: var(--fk-ink-3)

Card body (.card-body):
  padding: 18px 22px 22px
```

### Bento grid
```css
display: grid;
grid-template-columns: repeat(12, 1fr);
gap: 16px;
```
Column span classes: `.col-8`, `.col-7`, `.col-6`, `.col-5`, `.col-4`, `.col-3`.  
Cards stretch to fill (`flex: 1 1 auto; width: 100%`).

### Pills / chips / badges
```
Pill (.pill): height 24px, padding 0 10px, border-radius 999px, font-size 12px, font-weight 600
  .pill-green: background var(--fk-green-bg), color var(--fk-green)
  .pill-blue:  background var(--fk-blue-bg),  color var(--fk-blue)
  .pill-pink:  background var(--fk-pink-bg),  color var(--fk-pink)
  .pill-grey:  background var(--fk-card-2),   color var(--fk-ink-3)

Chip (.chip): padding 4px 10px, font-size 12px, font-weight 500
  background var(--fk-card-2), border 1px solid var(--fk-line), border-radius 8px
  .chip.dashed: background transparent, border-style dashed, color var(--fk-ink-3)

Delta badge (.delta): height 26px, padding 0 10px, border-radius 999px
  font-size 13px, font-weight 600
  background var(--fk-card), box-shadow var(--fk-shadow-sm), border 1px solid var(--fk-line)
  .delta.up: color var(--fk-green)
  .delta.down: color var(--fk-pink)
```

### Striped bars (skill composition + bridge skills)
```css
/* Fill bar = solid color + 45° repeating diagonal stripe overlay */
background-color: var(--fk-green);   /* or --fk-blue, --fk-pink */
background-image: repeating-linear-gradient(
  135deg,
  rgba(255,255,255,0.28) 0 2px,
  transparent 2px 6px
);
background-size: 9px 9px;
border-radius: 999px;

/* Track */
height: 12px;   /* composition bars */
height: 8px;    /* bridge bars */
background: var(--fk-well);
border-radius: 999px;
overflow: hidden;
```

### Insight card (gradient)
```css
background: radial-gradient(
  120% 140% at 85% 10%,
  #f7a23f 0%,
  #ed6aa6 32%,
  #7f7be0 60%,
  #2f5fd0 80%,
  #14245e 100%
);
/* No border. Color: #fff throughout. */

Big number: font-size 64px, font-weight 700, letter-spacing -0.04em
Headline:   font-size 18px, font-weight 600
Body copy:  font-size 13px, color rgba(255,255,255,0.85)

Insight tag pill:
  background rgba(255,255,255,0.18), backdrop-filter blur(4px)
  border 1px solid rgba(255,255,255,0.25)
  padding 5px 11px, border-radius 999px, font-size 12px
```

### Score / metric numbers
```
Big number (composition card): font-size 52px, font-weight 700, letter-spacing -0.04em
Metric number (metric cards):  font-size 44px, font-weight 700, letter-spacing -0.035em
```

### Node drawer (skill graph)
```
position: absolute, right: 0, top: 0, bottom: 0
width: 320px
background: var(--fk-card), border-left: 1px solid var(--fk-line)
padding: 20px, gap: 14px
box-shadow: -12px 0 30px rgba(20,22,27,0.06)

Animation on enter:
@keyframes drawer-in {
  from { transform: translateX(16px); opacity: 0; }
  to   { transform: none; opacity: 1; }
}
duration: 0.2s ease-out
```

### AI prompt bar (below graph)
```
margin: 0 14px 14px
padding: 12px 14px
border: 1px solid var(--fk-line-2), border-radius: 12px
background: var(--fk-card-2), color: var(--fk-ink-3), font-size: 13px
Spark icon: color var(--fk-brand)
```

### App frame
```css
max-width: 1500px;
margin: 22px auto;
min-height: calc(100vh - 44px);
background: var(--fk-page);
border-radius: 24px;   /* var(--fk-radius-xl) */
box-shadow: 0 1px 2px rgba(20,22,27,0.05), 0 22px 60px rgba(20,22,27,0.12);
padding: 18px 22px 26px;
```

### Footer
```
display: flex, align-items: center, gap: 12px
padding-top: 8px
font-size: 12px, color: var(--fk-ink-4)
font-family: var(--mono)  ← Geist Mono
```

### Responsive breakpoint (≤ 820px)
```css
/* All column spans collapse to span 12 */
.col-8, .col-7, .col-6, .col-5, .col-4, .col-3 { grid-column: span 12; }
/* App frame padding tightens */
.ov-app { padding: 14px 14px 20px; }
/* Nav links hide */
.nav-links { display: none; }
/* Title shrinks */
.title h1 { font-size: 30px; }
```

---

## Icon Library (inline SVGs from `overview-app.jsx`)

All icons are hand-rolled inline SVGs. No icon library dependency. Use these exact paths for consistency.

```jsx
const I = {
  search: <svg viewBox="0 0 24 24" fill="none">
    <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/>
    <path d="m20 20-3-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
  </svg>,

  bell: <svg viewBox="0 0 24 24" fill="none">
    <path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
    <path d="M10 20a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
  </svg>,

  link: <svg viewBox="0 0 24 24" fill="none">
    <path d="M10 13a4 4 0 0 0 5.66 0l2-2a4 4 0 1 0-5.66-5.66l-1 1M14 11a4 4 0 0 0-5.66 0l-2 2A4 4 0 1 0 6 18.66l1-1"
      stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>,

  plus: <svg viewBox="0 0 24 24" fill="none">
    <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"/>
  </svg>,

  refresh: <svg viewBox="0 0 24 24" fill="none">
    <path d="M20 11a8 8 0 1 0-.5 3.5M20 5v6h-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>,

  download: <svg viewBox="0 0 24 24" fill="none">
    <path d="M12 4v11m0 0 4-4m-4 4-4-4M5 19h14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>,

  dots: <svg viewBox="0 0 24 24" fill="none">
    <circle cx="6" cy="12" r="1.6" fill="currentColor"/>
    <circle cx="12" cy="12" r="1.6" fill="currentColor"/>
    <circle cx="18" cy="12" r="1.6" fill="currentColor"/>
  </svg>,

  spark: <svg viewBox="0 0 24 24" fill="none">
    <path d="M12 3l1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z" fill="currentColor"/>
  </svg>,

  check: <svg viewBox="0 0 24 24" fill="none">
    <path d="M5 12.5 10 17l9-10" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>,

  star: <svg viewBox="0 0 24 24" fill="none">
    <path d="M12 4l2.3 5 5.4.5-4.1 3.6 1.2 5.3L12 21l-4.8 2.5 1.2-5.3L4.3 9.5 9.7 9 12 4Z" fill="currentColor"/>
  </svg>,

  repo: <svg viewBox="0 0 24 24" fill="none">
    <path d="M6 4h11a2 2 0 0 1 2 2v13H7a2 2 0 0 1-2-2V4Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
    <path d="M7 17h12M9 8h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
  </svg>,

  hex: <svg viewBox="0 0 24 24" fill="none">
    <path d="M12 3.5l7 4v9l-7 4-7-4v-9l7-4Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
  </svg>,

  arrow: <svg viewBox="0 0 24 24" fill="none">
    <path d="M5 12h13m0 0-5-5m5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>,

  up: <svg viewBox="0 0 24 24" fill="none">
    <path d="M5 15l7-7 7 7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>,
}
```

---

## Login Page Design Spec (extends the reference system)

The login page is **not in the reference HTML** — it's a new screen that must feel native to the Zentra design system.

```
Background: var(--fk-outer)  [#d4d3d1 — same as the page behind the app frame]

Centered content column: max-width 400px

─── Logo block (top, centered) ───────────────────────────────
  Logo mark:
    width: 44px, height: 44px, border-radius: 14px
    background: linear-gradient(135deg, #f7943f, #ec6a1e)
    box-shadow: 0 4px 14px rgba(236,106,30,0.30)
    Icon: hex SVG, 20×20, fill white

  Wordmark: "FirstKnock"
    font-size: 24px, font-weight: 600, letter-spacing: -0.02em
    color: var(--fk-ink)

  Tagline: "Your résumé, as a knowledge graph."
    font-size: 14px, color: var(--fk-ink-3), margin-top: 6px

─── Card ─────────────────────────────────────────────────────
  background: var(--fk-card)
  border: 1px solid var(--fk-line)
  border-radius: 20px  (var(--fk-radius-lg))
  box-shadow: var(--fk-shadow)
  padding: 32px

  Headline: "Sign in"
    font-size: 20px, font-weight: 600, letter-spacing: -0.015em
    color: var(--fk-ink)

  Sub: "Enter the email you'd like to use. Returning users are recognised automatically."
    font-size: 13px, color: var(--fk-ink-3), margin-top: 4px, margin-bottom: 24px

  Email input:
    height: 42px, width: 100%
    border: 1px solid var(--fk-line-2), border-radius: 12px
    padding: 0 14px, font-size: 14px
    background: var(--fk-card)
    placeholder color: var(--fk-ink-4)
    focus: border-color var(--fk-ink), outline none

  "Continue" button (full-width, below input, margin-top: 12px):
    height: 42px, border-radius: 12px
    background: var(--fk-ink), color: #fff
    font-size: 14px, font-weight: 600
    hover: background #000
    disabled (empty email): opacity 0.4

  "Returning user" state (email found in localStorage):
    Show above the button: "Welcome back, [name] →" in fk-green
    Button label changes to "Continue as [name]"

─── Footer micro-text ────────────────────────────────────────
  font-size: 12px, color: var(--fk-ink-4), text-align: center
  font-family: var(--mono)
  "firstknock · no password needed"
```

---

## Upload Modal Design Spec (extends the reference system)

Uses shadcn `Dialog`. Content must match the FK card aesthetic — same `--fk-card` surface, `--fk-line` borders.

```
Dialog content:
  max-width: 480px
  border-radius: 20px  (var(--fk-radius-lg))
  padding: 28px
  background: var(--fk-card)

Step 1 — Upload:
  Title: "Analyse your résumé" (20px/600)
  Sub: "We'll parse it, build a skill graph, and infer hidden skills." (13px, fk-ink-3)
  Dropzone: existing component, full-width
  Email row: label + input (pre-filled, grayed out)
  Button: same style as login "Continue" button
  Error: 13px, color #e34 (or fk-pink), margin-top: 8px

Step 2 — Processing:
  Title: "Building your graph" (20px/600)
  Sub: "This takes about 20–30 seconds." (13px, fk-ink-3)
  Stages list (5 items):
    Each row: 20px circle indicator + label
    Pending:   circle background var(--fk-well), label color var(--fk-ink-4)
    Complete:  circle background var(--fk-green), check SVG white, label color var(--fk-ink)
    font-size: 14px, gap between rows: 14px
  Progress indicator: pulsing orange dot (8px, var(--fk-brand)) + "Processing…" mono text

Step 3 — Done:
  Title: "Your graph is ready ✦" (20px/600)
  Sub: "Closing in a moment…" or "View your dashboard"
  Large green check circle: 56px, background var(--fk-green), centered
  Button: "Go to dashboard" — same full-width black button style
  Auto-closes after 1500ms
```

---

## Graph Node Color Spec (from `overview.css` + `dashboard-data.js`)

```
Person / YOU:  fill #14161b  (var(--fk-ink))
Company:       fill #14161b  (same as Person)
Explicit Skill: fill #fff, stroke 1.3px #14161b (solid ring)
Inferred Skill: fill #fff, stroke 1.3px #14161b dashed
Project:       fill #eef1f6
Institution:   fill #e3e1dc

Edges:         stroke #e3e1dc (var(--fk-line-2)), default
               stroke #14161b (var(--fk-ink)), focused / hovered
IMPLIES edges: dashed stroke

Hover behaviour:
  Hovered node + direct neighbours: opacity 1.0
  All others: opacity 0.18
  Connected edges: thicken (strokeWidth × 1.5) + darken to var(--fk-ink)
```

---

## Sample Data Reference (`dashboard-data.js`)

The reference HTML uses `window.DATA` which mirrors the API shapes exactly. Use this as ground truth for component props when the backend is unavailable:

- `PROFILE` → `GET /profile/{user_id}` shape
- `SKILLS` → `GET /skills/{user_id}` — includes `community`, `via`, `inferred_by`, `reason`
- `BRIDGES` → `GET /analytics.bridge_skills` — includes `note` field (not yet in API schema, add if needed)
- `TIMELINE` → `GET /analytics.career_timeline` — includes `stage`, `industry`, `stack`
- `PROJECTS` → `GET /resume.enriched.github.pinned_repos` — includes `summary`, `stack`, `is_new`
- `EDGES` → `GET /graph.links` — typed as `HAS_SKILL`, `WORKED_AT`, `BUILT`, `USES`, `CO_OCCURS`, `IMPLIES`
- `COMMUNITIES` → `GET /graph.communities` — includes `short` label for filter chips
