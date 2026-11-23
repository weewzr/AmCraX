/** Input domain of the simulator: valid ranges and warnings when an input is outside a fitted or stored domain. */
import type { SimInputs } from './simulate'
import type { SimData } from './types'

export interface Range { min: number; max: number; default: number; unit: string; step?: number; note: string }

/**
 * Hard ranges of the UI controls. Limits are set by the models (NASA-7 range, Python CaseInputs bounds, process grid),
 * NOT by the fitted ranges of the rate laws (those produce warnings and the label 'extrapolation').
 */
export function inputRanges(d: SimData): Record<string, Range> {
  const m = d.model
  const g = m.process.grid
  const def = m.process.inputs_defaults
  return {
    T_C: { min: 300, max: g.T_C[g.T_C.length - 1], default: def.reactor_temperature_C as number, unit: 'degC', step: 1,
      note: `process energy balance available ${g.T_C[0]}-${g.T_C[g.T_C.length - 1]} degC (Python grid); reactor alone from 300 degC` },
    P_bar: { min: 1.01325, max: g.P_bar[g.P_bar.length - 1], default: def.reactor_pressure_bar as number, unit: 'bar', step: 0.5,
      note: `process energy balance needs P >= ${g.P_bar[0]} bar (Python flowsheet minimum ${m.process.min_flowsheet_pressure_bar} bar)` },
    W_kg: { min: 0.1, max: 2000, default: 100, unit: 'kg catalyst (all tubes)', note: 'total catalyst mass' },
    n_tubes: { min: 1, max: 500, default: m.reactor.default_n_tubes, unit: '-', step: 1, note: 'as the stored Aspen cases (50 tubes of 0.126 m)' },
    feed_total_kmol_h: { min: 10, max: 500, default: def.feed_total_kmol_h as number, unit: 'kmol/h', note: 'baseline composition (NH3 99.8 / H2O 0.2 mol%) only' },
    psa_h2_recovery: { min: 0.5, max: 0.99, default: def.psa_h2_recovery as number, unit: '-', step: 0.01, note: 'assumed input (reduced-order PSA)' },
    psa_n2_slip: { min: 0, max: 0.05, default: def.psa_n2_slip as number, unit: '-', note: 'assumed input (reduced-order PSA)' },
    T_wall_C: { min: 300, max: 900, default: 650, unit: 'degC', note: "mode 'external' only" },
    U_W_m2K: { min: 0, max: 500, default: 100, unit: 'W/(m2 K)', note: "mode 'external' only" },
    duty_kW: { min: 0, max: 5000, default: 1400, unit: 'kW', note: "mode 'duty' only (browser-only mode)" },
    nh3_price_USD_per_t: { min: 100, max: 1500, default: m.economics.nh3_price_scenarios_USD_per_t.grey, unit: 'USD/t NH3', note: 'scenario price, not a Singapore transaction price' },
    carbon_price_SGD_per_t: { min: 0, max: 500, default: m.economics.carbon_tax.rate_2026_SGD_per_tCO2e, unit: 'SGD/tCO2e', note: 'hypothetical mode only; not Singapore law' },
  }
}

/** Warnings for one input set (empty = everything inside the fitted / stored domains). */
export function domainWarnings(d: SimData, x: SimInputs): string[] {
  const w: string[] = []
  const m = d.model
  const l = m.kinetics.laws[x.catalyst_id]
  const r = inputRanges(d)
  for (const k of Object.keys(r)) {
    const v = (x as unknown as Record<string, number | undefined>)[k]
    if (typeof v === 'number' && (v < r[k].min || v > r[k].max)) w.push(`${k} = ${v} is outside the control range ${r[k].min}-${r[k].max} ${r[k].unit}`)
  }
  if (l) {
    const TK = x.T_C + 273.15
    if (TK < l.validity.T_min_K - 1e-6 || TK > l.validity.T_max_K + 1e-6)
      w.push(`T = ${x.T_C} degC is outside the fitted range of ${l.label} (${(l.validity.T_min_K - 273.15).toFixed(0)}-${(l.validity.T_max_K - 273.15).toFixed(0)} degC): extrapolation`)
    if (x.P_bar < l.validity.P_min_bar - 1e-6 || x.P_bar > l.validity.P_max_bar + 1e-6)
      w.push(`P = ${x.P_bar} bar is outside the fitted range of ${l.label} (${l.validity.P_min_bar}-${l.validity.P_max_bar} bar): extrapolation`)
  } else w.push(`unknown catalyst ${x.catalyst_id}`)
  const g = m.process.grid
  if (x.P_bar < g.P_bar[0] || x.P_bar > g.P_bar[g.P_bar.length - 1] || x.T_C < g.T_C[0] || x.T_C > g.T_C[g.T_C.length - 1])
    w.push('outside the Python process grid: process energy balance, economics and carbon are not available')
  const eg = d.anchors.equilibrium_grid
  if (x.T_C < eg.T_C[0] || x.T_C > eg.T_C[eg.T_C.length - 1] || x.P_bar < eg.P_bar[0] || x.P_bar > eg.P_bar[eg.P_bar.length - 1])
    w.push('outside the stored Aspen equilibrium grid: no Aspen equilibrium value')
  if (x.mode !== 'isothermal') w.push('non-isothermal reactor: downstream duties of the process balance are those of an outlet at the inlet temperature (reduction)')
  return w
}

/** True when T, P (and every profile temperature) lie inside the fitted range of the rate law. */
export function insideFittedRange(d: SimData, catalyst_id: string, T_K: number[], P_bar: number[]): boolean {
  const v = d.model.kinetics.laws[catalyst_id].validity
  const e = 1e-6
  return T_K.every((t) => t >= v.T_min_K - e && t <= v.T_max_K + e) && P_bar.every((p) => p >= v.P_min_bar - e && p <= v.P_max_bar + e)
}
