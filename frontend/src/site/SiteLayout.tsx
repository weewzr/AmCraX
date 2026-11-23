import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { GITHUB_URL, IS_PAGES, PORTFOLIO_URL } from '../api/url'
import { useData } from '../data/DataContext'
import { STATIC_SITE_NOTICE } from '../components/Shell'
import { exportDate } from './data'
import { REPORT_PDF, downloadUrl } from './downloads'
import { anchorId, platformPath, SITE_ROUTES, titleFor } from './routes'
import { useTheme } from './theme'
import { ExtLink, Wordmark } from './ui'

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

export function SiteLayout() {
  const [open, setOpen] = useState(false)
  const [theme, toggleTheme] = useTheme()
  const { pathname } = useLocation()
  const { manifest } = useData()
  useEffect(() => { setOpen(false) }, [pathname])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  const d = exportDate(manifest?.exported_utc)
  return (
    <div className="site">
      <a href="#site-main" className="skip" onClick={(e) => { e.preventDefault(); const m = document.getElementById('site-main'); m?.focus(); m?.scrollIntoView() }}>Skip to content</a>
      <ModeNotice />
      <header className="site-header">
        <div className="wrap site-bar">
          <Link to="/" className="brand-link" aria-label="AmCraX home"><Wordmark /></Link>
          <nav id="site-nav" className={`site-nav ${open ? 'open' : ''}`} aria-label="Main">
            <ul>
              {SITE_ROUTES.map((r) => (
                <li key={r.path}><NavLink to={r.path} end={r.path !== '/hypotheses'} className={({ isActive }) => (isActive ? 'active' : '')}>{r.label}</NavLink></li>
              ))}
            </ul>
          </nav>
          <div className="site-actions">
            <Link to={platformPath('/pfd')} className="btn btn-primary site-cta">Open the platform</Link>
            <button type="button" className="btn icon-btn" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
            <button type="button" className="btn icon-btn nav-toggle" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen((o) => !o)}>
              <span className="nav-toggle-bars" aria-hidden="true" /><span className="sr-only">{open ? 'Close menu' : 'Open menu'}</span>
            </button>
          </div>
        </div>
      </header>
      <main id="site-main" tabIndex={-1}>
        <RouteEffects />
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="wrap footer-grid">
          <div>
            <Wordmark className="footer-mark" />
            <p className="muted footer-blurb">Ammonia Cracking Simulation and Optimisation Platform. Aspen Plus V15 flowsheet, independent Python models, FastAPI back end and a React dashboard.</p>
          </div>
          <nav aria-label="Footer">
            <h2 className="footer-h">Project</h2>
            <ul>
              <li><ExtLink href={GITHUB_URL}>GitHub repository</ExtLink></li>
              <li><ExtLink href={PORTFOLIO_URL}>Portfolio</ExtLink></li>
              <li>{IS_PAGES ? <a href={downloadUrl(REPORT_PDF.file)}>Technical report (PDF)</a> : <Link to="/docs">Documentation and downloads</Link>}</li>
              <li><ExtLink href={`${GITHUB_URL}/blob/main/LICENSE`}>Licence: MIT</ExtLink></li>
            </ul>
          </nav>
          <div>
            <h2 className="footer-h">Data</h2>
            <p className="muted">{d ? `Results generated ${d}` : 'Results generated: export date unavailable'}{manifest?.exported_utc ? ` (${manifest.exported_utc})` : ''}.</p>
            <p className="muted">Every number on this site is read from the stored results of Aspen Plus V15 runs or of the independent Python models. The site does not run Aspen Plus.</p>
          </div>
        </div>
        <div className="wrap footer-legal muted">
          Aspen Plus is a trademark of Aspen Technology, Inc. AmCraX is an independent project and is not affiliated with or endorsed by AspenTech.
        </div>
      </footer>
    </div>
  )
}
