import { getJson } from './client'
import type { DataSource } from './types'
import { postJson, type DataFile } from './postjson'

export interface Provenance { value: unknown; unit?: string; source?: string; citekey?: string | null; page?: string | number | null; locator?: string | null; note?: string | null }
export interface CapexInfo {
  method: string; total_capex_USD: number | null; capex_multiplier: number; estimate_class: string; cost_basis?: string
  selected?: { citekey?: string | null; scaled_capex_USD?: number | null; method?: string; page?: string | null; locator?: string | null }
  alternatives?: { method: string; scaled_capex_USD: number | null; citekey?: string | null }[]
}
export interface EconResult {
  case_id: string
  source: DataSource
  input_source?: DataSource
  lcoh_USD_per_kg: number | null
  breakdown_USD_per_kg: Record<string, number | null>
  annual_costs_USD_per_yr?: Record<string, number | null>
  annual_h2_kg: number | null
  h2_product_kg_h: number | null
  crf: number | null
  capex: CapexInfo
  kg_nh3_feed_per_kg_h2: number | null
  kg_nh3_fuel_per_kg_h2: number | null
  stoichiometric_floor_kg_nh3_per_kg_h2: number | null
  reconversion_cost_USD_per_kg: number | null
  cost_basis?: string
  assumptions: Record<string, unknown>
  provenance: Record<string, Provenance>
  notes?: string[]
  // only in the stored analysis file
  tornado?: TornadoItem[]
  literature_benchmarks?: LitBenchmark[]
  breakeven?: { target_lcoh_USD_per_kg: number; nh3_price_USD_per_t: number | null }
}
export interface TornadoItem {
  parameter: string; unit?: string; base_value: number; low_value: number; high_value: number
  lcoh_base: number; lcoh_at_low: number; lcoh_at_high: number; swing: number; source_of_range?: string
}
export interface LitBenchmark {
  value: number | null; unit: string; label: string; citekey: string; page?: number | string | null; locator?: string | null
  nh3_price_USD_per_t?: number | null; kind?: string; source?: string
}
export interface EconOverrides {
  nh3_price_USD_per_t?: number; discount_rate?: number; plant_life_yr?: number; operating_hours_h_per_yr?: number
  capex_multiplier?: number; catalyst?: 'Ni' | 'Ru'
}
export interface EconResponse { case_id: string; overrides: EconOverrides; result: EconResult }

export const postLcoh = (caseId: string, overrides: EconOverrides, signal?: AbortSignal) =>
  postJson<EconResponse>('/api/economics/lcoh', { case_id: caseId, overrides }, signal)

/** Stored analysis file (default assumptions) for a case: tornado, literature benchmarks, breakeven. */
export const fetchEconStored = (caseId: string, signal?: AbortSignal) =>
  getJson<EconResult>(`/api/data/analysis/economics_${encodeURIComponent(caseId)}`, signal)

export interface PriceCurveRow { nh3_price_USD_per_t: number; lcoh_USD_per_kg: number }
export const fetchStoredPriceCurve = async (caseId: string, signal?: AbortSignal): Promise<PriceCurveRow[]> => {
  const d = await getJson<DataFile<PriceCurveRow>>(`/api/data/sensitivity/lcoh_vs_ammonia_price_${encodeURIComponent(caseId)}`, signal)
  return d.rows ?? []
}

/** Live curve: LCOH at several ammonia prices with the current what-if overrides (one POST per point; python engine, fast). */
export async function fetchLiveCurve(caseId: string, overrides: EconOverrides, prices: number[], signal?: AbortSignal): Promise<PriceCurveRow[]> {
  const out = await Promise.all(prices.map((p) => postLcoh(caseId, { ...overrides, nh3_price_USD_per_t: p }, signal)))
  return out.map((o, i) => ({ nh3_price_USD_per_t: prices[i], lcoh_USD_per_kg: o.result.lcoh_USD_per_kg as number }))
}