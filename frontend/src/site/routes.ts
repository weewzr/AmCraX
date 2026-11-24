/**
 * Route table of the public site and helpers shared by the site and the platform. Hash routes: "#/results", "#/platform/pfd".
 *
 * NAV_GROUPS is the single source of the site structure: the top navigation, the footer, the command palette, the page
 * breadcrumbs and the section numbers ("2.3") are all derived from it, so a moved or added page cannot leave a stale number.
 */
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

export interface NavPage {
  /** route path (pathname), optionally with an in-page anchor: '/docs#downloads' */
  to: string
  /** short label used in menus */
  label: string
  /** page title (document title, breadcrumb) */
  title: string
  /** one line for the command palette */
  hint?: string
}
export interface NavGroup { id: string; label: string; pages: NavPage[] }

/**
 * The five top-level groups of the public site, in order. Every public route appears exactly once as a page without an anchor;
 * entries with an anchor ("#lca", "#downloads") are shortcuts into a page and get no section number.
 */
export const NAV_GROUPS: NavGroup[] = [
  { id: 'simulator', label: 'Simulator', pages: [
    { to: '/', label: 'Process simulator', title: 'Process simulator', hint: 'Interactive flowsheet solved in the browser' },
    { to: '/pfd', label: 'Process flow diagram', title: 'Interactive process flow diagram', hint: 'Stored Aspen results on the flowsheet' },
  ] },
  { id: 'findings', label: 'Findings', pages: [
    { to: '/hypotheses', label: 'Hypotheses and verdicts', title: 'Hypothesis testing', hint: 'Evidence matrix: four hypotheses' },
    { to: '/hypotheses/catalyst', label: 'Catalysts and heat integration', title: 'Catalyst comparison and heat integration', hint: 'Hypothesis H3' },
    { to: '/hypotheses/economics', label: 'Singapore economics', title: 'Singapore techno-economics', hint: 'Hypothesis H2' },
    { to: '/hypotheses/purification', label: 'Purification', title: 'Hydrogen purification: PSA and membrane', hint: 'Hypothesis H4' },
    { to: '/hypotheses/end-use', label: 'End use and carbon', title: 'End-use comparison and life-cycle carbon', hint: 'Hypotheses H1 and H2' },
    { to: '/hypotheses/end-use#lca', label: 'Environmental analysis', title: 'Environmental analysis', hint: 'Carbon intensity by ammonia route' },
  ] },
  { id: 'results', label: 'Results', pages: [
    { to: '/overview', label: 'Overview', title: 'Overview', hint: 'The project and the baseline case at a glance' },
    { to: '/results', label: 'Engineering results', title: 'Engineering results', hint: 'Conversion, duties, heat integration, cost and carbon' },
    { to: '/why', label: 'Why ammonia cracking', title: 'Why ammonia cracking', hint: 'Background' },
  ] },
  { id: 'methods', label: 'Methods and validation', pages: [
    { to: '/methodology', label: 'Methodology', title: 'Simulation methodology', hint: 'Aspen model, Python models, assumptions' },
    { to: '/research', label: 'Research and validation', title: 'Research and validation', hint: 'Validation matrix, failures, references' },
    { to: '/hypotheses/validation', label: 'Validation by evidence kind', title: 'Research validation summary', hint: 'Checks kept apart by evidence kind' },
    { to: '/hypotheses/aspen-evidence', label: 'Aspen evidence gallery', title: 'Aspen Plus V15 evidence gallery', hint: 'Genuine Aspen Plus V15 captures' },
    { to: '/architecture', label: 'Software architecture', title: 'Software architecture', hint: 'Aspen, Python, FastAPI, React' },
  ] },
  { id: 'docs', label: 'Docs and downloads', pages: [
    { to: '/docs', label: 'Documentation and downloads', title: 'Documentation and downloads', hint: 'Report, deck, validation documents' },
    { to: '/docs#downloads', label: 'Technical report', title: 'Technical report', hint: 'PDF and Word downloads' },
    { to: '/about', label: 'About and limits', title: 'About AmCraX', hint: 'Origin, credits, what AmCraX does not claim' },
  ] },
]

const isAnchor = (to: string) => to.includes('#')

/** Section number of a page ("2.3"), derived from its position in NAV_GROUPS; anchors are not numbered. */
export function sectionOf(pathname: string): string | null {
  for (const [gi, g] of NAV_GROUPS.entries()) {
    const numbered = g.pages.filter((p) => !isAnchor(p.to))
    const i = numbered.findIndex((p) => p.to === pathname)
    if (i >= 0) return `${gi + 1}.${i + 1}`
  }
  return null
}

/** Group and page of a pathname (anchor entries are skipped), or null for unknown paths. */
export function locate(pathname: string): { group: NavGroup; page: NavPage; section: string } | null {
  for (const g of NAV_GROUPS) {
    const page = g.pages.find((p) => !isAnchor(p.to) && p.to === pathname)
    if (page) return { group: g, page, section: sectionOf(pathname) as string }
  }
  return null
}

/** Breadcrumb line shown above each page title: "Section 2.3 · Findings". */
export function eyebrowFor(pathname: string): string | null {
  const l = locate(pathname)
  return l ? `Section ${l.section} · ${l.group.label}` : null
}

export interface SiteRoute { path: string; label: string; title: string; section: string }

/** Every public page once, in navigation order (anchor shortcuts excluded); the section number is derived, never typed. */
export const SITE_ROUTES: SiteRoute[] = NAV_GROUPS.flatMap((g) => g.pages.filter((p) => !isAnchor(p.to)))
  .map((p) => ({ path: p.to, label: p.label, title: p.title, section: sectionOf(p.to) as string }))

/** Active group of a location: the group that holds the page (the anchor entries never decide it). */
export function activeGroup(pathname: string): string | null {
  return locate(pathname)?.group.id ?? null
}

/** Active state of one menu entry: exact page match; an anchor entry is active only on its own anchor. */
export function pageActive(p: NavPage, pathname: string, hash = ''): boolean {
  const [path, anchor] = p.to.split('#')
  if (anchor) return pathname === path && hash === `#${anchor}`
  if (pathname !== path) return false
  // the page entry is not "current" while its anchor shortcut is the location
  return !NAV_GROUPS.some((g) => g.pages.some((q) => q.to === `${pathname}${hash}` && isAnchor(q.to)))
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

export const hypothesisPath = (slug: string): string => (slug ? `/hypotheses/${slug}` : '/hypotheses')

/** Old or alternative paths that redirect to a current page (kept so that shared links keep working). */
export const REDIRECTS: { from: string; to: string }[] = [
  { from: '/simulator', to: '/' },
  { from: '/home', to: '/' },
  { from: '/environment', to: '/hypotheses/end-use#lca' },
  { from: '/validation', to: '/hypotheses/validation' },
  { from: '/aspen-evidence', to: '/hypotheses/aspen-evidence' },
  { from: '/downloads', to: '/docs#downloads' },
]

/** Document title for a pathname ("<page> - AmCraX"). */
export function titleFor(pathname: string): string {
  if (isPlatformPath(pathname)) return 'AmCraX platform'
  if (pathname === '/') return 'AmCraX - Interactive ammonia cracking process simulator'
  const l = locate(pathname)
  return l ? `${l.page.title} - AmCraX` : 'AmCraX - Ammonia cracking simulation and optimisation platform'
}

/** Split "#/results#lcoh" style locations: the router hands us pathname + hash separately; this normalises an anchor id. */
export function anchorId(hash: string): string | null {
  const id = hash.replace(/^#/, '')
  return id ? decodeURIComponent(id) : null
}
