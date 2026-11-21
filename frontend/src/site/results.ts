/** Pure data shaping for the Results page: snapshot rows in, chart rows out. No numbers are invented here; missing values stay null. */
import type { XYRow } from '../features/common/XYChart'

export type Num = number | null | undefined
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

export interface SweepRow { reactor_temperature_C?: Num; reactor_pressure_bar?: Num; nh3_conversion?: Num; [k: string]: unknown }

/** Wide table keyed by temperature with one column per pressure: { T, p5: conv%, p10: ... }. */
export function pivotTP(rows: SweepRow[]): { data: XYRow[]; pressures: number[] } {
  const pressures = [...new Set(rows.map((r) => num(r.reactor_pressure_bar)).filter((x): x is number => x !== null))].sort((a, b) => a - b)
  const byT = new Map<number, XYRow>()
  for (const r of rows) {
    const T = num(r.reactor_temperature_C), P = num(r.reactor_pressure_bar), X = num(r.nh3_conversion)
    if (T === null || P === null || X === null) continue
    const row = byT.get(T) ?? { T }
    row[`p${P}`] = X * 100
    byT.set(T, row)
  }
  return { data: [...byT.values()].sort((a, b) => (a.T as number) - (b.T as number)), pressures }
}

/** Merge several series (each a list of {x, y}) into rows keyed by x: { x, <key>: y }. */
export function mergeSeries(xKey: string, series: { key: string; points: { x: Num; y: Num }[] }[]): XYRow[] {
  const byX = new Map<number, XYRow>()
  for (const s of series) {
    for (const p of s.points) {
      const x = num(p.x), y = num(p.y)
      if (x === null || y === null) continue
      const row = byX.get(x) ?? { [xKey]: x }
      row[s.key] = y
      byX.set(x, row)
    }
  }
  return [...byX.values()].sort((a, b) => (a[xKey] as number) - (b[xKey] as number))
}

export const LCOH_LABEL: Record<string, string> = {
  capex: 'Capital charge', fixed_opex: 'Fixed operating cost', ammonia_feed: 'Ammonia feed', imported_heat: 'Imported heat',
  electricity: 'Electricity', cooling_water: 'Cooling water', catalyst: 'Catalyst',
}

export function breakdownRows(b: Record<string, number> | undefined): { name: string; value: number }[] {
  return Object.entries(b ?? {}).map(([k, v]) => ({ name: LCOH_LABEL[k] ?? k.replace(/_/g, ' '), value: v })).filter((r) => Number.isFinite(r.value))
}

export interface CiRow { nh3_route: string; heating_option: string; heating_label: string; total_kgCO2e_per_kgH2: number | null; breakdown_kgCO2e_per_kgH2: Record<string, number> }
export const CI_PARTS: { key: string; label: string }[] = [
  { key: 'upstream_ammonia', label: 'Upstream ammonia' }, { key: 'transport', label: 'Transport' },
  { key: 'electricity', label: 'Electricity' }, { key: 'external_heat', label: 'External heat' },
]

export function ciRows(rows: CiRow[]): Record<string, string | number | null>[] {
  return rows.map((r) => {
    const out: Record<string, string | number | null> = { name: `${r.nh3_route} NH3, ${r.heating_label}`, total: r.total_kgCO2e_per_kgH2 }
    for (const p of CI_PARTS) out[p.key] = num(r.breakdown_kgCO2e_per_kgH2?.[p.key]) ?? 0
    return out
  })
}

export interface DecisionVar { lower: number; upper: number; optimum: number; at_bound: string | null; unit: string }
export interface OptResult {
  id: string; label: string; metric: string; sense: string; feasible: boolean; variant?: string
  decision_variables: Record<string, DecisionVar>
  bound_active?: string[]
  improvement?: { metric: string; optimum: number; baseline: number; delta_rel: number; better: boolean }
}

/** The five single-objective runs with all four decision variables free (the "_TP" and constrained variants are in the platform). */
export function freeOptimisations(results: OptResult[]): OptResult[] {
  return results.filter((r) => /^all four/.test(r.variant ?? ''))
}

export const atBoundCount = (rs: OptResult[]): number => rs.filter((r) => (r.bound_active ?? []).length > 0).length

export const METRIC_UNIT: Record<string, string> = {
  lcoh_USD_per_kg: 'USD/kg H2', lhv_efficiency: '-', specific_heat_demand_kWh_per_kgH2: 'kWh/kg H2', h2_product_kg_h: 'kg/h', nh3_conversion: '-',
}
