// Direction A — Bento dashboard.
// Single scrolling page. Graph is the biggest tile; everything else is a
// modular card around it.

// ── Upload screen ─────────────────────────────────────────────
const A_Upload = () => (
  <WFrame url="firstknock.app/">
    <WAppBar right={<div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>v0.1 · dev</div>} />
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <div style={{ width: 540, display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div>
          <div style={{ fontFamily: WK.mono, fontSize: 10, letterSpacing: 1.6, color: WK.mute, textTransform: 'uppercase' }}>Step 1 of 2</div>
          <div style={{ fontFamily: WK.ui, fontSize: 28, fontWeight: 600, letterSpacing: -0.5, marginTop: 4 }}>Drop your resume.</div>
          <div style={{ fontSize: 13, color: WK.ink2, marginTop: 6, maxWidth: 420 }}>
            We parse it, build a skill graph, and pull in GitHub + company data. ~20s.
          </div>
        </div>

        <div style={{
          height: 220,
          border: `1.6px dashed ${WK.ink}`,
          borderRadius: 4,
          background: WK.fill0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 10,
          position: 'relative',
        }}>
          <div style={{
            width: 52, height: 64, border: `1.5px solid ${WK.ink}`, borderRadius: 2,
            position: 'relative', background: WK.fill1,
          }}>
            <div style={{ position: 'absolute', top: 0, right: 0, width: 14, height: 14, borderLeft: `1.5px solid ${WK.ink}`, borderBottom: `1.5px solid ${WK.ink}`, background: WK.fill0 }} />
            <div style={{ position: 'absolute', top: 22, left: 8, right: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <TLine w={36} h={2} /><TLine w={28} h={2} /><TLine w={32} h={2} />
            </div>
          </div>
          <div style={{ fontFamily: WK.ui, fontWeight: 500, fontSize: 13 }}>Drag a PDF or DOCX here</div>
          <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>or click to browse</div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontFamily: WK.mono, fontSize: 9, letterSpacing: 1.2, color: WK.mute, textTransform: 'uppercase' }}>Email</div>
          <div style={{
            height: 38, border: `1.2px solid ${WK.ink}`, borderRadius: 3, background: WK.fill0,
            display: 'flex', alignItems: 'center', padding: '0 12px',
            fontFamily: WK.mono, fontSize: 11, color: WK.ink,
          }}>
            iamaswinth@gmail.com
            <div style={{ marginLeft: 4, width: 1, height: 14, background: WK.ink, animation: 'none' }} />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>PDF · DOCX · max 5MB</div>
          <WBtn primary h={40} style={{ paddingInline: 22 }}>Start →</WBtn>
        </div>
      </div>
    </div>
    <WAnno top={70} right={20} width={170}>
      ← drop‑zone is the whole screen, not just the box
    </WAnno>
  </WFrame>
);

// ── Processing screen ─────────────────────────────────────────
const A_Processing = () => {
  const stages = [
    { k: 'parse',      done: true },
    { k: 'normalize',  done: true },
    { k: 'extract',    done: true },
    { k: 'resolve',    done: true },
    { k: 'persist',    done: true },
    { k: 'graph',      done: true },
    { k: 'enrichment', done: false, live: true },
    { k: 'inference',  done: false },
    { k: 'embedding',  done: false },
  ];
  return (
    <WFrame url="firstknock.app/ingest/eba00ecc-…">
      <WAppBar />
      <div style={{ flex: 1, padding: 40, display: 'flex', justifyContent: 'center' }}>
        <div style={{ width: 620, display: 'flex', flexDirection: 'column', gap: 22 }}>
          <div>
            <div style={{ fontFamily: WK.mono, fontSize: 10, letterSpacing: 1.6, color: WK.mute, textTransform: 'uppercase' }}>Step 2 of 2 · polling /resume/&#123;id&#125;</div>
            <div style={{ fontFamily: WK.ui, fontSize: 24, fontWeight: 600, letterSpacing: -0.5, marginTop: 4 }}>Building your graph…</div>
            <div style={{ fontSize: 12, color: WK.ink2, marginTop: 4 }}>
              Status: <span style={{ fontFamily: WK.mono }}>extracted</span> → enriched
            </div>
          </div>

          {/* progress bar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ height: 8, border: `1px solid ${WK.ink}`, borderRadius: 100, background: WK.fill0, overflow: 'hidden', display: 'flex' }}>
              <div style={{ width: '66%', background: WK.ink }} />
              <div style={{ width: '11%', background: stripeBg, backgroundColor: WK.fill2 }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>
              <span>6 of 9 stages complete</span><span>~12s remaining</span>
            </div>
          </div>

          {/* stage list */}
          <div style={{ border: `1.2px solid ${WK.ink}`, borderRadius: 4, background: WK.fill0 }}>
            {stages.map((s, i) => (
              <div key={s.k} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 14px',
                borderTop: i === 0 ? 'none' : `1px solid ${WK.weak}`,
              }}>
                <div style={{
                  width: 14, height: 14, borderRadius: 7,
                  border: `1.2px solid ${WK.ink}`,
                  background: s.done ? WK.ink : (s.live ? WK.fill2 : WK.fill0),
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {s.done && <div style={{ color: WK.fill0, fontSize: 9, lineHeight: 1 }}>✓</div>}
                  {s.live && <div style={{ width: 6, height: 6, background: WK.ink, borderRadius: 3 }} />}
                </div>
                <div style={{ fontFamily: WK.mono, fontSize: 11, flex: 1, color: s.done ? WK.ink : WK.ink2 }}>{s.k}</div>
                <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>
                  {s.done ? 'done' : s.live ? 'running…' : 'queued'}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>resume_id · eba00ecc‑36a7‑4f8c…</div>
            <WBtn>Skip to dashboard →</WBtn>
          </div>
        </div>
      </div>
      <WAnno top={300} left={30} width={150}>
        live stage gets a pulse + caret animation
      </WAnno>
    </WFrame>
  );
};

// ── Dashboard (bento) ─────────────────────────────────────────
const A_Dashboard = () => (
  <WFrame url="firstknock.app/profile/01e46dca‑…">
    <WAppBar />
    {/* identity strip */}
    <div style={{
      display: 'flex', alignItems: 'center', gap: 16,
      padding: '18px 24px',
      borderBottom: `1px solid ${WK.ink}`,
      background: WK.fill0,
    }}>
      <div style={{ width: 56, height: 56, borderRadius: 28, border: `1.4px solid ${WK.ink}`, background: WK.fill1, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WK.ui, fontWeight: 600 }}>AD</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontFamily: WK.ui, fontSize: 18, fontWeight: 600 }}>Aswinthraj Devaraj</div>
        <div style={{ fontSize: 11, color: WK.ink2 }}>Full Stack AI Engineer · Tirupur, TamilNadu</div>
        <div style={{ display: 'flex', gap: 6, marginTop: 2 }}>
          <Chip>github ↗</Chip><Chip>linkedin ↗</Chip>
          <Chip dark>seniority: mid</Chip>
          <Chip>18 mo · exp</Chip>
        </div>
      </div>
      <div style={{ flex: 1 }} />
      <WBtn>Export JSON</WBtn>
      <WBtn>Re-ingest</WBtn>
    </div>

    {/* bento */}
    <div style={{ flex: 1, padding: 18, display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gridAutoRows: 'minmax(80px, auto)', gap: 14, overflow: 'hidden' }}>
      {/* GRAPH - hero */}
      <div style={{ gridColumn: 'span 7', gridRow: 'span 4', minHeight: 0 }}>
        <WCard title="Skill Graph" eyebrow="GET /graph" action="zoom · filter · click ⤢ to focus"
          style={{ height: '100%', padding: 0, overflow: 'hidden' }}>
          <div style={{ flex: 1, position: 'relative', background: WK.fill0, minHeight: 0 }}>
            {/* fake graph nodes */}
            <FakeGraph />
            <div style={{ position: 'absolute', top: 10, left: 12, fontFamily: WK.mono, fontSize: 9, color: WK.mute, letterSpacing: 0.6 }}>52 nodes · 137 edges · 4 communities</div>
            <div style={{ position: 'absolute', bottom: 10, left: 12, display: 'flex', gap: 6, flexWrap: 'wrap', maxWidth: 380 }}>
              <Chip>LangGraph + Google ADK</Chip>
              <Chip>React + Next.js</Chip>
              <Chip>Data layer</Chip>
              <Chip dashed>+ 1</Chip>
            </div>
            <div style={{ position: 'absolute', bottom: 10, right: 12, display: 'flex', gap: 4 }}>
              <div style={{ width: 24, height: 24, border: `1px solid ${WK.ink}`, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WK.mono, fontSize: 10 }}>+</div>
              <div style={{ width: 24, height: 24, border: `1px solid ${WK.ink}`, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WK.mono, fontSize: 10 }}>−</div>
              <div style={{ width: 24, height: 24, border: `1px solid ${WK.ink}`, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WK.mono, fontSize: 10 }}>⤢</div>
            </div>
          </div>
        </WCard>
      </div>

      {/* SCORECARD */}
      <div style={{ gridColumn: 'span 5', gridRow: 'span 2', minHeight: 0 }}>
        <WCard eyebrow="GET /profile" title="At a glance" style={{ height: '100%' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, flex: 1, alignContent: 'center' }}>
            <Stat big="mid" small="seniority" />
            <Stat big="18mo" small="experience" />
            <Stat big="47" small="skills · 32 + 15" />
            <Stat big="12" small="github followers" />
          </div>
        </WCard>
      </div>

      {/* TIMELINE */}
      <div style={{ gridColumn: 'span 5', gridRow: 'span 2', minHeight: 0 }}>
        <WCard eyebrow="GET /analytics · career_timeline" title="Timeline" style={{ height: '100%' }}>
          <Timeline />
        </WCard>
      </div>

      {/* SKILLS */}
      <div style={{ gridColumn: 'span 4', gridRow: 'span 3', minHeight: 0 }}>
        <WCard eyebrow="GET /skills" title="Skills" action="32 explicit · 15 inferred" style={{ height: '100%' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1, overflow: 'hidden' }}>
            <WSubhead>By category</WSubhead>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {['Python','JavaScript','SQL','TypeScript'].map(s => <Chip key={s}>{s}</Chip>)}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {['FastAPI','Next.js','React','LangGraph','Google ADK'].map(s => <Chip key={s}>{s}</Chip>)}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {['RAG','Gemini Live','Pinecone'].map(s => <Chip key={s}>{s}</Chip>)}
            </div>
            <Rule />
            <WSubhead>Inferred · with reasons</WSubhead>
            <InferredRow name="WebRTC" reason="needed by Gemini Live for audio" conf="0.85" />
            <InferredRow name="Pydantic" reason="FastAPI is built on it" conf="0.90" />
            <InferredRow name="Agent State Machines" reason="LangGraph's core abstraction" conf="0.90" />
          </div>
        </WCard>
      </div>

      {/* PROJECTS */}
      <div style={{ gridColumn: 'span 4', gridRow: 'span 3', minHeight: 0 }}>
        <WCard eyebrow="GET /resume · projects + github" title="Projects · pinned repos" style={{ height: '100%' }}>
          <Project name="The Mind Surf" stack={['Next.js','Pinecone','FastAPI']} stars="★ 4" lang="TypeScript" isNew={false} />
          <Project name="firstknock" stack={['FastAPI','Memgraph','Neon']} stars="★ 7" lang="Python" isNew />
          <Project name="resume-rag-cli" stack={['LangGraph','Click']} stars="★ 2" lang="Python" />
        </WCard>
      </div>

      {/* BRIDGE / CENTRALITY */}
      <div style={{ gridColumn: 'span 4', gridRow: 'span 3', minHeight: 0 }}>
        <WCard eyebrow="GET /analytics · bridge_skills" title="Bridge skills" action="MAGE centrality" style={{ height: '100%' }}>
          <div style={{ fontSize: 11, color: WK.ink2, marginTop: -4 }}>
            Skills that connect multiple communities — your real superpower.
          </div>
          <Bridge name="FastAPI" cat="framework" v={0.87} />
          <Bridge name="Python" cat="language" v={0.74} />
          <Bridge name="Docker" cat="tool" v={0.42} />
          <Bridge name="TypeScript" cat="language" v={0.38} />
        </WCard>
      </div>
    </div>

    <WAnno top={56} right={18} width={150}>
      identity strip is sticky on scroll
    </WAnno>
  </WFrame>
);

// ── Graph focus (when "expand" is clicked) ────────────────────
const A_GraphFocus = () => (
  <WFrame url="firstknock.app/profile/01e46dca‑…/graph">
    <WAppBar right={<WBtn h={26}>← back to bento</WBtn>} />
    <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 280px', minHeight: 0 }}>
      <div style={{ borderRight: `1px solid ${WK.ink}`, position: 'relative', background: WK.fill0 }}>
        <FakeGraph dense />
        <div style={{ position: 'absolute', top: 14, left: 16, display: 'flex', gap: 6 }}>
          <Chip dark>All</Chip><Chip>Skills</Chip><Chip>Companies</Chip><Chip>Projects</Chip>
        </div>
        <div style={{ position: 'absolute', bottom: 14, left: 16, fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>
          Click a node to inspect →
        </div>
      </div>
      <div style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden' }}>
        <WSubhead action="× close">selected node</WSubhead>
        <div>
          <div style={{ fontFamily: WK.ui, fontSize: 18, fontWeight: 600 }}>LangGraph</div>
          <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute, marginTop: 2 }}>Skill · framework · explicit</div>
        </div>
        <Rule />
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <Chip dark>confidence 1.00</Chip>
          <Chip>community 1</Chip>
        </div>
        <Rule />
        <WSubhead>Co-occurs with</WSubhead>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {[['Google ADK',8],['RAG',7],['FastAPI',6],['Gemini Live',5],['Python',5]].map(([n,c]) => (
            <div key={n} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span>{n}</span><span style={{ fontFamily: WK.mono, color: WK.mute }}>×{c}</span>
            </div>
          ))}
        </div>
        <Rule />
        <WSubhead>Implies (inferred)</WSubhead>
        <div style={{ fontSize: 11, color: WK.ink2 }}>Agent State Machines · 0.90</div>
      </div>
    </div>
  </WFrame>
);

// ── Bento helpers ────────────────────────────────────────────
const Stat = ({ big, small }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
    <div style={{ fontFamily: WK.ui, fontSize: 26, fontWeight: 600, letterSpacing: -0.6, lineHeight: 1 }}>{big}</div>
    <div style={{ fontFamily: WK.mono, fontSize: 9, letterSpacing: 0.8, color: WK.mute, textTransform: 'uppercase' }}>{small}</div>
  </div>
);

const Timeline = () => {
  const entries = [
    { co: 'TechKareer', role: 'SWE Intern', start: 'Jan 26', end: 'now', months: 5, current: true, pos: 0.78 },
    { co: 'Praskla',    role: 'SWE Intern', start: 'Jul 25', end: 'Dec 25', months: 6, current: false, pos: 0.42 },
    { co: 'KSR College',role: 'B.E. CSE',   start: '2022',   end: '2026',   months: 48, current: false, pos: 0.05, edu: true },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1, justifyContent: 'center' }}>
      <div style={{ position: 'relative', height: 38 }}>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 19, height: 1, background: WK.ink }} />
        {entries.map((e, i) => (
          <div key={i} style={{ position: 'absolute', left: `${e.pos * 100}%`, top: 12, transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
            <div style={{ width: 14, height: 14, borderRadius: e.edu ? 2 : 7, border: `1.2px solid ${WK.ink}`, background: e.current ? WK.ink : WK.fill0 }} />
          </div>
        ))}
        <div style={{ position: 'absolute', left: 0, top: 0, fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>2022</div>
        <div style={{ position: 'absolute', right: 0, top: 0, fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>2026</div>
      </div>
      {entries.slice(0, 2).map((e, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', fontSize: 11 }}>
          <div>
            <span style={{ fontWeight: 600 }}>{e.co}</span>
            <span style={{ color: WK.mute }}> · {e.role}</span>
          </div>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>{e.start} → {e.end} · {e.months}mo</div>
        </div>
      ))}
    </div>
  );
};

const InferredRow = ({ name, reason, conf }) => (
  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontFamily: WK.ui, fontSize: 11, fontWeight: 500 }}>{name}</div>
      <div style={{ fontFamily: WK.ui, fontSize: 10, color: WK.mute, lineHeight: 1.3 }}>{reason}</div>
    </div>
    <Chip>{conf}</Chip>
  </div>
);

const Project = ({ name, stack, stars, lang, isNew }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingBlock: 4, borderTop: `1px dashed ${WK.weak}` }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ fontFamily: WK.ui, fontSize: 12, fontWeight: 600 }}>{name}</div>
      <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>{stars} · {lang}</div>
      {isNew && <Chip dark style={{ fontSize: 8, padding: '1px 5px' }}>NEW</Chip>}
    </div>
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
      {stack.map(s => <Chip key={s}>{s}</Chip>)}
    </div>
  </div>
);

const Bridge = ({ name, cat, v }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
    <div style={{ width: 90, fontFamily: WK.ui, fontSize: 11, fontWeight: 500 }}>{name}</div>
    <div style={{ flex: 1, height: 6, background: WK.fill2, border: `1px solid ${WK.ink}`, borderRadius: 100, overflow: 'hidden' }}>
      <div style={{ width: `${v * 100}%`, height: '100%', background: WK.ink }} />
    </div>
    <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute, width: 36, textAlign: 'right' }}>{v.toFixed(2)}</div>
  </div>
);

// Fake graph SVG — used by Direction A & C (B has its own dense variant)
const FakeGraph = ({ dense = false }) => {
  const nodes = dense ? GRAPH_DENSE : GRAPH_LIGHT;
  return (
    <svg viewBox="0 0 600 400" style={{ width: '100%', height: '100%', display: 'block' }}>
      {nodes.edges.map((e, i) => {
        const a = nodes.nodes[e[0]], b = nodes.nodes[e[1]];
        return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={WK.weak} strokeWidth="1" />;
      })}
      {nodes.nodes.map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r={n.r}
            fill={n.k === 'P' ? WK.ink : n.k === 'C' ? WK.fill2 : WK.fill0}
            stroke={WK.ink} strokeWidth={n.k === 'P' ? 1.5 : 1.2}
            strokeDasharray={n.inf ? '2 2' : undefined} />
          {n.label && (
            <text x={n.x + n.r + 4} y={n.y + 3} fontSize="9"
              fontFamily="JetBrains Mono, monospace" fill={WK.ink}>{n.label}</text>
          )}
        </g>
      ))}
    </svg>
  );
};

// Tiny inline "graph" geometry
const GRAPH_LIGHT = {
  nodes: [
    { x: 300, y: 200, r: 14, k: 'P', label: 'You' },
    { x: 180, y: 110, r: 9,  k: 'S', label: 'LangGraph' },
    { x: 220, y: 70,  r: 8,  k: 'S', label: 'Google ADK' },
    { x: 130, y: 170, r: 7,  k: 'S', label: 'RAG' },
    { x: 90,  y: 240, r: 6,  k: 'S', inf: true, label: 'WebRTC' },
    { x: 160, y: 280, r: 7,  k: 'S', label: 'Gemini Live' },
    { x: 430, y: 110, r: 9,  k: 'S', label: 'Next.js' },
    { x: 470, y: 170, r: 8,  k: 'S', label: 'React' },
    { x: 510, y: 240, r: 7,  k: 'S', label: 'TypeScript' },
    { x: 430, y: 300, r: 6,  k: 'S', inf: true, label: 'Tailwind' },
    { x: 300, y: 70,  r: 8,  k: 'C', label: 'TechKareer' },
    { x: 300, y: 340, r: 7,  k: 'C', label: 'Praskla' },
    { x: 80,  y: 130, r: 6,  k: 'S', label: 'Python' },
    { x: 530, y: 110, r: 6,  k: 'S', label: 'Pinecone' },
  ],
  edges: [
    [0,1],[0,2],[0,3],[0,4],[0,5],[0,6],[0,7],[0,8],[0,9],[0,10],[0,11],[0,12],[0,13],
    [1,2],[1,3],[1,5],[2,3],[3,4],[3,5],[4,5],[6,7],[7,8],[7,9],[6,13],[12,3],
    [10,1],[11,7],
  ],
};
const GRAPH_DENSE = {
  nodes: [...GRAPH_LIGHT.nodes,
    { x: 200, y: 320, r: 5, k: 'S', inf: true, label: 'Pydantic' },
    { x: 380, y: 350, r: 5, k: 'S', label: 'Docker' },
    { x: 380, y: 60,  r: 5, k: 'S', label: 'Vercel' },
    { x: 80,  y: 320, r: 5, k: 'S', label: 'Celery' },
  ],
  edges: [...GRAPH_LIGHT.edges, [0,14],[0,15],[0,16],[0,17],[14,3],[15,7],[16,6],[17,1]],
};

Object.assign(window, { A_Upload, A_Processing, A_Dashboard, A_GraphFocus, FakeGraph });
