import type { CompareResponse } from '../../api/simulation'
import type { DataSource, KPIs } from '../../api/types'

export interface KpiDef { key: keyof KPIs; label: string; unit: string; digits: number; group: 'performance' | 'product' | 'duty' | 'specific' }

export const KPI_DEFS: KpiDef[] = [
  { key: 'nh3_conversion', label: 'NH3 conversion', unit: '-', digits: 4, group: 'performance' },
  { key: 'h2_yield_overall', label: 'Overall H2 yield', unit: '-', digits: 4, group: 'performance' },
  { key: 'h2_purity_mole_frac', label: 'H2 purity (mole fraction)', unit: '-', digits: 5, group: 'performance' },
  { key: 'lhv_efficiency', label: 'LHV efficiency', unit: '-', digits: 4, group: 'performance' },
  { key: 'h2_product_kg_h', label: 'H2 product', unit: 'kg/h', digits: 1, group: 'product' },
  { key: 'h2_product_kmol_h', label: 'H2 product', unit: 'kmol/h', digits: 2, group: 'product' },
  { key: 'h2_in_cracked_gas_kmol_h', label: 'H2 in cracked gas', unit: 'kmol/h', digits: 2, group: 'product' },
  { key: 'reactor_duty_kW', label: 'Cracker duty', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'preheat_duty_kW', label: 'Preheater duty', unit: 'kW', digits: 1, group: 'duty' },
  { key: 'vaporiser_duty_kW', label: 'Vaporiser duty', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'recovered_heat_kW', label: 'Recovered heat (FEHE)', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'total_external_heating_kW', label: 'Total external heating', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'cooling_duty_kW', label: 'Cooling duty', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'pump_power_kW', label: 'Pump power', unit: 'kW', digits: 2, group: 'duty' },
  { key: 'tailgas_combustion_heat_kW', label: 'Tail-gas combustion heat', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'tailgas_lhv_kW', label: 'Tail-gas LHV', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'net_fuel_heat_deficit_kW', label: 'Net fuel heat deficit', unit: 'kW', digits: 0, group: 'duty' },
  { key: 'specific_heat_demand_kWh_per_kgH2', label: 'Specific heat demand', unit: 'kWh/kg H2', digits: 2, group: 'specific' },
]
export const kpiDef = (k: string) => KPI_DEFS.find((d) => d.key === k)

export const SOURCE_SHORT: Record<DataSource, string> = {
  aspen_plus_v15: 'Aspen', python_model: 'Python', literature: 'Literature', assumption: 'Assumption', demo: 'DEMO',
}

export interface CompareCell { v: number | null; d: number | null; rel: number | null }
export interface CompareDisplayRow { kpi: string; label: string; unit: string; digits: number; cells: Record<string, CompareCell> }

const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null)

/** Shape the API table (kpi, <id>, delta_<id>, delta_rel_<id>) into one row per KPI. */
export function shapeCompare(r: CompareResponse): CompareDisplayRow[] {
  const ids = r.cases.map((c) => c.case_id)
  return r.table.map((row) => {
    const def = kpiDef(row.kpi)
    const cells: Record<string, CompareCell> = {}
    for (const id of ids) cells[id] = { v: num(row[id]), d: num(row[`delta_${id}`]), rel: num(row[`delta_rel_${id}`]) }
    return { kpi: row.kpi, label: def?.label ?? row.kpi, unit: def?.unit ?? '', digits: def?.digits ?? 3, cells }
  })
}

/** True when the compared cases come from more than one provenance (e.g. Aspen vs Python). */
export function mixedEngines(r: CompareResponse): boolean {
  return new Set(r.cases.map((c) => c.source)).size > 1
}

export const caseLabel = (c: { case_id: string; source: DataSource }) => `${c.case_id} [${SOURCE_SHORT[c.source]}]`

/** Grouped-bar data: one row per KPI of the group, one numeric key per case. */
export function barData(rows: CompareDisplayRow[], group: KpiDef['group'], r: CompareResponse): Record<string, number | string | null>[] {
  const keys = new Set(KPI_DEFS.filter((d) => d.group === group).map((d) => d.key as string))
  return rows.filter((x) => keys.has(x.kpi)).map((x) => {
    const o: Record<string, number | string | null> = { kpi: `${x.label}${x.unit && x.unit !== '-' ? ` [${x.unit}]` : ''}` }
    for (const c of r.cases) o[c.case_id] = x.cells[c.case_id]?.v ?? null
    return o
  })
}

/** Parse the optional stored overlay table (GET /api/scenarios/comparison) without assuming a fixed shape. */
export interface OverlayTable { rows: Record<string, unknown>[]; columns: string[]; notes: string[] }
export function parseOverlay(x: unknown): OverlayTable | null {
  if (x === null || typeof x !== 'object') return null
  const o = x as Record<string, unknown>
  const arr = Array.isArray(x) ? x : (['rows', 'table', 'scenarios', 'comparison', 'items'].map((k) => o[k]).find(Array.isArray) as unknown[] | undefined)
  if (!arr || arr.length === 0 || typeof arr[0] !== 'object') return null
  const rows = arr as Record<string, unknown>[]
  const columns: string[] = []
  for (const r of rows) for (const k of Object.keys(r)) if (!columns.includes(k) && (r[k] === null || typeof r[k] !== 'object')) columns.push(k)
  const notes: string[] = []
  for (const k of ['assumptions', 'notes', 'note', 'description', 'basis']) {
    const v = o[k]
    if (typeof v === 'string') notes.push(v)
    else if (Array.isArray(v)) for (const s of v) if (typeof s === 'string') notes.push(s)
  }
  return { rows, columns, notes }
}
