import { getJson } from './client'
import type { DataSource } from './types'

export interface HeatStream {
  id: string
  name: string
  kind: 'hot' | 'cold' | string
  supply_temperature_C: number
  target_temperature_C: number
  duty_kW: number
  included_in?: string[]
  curve_T_C?: number[]
  curve_H_kW?: number[]
}
export interface HeatTargets {
  label: string
  dT_min_K: number
  hot_utility_kW: number | null
  cold_utility_kW: number | null
  heat_recovery_kW: number | null
  pinch_shifted_C: number | null
  pinch_hot_C: number | null
  pinch_cold_C: number | null
  threshold_problem?: boolean
  hot_composite_H_kW: number[]
  hot_composite_T_C: number[]
  cold_composite_H_kW: number[]
  cold_composite_T_C: number[]
  gcc_H_kW: number[]
  gcc_T_shifted_C: number[]
}
export interface HeatConfig {
  id: string
  label: string
  external_heating_kW: number | null
  external_cooling_kW: number | null
  process_heat_recovered_kW: number | null
  tailgas_heat_used_kW: number | null
  reduction_vs_no_recovery: number | null
  specific_heat_demand_kWh_per_kgH2: number | null
  basis: string
}
export interface FeheInfo {
  present_in_simulation: boolean
  duty_kW: number | null
  duty_source?: string
  hot_in_C: number | null
  hot_out_C: number | null
  cold_in_C: number | null
  cold_out_C: number | null
  hot_end_approach_K: number | null
  cold_end_approach_K: number | null
  min_internal_approach_K: number | null
  temperature_cross?: boolean
  approach_violation?: boolean
  lmtd_K: number | null
  ua_lmtd_kW_K: number | null
  ua_segmented_kW_K: number | null
  U_assumed_W_m2K: number | null
  U_range_W_m2K?: number[]
  area_m2: number | null
  area_range_m2?: number[]
  U_note?: string
  profile_duty_kW?: number[]
  profile_hot_T_C?: number[]
  profile_cold_T_C?: number[]
}
export interface HeatConsistency { item: string; model_kW: number | null; simulated_kW: number | null; rel_deviation: number | null }
export interface HeatResult {
  case_id: string
  source: DataSource
  input_source?: DataSource
  dT_min_K: number
  reactor_temperature_C?: number
  h2_product_kg_h?: number | null
  streams: HeatStream[]
  targets_process: HeatTargets
  targets_with_flue: HeatTargets
  configurations: HeatConfig[]
  fehe: FeheInfo | null
  consistency?: HeatConsistency[]
  assumptions?: string[]
  warnings?: string[] | string | null
  notes?: string[]
}
export interface HeatResponse { case_id: string; dT_min_K: number; result: HeatResult }

export const fetchHeat = (caseId: string, dTminK: number, signal?: AbortSignal) =>
  getJson<HeatResponse>(`/api/heat-integration/${encodeURIComponent(caseId)}?dT_min_K=${encodeURIComponent(String(dTminK))}`, signal)
