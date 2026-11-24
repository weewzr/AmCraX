/** Route table of the public site and helpers shared by the site and the platform. Hash routes: "#/results", "#/platform/pfd". */
export const PLATFORM = '/platform'

/** Path of a dashboard page: platformPath('/') -> '/platform', platformPath('/pfd') -> '/platform/pfd'. */
export function platformPath(p: string): string {
  const rest = p === '/' || p === '' ? '' : p.startsWith('/') ? p : `/${p}`
  return `${PLATFORM}${rest}`
}

/** True for any location that belongs to the engineering dashboard (rendered in the Shell). */
export function isPlatformPath(pathname: string): boolean {
  return pathname === PLATFORM || pathname.startsWith(`${PLATFORM}/`)
}

export interface SiteRoute { path: string; label: string; title: string; section: number }

/** The public pages, in order. Each has its own route; "/" is the process simulator (landing page, section 1). */
export const SITE_ROUTES: SiteRoute[] = [
  { path: '/', label: 'Simulator', title: 'Process simulator', section: 1 },
  { path: '/overview', label: 'Overview', title: 'Overview', section: 2 },
  { path: '/why', label: 'Why cracking', title: 'Why ammonia cracking', section: 3 },
  { path: '/pfd', label: 'Process flow results', title: 'Interactive process flow diagram', section: 4 },
  { path: '/methodology', label: 'Methodology', title: 'Simulation methodology', section: 5 },
  { path: '/results', label: 'Results', title: 'Engineering results', section: 6 },
  { path: '/architecture', label: 'Architecture', title: 'Software architecture', section: 7 },
  { path: '/research', label: 'Research', title: 'Research and validation', section: 8 },
  { path: '/docs', label: 'Docs', title: 'Documentation and downloads', section: 9 },
  { path: '/about', label: 'About', title: 'About AmCraX', section: 10 },
  { path: '/hypotheses', label: 'Hypotheses', title: 'Hypothesis testing', section: 11 },
]

export interface NavItem { label: string; to: string; /** match for the active state (pathname) */ match?: string }

/** Top navigation (Phase 2): the simulator first, then the research pages. Items map onto existing routes and anchors. */
export const NAV_PRIMARY: NavItem[] = [
  { label: 'Simulator', to: '/', match: '/' },
  { label: 'Hypotheses', to: '/hypotheses', match: '/hypotheses' },
  { label: 'Catalysts', to: '/hypotheses/catalyst', match: '/hypotheses/catalyst' },
  { label: 'Singapore Economics', to: '/hypotheses/economics', match: '/hypotheses/economics' },
  { label: 'Purification', to: '/hypotheses/purification', match: '/hypotheses/purification' },
  { label: 'End Use', to: '/hypotheses/end-use', match: '/hypotheses/end-use' },
  { label: 'Environmental Analysis', to: '/hypotheses/end-use#lca' },
  { label: 'Validation', to: '/hypotheses/validation', match: '/hypotheses/validation' },
  { label: 'Aspen Evidence', to: '/hypotheses/aspen-evidence', match: '/hypotheses/aspen-evidence' },
  { label: 'Technical Report', to: '/docs#downloads' },
  { label: 'Documentation', to: '/docs', match: '/docs' },
]

/** Existing pages outside the primary list: reachable from the "More pages" menu and from the footer. */
export const NAV_MORE: NavItem[] = SITE_ROUTES.filter((r) => ['/overview', '/why', '/pfd', '/methodology', '/results', '/architecture', '/research', '/about'].includes(r.path))
  .map((r) => ({ label: r.label, to: r.path, match: r.path }))

/** Active state of a nav item: exact pathname match (the hypotheses root is active only on its own page). */
export function navActive(item: NavItem, pathname: string, hash = ''): boolean {
  if (!item.match) return false
  if (item.match === '/hypotheses/end-use' && hash === '#lca') return false
  return pathname === item.match
}

/** Older pages that show the legacy core cost results (3.92 USD/kg, 0.084 USD/kWh): they carry the "legacy core result" banner. */
export const LEGACY_PATHS: string[] = ['/overview', '/results', '/methodology', '/research']

/** Sub-pages of the Hypotheses section (/hypotheses/<slug>); the section's root page holds the evidence matrix. */
export const HYPOTHESIS_PAGES: { slug: string; label: string; title: string }[] = [
  { slug: '', label: 'Evidence matrix', title: 'Evidence matrix: four hypotheses' },
  { slug: 'catalyst', label: 'Catalysts', title: 'Catalyst comparison and heat integration' },
  { slug: 'economics', label: 'Singapore economics', title: 'Singapore techno-economics' },
  { slug: 'purification', label: 'Purification', title: 'Hydrogen purification: PSA and membrane' },
  { slug: 'end-use', label: 'End use and carbon', title: 'End-use comparison and life-cycle carbon' },
  { slug: 'validation', label: 'Validation', title: 'Research validation summary' },
  { slug: 'aspen-evidence', label: 'Aspen evidence', title: 'Aspen Plus V15 evidence gallery' },
]

export const hypothesisPath = (slug: string): string => (slug ? `/hypotheses/${slug}`  : '/hypotheses')

/** Document title for a pathname ("AmCraX - <page>"). */
export function titleFor(pathname: string): string {
  if (isPlatformPath(pathname)) return 'AmCraX platform'
  const hp = HYPOTHESIS_PAGES.find((x) => x.slug && pathname === hypothesisPath(x.slug))
  if (hp) return `${hp.title} - AmCraX`
  const r = SITE_ROUTES.find((x) => x.path === pathname)
  if (pathname === '/') return 'AmCraX - Interactive ammonia cracking process simulator'
  return r ? `${r.title} - AmCraX` : 'AmCraX - Ammonia cracking simulation and optimisation platform'
}

/** Split "#/results#lcoh" style locations: the router hands us pathname + hash separately; this normalises an anchor id. */
export function anchorId(hash: string): string | null {
  const id = hash.replace(/^#/, '')
  return id ? decodeURIComponent(id) : null
}
