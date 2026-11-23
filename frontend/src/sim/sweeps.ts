/** Series for the eight simulator graphs. Every point carries its source label. */
import { aspenEquilibrium } from './anchors'
import { rate } from './kinetics'
import { simulate, type NH3Route, type SimInputs, type SimOutputs } from './simulate'
import { equilibriumConversion } from './thermo'
import type { SimData, SourceLabel } from './types'

export interface Pt { x: number; y: number | null; source: SourceLabel }

const range = (a: number, b: number, n: number) => Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1))

/** 1. Conversion against temperature: browser equilibrium, Aspen equilibrium (grid nodes / interpolation), kinetic outlet. */
export function conversionVsTemperature(d: SimData, base: SimInputs, Tmin = 300, Tmax = 800, n = 26) {
  const eq: Pt[] = [], aspen: Pt[] = [], kin: Pt[] = []
  for (const T of range(Tmin, Tmax, n)) {
    eq.push({ x: T, y: equilibriumConversion(d.model, T + 273.15, base.P_bar, { NH3: 1 }), source: 'browser-model' })
    const a = aspenEquilibrium(d.anchors, T, base.P_bar)
    if (a) aspen.push({ x: T, y: a.value, source: a.source })
    const r = simulate({ ...base, T_C: T, n_points: 2 }, d)
    kin.push({ x: T, y: r.reactor.conversion.value, source: r.reactor.conversion.source })
  }
  return { equilibrium_browser: eq, equilibrium_aspen: aspen, kinetic: kin, x_unit: 'degC', y_unit: '-' }
}

/**
 * 2. Rate against temperature for selected catalysts at a fixed gas state: baseline feed converted to `X`
 * (default 0.1) at P. Rate in mol NH3 / (kg_cat s).
 */
export function rateVsTemperature(d: SimData, catalyst_ids: string[], P_bar: number, X = 0.1, Tmin = 300, Tmax = 800, n = 51) {
  const f = d.model.reactor.baseline_feed_kmol_h
  const nn = { NH3: f.NH3 * (1 - X), H2: 1.5 * f.NH3 * X, N2: 0.5 * f.NH3 * X, H2O: f.H2O }
  const tot = nn.NH3 + nn.H2 + nn.N2 + nn.H2O
  const p = Object.fromEntries(Object.entries(nn).map(([k, v]) => [k, (v / tot) * P_bar]))
  const out: Record<string, Pt[]> = {}
  for (const id of catalyst_ids) {
    const v = d.model.kinetics.laws[id].validity
    out[id] = range(Tmin, Tmax, n).map((T) => {
      const TK = T + 273.15
      let y: number | null = null
      try { y = rate(d.model, id, TK, p) } catch { y = null }
      const inside = TK >= v.T_min_K - 1e-6 && TK <= v.T_max_K + 1e-6 && P_bar >= v.P_min_bar - 1e-6 && P_bar <= v.P_max_bar + 1e-6
      return { x: T, y, source: inside ? 'browser-model' : 'extrapolation' }
    })
  }
  return { series: out, x_unit: 'degC', y_unit: 'mol NH3 kg_cat^-1 s^-1', state: { X, P_bar } }
}

/** 3 and 4. Conversion and temperature against bed length (and catalyst mass) from one simulate() result. */
export function axialProfiles(r: SimOutputs) {
  const p = r.reactor.pfr.profiles
  const s: SourceLabel = r.reactor.label === 'aspen' ? 'browser-model' : r.reactor.label
  const a = r.reactor.aspen
  return {
    conversion_vs_length: p.z_m.map((z, i) => ({ x: z, y: p.conversion[i], source: s })),
    temperature_vs_length: p.z_m.map((z, i) => ({ x: z, y: p.T_K[i] - 273.15, source: s })),
    pressure_vs_length: p.z_m.map((z, i) => ({ x: z, y: p.P_bar[i], source: s })),
    conversion_vs_mass: p.W_kg.map((w, i) => ({ x: w, y: p.conversion[i], source: s })),
    aspen: a && a.profiles.length_m ? {
      conversion_vs_length: a.profiles.length_m.map((z, i) => ({ x: z, y: a.profiles.conversion ? a.profiles.conversion[i] : null, source: 'aspen' as SourceLabel })),
      temperature_vs_length: a.profiles.length_m.map((z, i) => ({ x: z, y: a.profiles.T_C ? a.profiles.T_C[i] : null, source: 'aspen' as SourceLabel })),
    } : null,
    x_unit: 'm',
  }
}

/** 5. Hydrogen production against heat input: browser-only 'duty' mode, duty from 0 to dutyMax at fixed inlet state. */
export function h2VsHeatInput(d: SimData, base: SimInputs, dutyMax_kW = 2500, n = 26) {
  return range(0, dutyMax_kW, n).map((q) => {
    const r = simulate({ ...base, mode: 'duty', duty_kW: q, n_points: 2 }, d)
    const h2 = r.process ? r.process.h2_product_kg_h : null
    return { x: q, y: h2 ? h2.value : null, source: (h2 ? h2.source : r.reactor.label) as SourceLabel, conversion: r.reactor.conversion.value,
      outlet_T_C: r.reactor.outlet_T_C.value }
  })
}

export type CostVariable = 'T_C' | 'P_bar' | 'W_kg' | 'psa_h2_recovery' | 'nh3_price_USD_per_t' | 'feed_total_kmol_h'

/** 6. Hydrogen cost (LCOH, USD and SGD per kg) against one variable, by catalyst. */
export function costVsVariable(d: SimData, base: SimInputs, variable: CostVariable, values: number[], catalyst_ids: string[]) {
  const out: Record<string, (Pt & { y_SGD: number | null })[]> = {}
  for (const id of catalyst_ids) {
    out[id] = values.map((v) => {
      const r = simulate({ ...base, catalyst_id: id, [variable]: v, n_points: 2 }, d)
      return { x: v, y: r.economics ? r.economics.lcoh_USD_per_kg : null, y_SGD: r.economics ? r.economics.lcoh_SGD_per_kg : null,
        source: r.economics ? r.economics.label : 'extrapolation' }
    })
  }
  return { series: out, variable, y_unit: 'USD/kg H2' }
}

/** 7. Energy balance bars of one simulate() result (kW). */
export function energyBalance(r: SimOutputs) {
  const p = r.process
  if (!p) return null
  return [
    { key: 'external_heating', label: 'External heating (vaporiser + preheat + reactor)', ...p.total_external_heating_kW },
    { key: 'recovered_heat', label: 'Recovered heat (feed-effluent exchanger)', ...p.recovered_heat_kW },
    { key: 'reactor_duty', label: 'Reactor duty', ...p.reactor_duty_kW },
    { key: 'preheat', label: 'Preheater', ...p.preheat_duty_kW },
    { key: 'vaporiser', label: 'Vaporiser', ...p.vaporiser_duty_kW },
    { key: 'tailgas_heat', label: 'Tail-gas combustion heat', ...p.tailgas_combustion_heat_kW },
    { key: 'net_deficit', label: 'Net fuel heat deficit', ...p.net_fuel_heat_deficit_kW },
    { key: 'cooling', label: 'Cooler', ...p.cooling_duty_kW },
  ]
}

/** 8. Carbon intensity and carbon cost (actual and hypothetical) for grey, blue and green ammonia. */
export function carbonByRoute(d: SimData, base: SimInputs, hypothetical_price_SGD_per_t: number) {
  const routes: NH3Route[] = ['grey', 'blue', 'green']
  return routes.map((route) => {
    const act = simulate({ ...base, nh3_route: route, carbon_mode: 'actual', n_points: 2 }, d)
    const hyp = simulate({ ...base, nh3_route: route, carbon_mode: 'hypothetical', carbon_price_SGD_per_t: hypothetical_price_SGD_per_t, n_points: 2 }, d)
    return {
      route, ci_kgCO2e_per_kgH2: act.carbon ? act.carbon.intensity.total_kgCO2e_per_kgH2 : null,
      breakdown: act.carbon ? act.carbon.intensity.breakdown_kgCO2e_per_kgH2 : null,
      actual_cost_SGD_per_kg: act.carbon ? act.carbon.cost.SGD_per_kg_H2 : null,
      hypothetical_cost_SGD_per_kg: hyp.carbon ? hyp.carbon.cost.SGD_per_kg_H2 : null,
      lcoh_actual_SGD: act.carbon ? act.carbon.cost.lcoh_SGD_per_kg : null,
      lcoh_hypothetical_SGD: hyp.carbon ? hyp.carbon.cost.lcoh_SGD_per_kg : null,
      source: (act.carbon ? act.carbon.label : 'extrapolation') as SourceLabel,
    }
  })
}
