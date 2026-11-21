import type { CaseInputs, DataSource } from './types'
import { requestJson } from './http'

export type Engine = 'aspen' | 'python'
export type JobState = 'queued' | 'running' | 'succeeded' | 'failed' | 'timeout'

export interface Job {
  job_id: string
  kind: string
  engine: string
  label: string
  state: JobState
  message: string | null
  created_utc: string
  started_utc: string | null
  finished_utc: string | null
  queue_time_s: number | null
  run_time_s: number | null
  case_id: string | null
  progress: unknown
  result: unknown
}

export const startSimulation = (inputs: CaseInputs, engine: Engine, signal?: AbortSignal) =>
  requestJson<Job>('/api/simulation/run', { method: 'POST', body: { inputs, engine }, signal })
export const fetchJob = (id: string, signal?: AbortSignal) => requestJson<Job>(`/api/jobs/${encodeURIComponent(id)}`, { signal })

export interface ScenarioDef { id: string; label: string; overrides: Record<string, unknown>; rationale: string }
export interface ScenarioDefinitions {
  description?: string
  process_scenarios: ScenarioDef[]
  overlays?: Record<string, unknown>
}
export const fetchScenarioDefinitions = (signal?: AbortSignal) => requestJson<ScenarioDefinitions>('/api/scenarios/definitions', { signal })

export interface CompareCase { case_id: string; source: DataSource; converged: boolean }
export interface CompareRow { kpi: string; [col: string]: number | string | null }
export interface ChangedInput { input: string; values: Record<string, number | string | boolean | null> }
export interface CompareResponse {
  cases: CompareCase[]
  reference_case: string
  columns: string[]
  table: CompareRow[]
  changed_inputs: ChangedInput[]
}
export const compareCases = (caseIds: string[], signal?: AbortSignal) =>
  requestJson<CompareResponse>('/api/scenarios/compare', { method: 'POST', body: { case_ids: caseIds, engine: 'python' }, signal })

/** Stored LCOH / carbon-intensity overlay table. Shape is not fixed by the contract: parsed defensively in features/simulation/overlay.ts. */
export const fetchScenarioComparison = (signal?: AbortSignal) => requestJson<unknown>('/api/scenarios/comparison', { signal })

export const exportUrl = (caseId: string, format: 'json' | 'csv' | 'xlsx') =>
  `/api/export/${encodeURIComponent(caseId)}?format=${format}`
