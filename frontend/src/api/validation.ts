import { ApiError, getJson } from './client'

/** GET /api/data/{category}/{name} (generic CSV/JSON dataset endpoint). */
export interface Dataset {
  name: string
  category: string
  columns: string[]
  rows: Record<string, unknown>[]
  source_note?: string
}
export type DataCategory = 'sensitivity' | 'validation' | 'optimisation' | 'analysis'

export const fetchDataset = (category: DataCategory, name: string, signal?: AbortSignal) =>
  getJson<Dataset>(`/api/data/${category}/${encodeURIComponent(name)}`, signal)

export type ValidationStatus = 'pass' | 'fail' | 'not_run' | 'informational'
export interface ValidationItem {
  id: string
  model_component: string
  validation_method: string
  reference: string
  expected_behaviour: string
  actual_result: string
  metric: string
  tolerance: string
  status: ValidationStatus
  limitations: string
  evidence_files: string[]
}

const STATUSES: ValidationStatus[] = ['pass', 'fail', 'not_run', 'informational']
const str = (v: unknown): string => (v === null || v === undefined ? '' : typeof v === 'string' ? v : JSON.stringify(v))

/** Accepts either a bare array or {items|matrix|rows|checks: [...]}; unknown status values become not_run (never pass). */
export function normaliseMatrix(body: unknown): ValidationItem[] {
  let arr: unknown[] = []
  if (Array.isArray(body)) arr = body
  else if (body && typeof body === 'object') {
    const o = body as Record<string, unknown>
    const hit = ['items', 'matrix', 'rows', 'checks', 'validation'].map((k) => o[k]).find(Array.isArray)
    if (Array.isArray(hit)) arr = hit
  }
  return arr
    .filter((r): r is Record<string, unknown> => !!r && typeof r === 'object')
    .map((r, i) => {
      const st = str(r.status).toLowerCase() as ValidationStatus
      const ev = r.evidence_files
      return {
        id: str(r.id) || `item-${i + 1}`,
        model_component: str(r.model_component),
        validation_method: str(r.validation_method),
        reference: str(r.reference),
        expected_behaviour: str(r.expected_behaviour),
        actual_result: str(r.actual_result),
        metric: str(r.metric),
        tolerance: str(r.tolerance),
        status: STATUSES.includes(st) ? st : 'not_run',
        limitations: str(r.limitations),
        evidence_files: Array.isArray(ev) ? ev.map(str) : ev ? [str(ev)] : [],
      }
    })
}

export async function fetchValidationMatrix(signal?: AbortSignal): Promise<ValidationItem[]> {
  return normaliseMatrix(await getJson<unknown>('/api/validation', signal))
}

export { ApiError }
