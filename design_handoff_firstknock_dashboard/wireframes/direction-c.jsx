// Direction C — Sidebar + focused panes. Left rail lists sections; main
// pane shows one focused view at a time. More structured / report-like.

// Sidebar reused across screens
const C_Sidebar = ({ active = 'overview' }) => {
  const items = [
    { k: 'overview', n: 'Overview', kbd: 'O' },
    { k: 'graph',    n: 'Skill graph', kbd: 'G' },
    { k: 'skills',   n: 'Skills', kbd: 'S' },
    { k: 'timeline', n: 'Career', kbd: 'C' },
    { k: 'projects', n: 'Projects', kbd: 'P' },
    { k: 'analytics',n: 'Analytics', kbd: 'A' },
    { k: 'raw',      n: 'Raw resume', kbd: 'R' },
  ];
  return (
    <div style={{
      width: 200, borderRight: `1px solid ${WK.ink}`, background: WK.fill1,
      display: 'flex', flexDirection: 'column', padding: '20px 0',
      flexShrink: 0,
    }}>
      <div style={{ padding: '0 16px 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 18, height: 18, border: `1.5px solid ${WK.ink}`, borderRadius: 2, position: 'relative' }}>
          <div style={{ position: 'absolute', inset: 3, border: `1.2px solid ${WK.ink}`, borderRadius: 1 }} />
        </div>
        <div style={{ fontFamily: WK.mono, fontWeight: 600, fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>FirstKnock</div>
      </div>
      <div style={{ padding: '8px 14px 4px', fontFamily: WK.mono, fontSize: 9, color: WK.mute, letterSpacing: 1.2, textTransform: 'uppercase' }}>Profile</div>
      <div style={{ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: 1 }}>
        {items.map((it) => {
          const isActive = it.k === active;
          return (
            <div key={it.k} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '7px 10px',
              borderRadius: 3,
              fontFamily: WK.ui, fontSize: 12,
              fontWeight: isActive ? 600 : 400,
              background: isActive ? WK.ink : 'transparent',
              color: isActive ? WK.fill0 : WK.ink2,
              borderLeft: isActive ? `2px solid ${WK.ink}` : '2px solid transparent',
            }}>
              <div style={{ flex: 1 }}>{it.n}</div>
              <div style={{
                fontFamily: WK.mono, fontSize: 9,
                padding: '1px 4px',
                border: `1px solid ${isActive ? WK.fill0 : WK.weak}`,
                borderRadius: 2,
                opacity: 0.7,
              }}>{it.kbd}</div>
            </div>
          );
        })}
      </div>
      <div style={{ flex: 1 }} />
      <div style={{ padding: '0 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Rule />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 24, height: 24, borderRadius: 12, border: `1.2px solid ${WK.ink}`, background: WK.fill0, fontFamily: WK.ui, fontWeight: 600, fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>AD</div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: WK.ui, fontSize: 11, fontWeight: 600 }}>Aswinthraj D.</div>
            <div style={{ fontFamily: WK.mono, fontSize: 8, color: WK.mute }}>mid · 18mo</div>
          </div>
        </div>
        <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>polled 12s ago</div>
      </div>
    </div>
  );
};

// ── Upload (C) ────────────────────────────────────────────────
const C_Upload = () => (
  <WFrame url="firstknock.app/">
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Empty sidebar with all items disabled — emphasizes onboarding */}
      <div style={{ width: 200, borderRight: `1px solid ${WK.ink}`, background: WK.fill1, padding: '20px 0', flexShrink: 0 }}>
        <div style={{ padding: '0 16px 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 18, height: 18, border: `1.5px solid ${WK.ink}`, borderRadius: 2, position: 'relative' }}>
            <div style={{ position: 'absolute', inset: 3, border: `1.2px solid ${WK.ink}`, borderRadius: 1 }} />
          </div>
          <div style={{ fontFamily: WK.mono, fontWeight: 600, fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>FirstKnock</div>
        </div>
        <div style={{ padding: '8px 14px', fontFamily: WK.mono, fontSize: 9, color: WK.mute, letterSpacing: 1.2, textTransform: 'uppercase' }}>Profile · locked</div>
        <div style={{ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: 1, opacity: 0.4 }}>
          {['Overview','Skill graph','Skills','Career','Projects','Analytics','Raw resume'].map((n) => (
            <div key={n} style={{ padding: '7px 10px', fontFamily: WK.ui, fontSize: 12, color: WK.mute, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontFamily: WK.mono, fontSize: 10 }}>🔒</span>{n}
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ height: 48, display: 'flex', alignItems: 'center', padding: '0 24px', borderBottom: `1px solid ${WK.ink}`, background: WK.fill0, gap: 10 }}>
          <div style={{ fontFamily: WK.mono, fontSize: 9, letterSpacing: 1.2, color: WK.mute, textTransform: 'uppercase' }}>Onboarding</div>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>›</div>
          <div style={{ fontFamily: WK.ui, fontSize: 12, fontWeight: 500 }}>Upload resume</div>
        </div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40, background: WK.fill1 }}>
          <div style={{ width: 600, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontFamily: WK.ui, fontSize: 22, fontWeight: 600, letterSpacing: -0.4, lineHeight: 1.2 }}>
                Start with your resume.
              </div>
              <div style={{ fontSize: 12, color: WK.ink2, lineHeight: 1.5 }}>
                We&rsquo;ll parse experience, projects and skills, then enrich with
                public GitHub + company data and infer hidden capabilities.
              </div>
              <Rule />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11, color: WK.ink2 }}>
                {['Parse PDF / DOCX', 'Pull GitHub stars + READMEs', 'Resolve companies (stage, industry)', 'Infer implicit skills via LLM + graph'].map((t) => (
                  <div key={t} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <div style={{ width: 12, height: 12, border: `1.2px solid ${WK.ink}`, borderRadius: 2, background: WK.fill0 }} />
                    {t}
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{
                height: 180, border: `1.5px dashed ${WK.ink}`, borderRadius: 4,
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6,
                background: WK.fill0,
              }}>
                <div style={{ fontFamily: WK.ui, fontWeight: 600, fontSize: 13 }}>Drop file</div>
                <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>PDF · DOCX · 5MB</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute, textTransform: 'uppercase', letterSpacing: 1 }}>Email</div>
                <div style={{ height: 34, border: `1.2px solid ${WK.ink}`, borderRadius: 3, padding: '0 10px', display: 'flex', alignItems: 'center', fontFamily: WK.mono, fontSize: 11, background: WK.fill0 }}>
                  iamaswinth@gmail.com
                </div>
              </div>
              <WBtn primary h={40}>Ingest →</WBtn>
            </div>
          </div>
        </div>
      </div>
    </div>
  </WFrame>
);

// ── Processing (C) — sidebar reveals as stages finish ─────────
const C_Processing = () => (
  <WFrame url="firstknock.app/profile/01e46dca‑…">
    <div style={{ display: 'flex', height: '100%' }}>
      {/* sidebar — first 4 items "unlock" as stages finish */}
      <div style={{ width: 200, borderRight: `1px solid ${WK.ink}`, background: WK.fill1, padding: '20px 0', flexShrink: 0 }}>
        <div style={{ padding: '0 16px 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 18, height: 18, border: `1.5px solid ${WK.ink}`, borderRadius: 2 }} />
          <div style={{ fontFamily: WK.mono, fontWeight: 600, fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>FirstKnock</div>
        </div>
        <div style={{ padding: '8px 14px', fontFamily: WK.mono, fontSize: 9, color: WK.mute, letterSpacing: 1.2, textTransform: 'uppercase' }}>Profile · building</div>
        <div style={{ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: 1 }}>
          {[
            ['Overview',      'unlocked'],
            ['Skill graph',   'unlocked'],
            ['Skills',        'unlocked'],
            ['Career',        'unlocked'],
            ['Projects',      'pending'],
            ['Analytics',     'pending'],
            ['Raw resume',    'unlocked'],
          ].map(([n, s]) => (
            <div key={n} style={{
              padding: '7px 10px',
              fontFamily: WK.ui, fontSize: 12,
              color: s === 'unlocked' ? WK.ink : WK.mute2,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              opacity: s === 'unlocked' ? 1 : 0.55,
            }}>
              <span>{n}</span>
              {s === 'pending' && <div style={{ width: 8, height: 8, borderRadius: 4, border: `1px dashed ${WK.ink2}` }} />}
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ height: 48, display: 'flex', alignItems: 'center', padding: '0 24px', borderBottom: `1px solid ${WK.ink}`, background: WK.fill0, gap: 12 }}>
          <div style={{ fontFamily: WK.ui, fontSize: 14, fontWeight: 600 }}>Building your profile</div>
          <Chip dashed>polling · 3s</Chip>
        </div>
        <div style={{ flex: 1, padding: 24, display: 'flex', flexDirection: 'column', gap: 16, background: WK.fill1 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {[
              ['Identity',    'name · email · linkedin', 100],
              ['Experience',  '2 roles · 11 months',     100],
              ['Projects',    '3 found · enriching…',    72],
              ['Skills',      '32 explicit',             100],
              ['Inferred',    'querying llm…',           45],
              ['Embeddings',  'queued',                  0],
            ].map(([t, sub, p]) => (
              <div key={t} style={{ border: `1.2px solid ${WK.ink}`, borderRadius: 4, padding: 12, background: WK.fill0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <div style={{ fontFamily: WK.ui, fontSize: 12, fontWeight: 600 }}>{t}</div>
                  <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>{p}%</div>
                </div>
                <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>{sub}</div>
                <div style={{ height: 4, background: WK.fill2, border: `1px solid ${WK.weak}`, borderRadius: 100, overflow: 'hidden' }}>
                  <div style={{ width: `${p}%`, height: '100%', background: WK.ink }} />
                </div>
              </div>
            ))}
          </div>
          <Rule />
          <div style={{ display: 'flex', gap: 18 }}>
            <div style={{ flex: 1, border: `1.2px solid ${WK.ink}`, borderRadius: 4, background: WK.fill0, padding: 14 }}>
              <WSubhead action="live · /resume/{id}">Log</WSubhead>
              <div style={{ marginTop: 8, fontFamily: WK.mono, fontSize: 10, color: WK.ink2, lineHeight: 1.6 }}>
                {[
                  '[10:30:00] POST /ingest · file=resume.pdf',
                  '[10:30:01] parse ✓ · 4 pages',
                  '[10:30:03] extract ✓ · 32 skills, 2 roles',
                  '[10:30:04] graph ✓ · 41 nodes, 102 edges',
                  '[10:30:08] enrichment.github ✓ · 18 repos',
                  '[10:30:11] enrichment.company → resolving TechKareer…',
                  '[10:30:14] infer → llm thinking…',
                ].map((l, i) => <div key={i}>{l}</div>)}
              </div>
            </div>
            <div style={{ width: 240, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <WSubhead>Status</WSubhead>
              <div style={{ fontFamily: WK.ui, fontSize: 28, fontWeight: 600 }}>extracted</div>
              <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>→ enriched in ~12s</div>
              <Rule />
              <WBtn>Skip to overview →</WBtn>
            </div>
          </div>
        </div>
      </div>
    </div>
  </WFrame>
);

// ── Dashboard (C) · Overview pane ─────────────────────────────
const C_Overview = () => (
  <WFrame url="firstknock.app/profile/01e46dca‑…">
    <div style={{ display: 'flex', height: '100%' }}>
      <C_Sidebar active="overview" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* breadcrumb + actions */}
        <div style={{ height: 48, display: 'flex', alignItems: 'center', padding: '0 24px', borderBottom: `1px solid ${WK.ink}`, background: WK.fill0, gap: 10 }}>
          <div style={{ fontFamily: WK.mono, fontSize: 9, letterSpacing: 1.2, color: WK.mute, textTransform: 'uppercase' }}>Aswinthraj Devaraj</div>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>›</div>
          <div style={{ fontFamily: WK.ui, fontSize: 12, fontWeight: 600 }}>Overview</div>
          <div style={{ flex: 1 }} />
          <Chip>last sync · 1m ago</Chip>
          <WBtn>Share</WBtn>
          <WBtn>Re-ingest</WBtn>
        </div>

        {/* hero strip — identity + headline stat */}
        <div style={{ padding: '20px 24px', borderBottom: `1px solid ${WK.weak}`, background: WK.fill0, display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{ width: 72, height: 72, borderRadius: 36, border: `1.6px solid ${WK.ink}`, background: WK.fill1, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WK.ui, fontWeight: 600, fontSize: 20 }}>AD</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: WK.ui, fontSize: 24, fontWeight: 600, letterSpacing: -0.4 }}>Aswinthraj Devaraj</div>
            <div style={{ fontSize: 12, color: WK.ink2 }}>Full Stack AI Engineer · Tirupur, TamilNadu</div>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <Chip>github.com/iamaswinth ↗</Chip>
              <Chip>linkedin ↗</Chip>
              <Chip>iamaswinth@gmail.com</Chip>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 28 }}>
            <Stat big="mid" small="seniority" />
            <Stat big="18mo" small="experience" />
            <Stat big="47" small="skills total" />
            <Stat big="12" small="gh followers" />
          </div>
        </div>

        {/* two-col content */}
        <div style={{ flex: 1, padding: 20, display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16, overflow: 'hidden', background: WK.fill1 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, minHeight: 0 }}>
            <WCard eyebrow="GET /graph" title="Skill graph · preview" action="open ↗ G" style={{ flex: 1, padding: 0 }}>
              <div style={{ flex: 1, position: 'relative', minHeight: 200 }}>
                <FakeGraph />
                <div style={{ position: 'absolute', bottom: 8, left: 10, fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>52 nodes · 4 communities</div>
              </div>
            </WCard>
            <WCard eyebrow="GET /analytics" title="Career timeline">
              <Timeline />
            </WCard>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, minHeight: 0, overflow: 'hidden' }}>
            <WCard eyebrow="GET /skills" title="Top skills" action="32 explicit · 15 inferred">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {['Python','TypeScript','FastAPI','Next.js','React','LangGraph','Google ADK','RAG','Gemini Live','Pinecone','Docker','Pydantic','WebRTC','PostgreSQL'].map((s, i) => (
                  <Chip key={s} dashed={i > 9}>{s}</Chip>
                ))}
              </div>
            </WCard>
            <WCard eyebrow="GET /analytics · bridge" title="Bridge skills">
              <Bridge name="FastAPI" cat="framework" v={0.87} />
              <Bridge name="Python" cat="language" v={0.74} />
              <Bridge name="Docker" cat="tool" v={0.42} />
            </WCard>
            <WCard eyebrow="GET /resume · projects" title="Pinned projects" style={{ minHeight: 0, overflow: 'hidden' }}>
              <Project name="The Mind Surf" stack={['Next.js','Pinecone','FastAPI']} stars="★ 4" lang="TS" />
              <Project name="firstknock" stack={['FastAPI','Memgraph']} stars="★ 7" lang="Py" isNew />
            </WCard>
          </div>
        </div>
      </div>
    </div>
    <WAnno top={70} left={210} width={140}>
      keyboard shortcut hints in side rail → fast nav
    </WAnno>
  </WFrame>
);

// ── Dashboard (C) · Graph pane ────────────────────────────────
const C_GraphPane = () => (
  <WFrame url="firstknock.app/profile/01e46dca‑…/graph">
    <div style={{ display: 'flex', height: '100%' }}>
      <C_Sidebar active="graph" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ height: 48, display: 'flex', alignItems: 'center', padding: '0 24px', borderBottom: `1px solid ${WK.ink}`, background: WK.fill0, gap: 10 }}>
          <div style={{ fontFamily: WK.mono, fontSize: 9, letterSpacing: 1.2, color: WK.mute, textTransform: 'uppercase' }}>Profile › Skill graph</div>
          <div style={{ flex: 1 }} />
          <Chip dark>2D</Chip><Chip>3D</Chip>
          <WBtn>Export PNG</WBtn>
        </div>

        {/* graph toolbar */}
        <div style={{ height: 40, display: 'flex', alignItems: 'center', padding: '0 20px', borderBottom: `1px solid ${WK.weak}`, gap: 10, background: WK.fill0 }}>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>Filter:</div>
          <Chip dark>All</Chip><Chip>Skills</Chip><Chip>Companies</Chip><Chip>Projects</Chip><Chip>Education</Chip>
          <div style={{ width: 1, height: 16, background: WK.weak, margin: '0 8px' }} />
          <Chip>Explicit</Chip><Chip>Inferred</Chip>
          <div style={{ flex: 1 }} />
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>52 / 137 · 4 communities</div>
        </div>

        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 300px', minHeight: 0 }}>
          <div style={{ position: 'relative', background: WK.fill0 }}>
            <FakeGraph dense />
            <div style={{ position: 'absolute', top: 14, left: 16, fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>scroll to zoom · drag to pan</div>
            <div style={{ position: 'absolute', bottom: 14, right: 14, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {['+','−','⟲','⛶'].map((s) => (
                <div key={s} style={{ width: 26, height: 26, border: `1px solid ${WK.ink}`, background: WK.fill0, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WK.mono, fontSize: 11 }}>{s}</div>
              ))}
            </div>
          </div>
          <div style={{ borderLeft: `1px solid ${WK.ink}`, background: WK.fill1, padding: 16, display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden' }}>
            <WSubhead>Communities</WSubhead>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <CommLine n="LangGraph + Google ADK" count={6} on />
              <CommLine n="React + Next.js" count={5} on />
              <CommLine n="Data layer" count={4} on />
              <CommLine n="DevOps" count={3} />
            </div>
            <Rule />
            <WSubhead action="× close">selected</WSubhead>
            <div>
              <div style={{ fontFamily: WK.ui, fontSize: 16, fontWeight: 600 }}>LangGraph</div>
              <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>framework · explicit · 1.00</div>
            </div>
            <Rule />
            <WSubhead>Co-occurs</WSubhead>
            {[['Google ADK',8],['RAG',7],['FastAPI',6]].map(([n,c]) => (
              <div key={n} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span>{n}</span><span style={{ fontFamily: WK.mono, color: WK.mute }}>×{c}</span>
              </div>
            ))}
            <Rule />
            <WSubhead>Implies</WSubhead>
            <div style={{ fontSize: 11 }}>Agent State Machines <span style={{ color: WK.mute }}>· 0.90</span></div>
          </div>
        </div>
      </div>
    </div>
  </WFrame>
);

Object.assign(window, { C_Sidebar, C_Upload, C_Processing, C_Overview, C_GraphPane });
