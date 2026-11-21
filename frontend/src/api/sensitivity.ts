import type { CaseInputs } from './types'
import type { Engine, Job } from './simulation'
import { requestJson } from './http'

export interface DatasetInfo { name: string; file: string; columns: string[]; rows: number; size_bytes?: number; modified_utc?: string }
export type Cell = number | string | boolean | null
export type DataRow = Record<string, Cell>
export interface Dataset { name: string; columns: string[]; rows: DataRow[]; count: number; source_note?: string }

export const fetchDatasets = (signal?: AbortSignal) =>
  requestJson<{ count: number; datasets: DatasetInfo[] }>('/api/sensitivity/datasets', { signal })
export const fetchDataset = (name: string, signal?: AbortSignal) =>
  requestJson<Dataset>(`/api/sensitivity/datasets/${encodeURIComponent(name)}`, { signal })

export interface SweepRequest { variable: string; values: number[]; base_inputs?: Partial<CaseInputs>; engine: Engine }
export interface SweepResponse { variable: string; engine: string; source: string; count: number; rows: DataRow[] }
/** python engine answers synchronously with rows (HTTP 200); aspen answers with a job (HTTP 202). */
export const runSweep = (req: SweepRequest, signal?: AbortSignal) =>
  requestJson<SweepResponse | Job>('/api/sensitivity/run', { method: 'POST', body: req, signal })

export function isJob(x: SweepResponse | Job): x is Job {
  return typeof (x as Job).job_id === 'string'
}
