import { getJson } from './client'
import { postJson, type DataFile } from './postjson'

export type Row = Record<string, number | string | boolean | null>
export interface DecisionVar { lower: number; upper: number; optimum: number | null; at_bound: 'upper' | 'lower' | null | string; unit?: string; bounds_basis?: string }
export interface OptMetric { metric: string; optimum: number | null; baseline: number | null; delta: number | null; delta_rel: number | null; better: boolean }
export interface OptResult {
  id?: string; variant?: string; objective: string; label: string; metric: string; sense: 'min' | 'max' | string; engine?: string; source?: string; created_utc?: string
  decision_variables: Record<string, DecisionVar>
  fixed_inputs?: Record<string, unknown>
  constraints?: { settings?: Record<string, unknown>; values_at_optimum?: Record<string, number | null>; active?: string[]; definitions?: Record<string, string>; convention?: string }
  optimum_metrics?: Record<string, unknown>; baseline_metrics?: Record<string, unknown>
  improvement?: OptMetric
  bound_active?: string[]; driver?: string; model_limitation?: string[]; limitations?: string[]
  solver?: { method?: string; success?: boolean; feasible?: boolean; nfev_objective?: number; model_runs?: number; model_failures?: number; de_message?: string; polish?: { success?: boolean; message?: string } }
  flatness?: Record<string, { tolerance_rel: number; range_within_tol: number[]; fraction_of_bound_range: number }>
}
export interface ParetoFront { objectives: string[]; senses: string[]; overlay: string; points: Row[]; n_points: number; unconstrained_front_infeasible_points?: Row[] }
export interface ConflictPair { pair: string[]; senses: string[]; spearman_rho_min_sense: number; n_feasible_points: number; n_non_dominated: number; n_distinct_non_dominated: number; classification: string }
export interface ParetoFile { n_grid_points?: number; n_feasible?: number; method?: string; fronts: ParetoFront[]; conflicts?: { method?: string; caveat?: string; pairs: ConflictPair[] } }

export const fetchData = <T>(name: string, s?: AbortSignal) => getJson<T>(`/api/data/optimisation/${name}`, s)
export const fetchGrid = (s?: AbortSignal) => getJson<DataFile<Row>>('/api/data/optimisation/design_grid', s).then((d) => d.rows ?? [])

export interface RunRequest { case_id?: string; objective: string; method: string; bounds?: Record<string, [number, number]>; constraints?: Record<string, number | boolean | null> }
export const runOptimisation = (req: RunRequest, s?: AbortSignal) => postJson<{ source: string; result: OptResult }>('/api/optimisation/run', req, s)