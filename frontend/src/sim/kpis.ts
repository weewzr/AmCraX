/**
 * Derived KPIs of one simulate() result (thin helpers for the simulator page; no new model).
 *
 * lhvEfficiency follows backend/amcrax/kpis.py exactly:
 *   LHV(H2 product) / (LHV(NH3 feed) + max(net fuel heat deficit, 0) + pump power)
 * a first-law, upper-bound metric (imported heat counted 1:1 against LHV, flue heat credited regardless of its level).
 */
import type { SimOutputs } from './simulate'
import type { Labelled, SimModel, SourceLabel } from './types'

const worst = (s: SourceLabel[]): SourceLabel => (s.includes('extrapolation') ? 'extrapolation' : s.includes('interpolation') ? 'interpolation' : 'browser-model')

export function lhvEfficiency(m: SimModel, r: SimOutputs): Labelled | null {
  const p = r.process
  if (!p) return null
  const lhv = m.thermo.lhv_kJ_per_mol
  const prod = (p.h2_product_kmol_h.value * lhv.H2 * 1000) / 3600
  const feed = (p.nh3_feed_kmol_h.value * lhv.NH3 * 1000) / 3600
  const denom = feed + Math.max(p.net_fuel_heat_deficit_kW.value, 0) + p.pump_power_kW.value
  if (!(denom > 0) || !Number.isFinite(prod)) return null
  return { value: prod / denom, source: worst([p.h2_product_kmol_h.source, p.net_fuel_heat_deficit_kW.source, p.pump_power_kW.source]), unit: '-',
    note: 'LHV(H2 product) / (LHV(NH3 feed) + max(deficit, 0) + pump power), as amcrax.kpis (first-law upper bound)' }
}

/** Reaction rate at the bed inlet and outlet from the PFR profile, mol NH3 / (kg_cat s). */
export function inletOutletRate(r: SimOutputs): { inlet: Labelled; outlet: Labelled } {
  const q = r.reactor.pfr.profiles.rate_mol_per_kgcat_s
  const s: SourceLabel = r.reactor.label === 'aspen' ? 'browser-model' : r.reactor.label
  const unit = 'mol NH3/(kg cat s)'
  return { inlet: { value: q[0], source: s, unit }, outlet: { value: q[q.length - 1], source: s, unit } }
}
