// Shared app shell for FirstKnock — sidebar, topbar, greeting, stats.
// Mondays-style light SaaS chrome. Plain inline SVG icon set (currentColor).

const Icon = {
  grid: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.7" /><rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.7" /><rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.7" /><rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.7" /></svg>,
  graph: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="6" cy="6" r="2.5" stroke="currentColor" strokeWidth="1.7" /><circle cx="18" cy="7" r="2.5" stroke="currentColor" strokeWidth="1.7" /><circle cx="12" cy="17" r="2.5" stroke="currentColor" strokeWidth="1.7" /><path d="M8 7l8 1M7.5 8.5L11 15M16.5 9l-3.5 6" stroke="currentColor" strokeWidth="1.7" /></svg>,
  skills: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 3l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8 6.8 19l1-5.8L3.6 9.1l5.8-.8L12 3z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" /></svg>,
  folder: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /></svg>,
  clock: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.7" /><path d="M12 7.5V12l3 2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>,
  doc: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M6 3h7l5 5v13a0 0 0 0 1 0 0H6a0 0 0 0 1 0 0V3z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /><path d="M13 3v5h5M9 13h6M9 17h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>,
  gear: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.7" /><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>,
  help: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.7" /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .8-1 1.7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /><circle cx="12" cy="16.5" r="1" fill="currentColor" /></svg>,
  search: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" /><path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>,
  bell: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /><path d="M10 19a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.7" /></svg>,
  plus: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>,
  caret: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  share: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="18" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.7" /><circle cx="6" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.7" /><circle cx="18" cy="19" r="2.5" stroke="currentColor" strokeWidth="1.7" /><path d="M8.2 10.8l7.6-4.6M8.2 13.2l7.6 4.6" stroke="currentColor" strokeWidth="1.7" /></svg>,
  download: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 4v11m0 0l-4-4m4 4l4-4M5 19h14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  refresh: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M20 11a8 8 0 0 0-14-4.5L4 8M4 4v4h4M4 13a8 8 0 0 0 14 4.5L20 16M20 20v-4h-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  check: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M5 12.5l4.5 4.5L19 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  hexagon: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 3l7.5 4.5v9L12 21l-7.5-4.5v-9L12 3z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /></svg>,
  star: (p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><path d="M12 4l2.3 4.7 5.2.7-3.8 3.7.9 5.2L12 16.5 7.4 18l.9-5.2L4.5 9.4l5.2-.7L12 4z" /></svg>,
  fork: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="6" cy="6" r="2" stroke="currentColor" strokeWidth="1.7" /><circle cx="18" cy="6" r="2" stroke="currentColor" strokeWidth="1.7" /><circle cx="12" cy="18" r="2" stroke="currentColor" strokeWidth="1.7" /><path d="M6 8v2a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V8M12 13v3" stroke="currentColor" strokeWidth="1.7" /></svg>,
  list: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>,
  cal: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><rect x="3.5" y="5" width="17" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.7" /><path d="M3.5 9.5h17M8 3v4M16 3v4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>,
  bulb: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5.5 1.1.5 2.1h6c0-1 0-1.6.5-2.1A6 6 0 0 0 12 3z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /></svg>,
  bridge: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M3 17v-3a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v3M3 17h18M7 10V7M17 10V7M12 10v7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>,
  building: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><rect x="5" y="3" width="14" height="18" rx="1.5" stroke="currentColor" strokeWidth="1.7" /><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2M10 21v-3h4v3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>,
  menu: (p) => <svg viewBox="0 0 24 24" fill="none" {...p}><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
};

function Sidebar({ active = 'dashboard' }) {
  const nav = [
  { k: 'dashboard', label: 'Dashboard', icon: 'grid', href: 'FirstKnock Dashboard.html' }];

  return (
    <aside className="side">
      <div className="side-brand">
        <div className="side-brand-mark">{Icon.hexagon({ width: 16, height: 16 })}</div>
        <div className="side-wordmark">FirstKnock</div>
      </div>

      <nav className="side-nav">
        {nav.map((n) =>
        <a key={n.k} href={n.href} className={'nav-item' + (n.k === active ? ' is-active' : '')}>
            {Icon[n.icon]()}
            <span>{n.label}</span>
          </a>
        )}
      </nav>

      <div className="side-foot">
        <a href="FirstKnock Dashboard.html" className="nav-item">{Icon.gear()}<span>Settings</span></a>
        <a href="FirstKnock Dashboard.html" className="nav-item">
          {Icon.help()}<span>Help &amp; Support</span>
          <span className="nav-badge">8</span>
        </a>
      </div>
    </aside>);

}

// Toggles the sidebar open/closed by flipping a class on the .app shell.
function toggleSidebar() {
  const app = document.querySelector('.app');
  if (app) app.classList.toggle('side-collapsed');
}

function Topbar({ searchPlaceholder = 'Search skills, projects, companies…', cta = 'New Ingest', ctaHref = 'FirstKnock Upload.html' }) {
  return (
    <header className="topbar">
      <button className="icon-btn" onClick={toggleSidebar} aria-label="Toggle sidebar">{Icon.menu()}</button>
      <div className="search">
        {Icon.search()}
        <input placeholder={searchPlaceholder} />
        <span className="search-kbd">⌘ K</span>
      </div>
      <div className="topbar-spacer" />
      <div className="btn-split">
        <a href={ctaHref} className="btn-primary">{Icon.plus({ width: 17, height: 17 })} {cta}</a>
        <button className="btn-split-caret">{Icon.caret({ width: 15, height: 15 })}</button>
      </div>
      <button className="icon-btn">{Icon.bell()}<span className="dot" /></button>
      <div className="avatar">AD</div>
    </header>);

}

function greetingFor(d = new Date()) {
  const h = d.getHours();
  const part = h < 12 ? 'morning' : h < 18 ? 'afternoon' : 'evening';
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const n = d.getDate();
  const ord = n % 10 === 1 && n !== 11 ? 'st' : n % 10 === 2 && n !== 12 ? 'nd' : n % 10 === 3 && n !== 13 ? 'rd' : 'th';
  return { part, dateStr: `${days[d.getDay()]}, ${n}${ord} ${months[d.getMonth()]}` };
}

function Greeting({ name = 'Aswinthraj', actions }) {
  const { part, dateStr } = greetingFor();
  return (
    <div className="greet">
      <div>
        <div className="greet-date">{dateStr}</div>
        <h1 className="greet-title">Good {part}, {name} <span className="wave">👋</span></h1>
      </div>
      {actions && <div className="greet-actions">{actions}</div>}
    </div>);

}

function Stats({ items }) {
  return (
    <div className="stat-cards">
      {items.map((s, i) =>
      <div key={i} className="stat-card">
          <div className="stat-ico">{Icon[s.icon]()}</div>
          <div className="stat-meta">
            <div className="stat-num">{s.num}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        </div>
      )}
    </div>);

}

Object.assign(window, { Icon, Sidebar, Topbar, Greeting, Stats, greetingFor });