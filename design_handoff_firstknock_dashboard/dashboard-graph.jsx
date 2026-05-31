// Interactive force-graph-style visualisation for the FirstKnock dashboard.
// Pre-positioned cluster layout (community → quadrant). Hover dims non-
// neighbours; click selects for the side drawer; filter chips hide types
// or sources. SVG-based — no external graph library.

const { useState, useMemo, useRef, useEffect } = React;

// ── Layout: deterministic cluster placement keyed by community ────────
function buildLayout() {
  const { SKILLS, COMMUNITIES, TIMELINE, PROJECTS, EDUCATION, EDGES } = window.DATA;
  const W = 1000, H = 640;
  const cx = W / 2, cy = H / 2;

  const nodes = {};

  // YOU at center
  nodes['YOU'] = { id: 'YOU', label: 'YOU', kind: 'person', x: cx, y: cy, r: 18 };

  // Communities arranged on a ring around YOU.
  // Each gets a center point; skills are scattered around it.
  const commCenters = {
    1: { x: 260, y: 175, label: 'Agent stack',     spread: 110 },
    2: { x: 740, y: 175, label: 'Web · React',     spread: 110 },
    3: { x: 760, y: 480, label: 'Data layer',      spread: 95  },
    4: { x: 220, y: 480, label: 'Backend · DevOps', spread: 105 },
  };

  // Hash-based pseudo-random for deterministic but jittered placement.
  const hash = (s) => { let h = 0; for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0; return h; };
  const rand = (seed) => ((Math.abs(hash(seed)) % 1000) / 1000);

  // Place skills in their community cluster
  SKILLS.forEach((s, i) => {
    const c = commCenters[s.community];
    if (!c) return;
    // Polar coords inside the cluster
    const angle = rand(s.name) * Math.PI * 2;
    const dist = (0.4 + rand(s.name + 'r') * 0.6) * c.spread;
    const x = c.x + Math.cos(angle) * dist;
    const y = c.y + Math.sin(angle) * dist * 0.85;
    nodes[s.name] = {
      id: s.name, label: s.name, kind: 'skill',
      source: s.source, community: s.community,
      confidence: s.confidence, category: s.category,
      x, y, r: s.source === 'explicit' ? 7 : 5.5,
    };
  });

  // Companies along the top-center
  const companyX = [400, 600];
  TIMELINE.forEach((t, i) => {
    nodes['co:' + t.company] = {
      id: 'co:' + t.company, label: t.company, kind: 'company',
      x: companyX[i] || cx, y: 70 + i * 20, r: 9,
      data: t,
    };
  });

  // Projects on the bottom-center
  const projX = [310, 450, 590, 730];
  PROJECTS.forEach((p, i) => {
    nodes['proj:' + p.name] = {
      id: 'proj:' + p.name, label: p.name, kind: 'project',
      x: projX[i] || cx, y: 605 - (i % 2) * 10, r: 8,
      data: p,
    };
  });

  // Education far-left
  EDUCATION.forEach((e, i) => {
    nodes['edu:KSR'] = {
      id: 'edu:KSR', label: 'KSR College', kind: 'institution',
      x: 70, y: 320, r: 7, data: e,
    };
  });

  // Build neighbour set for hover-highlight
  const neighbours = {};
  Object.keys(nodes).forEach(k => neighbours[k] = new Set([k]));
  EDGES.forEach(([a, b]) => {
    if (!nodes[a] || !nodes[b]) return;
    neighbours[a].add(b); neighbours[b].add(a);
  });

  return { nodes, edges: EDGES.filter(([a, b]) => nodes[a] && nodes[b]), neighbours, W, H };
}

// ── Filters ───────────────────────────────────────────────────────────
const TYPE_FILTERS = [
  { id: 'all',     label: 'All',         match: () => true },
  { id: 'skill',   label: 'Skills',      match: (n) => n.kind === 'skill' || n.kind === 'person' },
  { id: 'company', label: 'Companies',   match: (n) => n.kind === 'company' || n.kind === 'person' },
  { id: 'project', label: 'Projects',    match: (n) => n.kind === 'project' || n.kind === 'person' },
];
const SOURCE_FILTERS = [
  { id: 'any',      label: 'All',      match: () => true },
  { id: 'explicit', label: 'Explicit', match: (n) => n.kind !== 'skill' || n.source === 'explicit' },
  { id: 'inferred', label: 'Inferred', match: (n) => n.kind !== 'skill' || n.source === 'inferred' },
];

function SkillGraph({ onSelectNode, accent }) {
  const layout = useMemo(buildLayout, []);
  const { nodes, edges, neighbours, W, H } = layout;
  const [hover, setHover] = useState(null);
  const [selected, setSelected] = useState(null);
  const [typeF, setTypeF] = useState('all');
  const [sourceF, setSourceF] = useState('any');
  const [commF, setCommF] = useState(null); // null = all communities

  const typeFn = TYPE_FILTERS.find(f => f.id === typeF).match;
  const sourceFn = SOURCE_FILTERS.find(f => f.id === sourceF).match;

  const isVisible = (n) => {
    if (n.kind === 'person') return true;
    if (!typeFn(n) || !sourceFn(n)) return false;
    if (commF != null && n.kind === 'skill' && n.community !== commF) return false;
    return true;
  };

  const focus = hover || selected;
  const isDimmed = (n) => focus && !neighbours[focus]?.has(n.id);

  const handleClick = (id) => {
    setSelected(id === selected ? null : id);
    if (onSelectNode) onSelectNode(id === selected ? null : nodes[id]);
  };

  const COMMUNITIES = window.DATA.COMMUNITIES;

  return (
    <div className="graph-wrap">
      {/* Filter bar */}
      <div className="graph-filters">
        <div className="gfilter-group">
          {TYPE_FILTERS.map(f => (
            <button key={f.id} className={'gchip' + (typeF === f.id ? ' is-active' : '')} onClick={() => setTypeF(f.id)}>{f.label}</button>
          ))}
        </div>
        <div className="gfilter-sep" />
        <div className="gfilter-group">
          {SOURCE_FILTERS.map(f => (
            <button key={f.id} className={'gchip' + (sourceF === f.id ? ' is-active' : '')} onClick={() => setSourceF(f.id)}>{f.label}</button>
          ))}
        </div>
        <div className="gfilter-sep" />
        <div className="gfilter-group" style={{ flexWrap: 'wrap', display: 'flex', gap: 7 }}>
          <button className={'gchip' + (commF == null ? ' is-active' : '')} onClick={() => setCommF(null)}>All communities</button>
          {COMMUNITIES.map(c => (
            <button key={c.id} className={'gchip' + (commF === c.id ? ' is-active' : '')} onClick={() => setCommF(c.id === commF ? null : c.id)}>{c.name}</button>
          ))}
        </div>
      </div>

      {/* SVG */}
      <svg viewBox={`0 0 ${W} ${H}`} className="graph-svg" preserveAspectRatio="xMidYMid meet">
        {/* Edges */}
        <g>
          {edges.map(([a, b, type], i) => {
            const na = nodes[a], nb = nodes[b];
            if (!na || !nb || !isVisible(na) || !isVisible(nb)) return null;
            const dim = focus && !(neighbours[focus]?.has(a) && neighbours[focus]?.has(b));
            const isImplies = type === 'IMPLIES';
            return (
              <line key={i}
                x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                stroke={focus && !dim ? '#14161b' : '#e3e1dc'}
                strokeWidth={focus && !dim ? 1.3 : 0.8}
                strokeDasharray={isImplies ? '3 3' : undefined}
                strokeOpacity={dim ? 0.18 : 0.7} />
            );
          })}
        </g>

        {/* Community halos (subtle backgrounds visible only when one is selected) */}
        {commF != null && (() => {
          const c = { 1: [260, 175], 2: [740, 175], 3: [760, 480], 4: [220, 480] }[commF];
          if (!c) return null;
          return <circle cx={c[0]} cy={c[1]} r={130} fill="none" stroke={accent} strokeWidth="1.4" strokeDasharray="2 4" opacity="0.7" />;
        })()}

        {/* Nodes */}
        <g>
          {Object.values(nodes).map(n => {
            if (!isVisible(n)) return null;
            const dim = isDimmed(n);
            const isHover = hover === n.id;
            const isSelected = selected === n.id;
            const isYou = n.kind === 'person';

            const fill = isYou ? accent
              : n.kind === 'company' ? '#14161b'
              : n.kind === 'project' ? '#eef1f6'
              : n.kind === 'institution' ? '#e3e1dc'
              : n.source === 'explicit' ? '#fff'
              : '#fff';
            const stroke = n.kind === 'company' ? '#14161b'
              : '#14161b';
            const dashed = n.kind === 'skill' && n.source === 'inferred';
            const r = n.r + (isHover || isSelected ? 2 : 0);

            return (
              <g key={n.id}
                style={{ cursor: 'pointer', opacity: dim ? 0.18 : 1, transition: 'opacity .2s' }}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                onClick={() => handleClick(n.id)}>
                {(isHover || isSelected) && (
                  <circle cx={n.x} cy={n.y} r={r + 6}
                    fill="none" stroke={accent} strokeWidth="1.4" opacity="0.9" />
                )}
                <circle cx={n.x} cy={n.y} r={r}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={isYou ? 1.6 : 1.3}
                  strokeDasharray={dashed ? '2.5 2' : undefined} />
                {(isHover || isSelected || isYou || n.kind === 'company' || n.kind === 'project' || (focus && neighbours[focus]?.has(n.id)) || n.r >= 7) && (
                  <text x={n.x} y={n.y + r + 11}
                    textAnchor="middle"
                    fontSize={isYou ? 11 : 10}
                    fontWeight={isYou ? 600 : isSelected || isHover ? 600 : 500}
                    fontFamily="Geist, Inter, sans-serif"
                    fill="#14161b"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}>
                    {n.label}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Counts strip */}
      <div className="graph-counts">
        <span><b>{Object.values(nodes).filter(isVisible).length}</b> nodes</span>
        <span><b>{edges.filter(([a, b]) => isVisible(nodes[a]) && isVisible(nodes[b])).length}</b> edges</span>
        <span><b>{window.DATA.COMMUNITIES.length}</b> communities</span>
        <span style={{ marginLeft: 'auto', color: 'var(--ink-4)' }}>
          {focus ? `focused on ${focus.replace(/^(co:|proj:|edu:)/, '')}` : 'hover or click a node'}
        </span>
      </div>
    </div>
  );
}

// ── Node drawer (side panel that opens on click) ─────────────────────
function NodeDrawer({ node, onClose, accent }) {
  if (!node) return null;
  const { SKILLS, EDGES, TIMELINE, PROJECTS } = window.DATA;

  // Resolve enriched details based on kind
  const detail = (() => {
    if (node.kind === 'skill') {
      const s = SKILLS.find(x => x.name === node.label);
      const coOccurs = EDGES
        .filter(([a, b, t]) => t === 'CO_OCCURS' && (a === node.id || b === node.id))
        .map(([a, b]) => a === node.id ? b : a)
        .filter(n => SKILLS.find(s => s.name === n));
      const implies = EDGES
        .filter(([a, b, t]) => t === 'IMPLIES' && a === node.id)
        .map(([_, b]) => b);
      return { kind: 'skill', s, coOccurs, implies };
    }
    if (node.kind === 'company') {
      const t = TIMELINE.find(x => 'co:' + x.company === node.id);
      return { kind: 'company', t };
    }
    if (node.kind === 'project') {
      const p = PROJECTS.find(x => 'proj:' + x.name === node.id);
      return { kind: 'project', p };
    }
    if (node.kind === 'person') return { kind: 'person' };
    if (node.kind === 'institution') return { kind: 'institution' };
    return {};
  })();

  return (
    <div className="drawer">
      <div className="drawer-head">
        <div className="drawer-eyebrow">
          {detail.kind === 'skill' ? (detail.s.source === 'inferred' ? 'Inferred skill' : 'Skill')
            : detail.kind === 'company' ? 'Company'
            : detail.kind === 'project' ? 'Project · pinned repo'
            : detail.kind === 'person' ? 'You' : 'Institution'}
        </div>
        <button className="drawer-close" onClick={onClose} aria-label="close">×</button>
      </div>
      <div className="drawer-title">{node.label}</div>

      {detail.kind === 'skill' && (
        <>
          <div className="drawer-meta">
            <span>{detail.s.category}</span>
            <span>·</span>
            <span>community {detail.s.community}</span>
            <span>·</span>
            <span style={{ color: detail.s.source === 'inferred' ? 'var(--green-fg)' : 'var(--ink)', fontWeight: 600 }}>
              {detail.s.confidence.toFixed(2)} confidence
            </span>
          </div>

          {detail.s.source === 'inferred' && (
            <div className="drawer-section">
              <div className="drawer-label">Why we infer this</div>
              <div className="quote">
                {detail.s.reason}
              </div>
              <div className="drawer-meta" style={{ marginTop: 8 }}>
                Reached via <b>{(detail.s.via || []).join(' · ')}</b>
              </div>
              <div className="drawer-meta">
                Method · <span className="fk-mono">{detail.s.inferred_by}</span>
              </div>
            </div>
          )}

          {detail.coOccurs.length > 0 && (
            <div className="drawer-section">
              <div className="drawer-label">Co-occurs with</div>
              <div className="chip-row">
                {detail.coOccurs.map(n => <span key={n} className="chip">{n}</span>)}
              </div>
            </div>
          )}

          {detail.implies.length > 0 && (
            <div className="drawer-section">
              <div className="drawer-label">Implies</div>
              <div className="chip-row">
                {detail.implies.map(n => <span key={n} className="chip dashed">{n}</span>)}
              </div>
            </div>
          )}
        </>
      )}

      {detail.kind === 'company' && (
        <>
          <div className="drawer-meta">{detail.t.title}</div>
          <div className="drawer-meta">
            <span className="fk-mono">{detail.t.start}</span> →{' '}
            <span className="fk-mono">{detail.t.end || 'now'}</span>
            <span style={{ marginLeft: 6 }}>· {detail.t.months}mo</span>
          </div>
          <div className="drawer-section">
            <div className="drawer-label">Stage · industry</div>
            <div className="chip-row">
              <span className="chip">{detail.t.stage}</span>
              <span className="chip">{detail.t.industry}</span>
            </div>
          </div>
          <div className="drawer-section">
            <div className="drawer-label">Stack you used</div>
            <div className="chip-row">
              {detail.t.stack.map(s => <span key={s} className="chip">{s}</span>)}
            </div>
          </div>
        </>
      )}

      {detail.kind === 'project' && (
        <>
          <div className="drawer-meta">
            ★ {detail.p.stars} · {detail.p.language}
            {detail.p.is_new && <span className="pill pill-green" style={{ marginLeft: 6, height: 20 }}>New</span>}
          </div>
          <div className="drawer-body">{detail.p.summary}</div>
          <div className="drawer-section">
            <div className="drawer-label">Stack</div>
            <div className="chip-row">
              {detail.p.stack.map(s => <span key={s} className="chip">{s}</span>)}
            </div>
          </div>
          <div className="drawer-section">
            <div className="drawer-label">Topics</div>
            <div className="chip-row">
              {detail.p.topics.map(s => <span key={s} className="chip dashed">{s}</span>)}
            </div>
          </div>
        </>
      )}

      {detail.kind === 'person' && (
        <>
          <div className="drawer-meta">You · the root of this graph</div>
          <div className="drawer-body">
            Click any skill, company or project node to see how the graph connects it
            back to your work.
          </div>
        </>
      )}
    </div>
  );
}

Object.assign(window, { SkillGraph, NodeDrawer });
