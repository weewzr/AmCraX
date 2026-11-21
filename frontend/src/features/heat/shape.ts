import type { XYRow } from '../common/XYChart'
import type { SimulationResult } from '../../api/types'

const fin = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

/** Composite curves as rows keyed by cumulative heat H [kW]: hot / cold temperature (null where a curve has no point). */
export function compositeRows(hotH: number[], hotT: number[], coldH: number[], coldT: number[]): XYRow[] {
  const map = new Map<number, XYRow>()
  const put = (H: number, key: 'hot' | 'cold', T: number) => {
    const k = Math.round(H * 1e6) / 1e6
    const r = map.get(k) ?? { H: k, hot: null, cold: null }
    r[key] = T
    map.set(k, r)
  }
  hotH.forEach((h, i) => { if (fin(h) && fin(hotT[i])) put(h, 'hot', hotT[i]) })
  coldH.forEach((h, i) => { if (fin(h) && fin(coldT[i])) put(h, 'cold', coldT[i]) })
  return [...map.values()].sort((a, b) => (a.H as number) - (b.H as number))
}

/** Grand composite curve: temperature on y, net heat flow on x (data order kept). */
export function gccRows(H: number[], T: number[]): XYRow[] {
  const out: XYRow[] = []
  H.forEach((h, i) => { if (fin(h) && fin(T[i])) out.push({ H: h, T: T[i] }) })
  return out
}

export interface DutyRow { id: string; label: string; duty_kW: number | null }
const DUTY_BLOCKS: [string, string][] = [
  ['VAPORIZR', 'Vaporiser'], ['FEHE', 'FEHE (heat recovered)'], ['HEATER', 'Trim heater'], ['CRACKER', 'Cracker (reaction)'],
  ['COOLER', 'Cooler'], ['FLUEHX', 'Flue-gas heat exchanger'],
]
/** Duty breakdown of the active case from block duties (kW, positive = heat added to the process stream). */
export function dutyBreakdown(c: SimulationResult): DutyRow[] {
  return DUTY_BLOCKS.filter(([id]) => id in c.blocks).map(([id, label]) => ({ id, label, duty_kW: c.blocks[id].duty_kW }))
}

export interface HiCompareRow { label: string; unit: string; digits: number; withHi: number | null; without: number | null }
/** With vs without heat integration, only from two genuine results (never synthesised). */
export function hiComparison(a: SimulationResult, b: SimulationResult): HiCompareRow[] {
  const items: [string, string, number, (c: SimulationResult) => number | null][] = [
    ['Total external heating', 'kW', 0, (c) => c.kpis.total_external_heating_kW],
    ['Recovered heat (FEHE)', 'kW', 0, (c) => c.kpis.recovered_heat_kW],
    ['Cooling duty', 'kW', 0, (c) => c.kpis.cooling_duty_kW],
    ['Specific heat demand', 'kWh/kg H2', 2, (c) => c.kpis.specific_heat_demand_kWh_per_kgH2],
    ['LHV efficiency', '-', 3, (c) => c.kpis.lhv_efficiency],
    ['H2 product', 'kg/h', 1, (c) => c.kpis.h2_product_kg_h],
    ['NH3 conversion', '-', 4, (c) => c.kpis.nh3_conversion],
  ]
  return items.map(([label, unit, digits, f]) => ({ label, unit, digits, withHi: f(a), without: f(b) }))
}
