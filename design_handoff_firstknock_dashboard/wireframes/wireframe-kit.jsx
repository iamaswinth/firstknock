// Wireframe primitives — clean greyscale, lo-fi but neat.
// Shared across all three directions.

const WK = {
  ink: '#1a1a1a',
  ink2: '#3a3a3a',
  mute: '#7a7a7a',
  mute2: '#a8a8a8',
  line: '#1a1a1a',
  weak: '#d4d4d4',
  fill0: '#ffffff',
  fill1: '#f4f4f2',
  fill2: '#e8e8e6',
  fill3: '#dedcd8',
  ui: 'Inter, system-ui, sans-serif',
  mono: '"JetBrains Mono", ui-monospace, monospace',
  hand: '"Architects Daughter", cursive',
};

// One stripe pattern used for image placeholders / "this slot has content"
const stripeBg =
  'repeating-linear-gradient(135deg, transparent 0 6px, rgba(0,0,0,0.06) 6px 7px)';
const dotsBg =
  'radial-gradient(circle, rgba(0,0,0,0.18) 1px, transparent 1.2px) 0 0 / 8px 8px';

// Thin rule
const Rule = ({ vertical, color = WK.weak, style = {} }) => (
  <div style={{
    background: color,
    ...(vertical ? { width: 1, alignSelf: 'stretch' } : { height: 1, width: '100%' }),
    ...style,
  }} />
);

// Sized text placeholder. Pass length (chars) or width(px). h sets height.
const TLine = ({ w = 80, h = 8, dark = false, rounded = 2, style = {} }) => (
  <div style={{
    width: typeof w === 'number' ? w : w,
    height: h,
    background: dark ? WK.ink2 : WK.mute2,
    borderRadius: rounded,
    ...style,
  }} />
);

// Block of stacked TLines (like a paragraph)
const TBlock = ({ lines = 3, w = 200, gap = 6, last = 0.6 }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap }}>
    {Array.from({ length: lines }).map((_, i) => (
      <TLine key={i} w={i === lines - 1 ? w * last : w} h={6} />
    ))}
  </div>
);

// Pill / chip — used for skills and statuses
const Chip = ({ children, dark, dashed, style = {} }) => (
  <div style={{
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '3px 8px',
    border: `1px ${dashed ? 'dashed' : 'solid'} ${WK.ink}`,
    background: dark ? WK.ink : WK.fill0,
    color: dark ? WK.fill0 : WK.ink,
    borderRadius: 100,
    fontSize: 10,
    fontFamily: WK.mono,
    letterSpacing: 0.2,
    whiteSpace: 'nowrap',
    ...style,
  }}>{children}</div>
);

// Wireframe button
const WBtn = ({ children, primary, w, h = 32, style = {} }) => (
  <div style={{
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: '0 14px',
    height: h,
    width: w,
    border: `1.2px solid ${WK.ink}`,
    background: primary ? WK.ink : WK.fill0,
    color: primary ? WK.fill0 : WK.ink,
    borderRadius: 3,
    fontFamily: WK.ui,
    fontSize: 11,
    fontWeight: 500,
    letterSpacing: 0.2,
    ...style,
  }}>{children}</div>
);

// Card wrapper with optional title
const WCard = ({ title, eyebrow, action, children, dashed, pad = 16, style = {} }) => (
  <div style={{
    border: `1.2px ${dashed ? 'dashed' : 'solid'} ${WK.ink}`,
    background: WK.fill0,
    borderRadius: 4,
    padding: pad,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    minWidth: 0,
    ...style,
  }}>
    {(title || eyebrow || action) && (
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
          {eyebrow && <div style={{ fontFamily: WK.mono, fontSize: 9, letterSpacing: 1.4, textTransform: 'uppercase', color: WK.mute }}>{eyebrow}</div>}
          {title && <div style={{ fontFamily: WK.ui, fontSize: 14, fontWeight: 600, color: WK.ink, lineHeight: 1.2 }}>{title}</div>}
        </div>
        {action && <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute, letterSpacing: 0.8 }}>{action}</div>}
      </div>
    )}
    {children}
  </div>
);

// Image placeholder rectangle with striped fill + label
const WSlot = ({ label = 'image', w = '100%', h = 80, style = {} }) => (
  <div style={{
    width: w, height: h,
    border: `1px dashed ${WK.ink}`,
    background: stripeBg,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: WK.mono,
    fontSize: 10,
    color: WK.ink2,
    letterSpacing: 0.4,
    ...style,
  }}>{label}</div>
);

// Frame chrome — the artboards mock a browser window so the wireframe reads
// as a real screen, not a floating layout.
const WFrame = ({ url, children, dark, style = {} }) => (
  <div style={{
    width: '100%', height: '100%',
    background: dark ? WK.ink : WK.fill1,
    display: 'flex',
    flexDirection: 'column',
    fontFamily: WK.ui,
    color: dark ? WK.fill0 : WK.ink,
    ...style,
  }}>
    <div style={{
      height: 28, display: 'flex', alignItems: 'center', gap: 8,
      padding: '0 12px',
      background: dark ? '#0d0d0d' : WK.fill2,
      borderBottom: `1px solid ${dark ? '#2a2a2a' : WK.ink}`,
      flexShrink: 0,
    }}>
      <div style={{ display: 'flex', gap: 5 }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ width: 9, height: 9, borderRadius: 5, border: `1px solid ${dark ? '#3a3a3a' : WK.ink}` }} />
        ))}
      </div>
      <div style={{
        flex: 1,
        height: 16,
        background: dark ? '#1a1a1a' : WK.fill0,
        border: `1px solid ${dark ? '#3a3a3a' : WK.ink}`,
        borderRadius: 3,
        display: 'flex', alignItems: 'center',
        padding: '0 8px',
        fontFamily: WK.mono,
        fontSize: 9,
        color: dark ? WK.mute : WK.mute,
        letterSpacing: 0.4,
      }}>{url}</div>
    </div>
    <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}>{children}</div>
  </div>
);

// Top app bar of the product itself (inside the browser frame)
const WAppBar = ({ right }) => (
  <div style={{
    height: 44,
    borderBottom: `1px solid ${WK.ink}`,
    display: 'flex',
    alignItems: 'center',
    padding: '0 20px',
    gap: 14,
    background: WK.fill0,
    flexShrink: 0,
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 18, height: 18, border: `1.5px solid ${WK.ink}`, borderRadius: 2, position: 'relative' }}>
        <div style={{ position: 'absolute', inset: 3, border: `1.2px solid ${WK.ink}`, borderRadius: 1 }} />
      </div>
      <div style={{ fontFamily: WK.mono, fontWeight: 600, fontSize: 12, letterSpacing: 1, textTransform: 'uppercase' }}>FirstKnock</div>
    </div>
    <div style={{ flex: 1 }} />
    {right || (
      <>
        <div style={{ fontFamily: WK.mono, fontSize: 10, color: WK.mute }}>iamaswinth@gmail.com</div>
        <div style={{ width: 28, height: 28, borderRadius: 14, border: `1.2px solid ${WK.ink}`, background: WK.fill1 }} />
      </>
    )}
  </div>
);

// A tiny "section header" used inside cards
const WSubhead = ({ children, action }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
    <div style={{
      fontFamily: WK.mono, fontSize: 9, letterSpacing: 1.4,
      textTransform: 'uppercase', color: WK.mute,
    }}>{children}</div>
    {action && <div style={{ fontFamily: WK.mono, fontSize: 9, color: WK.mute }}>{action}</div>}
  </div>
);

// Annotation arrow + caption — for design notes overlaying screens
const WAnno = ({ children, top, left, right, bottom, width = 160, dir = 'left' }) => (
  <div style={{
    position: 'absolute', top, left, right, bottom, width,
    fontFamily: WK.hand,
    fontSize: 13,
    lineHeight: 1.25,
    color: WK.ink,
    zIndex: 5,
  }}>
    <div>{children}</div>
  </div>
);

Object.assign(window, {
  WK, Rule, TLine, TBlock, Chip, WBtn, WCard, WSlot, WFrame, WAppBar, WSubhead, WAnno,
  stripeBg, dotsBg,
});
