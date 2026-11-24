/**
 * Simulator page state: control values, reducer, presets, the output rows shown on the page, compare (case A / case B)
 * and export. Every number in an output row comes from the browser simulation core (src/sim); this file only selects,
 * labels and formats. Where the core gives no value, the row value is null and the page shows "not modelled".
 */
import { inletOutletRate, inputRanges, lhvEfficiency, simulate, ROUTE_PRICE_SCENARIO, type NH3Route, type SimData, type SimInputs, type SimOutputs, type SourceLabel, type CatalystPriceSource, type CostKey } from '../sim'

export type ReactorMode = 'equilibrium' | 'isothermal' | 'adiabatic' | 'duty'
export type Purification = 'psa' | 'membrane'
export type CarbonMode = 'actual' | 'hypothetical'

export interface SimState {
  catalyst_id: string
  T_C: number
  P_bar: number
  W_kg: number
  feed_total_kmol_h: number
  reactor: ReactorMode
  /** reactor heat input in the 'specified heat duty' mode, kW */
  duty_kW: number
  heat_integration: boolean
  pressure_drop: boolean
  purification: Purification
  psa_h2_recovery: number
  nh3_route: NH3Route
  /** null = the price scenario of the route */
  nh3_price_USD_per_t: number | null
  carbon_mode: CarbonMode
  carbon_price_SGD_per_t: number
  /** catalyst price of the economics (kinetic modes): metal-content derived scenario or the Phase 1 published TEA price */
  catalyst_price_source: CatalystPriceSource
  /** id of the preset the state was loaded from; cleared by any edit */
  preset: string | null
}

export const REACTOR_MODES: { id: ReactorMode; label: string; note: string }[] = [
  { id: 'equilibrium', label: 'Equilibrium reactor (Aspen baseline)', note: 'RGibbs-type cracker at the set T and P, as the Aspen baseline flowsheet' },
  { id: 'isothermal', label: 'Isothermal kinetic (plug flow)', note: 'packed-bed PFR held at the set temperature, rate law of the selected catalyst' },
  { id: 'adiabatic', label: 'Adiabatic kinetic (plug flow)', note: 'no heat added in the bed: the gas cools as it reacts' },
  { id: 'duty', label: 'Specified heat duty (plug flow)', note: 'a fixed heat input spread evenly over the catalyst (browser-only mode, no Aspen counterpart)' },
]

/** Reset target: the stored Aspen Plus V15 baseline flowsheet (case "baseline": 600 degC, 20 bar, heat integration, PSA 85 %). */
export function baselineState(d: SimData): SimState {
  const def = d.model.process.inputs_defaults
  return {
    catalyst_id: 'ru_kum_temkin_pyzhev',
    T_C: def.reactor_temperature_C as number,
    P_bar: def.reactor_pressure_bar as number,
    W_kg: 100,
    feed_total_kmol_h: def.feed_total_kmol_h as number,
    reactor: 'equilibrium',
    duty_kW: inputRanges(d).duty_kW.default,
    heat_integration: def.heat_integration as boolean,
    pressure_drop: false,
    purification: 'psa',
    psa_h2_recovery: def.psa_h2_recovery as number,
    nh3_route: 'grey',
    nh3_price_USD_per_t: null,
    carbon_mode: 'actual',
    carbon_price_SGD_per_t: d.model.economics.carbon_tax.rate_2026_SGD_per_tCO2e,
    catalyst_price_source: d.model.economics.catalyst_prices.default_level,
    preset: 'baseline',
  }
}

export interface Preset { id: string; label: string; caseId: string; kind: string; patch: Partial<SimState>; /** one sentence: what the stored case is and why it exists */ about: string }

/**
 * Presets that reproduce stored Aspen Plus V15 cases exactly (inputs copied from aspen_anchors.json), so that the page
 * shows Aspen values. Each preset is checked against the data (presetMatches) before it is offered.
 */
export const PRESETS: Preset[] = [
  { id: 'baseline', label: 'Aspen baseline, 600 degC, 20 bar', caseId: 'baseline', kind: 'Aspen core flowsheet', patch: {},
    about: 'The reference flowsheet: equilibrium (RGibbs) cracker at 600 degC and 20 bar with heat recovery and PSA at 85 % recovery; every cost comparison starts here.' },
  { id: 'baseline_no_hi', label: 'Baseline without heat recovery', caseId: 'baseline_no_hi', kind: 'Aspen core flowsheet', patch: { heat_integration: false },
    about: 'The baseline with the feed-effluent exchanger bypassed, stored to show what heat integration is worth.' },
  { id: 'scn_low_temperature', label: 'Equilibrium cracker, 500 degC', caseId: 'scn_low_temperature', kind: 'Aspen core flowsheet', patch: { T_C: 500 },
    about: 'The baseline at 500 degC, stored to show the lower equilibrium conversion at a lower temperature.' },
  { id: 'scn_high_temperature', label: 'Equilibrium cracker, 700 degC', caseId: 'scn_high_temperature', kind: 'Aspen core flowsheet', patch: { T_C: 700 },
    about: 'The baseline at 700 degC, stored to show the conversion gain and the extra heat demand at a higher temperature.' },
  { id: 'scn_low_pressure', label: 'Equilibrium cracker, 5 bar', caseId: 'scn_low_pressure', kind: 'Aspen core flowsheet', patch: { P_bar: 5 },
    about: 'The baseline at 5 bar, stored to show the effect of pressure on equilibrium conversion.' },
  { id: 'ci_kum_T499_P20_W100_hi', label: 'Ru/Al2O3 kinetic, 499 degC', caseId: 'ci_kum_T499_P20_W100_hi', kind: 'Aspen RPlug, integrated flowsheet',
    patch: { reactor: 'isothermal', catalyst_id: 'ru_kum_temkin_pyzhev', T_C: 499, P_bar: 20, W_kg: 100 },
    about: 'An isothermal plug-flow reactor with the Ru/Al2O3 rate law inside the integrated flowsheet, 20 bar, 100 kg catalyst; a low-temperature catalyst case.' },
  { id: 'ci_tni_T594_P20_W100_hi', label: 'Ni/MgO kinetic, 594 degC', caseId: 'ci_tni_T594_P20_W100_hi', kind: 'Aspen RPlug, integrated flowsheet',
    patch: { reactor: 'isothermal', catalyst_id: 'ni_takahashi_microkinetic', T_C: 594, P_bar: 20, W_kg: 100 },
    about: 'An isothermal plug-flow reactor with the Ni/MgO rate law inside the integrated flowsheet, 20 bar, 100 kg catalyst; the nickel comparison case.' },
  { id: 'ci_luc5_T572_P20_W100_hi', label: '5Ni1Ru/CeO2 kinetic, 572 degC', caseId: 'ci_luc5_T572_P20_W100_hi', kind: 'Aspen RPlug, integrated flowsheet',
    patch: { reactor: 'isothermal', catalyst_id: 'nire_ceo2_5ni1ru_lucentini_lhhw', T_C: 572, P_bar: 20, W_kg: 100 },
    about: 'An isothermal plug-flow reactor with the 5Ni1Ru/CeO2 rate law inside the integrated flowsheet, 20 bar, 100 kg catalyst; the bimetallic case.' },
  { id: 'cv_kum_03_T450_P10_W200', label: 'Ru/Al2O3 in its fitted range, 450 degC', caseId: 'cv_kum_03_T450_P10_W200', kind: 'Aspen RPlug, reactor only',
    patch: { reactor: 'isothermal', catalyst_id: 'ru_kum_temkin_pyzhev', T_C: 450, P_bar: 10, W_kg: 200 },
    about: 'A reactor-only Aspen case at 450 degC and 10 bar with 200 kg catalyst, chosen inside the fitted range of the Ru/Al2O3 rate law (no extrapolation).' },
  { id: 'cs_AD_kum_Tin650_P20_W100', label: 'Ru/Al2O3 adiabatic, inlet 650 degC', caseId: 'cs_AD_kum_Tin650_P20_W100', kind: 'Aspen RPlug, reactor only',
    patch: { reactor: 'adiabatic', catalyst_id: 'ru_kum_temkin_pyzhev', T_C: 650, P_bar: 20, W_kg: 100 },
    about: 'A reactor-only Aspen case with no heat added in the bed, inlet 650 degC: the gas cools as it reacts.' },
]

/** Inputs the page holds fixed (C7), read from the exported Python defaults; nothing is hard-coded here. */
export const FIXED_INPUTS: { key: string; label: string; unit: string }[] = [
  { key: 'feed_h2o_mole_frac', label: 'Water in the ammonia feed (mole fraction)', unit: '-' },
  { key: 'psa_feed_temperature_C', label: 'PSA feed temperature', unit: 'degC' },
  { key: 'psa_n2_slip', label: 'Nitrogen slip to the product (PSA)', unit: '-' },
  { key: 'stack_temperature_C', label: 'Stack temperature', unit: 'degC' },
  { key: 'fehe_hot_end_approach_K', label: 'FEHE hot-end approach', unit: 'K' },
  { key: 'burner_excess_air', label: 'Excess combustion air (fraction)', unit: '-' },
  { key: 'property_method', label: 'Property method of the Aspen and Python flowsheets', unit: '' },
]

export function fixedValues(d: SimData): { key: string; label: string; unit: string; value: number | boolean | string }[] {
  const def = d.model.process.inputs_defaults
  return FIXED_INPUTS.filter((f) => def[f.key] !== undefined).map((f) => ({ ...f, value: def[f.key] }))
}

/** Controls the page does not offer, and why (C7). */
export const WITHHELD: string[] = [
  'Pd-Ag membrane model: not ported to the browser; a stored Python comparison is shown instead.',
  'Ammonia feed composition: held at the baseline feed (no composition control).',
  'Transient operation (start-up, load change): the simulator solves steady states only.',
  'Catalyst deactivation, radial gradients and the tube wall: not in the one-dimensional plug-flow model.',
  'Rate laws other than the five exported ones: catalysts without a fitted rate law are not offered.',
]

/** Export file name: amcrax_sim_<preset|custom>_<yyyymmddThhmm>.<ext> (UTC). */
export function exportName(preset: string | null, iso: string, ext: 'csv' | 'json'): string {
  const t = iso.replace(/[-:]/g, '').slice(0, 13)
  return `amcrax_sim_${(preset ?? 'custom').replace(/[^A-Za-z0-9_]/g, '_')}_${t}.${ext}`
}

export function presetState(d: SimData, id: string): SimState {
  const p = PRESETS.find((x) => x.id === id)
  if (!p) throw new RangeError(`unknown preset ${id}`)
  return { ...baselineState(d), ...p.patch, preset: id }
}

/** True when the stored Aspen case of a preset exists in the data and the preset's inputs reproduce it (shows an 'aspen' label). */
export function presetMatches(d: SimData, id: string): boolean {
  const p = PRESETS.find((x) => x.id === id)
  if (!p) return false
  const inCore = d.anchors.core_cases.some((c) => c.case_id === p.caseId)
  const inKin = d.anchors.kinetic_cases.some((c) => c.case_id === p.caseId)
  if (!inCore && !inKin) return false
  const r = simulate(toSimInputs(presetState(d, id), 2), d)
  return r.reactor.conversion.source === 'aspen'
}

export type Action =
  | { type: 'set'; key: keyof SimState; value: SimState[keyof SimState] }
  | { type: 'reset'; data: SimData }
  | { type: 'preset'; data: SimData; id: string }
  | { type: 'load'; state: SimState }

export function reducer(s: SimState, a: Action): SimState {
  switch (a.type) {
    case 'set':
      if (s[a.key] === a.value) return s
      return { ...s, [a.key]: a.value, preset: a.key === 'preset' ? (a.value as string | null) : null }
    case 'reset': return baselineState(a.data)
    case 'preset': return presetState(a.data, a.id)
    case 'load': return { ...a.state }
  }
}

/** Page state -> core inputs. The membrane has no browser model: the core runs with the PSA and the page hides its outputs. */
export function toSimInputs(s: SimState, n_points = 101): SimInputs {
  const kinetic = s.reactor !== 'equilibrium'
  return {
    catalyst_id: s.catalyst_id, T_C: s.T_C, P_bar: s.P_bar, W_kg: s.W_kg,
    mode: s.reactor === 'equilibrium' ? 'isothermal' : s.reactor,
    reactor_model: kinetic ? 'kinetic' : 'equilibrium',
    ...(s.reactor === 'duty' ? { duty_kW: s.duty_kW } : {}),
    pressure_drop: kinetic ? s.pressure_drop : false,
    feed_total_kmol_h: s.feed_total_kmol_h, heat_integration: s.heat_integration, psa_h2_recovery: s.psa_h2_recovery,
    nh3_route: s.nh3_route, ...(s.nh3_price_USD_per_t === null ? {} : { nh3_price_USD_per_t: s.nh3_price_USD_per_t }),
    carbon_mode: s.carbon_mode, carbon_price_SGD_per_t: s.carbon_price_SGD_per_t, catalyst_price_source: s.catalyst_price_source, n_points,
  }
}

// ---------------------------------------------------------------- source badges

export const SOURCE_TEXT: Record<SourceLabel, string> = {
  aspen: 'Aspen Plus V15',
  interpolation: 'Interpolated Aspen grid',
  'browser-model': 'Browser model (port of the Python model)',
  extrapolation: 'Extrapolation',
  assumption: 'Assumed scenario',
  statutory: 'Statutory result',
}
export const SOURCE_SHORT: Record<SourceLabel, string> = {
  aspen: 'Aspen', interpolation: 'Aspen grid', 'browser-model': 'Browser model', extrapolation: 'Extrapolation', assumption: 'Assumed', statutory: 'Statute',
}
export const SOURCE_HELP: Record<SourceLabel, string> = {
  aspen: 'Stored result of an Aspen Plus V15 run made offline for exactly these inputs',
  interpolation: 'Bilinear interpolation between stored Aspen Plus V15 grid points',
  'browser-model': 'Calculated in this page by the TypeScript port of the AmCraX Python model (checked against Python, not against experiments)',
  extrapolation: 'Browser model used outside the fitted range of the rate law or of a stored grid: treat with caution',
  assumption: 'Follows directly from an assumed input (scenario), not from a model of the equipment',
  statutory: 'Follows from the Singapore carbon tax law: the facility has no taxable direct emissions above the threshold, so the tax is zero whatever the reactor model',
}

// ---------------------------------------------------------------- output rows

export interface OutRow { key: string; label: string; unit: string; value: number | null; source: SourceLabel | null; note?: string; kind: 'frac' | 'num' }

const MEMBRANE_NOTE = 'not modelled: the Pd-Ag membrane is not ported to the browser (Python Sieverts model only)'

export interface CaseResult { state: SimState; out: SimOutputs; rows: OutRow[] }

export function runCase(s: SimState, d: SimData, n_points = 101): CaseResult {
  const out = simulate(toSimInputs(s, n_points), d)
  return { state: s, out, rows: outputRows(s, out, d) }
}

export function outputRows(s: SimState, r: SimOutputs, d: SimData): OutRow[] {
  const kinetic = s.reactor !== 'equilibrium'
  const mem = s.purification === 'membrane'
  const p = mem ? null : r.process
  const rows: OutRow[] = []
  const add = (key: string, label: string, unit: string, kind: OutRow['kind'], v: { value: number; source: SourceLabel; note?: string } | null | undefined, why?: string) =>
    rows.push(v && Number.isFinite(v.value) ? { key, label, unit, kind, value: v.value, source: v.source, note: v.note } : { key, label, unit, kind, value: null, source: null, note: why ?? 'not modelled' })
  const noProc = mem ? MEMBRANE_NOTE : 'not modelled: outside the stored process grid (400-800 degC, 3-50 bar)'
  add('conversion', 'NH3 conversion', '%', 'frac', r.reactor.conversion)
  add('eq_conversion_aspen', 'Equilibrium conversion (Aspen RGibbs grid, pure NH3)', '%', 'frac', r.equilibrium.aspen, 'not modelled: outside the stored Aspen equilibrium grid')
  add('eq_conversion_browser', 'Equilibrium conversion (ideal gas, pure NH3)', '%', 'frac', r.equilibrium.browser)
  add('h2_kg_h', 'Hydrogen production rate', 'kg/h', 'num', p?.h2_product_kg_h, noProc)
  const rr = inletOutletRate(r)
  add('rate_inlet', 'Reaction rate at the bed inlet', 'mol NH3/(kg cat s)', 'num', kinetic ? rr.inlet : null, 'not applicable: equilibrium reactor (no rate law)')
  add('rate_outlet', 'Reaction rate at the bed outlet', 'mol NH3/(kg cat s)', 'num', kinetic ? rr.outlet : null, 'not applicable: equilibrium reactor (no rate law)')
  add('reactor_duty_kW', 'Reactor heat duty', 'kW', 'num', r.reactor.duty_kW)
  add('outlet_T_C', 'Reactor outlet temperature', 'degC', 'num', r.reactor.outlet_T_C)
  const dp = kinetic && s.pressure_drop ? { value: r.reactor.pfr.outlet.pressure_drop_bar, source: r.reactor.label === 'aspen' ? 'browser-model' as SourceLabel : r.reactor.label, note: 'Ergun equation' } : null
  add('pressure_drop_bar', 'Bed pressure drop', 'bar', 'num', dp, kinetic ? 'not modelled: pressure drop switched off (as the stored Aspen cases)' : 'not modelled: equilibrium reactor')
  add('h2_purity', 'Hydrogen purity', '%', 'frac', p?.h2_purity_mole_frac, noProc)
  add('h2_recovery', 'Hydrogen recovery (PSA)', '%', 'frac', mem ? null : { value: s.psa_h2_recovery, source: 'assumption', note: 'assumed input of the reduced-order PSA' }, MEMBRANE_NOTE)
  add('lhv_efficiency', 'Energy efficiency (LHV)', '%', 'frac', mem ? null : lhvEfficiency(d.model, r), noProc)
  const basis = ` (${d.model.economics.basis_short})`
  const e = mem ? null : r.economics
  const econSrc = e?.label
  add('lcoh_USD', `Hydrogen production cost${basis}`, 'USD/kg H2', 'num', mem ? null : r.economics?.lcoh_USD, noProc)
  add('lcoh_SGD', `Hydrogen production cost${basis}`, 'SGD/kg H2', 'num', mem ? null : r.economics?.lcoh_SGD, noProc)
  const fx = d.model.fx.SGD_per_USD
  add('npv_MUSD', `Net present value, ${d.model.economics.economic_assumptions.plant_life_yr} yr at ${(Number(d.model.economics.economic_assumptions.discount_rate) * 100).toFixed(0)} %, H2 sold at ${e?.h2_price_USD_per_kg ?? d.model.economics.h2_selling_price_USD_per_kg} USD/kg (pre-tax)`,
    'million USD', 'num', e && econSrc ? { value: e.npv_USD / 1e6, source: econSrc, note: `${(e.npv_USD * fx / 1e6).toFixed(2)} million SGD; constant prices, no depreciation, no working capital` } : null, noProc)
  add('payback_yr', 'Simple payback (capital cost / annual net cash flow)', 'yr', 'num', e && econSrc && e.payback_yr !== null ? { value: e.payback_yr, source: econSrc } : null,
    e && e.payback_yr === null ? 'not reached: annual revenue does not cover the operating cost at the assumed hydrogen price' : noProc)
  add('capex_MUSD', `Capital cost (${d.model.economics.capex_reference.method}, ${d.model.economics.capex_reference.cost_year} USD)`, 'million USD', 'num',
    e && econSrc ? { value: e.capex_total_USD / 1e6, source: econSrc, note: `${(e.capex_total_USD * fx / 1e6).toFixed(2)} million SGD` } : null, noProc)
  const green = s.nh3_route === 'green'
  add('carbon_intensity', green ? 'Carbon intensity (life cycle; green NH3 including embedded asset emissions)' : 'Carbon intensity (life cycle)', 'kg CO2e/kg H2', 'num',
    mem || !r.carbon ? null : { value: r.carbon.intensity.total_kgCO2e_per_kgH2, source: r.carbon.label }, noProc)
  if (green) add('carbon_intensity_zero_boundary', 'Carbon intensity, green NH3 on the boundary that counts renewable electricity as zero (Lee et al.; not used for the carbon cost)', 'kg CO2e/kg H2', 'num',
    mem || !r.carbon?.intensity_zero_boundary ? null : { value: r.carbon.intensity_zero_boundary.total_kgCO2e_per_kgH2, source: r.carbon.label }, noProc)
  // a zero actual-mode tax is the statutory result (no taxable direct emissions), not an output of the reactor model
  const statZero = s.carbon_mode !== 'hypothetical' && !!r.carbon && r.carbon.cost.SGD_per_kg_H2 === 0
  add('carbon_cost', s.carbon_mode === 'hypothetical' ? 'Carbon cost (HYPOTHETICAL price, not Singapore law)' : 'Carbon cost (actual Singapore carbon tax)', 'SGD/kg H2', 'num',
    mem || !r.carbon ? null : { value: r.carbon.cost.SGD_per_kg_H2, source: s.carbon_mode === 'hypothetical' ? 'assumption' : statZero ? 'statutory' : r.carbon.label, note: r.carbon.cost.label }, noProc)
  return rows
}

/** Cost components of one case, from the same evaluate call as the LCOH (USD and SGD per kg H2). */
export const COST_PARTS: { key: CostKey; label: string }[] = [
  { key: 'ammonia_feed', label: 'Ammonia feed' }, { key: 'capex', label: 'Capital (annualised)' }, { key: 'fixed_opex', label: 'Fixed operating cost' },
  { key: 'heat_fuel', label: 'Heat fuel' }, { key: 'catalyst', label: 'Catalyst' }, { key: 'electricity', label: 'Electricity' },
  { key: 'cooling_water', label: 'Cooling water' }, { key: 'carbon_tax', label: 'Carbon' },
]

export interface CostPart { key: CostKey; label: string; usd: number; sgd: number; share: number }

export function costBreakdown(r: SimOutputs): CostPart[] | null {
  const e = r.economics
  if (!e) return null
  const tot = e.lcoh_USD_per_kg
  return COST_PARTS.map((p) => ({ ...p, usd: e.breakdown_USD_per_kg[p.key], sgd: e.breakdown_SGD_per_kg[p.key], share: tot > 0 ? e.breakdown_USD_per_kg[p.key] / tot : 0 }))
}

export function formatValue(row: Pick<OutRow, 'value' | 'kind' | 'unit'>): string {
  const v = row.value
  if (v === null || !Number.isFinite(v)) return 'not modelled'
  if (row.kind === 'frac') return `${(v * 100).toFixed(Math.abs(v) < 0.1 || (v > 0.995 && v < 1) ? 2 : 1)} %`
  const a = Math.abs(v)
  const s = a === 0 ? '0' : a >= 1000 ? v.toFixed(0) : a >= 100 ? v.toFixed(1) : a >= 1 ? v.toFixed(2) : a >= 0.01 ? v.toFixed(3) : v.toExponential(2)
  return `${s} ${row.unit}`
}

// ---------------------------------------------------------------- compare

export interface CompareRow { key: string; label: string; unit: string; kind: OutRow['kind']; a: OutRow; b: OutRow; diff: number | null }

export function compareRows(a: OutRow[], b: OutRow[]): CompareRow[] {
  return b.map((rb) => {
    const ra = a.find((x) => x.key === rb.key) ?? { ...rb, value: null, source: null, note: 'not in case A' }
    const diff = ra.value !== null && rb.value !== null ? rb.value - ra.value : null
    return { key: rb.key, label: rb.label, unit: rb.unit, kind: rb.kind, a: ra, b: rb, diff }
  })
}

export function formatDiff(c: Pick<CompareRow, 'diff' | 'kind' | 'unit'>): string {
  if (c.diff === null) return 'n/a'
  if (c.kind === 'frac') return `${c.diff >= 0 ? '+' : ''}${(c.diff * 100).toFixed(2)} points`
  const t = formatValue({ value: c.diff, kind: 'num', unit: c.unit })
  return c.diff > 0 ? `+${t}` : t
}

/** Inputs that differ between two cases (for the compare header). */
export function changedInputs(a: SimState, b: SimState): (keyof SimState)[] {
  return (Object.keys(b) as (keyof SimState)[]).filter((k) => k !== 'preset' && a[k] !== b[k])
}

// ---------------------------------------------------------------- export

export const INPUT_UNITS: Partial<Record<keyof SimState, string>> = {
  T_C: 'degC', P_bar: 'bar', W_kg: 'kg', feed_total_kmol_h: 'kmol/h', duty_kW: 'kW', psa_h2_recovery: '-', nh3_price_USD_per_t: 'USD/t NH3',
  carbon_price_SGD_per_t: 'SGD/tCO2e',
}

export interface ExportCase { name: string; result: CaseResult }

export function exportJSON(cases: ExportCase[], d: SimData, generated: string): string {
  return JSON.stringify({
    tool: 'AmCraX browser process simulator',
    generated_utc: generated,
    note: 'Steady-state results computed in the browser from stored Aspen Plus V15 / Python data (static site). Not experimental validation.',
    source_labels: SOURCE_TEXT,
    fx: { SGD_per_USD: d.model.fx.SGD_per_USD, rate_date: d.model.fx.date, source: d.model.fx.source },
    economics_basis: d.model.economics.basis,
    economics_note: d.model.economics.basis_note,
    catalyst_prices: d.model.economics.catalyst_prices.statement,
    data_schema: d.model.schema,
    reference_scenario: d.model.economics.reference_scenario ? { id: d.model.economics.reference_scenario.id, version: d.model.economics.reference_scenario.version } : null,
    fixed_values: fixedValues(d).map((f) => ({ key: f.key, label: f.label, value: f.value, unit: f.unit || null, source: 'assumption' })),
    controls_not_offered: WITHHELD,
    cases: cases.map((c) => ({
      case: c.name,
      inputs: Object.fromEntries((Object.keys(c.result.state) as (keyof SimState)[]).map((k) => [k, { value: c.result.state[k], unit: INPUT_UNITS[k] ?? null }])),
      effective_nh3_price_scenario: c.result.state.nh3_price_USD_per_t === null ? ROUTE_PRICE_SCENARIO[c.result.state.nh3_route] : null,
      outputs: c.result.rows.map((r) => ({ key: r.key, label: r.label, value: r.value, unit: r.kind === 'frac' ? 'fraction' : r.unit,
        source: r.source, source_text: r.source ? SOURCE_TEXT[r.source] : 'not modelled', note: r.note ?? null })),
      warnings: c.result.out.warnings,
    })),
  }, null, 2)
}

const csvCell = (v: unknown): string => {
  const s = v === null || v === undefined ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function exportCSV(cases: ExportCase[]): string {
  const lines = [['case', 'section', 'key', 'label', 'value', 'unit', 'source', 'note'].join(',')]
  for (const c of cases) {
    for (const k of Object.keys(c.result.state) as (keyof SimState)[]) {
      lines.push([c.name, 'input', k, k, c.result.state[k], INPUT_UNITS[k] ?? '', 'input', ''].map(csvCell).join(','))
    }
    for (const r of c.result.rows) {
      lines.push([c.name, 'output', r.key, r.label, r.value, r.kind === 'frac' ? 'fraction' : r.unit, r.source ? SOURCE_TEXT[r.source] : 'not modelled', r.note ?? ''].map(csvCell).join(','))
    }
  }
  return lines.join('\n') + '\n'
}

// ---------------------------------------------------------------- graph series

/** Split a series into the fitted part (solid) and the extrapolated part (dashed), sharing boundary points so the line is continuous. */
export function splitExtrapolation(pts: { x: number; y: number | null; source: SourceLabel }[]): { fit: { x: number; y: number | null }[]; ext: { x: number; y: number | null }[] } {
  const isExt = pts.map((p) => p.source === 'extrapolation')
  return {
    fit: pts.map((p, i) => ({ x: p.x, y: !isExt[i] ? p.y : null })),
    ext: pts.map((p, i) => ({ x: p.x, y: isExt[i] || (i > 0 && isExt[i - 1]) || (i < pts.length - 1 && isExt[i + 1]) ? p.y : null })),
  }
}

