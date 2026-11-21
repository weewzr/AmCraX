import { getJson, isSnapshotActive, staticAssetUrl } from './client'
import { withBase } from './url'

export interface ReportItem { key: string; title: string; kind: string; file: string; path: string; bytes: number | null; modified_utc: string | null; url: string }
export interface FigureItem { name: string; url: string; size_bytes?: number }
export interface ShotItem {
  file: string; title: string; navigation_path?: string; what_is_shown?: string; why_it_matters?: string; status?: string
  reason_if_not?: string | null; visually_verified?: boolean; captured_local_time?: string; url: string
}
export interface ShotsResponse { aspen: ShotItem[]; aspen_manifest?: { aspen_version?: string; note?: string; model_file?: string }; dashboard?: { file: string; url: string; bytes?: number }[]; source?: string }
export interface RefItem { citekey: string; apa7: string; doi?: string | null; url?: string | null; doi_verified?: boolean; in_local_library?: boolean; verification?: string }
export interface TraceItem {
  model_component: string; source_citekey?: string; page?: string; locator?: string; operating_range?: string
  limitations?: string[] | string; usable?: boolean; implemented_in?: string; catalyst_reactor_assumptions?: string
}

/** Solved .apw workspace files are not version-controlled or published (only .inp and .bkp are), so they are never offered as downloads. */
export const isPublishedReport = (r: ReportItem): boolean => !/\.apw$/i.test(r.file)
export const fetchReports = (s?: AbortSignal) => getJson<{ count: number; reports: ReportItem[] }>('/api/reports', s).then((r) => r.reports.filter(isPublishedReport))
export const fetchFigures = (s?: AbortSignal) => getJson<{ count: number; figures: FigureItem[] }>('/api/figures', s).then((r) => r.figures)
export const fetchShots = (s?: AbortSignal) => getJson<ShotsResponse>('/api/screenshots', s)
export const fetchRefs = (s?: AbortSignal) => getJson<RefItem[]>('/api/references', s)
export const fetchTrace = (s?: AbortSignal) => getJson<TraceItem[]>('/api/traceability', s)

/** Static files (downloads, PNGs) are served by FastAPI; under the Vite dev server only /api and /figures are proxied, so point at the API origin there. */
export const assetUrl = (u: string): string => (isSnapshotActive() ? staticAssetUrl(u) : import.meta.env.DEV ? `http://127.0.0.1:8000${u}` : withBase(u))
