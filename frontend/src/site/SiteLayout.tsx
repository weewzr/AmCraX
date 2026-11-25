import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { GITHUB_URL, IS_PAGES, PORTFOLIO_URL } from '../api/url'
import { useData } from '../data/DataContext'
import { STATIC_SITE_NOTICE } from '../components/Shell'
import { CommandPalette } from './CommandPalette'
import { exportDate } from './data'
import { REPORT_PDF, downloadUrl } from './downloads'
import { HeadlineBasis } from './HeadlineBasis'
import { activeGroup, anchorId, LEGACY_PATHS, NAV_GROUPS, pageActive, platformPath, titleFor } from './routes'
import { useTheme } from './theme'
import { ExtLink, Wordmark } from './ui'

// The legacy banner lives with the research sections; loading it lazily keeps them out of the landing bundle.
const LegacyBanner = lazy(() => import('./hyp/phase2').then((m) => ({ default: m.LegacyBanner })))

/** Scroll to the top (or to an in-page anchor once its element exists), keep the document title current, move focus to <main> on navigation. */
function RouteEffects() {
  const { pathname, hash } = useLocation()
  const first = useRef(true)
  useEffect(() => { document.title = titleFor(pathname) }, [pathname])
  useEffect(() => {
    const id = anchorId(hash)
    let timer = 0
    let tries = 0
    let settleTimer = 0
    let settleTicks = 0
    const stop = () => window.clearInterval(settleTimer)
    const go = () => {
      const el = id ? document.getElementById(id) : null
      if (el) {
        el.scrollIntoView({ block: 'start' })
        // charts above the target load asynchronously and push it down: re-align for a few seconds unless the visitor scrolls
        window.addEventListener('wheel', stop, { once: true })
        window.addEventListener('touchstart', stop, { once: true })
        window.addEventListener('keydown', stop, { once: true })
        settleTimer = window.setInterval(() => { document.getElementById(id as string)?.scrollIntoView({ block: 'start' }); if (++settleTicks > 14) stop() }, 250)
        return
      }
      if (id && tries++ < 40) { timer = window.setTimeout(go, 100); return }
      window.scrollTo(0, 0)
    }
    go()
    if (!first.current && !id) document.getElementById('site-main')?.focus({ preventScroll: true })
    first.current = false
    return () => { window.clearTimeout(timer); stop() }
  }, [pathname, hash])
  return null
}

function ModeNotice() {
  const { mode, manifest, phase } = useData()
  const d = exportDate(manifest?.exported_utc)
  let text: string
  let cls = ''
  if (IS_PAGES) text = `${STATIC_SITE_NOTICE}${d ? ` Results exported ${d}.` : ''}`
  else if (phase === 'loading') text = 'Resolving data mode...'
  else if (mode === 'LIVE') text = 'Local build connected to the AmCraX API: LIVE results from the local results store.'
  else if (mode === 'SNAPSHOT') text = `Local build, API not reachable: showing the exported snapshot${d ? ` of ${d}` : ''}. Live Aspen Plus runs need the local platform.`
  else { text = 'DEMONSTRATION DATA - neither the API nor a results snapshot is available. Numbers on these pages are placeholders, not results.'; cls = 'notice-demo' }
  return <div className={`static-notice ${cls}`} role="status">{text}</div>
}

const isMac = () => typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)

/**
 * Public site frame. Navigation: five labelled groups from routes.NAV_GROUPS. On wide screens each group is a disclosure
 * button with its list of pages; below 1100 px the menu button shows all groups as labelled lists.
 */
export function SiteLayout() {
  const [open, setOpen] = useState(false)
  const [group, setGroup] = useState<string | null>(null)
  const [palette, setPalette] = useState(false)
  const navRef = useRef<HTMLElement>(null)
  const [theme, toggleTheme] = useTheme()
  const { pathname, hash } = useLocation()
  const { manifest } = useData()
  const current = activeGroup(pathname)
  // close the menus when the location changes (adjusted during render, not in an effect)
  const loc = `${pathname}${hash}`
  const [seenLoc, setSeenLoc] = useState(loc)
  if (seenLoc !== loc) { setSeenLoc(loc); setOpen(false); setGroup(null) }
  useEffect(() => {
    if (!open && !group) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      const g = group
      setOpen(false); setGroup(null)
      if (g) document.getElementById(`nav-btn-${g}`)?.focus()
    }
    const onDown = (e: PointerEvent) => { if (group && navRef.current && !navRef.current.contains(e.target as Node)) setGroup(null) }
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onDown)
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('pointerdown', onDown) }
  }, [open, group])
  // Ctrl+K / Cmd+K opens the command palette from any public page
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette(true) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  const d = exportDate(manifest?.exported_utc)
  const shortcut = isMac() ? 'Cmd K' : 'Ctrl K'
  return (
    <div className="site">
      <a href="#site-main" className="skip" onClick={(e) => { e.preventDefault(); const m = document.getElementById('site-main'); m?.focus(); m?.scrollIntoView() }}>Skip to content</a>
      <ModeNotice />
      <header className="site-header">
        <div className="wrap site-bar">
          <Link to="/" className="brand-link" aria-label="AmCraX home"><Wordmark /></Link>
          <nav id="site-nav" ref={navRef} className={`site-nav ${open ? 'open' : ''}`} aria-label="Main">
            <ul className="nav-groups">
              {NAV_GROUPS.map((g) => {
                const expanded = group === g.id
                return (
                  <li key={g.id} className={`nav-group${current === g.id ? ' is-current' : ''}${expanded ? ' is-open' : ''}`}>
                    <button type="button" id={`nav-btn-${g.id}`} className="nav-group-btn" aria-expanded={expanded} aria-controls={`nav-list-${g.id}`}
                      onClick={() => setGroup(expanded ? null : g.id)}>
                      {g.label}<span aria-hidden="true" className="nav-caret" />{current === g.id ? <span className="sr-only"> (current section)</span> : null}
                    </button>
                    <ul id={`nav-list-${g.id}`} className="nav-list" aria-label={g.label}>
                      {g.pages.map((p) => {
                        const on = pageActive(p, pathname, hash)
                        return (
                          <li key={p.to}>
                            <Link to={p.to} className={on ? 'active' : ''} aria-current={on ? 'page' : undefined}>
                              <span className="nav-label">{p.label}</span>{p.hint ? <span className="nav-hint">{p.hint}</span> : null}
                            </Link>
                          </li>
                        )
                      })}
                    </ul>
                  </li>
                )
              })}
            </ul>
          </nav>
          <div className="site-actions">
            <button type="button" className="btn search-btn" onClick={() => setPalette(true)} aria-keyshortcuts={isMac() ? 'Meta+K' : 'Control+K'}>
              <span>Search</span><kbd aria-hidden="true">{shortcut}</kbd>
            </button>
            <Link to={platformPath('/pfd')} className="btn site-cta">Open the platform</Link>
            <button type="button" className="btn icon-btn" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
            <button type="button" className="btn icon-btn nav-toggle" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen((o) => !o)}>
              <span className="nav-toggle-bars" aria-hidden="true" /><span className="sr-only">{open ? 'Close menu' : 'Open menu'}</span>
            </button>
          </div>
        </div>
      </header>
      <HeadlineBasis />
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
      <main id="site-main" tabIndex={-1}>
        <RouteEffects />
        {LEGACY_PATHS.includes(pathname) ? <Suspense fallback={null}><LegacyBanner /></Suspense> : null}
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="wrap footer-grid">
          <div>
            <Wordmark className="footer-mark" />
            <p className="muted footer-blurb">Ammonia Cracking Simulation and Optimisation Platform. Aspen Plus V15 flowsheet, independent Python models, FastAPI back end and a React dashboard.</p>
            <h2 className="footer-h">Project</h2>
            <ul>
              <li><ExtLink href={GITHUB_URL}>GitHub repository</ExtLink></li>
              <li><ExtLink href={PORTFOLIO_URL}>Portfolio</ExtLink></li>
              <li>{IS_PAGES ? <a href={downloadUrl(REPORT_PDF.file)}>Technical report (PDF)</a> : <Link to="/docs">Documentation and downloads</Link>}</li>
              <li><ExtLink href={`${GITHUB_URL}/blob/main/LICENSE`}>Licence: MIT</ExtLink></li>
            </ul>
          </div>
          <nav aria-label="Footer" className="footer-map">
            {NAV_GROUPS.map((g) => (
              <div key={g.id}>
                <h2 className="footer-h">{g.label}</h2>
                <ul>{g.pages.filter((p) => !p.to.includes('#')).map((p) => <li key={p.to}><Link to={p.to}>{p.label}</Link></li>)}</ul>
              </div>
            ))}
          </nav>
          <div>
            <h2 className="footer-h">Data</h2>
            <p className="muted">{d ? `Results generated ${d}` : 'Results generated: export date unavailable'}{manifest?.exported_utc ? ` (${manifest.exported_utc})` : ''}.</p>
            <p className="muted">Numbers on this site are read from the stored results of Aspen Plus V15 runs or of the independent Python models, or, on the simulator page, computed in your browser by a port of the Python model checked against it (each value is labelled). The site does not run Aspen Plus or Python.</p>
          </div>
        </div>
        <div className="wrap footer-legal muted">
          Aspen Plus is a trademark of Aspen Technology, Inc. AmCraX is an independent project and is not affiliated with or endorsed by AspenTech.
        </div>
      </footer>
    </div>
  )
}
