import { Link, NavLink, Outlet } from 'react-router-dom'
import { IS_PAGES } from '../api/url'
import { useData } from '../data/DataContext'
import { platformPath } from '../site/routes'
import { useTheme } from '../site/theme'
import { StatusPill, SourceBadge } from './ui'

/** Dashboard pages; every path lives under the /platform prefix (see site/routes.ts). */
export const SECTIONS: { path: string; label: string; end?: boolean }[] = [
  { path: platformPath('/'), label: 'Overview', end: true },
  { path: platformPath('/pfd'), label: 'Process Flow Diagram' },
  { path: platformPath('/simulation'), label: 'Simulation' },
  { path: platformPath('/reactor'), label: 'Reactor Analysis' },
  { path: platformPath('/heat'), label: 'Heat Integration' },
  { path: platformPath('/sensitivity'), label: 'Sensitivity Analysis' },
  { path: platformPath('/optimisation'), label: 'Optimisation' },
  { path: platformPath('/economics'), label: 'Techno-Economics' },
  { path: platformPath('/environment'), label: 'Environment' },
  { path: platformPath('/validation'), label: 'Validation' },
  { path: platformPath('/reports'), label: 'Reports' },
]

export const STATIC_SITE_NOTICE = 'Published results - static site. Live Aspen Plus runs need the local platform.'

function ModeBadge() {
  const { mode, manifest, phase } = useData()
  if (phase === 'loading') return <StatusPill kind="neutral">Resolving data mode...</StatusPill>
  if (mode === 'LIVE') return <StatusPill kind="ok">LIVE - API</StatusPill>
  if (mode === 'SNAPSHOT') {
    return <StatusPill kind="info">{IS_PAGES ? 'PUBLISHED RESULTS' : 'SNAPSHOT'} - exported {manifest?.exported_utc ?? 'time unknown'}</StatusPill>
  }
  if (mode === 'DEMO') return <StatusPill kind="error">DEMO DATA</StatusPill>
  return null
}

function ApiStatus() {
  const { mode, health, phase } = useData()
  if (phase === 'loading' || IS_PAGES) return null
  if (mode !== 'LIVE' || !health) return <StatusPill kind="warn">API unreachable</StatusPill>
  const aspen = health['aspen'] as { available?: boolean; reason?: string | null } | undefined
  const label = aspen === undefined ? null : aspen.available ? 'Aspen: available' : `Aspen: unavailable${aspen.reason ? ` (${aspen.reason})` : ''}`
  return (
    <>
      <StatusPill kind="ok">API {String(health.status)}</StatusPill>
      {label ? <span className="aspen-state">{label}</span> : null}
    </>
  )
}

export function Shell() {
  const { cases, activeId, setActiveId, phase, mode, active, manifest, caseLabel } = useData()
  const [theme, toggleTheme] = useTheme()
  return (
    <div className="shell">
      <a href="#main" className="skip" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus() }}>Skip to content</a>
      {mode === 'DEMO' && (
        <div className="demo-banner" role="alert">
          DEMONSTRATION DATA - not simulation results. Neither the API nor a results snapshot is available; everything shown is an illustrative placeholder.
        </div>
      )}
      {mode === 'SNAPSHOT' && (
        <div className="snapshot-banner" role="status">
          {IS_PAGES
            ? <>{STATIC_SITE_NOTICE} Results exported {manifest?.exported_utc ?? 'at an unknown time'}. Actions that need the API (running simulations, live sweeps, optimisation) are disabled.</>
            : <>SNAPSHOT MODE - the API is not reachable; showing real stored results exported at {manifest?.exported_utc ?? 'an unknown time'}. Actions that need the API (running simulations, live sweeps, optimisation) are disabled.</>}
        </div>
      )}
      <header className="topbar">
        <div className="brand">
          <span className="wordmark">AmCraX <span className="wm-sub">platform</span></span>
          <span className="tagline">Ammonia Cracking Simulation and Optimisation Platform</span>
        </div>
        <div className="topbar-right">
          <ModeBadge />
          <ApiStatus />
          <label className="case-select" title="Active case: drives PFD, Overview, Simulation, Heat Integration, Economics and Environment">
            <span>Case</span>
            <select value={activeId ?? ''} onChange={(e) => setActiveId(e.target.value)} disabled={phase !== 'ready' || cases.length === 0}>
              {cases.length === 0 && <option value="">no cases</option>}
              {cases.map((c) => (<option key={c.case_id} value={c.case_id} title={c.case_id}>{caseLabel(c.case_id)} [{c.source === 'aspen_plus_v15' ? 'Aspen' : c.source === 'python_model' ? 'Python' : c.source}]</option>))}
            </select>
          </label>
          {active ? <SourceBadge source={active.source} /> : null}
          <Link className="btn btn-sm" to="/">Project website</Link>
          <button type="button" className="btn btn-sm" onClick={toggleTheme} aria-label="Toggle light or dark theme">
            {theme === 'dark' ? 'Light theme' : 'Dark theme'}
          </button>
        </div>
      </header>
      <div className="body">
        <nav className="sidebar" aria-label="Platform sections">
          <ul>
            {SECTIONS.map((s) => (
              <li key={s.path}><NavLink to={s.path} end={s.end} className={({ isActive }) => (isActive ? 'active' : '')}>{s.label}</NavLink></li>
            ))}
          </ul>
        </nav>
        <main id="main" tabIndex={-1}><Outlet /></main>
      </div>
    </div>
  )
}
