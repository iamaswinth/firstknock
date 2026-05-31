// Direction B — Graph as canvas. Full-bleed force graph; everything else is
// a floating glass panel overlaid on it. Feels like a map / IDE.

// ── Upload (B) ────────────────────────────────────────────────
const B_Upload = () => (
  <WFrame url="firstknock.app/">
    {/* B leans into the dark canvas vibe even on upload — a faint graph
        skeleton in the background hints at what's coming */}
    <div style={{ position: 'absolute', inset: 0, opacity: 0.25, pointerEvents: 'none' }}>
      <FakeGraph dense />
    </div>
    <div style={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <WAppBar />
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <div style={{
          width: 460, padding: 28,
          background: WK.fill0,
          border: `1.4px solid ${WK.ink}`,
          borderRadius: 4,
          boxShadow: '0 14px 40px rgba(0,0,0,0.08)',
          display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          <div>
            <div style={{ fontFamily: WK.mono, fontSize: 10, letterSpacing: 1.6, color: WK.mute, textTransform: 'uppercase' }}>Resume → Graph</div>
            <div style={{ fontFamily: WK.ui, fontSize: 22, fontWeight: 600, letterSpacing: -0.4, marginTop: 6 }}>
              Turn your resume into a map.
            </div>
          </div>

          <div style={{
            height: 160,
            border: `1.4px dashed ${WK.ink}`,
            borderRadius: 4,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: WK.fill1,
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div style={{ display: 'flex', gap: 4 }}>
                {[0,1,2].map(i => (
                  <div key={i} style={{ width: 10, height: 10, borderRadius: 5, border: `1.2px solid ${WK.ink}`, background: i === 1 ? WK.ink : WK.fill0 }} />
                ))}
              </div>
              <div style={{ fontFamily: WK.ui, fontSize: 12, fontWeight: 500 }}>Drop PDF/DOCX</div>
              <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>or paste a link · or browse</div>
            </div>
          </div>

          <div style={{
            display: 'flex', gap: 8, alignItems: 'center',
            border: `1.2px solid ${WK.ink}`, borderRadius: 3,
            padding: '0 12px', height: 36,
          }}>
            <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>@</div>
            <div style={{ flex: 1, fontFamily: WK.mono, fontSize: 11 }}>iamaswinth@gmail.com</div>
          </div>

          <WBtn primary h={40}>Build my graph</WBtn>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute, textAlign: 'center' }}>
            ~20s · we extract, enrich with GitHub, infer hidden skills
          </div>
        </div>
      </div>
    </div>
    <WAnno top={120} left={20} width={150}>
      teaser graph in BG · animated, low opacity
    </WAnno>
  </WFrame>
);

// ── Processing (B) ────────────────────────────────────────────
const B_Processing = () => (
  <WFrame url="firstknock.app/build">
    <WAppBar right={<div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>polling · 3s</div>} />
    <div style={{ flex: 1, position: 'relative', background: WK.fill1 }}>
      {/* Background: graph being assembled live */}
      <div style={{ position: 'absolute', inset: 0 }}>
        <FakeGraph dense />
      </div>
      {/* Centered HUD strip */}
      <div style={{ position: 'absolute', left: '50%', bottom: 30, transform: 'translateX(-50%)', width: 600 }}>
        <div style={{
          background: WK.fill0, border: `1.4px solid ${WK.ink}`, borderRadius: 4,
          padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
          boxShadow: '0 14px 40px rgba(0,0,0,0.10)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontFamily: WK.ui, fontSize: 15, fontWeight: 600 }}>Assembling your graph</div>
            <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>6 / 9 · ~12s</div>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} style={{
                flex: 1, height: 8,
                border: `1px solid ${WK.ink}`,
                background: i < 6 ? WK.ink : i === 6 ? stripeBg : WK.fill0,
                backgroundColor: i === 6 ? WK.fill2 : undefined,
                borderRadius: 2,
              }} />
            ))}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>
            <span>parse · normalize · extract · resolve · persist · graph</span>
            <span style={{ color: WK.ink }}>→ enrichment…</span>
          </div>
        </div>
      </div>
      {/* Live discovery feed top-right */}
      <div style={{
        position: 'absolute', top: 16, right: 16, width: 220,
        background: WK.fill0, border: `1.2px solid ${WK.ink}`, borderRadius: 4,
        padding: 12, display: 'flex', flexDirection: 'column', gap: 8,
        fontFamily: WK.mono, fontSize: 10,
      }}>
        <WSubhead>Live · just found</WSubhead>
        {[
          ['+ company', 'TechKareer · seed'],
          ['+ skill',   'LangGraph'],
          ['+ skill',   'Gemini Live API'],
          ['+ infer',   'WebRTC ← Gemini'],
          ['+ repo',    'the-mind-surf · ★4'],
        ].map(([k, v], i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, color: WK.ink2 }}>
            <span style={{ color: WK.mute }}>{k}</span><span style={{ color: WK.ink, textAlign: 'right' }}>{v}</span>
          </div>
        ))}
      </div>
      {/* Identity stub top-left */}
      <div style={{
        position: 'absolute', top: 16, left: 16,
        background: WK.fill0, border: `1.2px solid ${WK.ink}`, borderRadius: 4,
        padding: 10, display: 'flex', gap: 10, alignItems: 'center',
      }}>
        <div style={{ width: 38, height: 38, borderRadius: 19, border: `1.2px solid ${WK.ink}`, background: stripeBg }} />
        <div>
          <div style={{ fontFamily: WK.ui, fontSize: 12, fontWeight: 600 }}>Aswinthraj Devaraj</div>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>tirupur · status: extracted</div>
        </div>
      </div>
    </div>
    <WAnno top={140} left={32} width={170}>
      nodes pop in as enrichment finishes — graph builds in front of the user
    </WAnno>
  </WFrame>
);

// ── Dashboard (B) — graph fullscreen with floating panels ─────
const B_Dashboard = () => (
  <WFrame url="firstknock.app/profile/01e46dca‑…">
    <WAppBar />
    <div style={{ flex: 1, position: 'relative', background: WK.fill1 }}>
      {/* base graph */}
      <div style={{ position: 'absolute', inset: 0 }}>
        <FakeGraph dense />
      </div>

      {/* top-left: identity card */}
      <Floating top={16} left={16} w={280}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ width: 44, height: 44, borderRadius: 22, border: `1.4px solid ${WK.ink}`, background: WK.fill1, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WK.ui, fontWeight: 600, fontSize: 13 }}>AD</div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: WK.ui, fontSize: 14, fontWeight: 600 }}>Aswinthraj Devaraj</div>
            <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>Full Stack AI Engineer</div>
          </div>
        </div>
        <Rule style={{ marginBlock: 10 }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
          <Mini big="mid" small="senior." />
          <Mini big="18mo" small="exp." />
          <Mini big="47" small="skills" />
        </div>
      </Floating>

      {/* top-right: legend / filters */}
      <Floating top={16} right={16} w={220}>
        <WSubhead>Legend</WSubhead>
        <LegendRow shape="dot-fill" label="you" />
        <LegendRow shape="ring" label="explicit skill" />
        <LegendRow shape="ring-dash" label="inferred skill" />
        <LegendRow shape="square" label="company" />
        <LegendRow shape="rounded" label="project" />
        <Rule style={{ marginBlock: 6 }} />
        <WSubhead>Communities</WSubhead>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontFamily: WK.mono, fontSize: 10 }}>
          <CommLine n="LangGraph + Google ADK" count={6} on />
          <CommLine n="React + Next.js" count={5} on />
          <CommLine n="Data layer" count={4} />
          <CommLine n="DevOps" count={3} />
        </div>
        <Rule style={{ marginBlock: 6 }} />
        <div style={{ display: 'flex', gap: 4 }}>
          <Chip dark>All</Chip><Chip>Explicit</Chip><Chip>Inferred</Chip>
        </div>
      </Floating>

      {/* bottom-left: timeline strip */}
      <Floating bottom={16} left={16} w={400}>
        <WSubhead action="GET /analytics">Career timeline</WSubhead>
        <Timeline />
      </Floating>

      {/* bottom-right: selected node detail */}
      <Floating bottom={16} right={16} w={280}>
        <WSubhead action="× deselect">Selected · skill</WSubhead>
        <div>
          <div style={{ fontFamily: WK.ui, fontSize: 15, fontWeight: 600 }}>LangGraph</div>
          <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>framework · explicit · 1.00</div>
        </div>
        <Rule />
        <div style={{ fontSize: 11, color: WK.ink2, lineHeight: 1.4 }}>
          Co-occurs with Google ADK (×8), RAG (×7), FastAPI (×6).
        </div>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          <Chip>Google ADK</Chip><Chip>RAG</Chip><Chip>FastAPI</Chip><Chip>Gemini Live</Chip>
        </div>
        <Rule />
        <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute, textTransform: 'uppercase', letterSpacing: 1 }}>Implies</div>
        <div style={{ fontSize: 11 }}>Agent State Machines · <span style={{ color: WK.mute }}>0.90</span></div>
      </Floating>

      {/* zoom widget bottom-center */}
      <div style={{
        position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)',
        background: WK.fill0, border: `1.2px solid ${WK.ink}`, borderRadius: 100,
        padding: '4px 6px', display: 'flex', gap: 2, alignItems: 'center',
      }}>
        {['−','100%','+','·','fit','center'].map((t, i) => (
          <div key={i} style={{ padding: '4px 10px', fontFamily: WK.mono, fontSize: 10, borderRight: i < 5 ? `1px solid ${WK.weak}` : 'none' }}>{t}</div>
        ))}
      </div>

      <WAnno top={80} right={250} width={130}>
        panels are draggable, collapsible
      </WAnno>
    </div>
  </WFrame>
);

// ── Node selected · richer side panel state ───────────────────
const B_NodeFocus = () => (
  <WFrame url="firstknock.app/profile/01e46dca‑…?node=skill-WebRTC">
    <WAppBar />
    <div style={{ flex: 1, position: 'relative', background: WK.fill1 }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.35 }}>
        <FakeGraph dense />
      </div>
      {/* highlighted node ring */}
      <div style={{
        position: 'absolute', top: 220, left: 110,
        width: 56, height: 56, borderRadius: 28,
        border: `1.5px solid ${WK.ink}`,
        boxShadow: `0 0 0 6px rgba(0,0,0,0.06), 0 0 0 12px rgba(0,0,0,0.04)`,
      }} />

      <Floating top={16} left={16} w={280}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 18, border: `1.2px solid ${WK.ink}`, background: WK.fill1 }} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: WK.ui, fontSize: 13, fontWeight: 600 }}>Aswinthraj Devaraj</div>
            <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>mid · 18 mo</div>
          </div>
        </div>
      </Floating>

      <Floating top={16} right={16} w={340} style={{ gap: 14 }}>
        <WSubhead action="× close">Selected · inferred skill</WSubhead>
        <div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <div style={{ fontFamily: WK.ui, fontSize: 22, fontWeight: 600, letterSpacing: -0.4 }}>WebRTC</div>
            <Chip dashed>inferred</Chip>
          </div>
          <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute, marginTop: 2 }}>tool · llm-inferred</div>
        </div>
        <Rule />
        <WSubhead>Why it's here</WSubhead>
        <div style={{ fontSize: 12, color: WK.ink2, lineHeight: 1.5, paddingLeft: 8, borderLeft: `2px solid ${WK.ink}` }}>
          “Gemini Live API requires WebRTC for real-time audio streaming.”
        </div>
        <div style={{ display: 'flex', gap: 14, fontFamily: WK.mono, fontSize: 10 }}>
          <div><span style={{ color: WK.mute }}>conf </span><span style={{ fontWeight: 600 }}>0.85</span></div>
          <div><span style={{ color: WK.mute }}>by </span><span>llm</span></div>
        </div>
        <Rule />
        <WSubhead>Reached via</WSubhead>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, flexWrap: 'wrap' }}>
          <Chip dark>you</Chip>→<Chip>Gemini Live</Chip>→<Chip dashed>WebRTC</Chip>
        </div>
        <Rule />
        <WSubhead>Neighbours</WSubhead>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {['Gemini Live','RAG','LangGraph'].map(s => <Chip key={s}>{s}</Chip>)}
        </div>
        <Rule />
        <div style={{ display: 'flex', gap: 6 }}>
          <WBtn>Pin to dashboard</WBtn>
          <WBtn>Mark as not mine</WBtn>
        </div>
      </Floating>

      <Floating bottom={16} left={16} w={440}>
        <WSubhead>Bridge skills · centrality</WSubhead>
        <Bridge name="FastAPI" cat="framework" v={0.87} />
        <Bridge name="Python" cat="language" v={0.74} />
        <Bridge name="Docker" cat="tool" v={0.42} />
      </Floating>

      <div style={{
        position: 'absolute', bottom: 16, right: 16,
        fontFamily: WK.mono, fontSize: 9, color: WK.mute,
        background: WK.fill0, border: `1px solid ${WK.weak}`, borderRadius: 3,
        padding: '4px 8px',
      }}>↑↓←→ navigate · esc deselect</div>
    </div>
  </WFrame>
);

// ── B helpers ─────────────────────────────────────────────────
const Floating = ({ top, left, right, bottom, w, children, style = {} }) => (
  <div style={{
    position: 'absolute', top, left, right, bottom, width: w,
    background: WK.fill0,
    border: `1.2px solid ${WK.ink}`,
    borderRadius: 4,
    padding: 14,
    display: 'flex', flexDirection: 'column', gap: 10,
    boxShadow: '0 10px 30px rgba(0,0,0,0.08)',
    ...style,
  }}>{children}</div>
);

const Mini = ({ big, small }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
    <div style={{ fontFamily: WK.ui, fontSize: 16, fontWeight: 600, lineHeight: 1 }}>{big}</div>
    <div style={{ fontFamily: WK.mono, fontSize: 8, color: WK.mute, textTransform: 'uppercase', letterSpacing: 0.8 }}>{small}</div>
  </div>
);

const LegendRow = ({ shape, label }) => {
  const size = 12;
  const node = (() => {
    switch (shape) {
      case 'dot-fill':   return <div style={{ width: size, height: size, borderRadius: size, background: WK.ink, border: `1px solid ${WK.ink}` }} />;
      case 'ring':       return <div style={{ width: size, height: size, borderRadius: size, background: WK.fill0, border: `1.2px solid ${WK.ink}` }} />;
      case 'ring-dash':  return <div style={{ width: size, height: size, borderRadius: size, background: WK.fill0, border: `1.2px dashed ${WK.ink}` }} />;
      case 'square':     return <div style={{ width: size, height: size, background: WK.fill2, border: `1.2px solid ${WK.ink}` }} />;
      case 'rounded':    return <div style={{ width: size, height: size, background: WK.fill0, border: `1.2px solid ${WK.ink}`, borderRadius: 3 }} />;
      default: return null;
    }
  })();
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: WK.mono, fontSize: 10, color: WK.ink2 }}>
      <div style={{ width: 16, display: 'flex', justifyContent: 'center' }}>{node}</div>
      {label}
    </div>
  );
};

const CommLine = ({ n, count, on }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
    <div style={{ width: 10, height: 10, border: `1.2px solid ${WK.ink}`, background: on ? WK.ink : WK.fill0, borderRadius: 2 }} />
    <span style={{ flex: 1 }}>{n}</span>
    <span style={{ color: WK.mute }}>{count}</span>
  </div>
);

Object.assign(window, { B_Upload, B_Processing, B_Dashboard, B_NodeFocus });
