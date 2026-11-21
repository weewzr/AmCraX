import { useMemo } from 'react'
import { getJson } from '../api/client'
import type { RefItem } from '../api/reports'
import type { SimulationResult } from '../api/types'
import { useAsync, type Async } from '../features/common/useAsync'
import { useData } from '../data/DataContext'

/** Documents are read through the same wrapper as the dashboard ("/api/..." logical paths; in SNAPSHOT mode they are answered by the bundled mirror). */
const cache = new Map<string, Promise<unknown>>()
export function cachedJson<T>(url: string): Promise<T> {
  let p = cache.get(url) as Promise<T> | undefined
  if (!p) {
    p = getJson<T>(url)
    p.catch(() => cache.delete(url)) // do not cache failures
    cache.set(url, p)
  }
  return p
}

/** True once a mode is resolved and real stored results can be read (LIVE or SNAPSHOT, never DEMO). */
export function useResultsReady(): boolean {
  const { phase, mode } = useData()
  return phase === 'ready' && (mode === 'LIVE' || mode === 'SNAPSHOT')
}

export function useJson<T>(url: string | null): Async<T> {
  const ready = useResultsReady()
  return useAsync(() => cachedJson<T>(url as string), [url], ready && url !== null)
}

export interface Rows<R> { rows: R[]; source_note?: string }
export const dataUrl = (category: string, name: string) => `/api/data/${category}/${name}`

export const useRows = <R,>(category: string, name: string): Async<Rows<R>> => useJson<Rows<R>>(dataUrl(category, name))

/** Reference list: map of citekey -> reference. */
export function useRefs(): Async<RefItem[]> {
  return useJson<RefItem[]>('/api/references')
}

export interface DatasetIndexItem { name: string; rows?: number }
export interface RunCount { aspenCases: number; sensitivityRuns: number; equilibriumPoints: number; total: number }

/**
 * Number of Aspen Plus runs behind the published results: stored Aspen cases (baselines, scenarios, optimisation candidates)
 * + rows of the Aspen sensitivity studies (aspen_*, excluding the native-STEMP re-runs, which repeat baseline points)
 * + points of the RGibbs equilibrium grid. Pure function so that it can be unit-tested.
 */
export function countAspenRuns(cases: Pick<SimulationResult, 'source'>[], sensitivity: DatasetIndexItem[], equilibriumPoints: number): RunCount {
  const aspenCases = cases.filter((c) => c.source === 'aspen_plus_v15').length
  const sensitivityRuns = sensitivity.filter((d) => /^aspen_/.test(d.name) && !/^aspen_native/.test(d.name)).reduce((a, d) => a + (d.rows ?? 0), 0)
  return { aspenCases, sensitivityRuns, equilibriumPoints, total: aspenCases + sensitivityRuns + equilibriumPoints }
}

/** Short, plain-language mode description for the footer and header notice. */
export function exportDate(manifestUtc: string | undefined | null): string | null {
  if (!manifestUtc) return null
  const m = manifestUtc.match(/^(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : null
}

/** One row of the validation matrix as stored (the fields the site quotes). */
export interface MatrixItem {
  id: string; family?: string; status: string; value?: number | null; tolerance?: number | null
  model_component?: string; validation_method?: string; reference?: string; actual_result?: string
}
/** The full validation matrix, keyed by item id (empty until loaded). */
export function useMatrix(): { items: MatrixItem[]; byId: Map<string, MatrixItem>; ready: boolean } {
  const m = useJson<unknown>('/api/validation')
  return useMemo(() => {
    const body = m.phase === 'ready' ? m.data : null
    const arr: MatrixItem[] = Array.isArray(body) ? (body as MatrixItem[]) : Array.isArray((body as { items?: unknown } | null)?.items) ? ((body as { items: MatrixItem[] }).items) : []
    return { items: arr, byId: new Map(arr.map((x) => [x.id, x])), ready: arr.length > 0 }
  }, [m])
}

export interface ValidationSummary {
  count: number
  by_status: { pass?: number; fail?: number; informational?: number; not_run?: number }
  file_summary?: {
    n_items: number
    by_family: Record<string, { n_items: number; pass: number; fail: number; not_run: number; informational: number }>
    failure_root_causes?: { cause: string; description: string; n_items: number; items: string[] }[]
  }
  meta?: { generated_utc?: string }
}
export const useValidationSummary = (): Async<ValidationSummary> => useJson<ValidationSummary>('/api/validation/summary')
