import { IS_PAGES, withBase } from './url'
import type {
  CaseSummary, Flowsheet, HealthInfo, SimulationResult, SnapshotManifest,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** GET a JSON document. Throws ApiError on non-2xx or when the body is not JSON (e.g. SPA fallback HTML). */
export async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) throw new ApiError(`${url} -> HTTP ${res.status}`, res.status)
  const text = await res.text()
  try {
    return JSON.parse(text) as T
  } catch {
    throw new ApiError(`${url} did not return JSON`, res.status)
  }
}

// ---- live API (FastAPI, proxied by Vite at /api) ----
export const fetchHealth = (signal?: AbortSignal) => getJson<HealthInfo>('/api/health', signal)
export const fetchFlowsheet = (signal?: AbortSignal) => getJson<Flowsheet>('/api/flowsheet', signal)
export async function fetchCaseList(signal?: AbortSignal): Promise<CaseSummary[]> {
  const body = await getJson<CaseSummary[] | { cases: CaseSummary[] }>('/api/cases', signal)
  return Array.isArray(body) ? body : body.cases
}
export const fetchCase = (caseId: string, signal?: AbortSignal) =>
  getJson<SimulationResult>(`/api/cases/${encodeURIComponent(caseId)}`, signal)

// ---- static snapshot (written by scripts/export_snapshot.py, served from /snapshot/) ----
export async function fetchManifest(signal?: AbortSignal): Promise<SnapshotManifest> {
  const m = await getJson<SnapshotManifest>(withBase('/snapshot/manifest.json'), signal)
  if (m === null || typeof m !== 'object' || Array.isArray(m)) throw new ApiError('invalid snapshot manifest', 200)
  return m
}
export interface SnapshotCaseRef { case_id: string; source?: string | null; file: string }
/** scripts/export_snapshot.py layout: /snapshot/flowsheet.json, /snapshot/cases.json (index), /snapshot/cases/<id>.json */
export const fetchSnapshotFlowsheet = (signal?: AbortSignal) => getJson<Flowsheet>(withBase('/snapshot/flowsheet.json'), signal)
export const fetchSnapshotCaseIndex = (signal?: AbortSignal) => getJson<SnapshotCaseRef[]>(withBase('/snapshot/cases.json'), signal)
export const fetchSnapshotCase = (ref: SnapshotCaseRef, signal?: AbortSignal) => getJson<SimulationResult>(withBase(`/snapshot/${ref.file}`), signal)
// ---- global fetch wrapper: API base override + SNAPSHOT-mode mirror (installed once from main.tsx) ----
/** Optional API origin override (build-time VITE_API_BASE), e.g. to point a static build at another / unused port. */
export const API_BASE: string = ((import.meta as unknown as { env?: Record<string, string | undefined> }).env?.VITE_API_BASE ?? '').replace(/\/$/, '')
let snapshotActive = IS_PAGES // the static Pages build never contacts the API, not even before the mode is resolved
export const setSnapshotActive = (on: boolean) => { snapshotActive = on }
export const isSnapshotActive = () => snapshotActive

/** Map a live API GET path onto the static mirror written by scripts/export_snapshot.py, or null when there is none. */
export function snapshotUrlFor(path: string): string | null {
  const [p] = path.split('?')
  let m: RegExpMatchArray | null
  const SIMPLE: Record<string, string> = {
    '/api/flowsheet': '/snapshot/flowsheet.json',
    '/api/scenarios/definitions': '/snapshot/scenarios_definitions.json',
    '/api/scenarios/comparison': '/snapshot/api/scenarios_comparison.json',
    '/api/validation': '/snapshot/api/validation.json',
    '/api/validation/summary': '/snapshot/api/validation_summary.json',
    '/api/references': '/snapshot/api/references.json',
    '/api/traceability': '/snapshot/api/traceability.json',
    '/api/figures': '/snapshot/api/figures.json',
    '/api/reports': '/snapshot/api/reports.json',
    '/api/screenshots': '/snapshot/api/screenshots.json',
    '/api/kinetics/catalysts': '/snapshot/api/kinetics_catalysts.json',
    '/api/economics/defaults': '/snapshot/api/economics_defaults.json',
    '/api/environment/factors': '/snapshot/api/environment_factors.json',
    '/api/optimisation/results': '/snapshot/api/optimisation_results.json',
  }
  if (SIMPLE[p]) return SIMPLE[p]
  if ((m = p.match(/^\/api\/cases\/([^/]+)$/))) return `/snapshot/cases/${m[1]}.json`
  if ((m = p.match(/^\/api\/data\/([^/]+)$/))) return `/snapshot/data/${m[1]}.json`
  if ((m = p.match(/^\/api\/data\/([^/]+)\/([^/]+)$/))) return `/snapshot/data/${m[1]}/${decodeURIComponent(m[2]).replace(/\.(csv|json)$/i, '')}.json`
  if ((m = p.match(/^\/api\/heat-integration\/([^/]+)$/))) return `/snapshot/data/analysis/heat_integration_${m[1]}.json`
  if (p === '/api/sensitivity/datasets') return '/snapshot/data/sensitivity.json'
  if ((m = p.match(/^\/api\/sensitivity\/datasets\/([^/]+)$/))) return `/snapshot/data/sensitivity/${decodeURIComponent(m[1])}.json`
  if (STATIC_PREFIXES.some((x) => p.startsWith(x))) return `/snapshot${p}`
  return null
}
const STATIC_PREFIXES = ['/figures/', '/aspen-screenshots/', '/dashboard-screenshots/']

/** Static assets (PNG, deliverable links) referenced from <img>/<a>: in SNAPSHOT mode they come from the mirror, in dev from the API origin. */
export function staticAssetUrl(u: string): string {
  if (snapshotActive && STATIC_PREFIXES.some((x) => u.startsWith(x))) return withBase(`/snapshot${u}`)
  return withBase(u)
}

function notInSnapshot(path: string): Response {
  return new Response(JSON.stringify({ error: 'snapshot_mode', detail: `${path} needs the live API; not available in SNAPSHOT mode.` }), {
    status: 503, headers: { 'Content-Type': 'application/json' },
  })
}

export function installFetchWrapper(): void {
  const w = window as unknown as { __amcraxFetch?: boolean }
  if (w.__amcraxFetch) return
  w.__amcraxFetch = true
  const orig = window.fetch.bind(window)
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname + input.search : input.url
    const isApi = url.startsWith('/api/') || url.startsWith('/figures/')
    if (!isApi) return orig(input, init)
    if (snapshotActive) {
      const method = (init?.method ?? 'GET').toUpperCase()
      const target = method === 'GET' ? snapshotUrlFor(url) : null
      if (!target) return notInSnapshot(url)
      const res = await orig(withBase(target), init)
      if (res.ok && url.startsWith('/api/heat-integration/')) {
        const body = await res.json()
        const id = decodeURIComponent(url.split('?')[0].split('/').pop() ?? '')
        return new Response(JSON.stringify(body && 'result' in body ? body : { case_id: id, dT_min_K: body?.dT_min_K ?? 20, result: body }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      if (res.ok && url.split('?')[0] === '/api/sensitivity/datasets') {
        // the mirror holds the generic /api/data/sensitivity listing; reshape it to the sensitivity endpoint's {datasets: [...]}
        const body = await res.json()
        const datasets = ((body?.items ?? []) as Record<string, unknown>[]).map((i) => ({ name: i.name, file: i.file, columns: i.columns ?? [], rows: i.rows ?? 0 }))
        return new Response(JSON.stringify({ count: datasets.length, datasets }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      return res
    }
    return orig(API_BASE ? API_BASE + url : input, init)
  }
}


