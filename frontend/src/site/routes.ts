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

/** The nine public sections, in order. Each has its own route; "/" is the landing page (section 1). */
export const SITE_ROUTES: SiteRoute[] = [
  { path: '/', label: 'Overview', title: 'Overview', section: 1 },
  { path: '/why', label: 'Why cracking', title: 'Why ammonia cracking', section: 2 },
  { path: '/pfd', label: 'Process flow', title: 'Interactive process flow diagram', section: 3 },
  { path: '/methodology', label: 'Methodology', title: 'Simulation methodology', section: 4 },
  { path: '/results', label: 'Results', title: 'Engineering results', section: 5 },
  { path: '/architecture', label: 'Architecture', title: 'Software architecture', section: 6 },
  { path: '/research', label: 'Research', title: 'Research and validation', section: 7 },
  { path: '/docs', label: 'Docs', title: 'Documentation and downloads', section: 8 },
  { path: '/about', label: 'About', title: 'About AmCraX', section: 9 },
]

/** Document title for a pathname ("AmCraX - <page>"). */
export function titleFor(pathname: string): string {
  if (isPlatformPath(pathname)) return 'AmCraX platform'
  const r = SITE_ROUTES.find((x) => x.path === pathname)
  return r && r.path !== '/' ? `${r.title} - AmCraX` : 'AmCraX - Ammonia cracking simulation and optimisation platform'
}

/** Split "#/results#lcoh" style locations: the router hands us pathname + hash separately; this normalises an anchor id. */
export function anchorId(hash: string): string | null {
  const id = hash.replace(/^#/, '')
  return id ? decodeURIComponent(id) : null
}
