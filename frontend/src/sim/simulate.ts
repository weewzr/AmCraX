/**
 * One entry point: simulate(inputs, data) -> every output with a source label.
 *
 * Labels: 'aspen' stored Aspen Plus V15 value for exactly these inputs; 'interpolation' inside a stored Aspen grid;
 * 'browser-model' browser port of the Python model; 'extrapolation' browser model outside the fitted range of the rate
 * law (or outside a stored grid); 'assumption' follows directly from an assumed input (PSA recovery / N2 slip).
 */
import { aspenEquilibrium, findCoreAnchor, findKineticAnchor } from './anchors'
import { carbonCost, carbonIntensity, type CarbonCost, type CIResult, type Heating } from './carbon'
import { domainWarnings, insideFittedRange } from './domain'
import { economicMetal, evaluateEconomics, type EconResult } from './economics'
import { simulatePFR, type PFRResult, type ThermalMode } from './pfr'
import { simulateProcess, type ProcessResult } from './process'
import { equilibriumConversion } from './thermo'
import type { KineticAnchor, Labelled, SimData, SourceLabel } from './types'

export type NH3Route = 'grey' | 'blue' | 'green'

export interface SimInputs {
  catalyst_id: string
  T_C: number
  P_bar: number
  W_kg: number
  mode: ThermalMode
  T_wall_C?: number
  U_W_m2K?: number
  duty_kW?: number
  n_tubes?: number
  tube_inner_diameter_m?: number
  pressure_drop?: boolean
  approach_factor?: boolean
  feed_total_kmol_h?: number
  heat_integration: boolean
  psa_h2_recovery?: number
  psa_n2_slip?: number
  nh3_route: NH3Route
  /** default: price scenario of the route (grey, blue, green_current) */
  nh3_price_USD_per_t?: number
  heating?: Heating
  carbon_mode?: 'actual' | 'hypothetical'
  carbon_price_SGD_per_t?: number
  n_points?: number
  /**
   * 'kinetic' (default): the PFR result feeds the process balance. 'equilibrium': the cracker is an equilibrium reactor at
   * (T_C, P_bar) as the Aspen baseline (RGibbs) and the Python flowsheet: process conversion = ideal-gas equilibrium,
   * reactor duty = isothermal duty at that conversion; the stored Aspen core case is used when the inputs match exactly.
   * The PFR is still run (for the axial-profile graphs), but its result does not enter the process balance.
   */
  reactor_model?: 'kinetic' | 'equilibrium'
}

export const ROUTE_PRICE_SCENARIO: Record<NH3Route, string> = { grey: 'grey', blue: 'blue', green: 'green_current' }

export interface SimOutputs {
  inputs: SimInputs
  warnings: string[]
  reactor: {
    pfr: PFRResult
    label: SourceLabel
    conversion: Labelled
    outlet_T_C: Labelled
    outlet_P_bar: Labelled
    duty_kW: Labelled
    approach_to_equilibrium: Labelled
    bed_length_m: Labelled
    aspen: KineticAnchor | null
  }
  equilibrium: { browser: Labelled; aspen: Labelled | null }
  process: (Record<keyof Omit<ProcessResult, 'grid_extrapolated' | 'grid_on_node'>, Labelled> & { available: boolean }) | null
  economics: (EconResult & { label: SourceLabel; lcoh_USD: Labelled; lcoh_SGD: Labelled }) | null
  carbon: { intensity: CIResult; label: SourceLabel; cost: CarbonCost } | null
}

const L = (value: number, source: SourceLabel, unit?: string, note?: string): Labelled => ({ value, source, unit, note })
const worst = (...s: SourceLabel[]): SourceLabel => (s.includes('extrapolation') ? 'extrapolation' : s.includes('interpolation') ? 'interpolation' : 'browser-model')

export function simulate(x: SimInputs, d: SimData): SimOutputs {
  const m = d.model
  const eqMode = x.reactor_model === 'equilibrium'
  // the rate law does not enter an equilibrium reactor: its fitted-range and non-isothermal warnings do not apply
  const warnings = domainWarnings(d, x).filter((w) => !eqMode || !/fitted range of|non-isothermal reactor/.test(w))
  const def = m.process.inputs_defaults
  const F = x.feed_total_kmol_h ?? (def.feed_total_kmol_h as number)
  const xw = def.feed_h2o_mole_frac as number
  const feed = { NH3: F * (1 - xw), H2O: F * xw }
  const nt = x.n_tubes ?? m.reactor.default_n_tubes
  const pd = x.pressure_drop ?? false
  const pmode: ThermalMode = eqMode ? 'isothermal' : x.mode
  const pfr = simulatePFR(m, { catalyst_id: x.catalyst_id, W_kg: x.W_kg, T_in_C: x.T_C, P_in_bar: x.P_bar, feed_kmol_h: feed, mode: pmode,
    T_wall_C: x.T_wall_C, U_W_m2K: x.U_W_m2K, duty_kW: x.duty_kW, n_tubes: nt, tube_inner_diameter_m: x.tube_inner_diameter_m,
    pressure_drop: pd, approach_factor: x.approach_factor, n_points: x.n_points ?? 101 })
  const fitted = insideFittedRange(d, x.catalyst_id, pfr.profiles.T_K, [x.P_bar])
  const rl: SourceLabel = eqMode ? 'browser-model' : fitted ? 'browser-model' : 'extrapolation'
  const anchor = eqMode ? null : findKineticAnchor(d.anchors, { catalyst_id: x.catalyst_id, T_C: x.T_C, P_bar: x.P_bar, W_kg: x.W_kg, mode: x.mode,
    pressure_drop: pd, n_tubes: nt, T_wall_C: x.T_wall_C, U_W_m2K: x.U_W_m2K })
  const o = pfr.outlet
  const R = x.psa_h2_recovery ?? (def.psa_h2_recovery as number)
  // ---- process (reactor outlet fed into the reduced Python flowsheet balance; equilibrium mode: the flowsheet's own equilibrium cracker)
  const pr = simulateProcess(m, { T_C: x.T_C, P_bar: x.P_bar, heat_integration: x.heat_integration, feed_total_kmol_h: F,
    psa_h2_recovery: R, psa_n2_slip: x.psa_n2_slip, ...(eqMode ? {} : { conversion: o.conversion, reactor_duty_kW: o.heat_input_kW }) })
  const core = eqMode && (x.psa_n2_slip === undefined || x.psa_n2_slip === def.psa_n2_slip)
    ? findCoreAnchor(d.anchors, { T_C: x.T_C, P_bar: x.P_bar, heat_integration: x.heat_integration, psa_h2_recovery: R, feed_total_kmol_h: F }) : null
  const reactor = eqMode ? {
    pfr, label: core ? 'aspen' as SourceLabel : 'browser-model' as SourceLabel,
    conversion: core ? L(core.kpis.nh3_conversion, 'aspen', '-', `Aspen core case ${core.case_id} (RGibbs)`) : L(pr.conversion, 'browser-model', '-', 'equilibrium reactor, ideal gas, baseline feed'),
    outlet_T_C: L(x.T_C, 'assumption', 'degC', 'isothermal equilibrium reactor: outlet at the set temperature'),
    outlet_P_bar: L(x.P_bar, 'assumption', 'bar', 'no pressure drop in the equilibrium reactor'),
    duty_kW: core ? L(core.kpis.reactor_duty_kW, 'aspen', 'kW', `Aspen core case ${core.case_id}`) : L(pr.reactor_duty_kW, 'browser-model', 'kW', 'isothermal duty at equilibrium, ideal gas'),
    approach_to_equilibrium: L(1, 'assumption', '-', 'equilibrium reactor by definition'),
    bed_length_m: L(pfr.bed_length_m, 'browser-model', 'm', 'kinetic PFR of the selected catalyst, for reference only'),
    aspen: null,
  } : {
    pfr, label: anchor ? 'aspen' as SourceLabel : rl,
    conversion: anchor ? L(anchor.conversion, 'aspen', '-', `Aspen case ${anchor.case_id}; browser ${o.conversion.toFixed(4)}`) : L(o.conversion, rl, '-'),
    outlet_T_C: anchor ? L(anchor.outlet.T_C, 'aspen', 'degC') : L(o.T_C, rl, 'degC'),
    outlet_P_bar: anchor ? L(anchor.outlet.P_bar, 'aspen', 'bar') : L(o.P_bar, rl, 'bar'),
    duty_kW: anchor ? L(anchor.duty_kW, 'aspen', 'kW') : L(o.heat_input_kW, rl, 'kW', 'H_out - H_in, ideal gas'),
    approach_to_equilibrium: L(o.approach_to_equilibrium, rl, '-', 'X / X_eq (ideal gas, local T and P)'),
    bed_length_m: anchor ? L(anchor.reactor_length_m, 'aspen', 'm') : L(pfr.bed_length_m, 'browser-model', 'm'),
    aspen: anchor,
  }
  const xeqB = equilibriumConversion(m, x.T_C + 273.15, x.P_bar, { NH3: 1 })
  const aeq = aspenEquilibrium(d.anchors, x.T_C, x.P_bar)
  const equilibrium = { browser: L(xeqB, 'browser-model', '-', 'ideal gas, pure NH3'),
    aspen: aeq ? L(aeq.value, aeq.source, '-', 'Aspen RGibbs PENG-ROB, pure NH3') : null }

  let process: SimOutputs['process'] = null
  let econ: SimOutputs['economics'] = null
  let carbon: SimOutputs['carbon'] = null
  const available = !pr.grid_extrapolated
  if (available) {
    const integ = eqMode ? null : findKineticAnchor(d.anchors, { catalyst_id: x.catalyst_id, T_C: x.T_C, P_bar: x.P_bar, W_kg: x.W_kg, mode: x.mode, pressure_drop: pd,
      n_tubes: nt, configuration: 'integrated', heat_integration: x.heat_integration })
    const aspenK = core ? { ...core.kpis, conversion: core.kpis.nh3_conversion } : integ && F === 100 && R === (def.psa_h2_recovery as number) ? integ.flowsheet_kpis : null
    const caseId = core ? `core case ${core.case_id}` : `integrated case ${integ?.case_id}`
    const pl = worst(rl)
    const val = (k: keyof ProcessResult, unit: string, src: SourceLabel = pl): Labelled =>
      aspenK && typeof aspenK[k] === 'number' ? L(aspenK[k] as number, 'aspen', unit, `Aspen ${caseId}`) : L(pr[k] as number, src, unit)
    process = {
      available: true,
      conversion: val('conversion', '-'), equilibrium_conversion: L(pr.equilibrium_conversion, 'browser-model', '-'),
      h2_in_cracked_gas_kmol_h: val('h2_in_cracked_gas_kmol_h', 'kmol/h'), h2_product_kmol_h: val('h2_product_kmol_h', 'kmol/h'),
      h2_product_kg_h: val('h2_product_kg_h', 'kg/h'), h2_purity_mole_frac: val('h2_purity_mole_frac', '-', 'assumption'),
      reactor_duty_kW: val('reactor_duty_kW', 'kW'), preheat_duty_kW: val('preheat_duty_kW', 'kW', 'browser-model'),
      vaporiser_duty_kW: val('vaporiser_duty_kW', 'kW', 'browser-model'), recovered_heat_kW: val('recovered_heat_kW', 'kW', 'browser-model'),
      total_external_heating_kW: val('total_external_heating_kW', 'kW'), cooling_duty_kW: val('cooling_duty_kW', 'kW', 'browser-model'),
      pump_power_kW: val('pump_power_kW', 'kW', 'browser-model'), tailgas_lhv_kW: val('tailgas_lhv_kW', 'kW'),
      tailgas_combustion_heat_kW: val('tailgas_combustion_heat_kW', 'kW'), net_fuel_heat_deficit_kW: val('net_fuel_heat_deficit_kW', 'kW'),
      nh3_feed_kmol_h: L(pr.nh3_feed_kmol_h, 'assumption', 'kmol/h', 'input'),
    }
    if (aspenK) warnings.push(`process KPIs taken from the stored Aspen ${caseId}`)
    const summ = { h2_kg_h: process.h2_product_kg_h.value, nh3_feed_kmol_h: pr.nh3_feed_kmol_h, heat_deficit_kW: process.net_fuel_heat_deficit_kW.value,
      cooling_kW: process.cooling_duty_kW.value, pump_kW: process.pump_power_kW.value }
    const metal = economicMetal(m, m.kinetics.laws[x.catalyst_id].metal)
    const heatFuel = (x.heating ?? 'self_firing') === 'natural_gas' ? 'natural_gas' : 'ammonia'
    const e = evaluateEconomics(m, summ, x.nh3_price_USD_per_t ?? ROUTE_PRICE_SCENARIO[x.nh3_route], {
      catalyst: metal, catalyst_mass_kg: x.W_kg, heat_fuel: heatFuel })
    if (m.kinetics.laws[x.catalyst_id].metal !== metal) e.notes.push(`${m.kinetics.laws[x.catalyst_id].metal} catalyst priced as ${metal} (assumption, model.economics.catalyst_metal_map_note)`)
    const el: SourceLabel = aspenK ? 'browser-model' : pl
    econ = { ...e, label: el, lcoh_USD: L(e.lcoh_USD_per_kg, el, 'USD/kg H2'), lcoh_SGD: L(e.lcoh_SGD_per_kg, el, 'SGD/kg H2', `fx ${m.fx.SGD_per_USD} SGD/USD (rate date ${m.fx.date})`) }
    const ci = carbonIntensity(m, { h2_kg_h: summ.h2_kg_h, nh3_feed_kg_h: pr.nh3_feed_kmol_h * m.thermo.molar_mass_g_mol.NH3,
      heat_deficit_kW: summ.heat_deficit_kW, pump_kW: summ.pump_kW }, x.nh3_route, x.heating ?? 'self_firing')
    carbon = { intensity: ci, label: el, cost: carbonCost(m, e, ci, x.carbon_mode ?? 'actual', x.carbon_price_SGD_per_t ?? 0) }
  }
  return { inputs: x, warnings, reactor, equilibrium, process, economics: econ, carbon }
}
