// FirstKnock — "Zentra"-style overview. Renders the whole dashboard.
// Reuses SkillGraph + NodeDrawer (from dashboard-graph.jsx) and window.DATA.

const { useState: useStateO, useMemo: useMemoO } = React;

// ── Icons ──────────────────────────────────────────────────────────────
const I = {
  search:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/><path d="m20 20-3-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>,
  bell:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/><path d="M10 20a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>,
  link:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M10 13a4 4 0 0 0 5.66 0l2-2a4 4 0 1 0-5.66-5.66l-1 1M14 11a4 4 0 0 0-5.66 0l-2 2A4 4 0 1 0 6 18.66l1-1" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  cal:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><rect x="4" y="5" width="16" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.7"/><path d="M4 9h16M9 3v4M15 3v4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>,
  chev:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="m7 10 5 5 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  plus:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"/></svg>,
  refresh:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M20 11a8 8 0 1 0-.5 3.5M20 5v6h-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  download:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 4v11m0 0 4-4m-4 4-4-4M5 19h14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  dots:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="6" cy="12" r="1.6" fill="currentColor"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/><circle cx="18" cy="12" r="1.6" fill="currentColor"/></svg>,
  spark:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 3l1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z" fill="currentColor"/></svg>,
  up:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M5 15l7-7 7 7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  check:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M5 12.5 10 17l9-10" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  star:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 4l2.3 5 5.4.5-4.1 3.6 1.2 5.3L12 21l-4.8 2.5 1.2-5.3L4.3 9.5 9.7 9 12 4Z" fill="currentColor"/></svg>,
  repo:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M6 4h11a2 2 0 0 1 2 2v13H7a2 2 0 0 1-2-2V4Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/><path d="M7 17h12M9 8h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>,
  arrow:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M5 12h13m0 0-5-5m5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  hex:(p)=><svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 3.5l7 4v9l-7 4-7-4v-9l7-4Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/></svg>,
};

// ── Top nav ─────────────────────────────────────────────────────────────
function Nav() {
  const links = ['Overview', 'Skills', 'Graph', 'Projects', 'Timeline', 'Documents'];
  const hrefs = { Overview: '#top', Skills: '#skills', Graph: '#graph', Projects: '#projects', Timeline: '#timeline', Documents: 'FirstKnock Upload.html' };
  return (
    <nav className="nav">
      <div className="nav-brand">
        <div className="nav-mark">{I.hex({ width: 17, height: 17 })}</div>
        <div className="nav-name">FirstKnock</div>
      </div>
      <div className="nav-links">
        {links.map((l, i) => (
          <a key={l} href={hrefs[l]} className={'nav-link' + (i === 0 ? ' is-active' : '')}>{l}</a>
        ))}
      </div>
      <div className="nav-right">
        <button className="nav-circle">{I.search({ width: 18, height: 18 })}</button>
        <button className="nav-circle">{I.bell({ width: 18, height: 18 })}<span className="ping" /></button>
        <div className="nav-avatar"><span>AD</span></div>
      </div>
    </nav>
  );
}

// ── Title bar ───────────────────────────────────────────────────────────
function TitleBar() {
  return (
    <div className="titlebar" id="top">
      <div className="title">
        <h1>Overview</h1>
        <button className="title-link">{I.link({ width: 15, height: 15 })}</button>
      </div>
      <div className="title-spacer" />
      <button className="tb-pill">{I.cal()}<span>Synced · May 29</span></button>
      <span className="tb-muted">from</span>
      <button className="tb-pill">{I.refresh()}<span>resume.pdf</span>{I.chev({ width: 14, height: 14 })}</button>
      <button className="tb-pill">{I.download()}<span>Export JSON</span></button>
      <button className="tb-pill tb-add">{I.plus({ width: 15, height: 15 })}<span>Add widget</span></button>
    </div>
  );
}

// ── Card shell ──────────────────────────────────────────────────────────
function Card({ title, sub, right, children, className = '', id, style }) {
  return (
    <section className={'card ' + className} id={id} style={style}>
      {(title || right) && (
        <div className="card-head">
          {title && <div><div className="card-title">{title}</div>{sub && <div className="card-sub">{sub}</div>}</div>}
          <div className="card-spacer" />
          {right}
          <button className="card-menu">{I.dots({ width: 18, height: 18 })}</button>
        </div>
      )}
      {children}
    </section>
  );
}

// ── Skill composition (Gross-Volume analog) ─────────────────────────────
function CompositionCard() {
  const { SKILLS } = window.DATA;
  const explicit = SKILLS.filter(s => s.source === 'explicit').length;
  const inferred = SKILLS.filter(s => s.source === 'inferred').length;
  const total = SKILLS.length;
  const cats = [
    { label: 'Frameworks', n: SKILLS.filter(s => s.category === 'framework').length, cls: 'green' },
    { label: 'Languages',  n: SKILLS.filter(s => s.category === 'language').length,  cls: 'blue' },
    { label: 'Tools & infra', n: SKILLS.filter(s => s.category === 'tool').length,   cls: 'pink' },
  ];
  const max = Math.max(...cats.map(c => c.n));
  return (
    <Card title="Skill Composition">
      <div className="card-body" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="score-row">
          <div className="score-num">{total}</div>
          <span className="delta up">{I.up()} {inferred} inferred</span>
        </div>
        <div className="card-sub" style={{ marginTop: 6 }}>{explicit} explicit · {inferred} inferred across 4 communities</div>
        <div className="breakdown">
          {cats.map(c => (
            <div className="bd-row" key={c.label}>
              <div className="bd-top">
                <span className="bd-label">{c.label}</span>
                <span className="bd-val">{c.n}</span>
              </div>
              <div className="bd-bar"><div className={'bd-fill ' + c.cls} style={{ width: (38 + (c.n / max) * 62) + '%' }} /></div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ── Insights gradient (bridge superpower) ───────────────────────────────
function InsightCard() {
  return (
    <Card className="insight">
      <div className="card-body">
        <div className="insight-tag">{I.spark({ width: 13, height: 13 })} Insight</div>
        <div className="insight-num">87%</div>
        <div className="insight-head">FastAPI is your strongest bridge skill.</div>
        <div className="insight-body">
          It links 3 of your 4 skill communities — Agent stack, Data layer and DevOps.
          Lead with it: it's the spine of how your work connects.
        </div>
      </div>
    </Card>
  );
}

// ── Dot-matrix metric ───────────────────────────────────────────────────
function DotMatrix({ peakCol, color }) {
  const cols = [2, 3, 4, 3, 5, 6, 8, 6, 4, 3, 4, 3, 2];
  const max = 8;
  return (
    <div className="dotmatrix">
      {cols.map((h, i) => (
        <div className="dm-col" key={i}>
          {Array.from({ length: max }).map((_, r) => (
            <span key={r} className={'dm-dot' + (r < h ? (i === peakCol ? ` on-${color}` : ` on-${color}`) : '')}
              style={r >= h ? undefined : (i === peakCol ? undefined : { opacity: 0.45 })} />
          ))}
        </div>
      ))}
    </div>
  );
}

function MetricCard({ title, value, peakLabel, peak, delta, color, sub }) {
  return (
    <Card title={title}>
      <div className="card-body">
        <div className="metric-row">
          <div className="metric-num">{value}</div>
          <div className="metric-mid">
            <span className="tag">{peakLabel} <b>{peak}</b></span>
            <DotMatrix peakCol={6} color={color} />
          </div>
          <div className="metric-right">
            <div className="metric-vs">{sub}</div>
            <div className={'metric-delta ' + color}>{delta}</div>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ── Activity step chart (Retention analog) ──────────────────────────────
function ActivityCard() {
  const data = [22, 30, 26, 41, 38, 52, 60, 48, 55, 44, 36, 30];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const W = 380, H = 150, pad = 6;
  const max = 70;
  const stepW = (W - pad * 2) / data.length;
  let d = `M ${pad} ${H - (data[0] / max) * (H - 20)}`;
  data.forEach((v, i) => {
    const x0 = pad + i * stepW, x1 = pad + (i + 1) * stepW;
    const y = H - (v / max) * (H - 20);
    d += ` L ${x0} ${y} L ${x1} ${y}`;
  });
  const peakIdx = data.indexOf(Math.max(...data));
  const peakX = pad + (peakIdx + 0.5) * stepW;
  const peakY = H - (data[peakIdx] / max) * (H - 20);
  return (
    <Card title="Commit Activity" sub="public GitHub events">
      <div className="card-body">
        <div className="chart-wrap">
          <div className="chart-bubble">Peak · 60</div>
          <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" preserveAspectRatio="none">
            <defs>
              <pattern id="vstripe" width="4" height="8" patternUnits="userSpaceOnUse">
                <rect width="4" height="8" fill="var(--pink-soft)" />
                <rect width="1.4" height="8" fill="var(--pink-bg)" />
              </pattern>
            </defs>
            <path d={`${d} L ${W - pad} ${H} L ${pad} ${H} Z`} fill="url(#vstripe)" stroke="none" />
            <path d={d} fill="none" stroke="var(--pink)" strokeWidth="2.4" strokeLinejoin="round" />
            <circle cx={peakX} cy={peakY} r="3.6" fill="var(--pink)" />
          </svg>
        </div>
        <div className="chart-axis">{months.map(m => <span key={m}>{m}</span>)}</div>
      </div>
    </Card>
  );
}

// ── Bridge skills ───────────────────────────────────────────────────────
function BridgeCard() {
  const { BRIDGES } = window.DATA;
  return (
    <Card title="Bridge Skills" sub="MAGE betweenness centrality" id="skills">
      <div className="card-body">
        <div className="list">
          {BRIDGES.map((b, i) => (
            <div className="bridge" key={b.name}>
              <div className="bridge-rank">{i + 1}</div>
              <div className="bridge-body">
                <div className="bridge-line">
                  <span className="bridge-name">{b.name}</span>
                  <span className="bridge-cat">{b.category}</span>
                  <span className="bridge-cent">{b.centrality.toFixed(2)}</span>
                </div>
                <div className="bridge-bar"><div className="bridge-fill" style={{ width: (b.centrality * 100) + '%' }} /></div>
                <div className="bridge-note">{b.note}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ── Inferred skills with reasoning ──────────────────────────────────────
function InferredCard() {
  const inferred = window.DATA.SKILLS.filter(s => s.source === 'inferred')
    .sort((a, b) => b.confidence - a.confidence);
  return (
    <Card title="Inferred Skills" sub="not on the résumé — derived from context">
      <div className="card-body" style={{ paddingTop: 4 }}>
        <div className="list">
          {inferred.map(s => {
            const high = s.confidence >= 0.85;
            return (
              <div className="note" key={s.name}>
                <div className={'note-check' + (high ? ' high' : '')}>{high && I.check()}</div>
                <div className="note-body">
                  <div className="note-top">
                    <span className="note-name">{s.name}</span>
                    <span className={'note-conf' + (high ? ' high' : '')}>{Math.round(s.confidence * 100)}%</span>
                  </div>
                  <div className="note-reason">{s.reason}</div>
                  <div className="note-chain">
                    <span className="note-via">via</span>
                    {(s.via || []).map((v, i) => (
                      <React.Fragment key={v}>
                        {i > 0 && <span className="note-arrow">·</span>}
                        <span className="chip">{v}</span>
                      </React.Fragment>
                    ))}
                    <span className="note-arrow">{I.arrow({ width: 15, height: 15 })}</span>
                    <span className="chip dashed">{s.name}</span>
                    <span className="note-method" style={{ marginLeft: 'auto' }}>{s.inferred_by}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

// ── Projects / repos ────────────────────────────────────────────────────
const LANG_COLOR = { TypeScript: '#2f6af0', Python: '#14a05a', JavaScript: '#e6b400' };
function ProjectsCard() {
  const { PROJECTS } = window.DATA;
  return (
    <Card title="Pinned Repositories" sub={`${PROJECTS.length} from github.com/iamaswinth`} id="projects">
      <div className="card-body" style={{ paddingTop: 4 }}>
        <div className="list">
          {PROJECTS.map(p => (
            <div className="li" key={p.name}>
              <div className="li-top">
                <div className="li-ico">{I.repo()}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="li-name">{p.name}</span>
                    {p.is_new && <span className="pill pill-green">New</span>}
                  </div>
                </div>
                <span className="li-meta"><span className="lang-dot" style={{ background: LANG_COLOR[p.language] || '#999' }} />{p.language}</span>
                <span className="li-meta">{I.star({ width: 13, height: 13 })}{p.stars}</span>
              </div>
              <p className="li-sum">{p.summary}</p>
              <div className="chip-row">{p.stack.map(s => <span className="chip" key={s}>{s}</span>)}</div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ── Timeline ────────────────────────────────────────────────────────────
const TL_COLORS = ['#2f6af0', '#e6457f', '#14a05a'];
function TimelineCard() {
  const { TIMELINE, EDUCATION } = window.DATA;
  const fmt = (s) => { if (!s) return 'Present'; const [y, m] = s.split('-'); return m ? `${['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][+m]} ${y}` : y; };
  return (
    <Card title="Career Timeline" sub="18 months · 2 roles" id="timeline">
      <div className="card-body" style={{ paddingTop: 4 }}>
        <div className="tl">
          {TIMELINE.map((t, i) => (
            <div className="tl-item" key={t.company}>
              <div className="tl-bar" style={{ background: TL_COLORS[i] }} />
              <div className="tl-body">
                <div className="tl-top">
                  <span className="tl-co">{t.company}</span>
                  {t.is_current && <span className="pill pill-green">Current</span>}
                </div>
                <div className="tl-role">{t.title}</div>
                <div className="tl-meta">
                  <span className="fk-mono">{fmt(t.start)} → {fmt(t.end)}</span>
                  <span className="sep">•</span><span>{t.months}mo</span>
                  <span className="sep">•</span><span>{t.stage} · {t.industry}</span>
                </div>
                <div className="tl-stack">{t.stack.map(s => <span className="chip" key={s}>{s}</span>)}</div>
              </div>
            </div>
          ))}
          {EDUCATION.map((e) => (
            <div className="tl-item" key={e.institution}>
              <div className="tl-bar" style={{ background: '#a7aab1' }} />
              <div className="tl-body">
                <div className="tl-top"><span className="tl-co">{e.degree} · {e.field}</span></div>
                <div className="tl-role">{e.institution}</div>
                <div className="tl-meta"><span className="fk-mono">{e.start} → {e.end}</span></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ── Graph card (hero) ───────────────────────────────────────────────────
function GraphCard() {
  const [selected, setSelected] = useStateO(null);
  return (
    <Card title="Skill Graph" sub="hover to trace · click a node for detail" id="graph"
      className="" style={{ minHeight: 560 }}>
      <div className="graph-stage">
        <SkillGraph accent="#14161b" onSelectNode={setSelected} />
        {selected && <NodeDrawer node={selected} onClose={() => setSelected(null)} accent="#14161b" />}
      </div>
      <div className="graph-prompt">
        {I.spark({ width: 16, height: 16, className: 'spark' })}
        <span>Ask the graph — “what connects my agent work to my data skills?”</span>
      </div>
    </Card>
  );
}

// ── App ─────────────────────────────────────────────────────────────────
function OverviewApp() {
  return (
    <div className="ov-app">
      <Nav />
      <TitleBar />
      <div className="bento">
        <div className="col-8" style={{ display: 'flex' }}><GraphCard /></div>
        <div className="col-4" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <CompositionCard />
          <div style={{ flex: 1, display: 'flex' }}><InsightCard /></div>
        </div>

        <div className="col-4" style={{ display: 'flex' }}><BridgeCard /></div>
        <div className="col-4" style={{ display: 'flex' }}><InferredCard /></div>
        <div className="col-4" style={{ display: 'flex' }}><ActivityCard /></div>

        <div className="col-7" style={{ display: 'flex' }}><ProjectsCard /></div>
        <div className="col-5" style={{ display: 'flex' }}><TimelineCard /></div>

        <div className="col-6" style={{ display: 'flex' }}>
          <MetricCard title="Skills Mapped" value="23" peakLabel="Top" peak="Agent stack"
            delta="+8 inferred" color="green" sub="across communities" />
        </div>
        <div className="col-6" style={{ display: 'flex' }}>
          <MetricCard title="GitHub Reach" value="18" peakLabel="Peak" peak="firstknock"
            delta="12 followers" color="blue" sub="public repos" />
        </div>
      </div>
      <div className="foot">
        <span>FirstKnock · resume → knowledge graph</span>
        <span style={{ marginLeft: 'auto' }}>user_id 01e46dca · {window.DATA.SKILLS.length} skills · {window.DATA.EDGES.length} edges</span>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<OverviewApp />);
