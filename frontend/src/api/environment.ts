import { getJson } from './client'
import type { DataSource } from './types'
import { postJson } from './postjson'

export interface CiFactor { name: string; value: number; unit: string; provenance: string; source: string; note?: string | null; overridden?: boolean }
export interface CiResult {
  case_id: string; input_source?: DataSource; source: DataSource; method: string; system_boundary: string
  scenario: string; nh3_route: string; heating_option: string; grid: string
  total_kgCO2e_per_kgH2: number | null
  breakdown_kgCO2e_per_kgH2: Record<string, number | null>
  h2_product_kg_h?: number | null; kg_nh3_per_kg_h2?: number | null; heat_deficit_kW?: number | null; electricity_kW?: number | null
  transport_distance_km: number | null
  factors?: CiFactor[]
  notes?: string[]
}
export interface CiOverrides { distance_km?: number; grid_ef_kg_per_kWh?: number }
export interface RefLine { label: string; value_kgCO2e_per_kgH2: number; source: string; note?: string }
export interface StoredEnv { scenarios?: Record<string, CiResult>; comparison: { rows: unknown[]; reference_lines: RefLine[]; system_boundary: string; method: string; notes?: string[] } }

export const ROUTES = ['green', 'blue', 'grey'] as const
export const HEATING = ['natural_gas', 'self_firing', 'electric'] as const
export const HEATING_LABEL: Record<string, string> = { natural_gas: 'imported natural gas', self_firing: 'tail gas + NH3 self-firing', electric: 'electric heating' }

export const postCarbon = (caseId: string, scenario: string, overrides: CiOverrides, signal?: AbortSignal) =>
  postJson<{ result: CiResult }>('/api/environment/carbon-intensity', { case_id: caseId, scenario, overrides }, signal).then((r) => r.result)

/** All 3 x 3 route/heating scenarios for one case (python engine; nine small POSTs). */
export const fetchAllScenarios = (caseId: string, overrides: CiOverrides, signal?: AbortSignal) =>
  Promise.all(ROUTES.flatMap((r) => HEATING.map((h) => postCarbon(caseId, `${r}/${h}`, overrides, signal))))

export const fetchStoredEnv = (caseId: string, signal?: AbortSignal) =>
  getJson<StoredEnv>(`/api/data/analysis/environmental_${encodeURIComponent(caseId)}`, signal)
