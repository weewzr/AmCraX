/**
 * One place for every asset / data URL that is not an API call.
 *
 * The app is built twice: for local use (Vite base "/") and for GitHub Pages (`vite build --mode pages`,
 * base "/AmCraX/"). Code keeps writing *logical* absolute paths ("/snapshot/manifest.json", "/figures/x.png",
 * "/downloads/report.pdf"); `withBase` turns them into URLs that are correct under the active base.
 */
export const BASE_URL: string = import.meta.env.BASE_URL || '/'

/** True in the static GitHub Pages build: the API is never contacted and the app always runs on the bundled snapshot. */
export const IS_PAGES: boolean = import.meta.env.MODE === 'pages'

/** Prefix a logical absolute path ("/x/y" or "x/y") with the base. Absolute http(s)/data/hash URLs are returned unchanged. */
export function withBase(path: string, base: string = BASE_URL): string {
  if (/^([a-z][a-z0-9+.-]*:|#|\/\/)/i.test(path)) return path
  const b = base.endsWith('/') ? base : `${base}/`
  return b + path.replace(/^\/+/, '')
}

/** Inverse of `withBase` for a pathname: "/AmCraX/snapshot/a.json" -> "/snapshot/a.json". */
export function stripBase(pathname: string, base: string = BASE_URL): string {
  const b = base.endsWith('/') ? base : `${base}/`
  if (b === '/') return pathname
  if (pathname === b.slice(0, -1)) return '/'
  return pathname.startsWith(b) ? `/${pathname.slice(b.length)}` : pathname
}

/** Absolute public origin of the published site (used only for share metadata and visible links, never for fetching). */
export const SITE_URL = 'https://weewzr.github.io/AmCraX/'
export const GITHUB_URL = 'https://github.com/weewzr/AmCraX'
export const GITHUB_DOCS_URL = `${GITHUB_URL}/tree/main/docs`
export const PORTFOLIO_URL = 'https://weewzr.github.io/weewzr/'
export const PORTFOLIO_PROJECT_URL = 'https://weewzr.github.io/weewzr/projects/amcrax/'
