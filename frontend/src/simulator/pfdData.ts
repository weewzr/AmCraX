/**
 * Geometry and per-stream data of the simulator's process flow diagram. Unit tags and stream numbers follow the Aspen
 * flowsheet (frontend/public/snapshot/flowsheet.json, src/pfd/mapping.ts): FEED, S1-S7, H2PROD, TAILGAS, AIR, FLUE, STACK;
 * PUMP, VAPORIZR, FEHE, HEATER, CRACKER, COOLER, PSA, BURNER, FLUEHX.
 *
 * Numbers shown in the tooltips are taken from the core's outputs only. The particle mix of each stream is derived from
 * those outputs for the animation (colour and density), and is never displayed as a number.
 */
import type { SimData, SourceLabel } from '../sim'
import type { CaseResult } from './model'

export type P = [number, number]
export interface StreamGeom { id: string; pts: P[]; tag: P; bypassOnly?: boolean; hiOnly?: boolean }

export const VIEW = { w: 1180, h: 490 }

/** Stream polylines. Streams with hiOnly exist only with heat recovery; bypassOnly replace them when it is off. */
export const STREAMS: StreamGeom[] = [
  { id: 'FEED', pts: [[92, 360], [134, 360]], tag: [113, 343] },
  { id: 'S1', pts: [[166, 360], [214, 360]], tag: [190, 343] },
  { id: 'S2', pts: [[294, 360], [384, 360]], tag: [340, 343], hiOnly: true },
  { id: 'S2', pts: [[294, 360], [340, 360], [340, 432], [506, 432], [506, 360], [530, 360]], tag: [423, 432], bypassOnly: true },
  { id: 'S3', pts: [[476, 360], [530, 360]], tag: [506, 343], hiOnly: true },
  { id: 'S4', pts: [[594, 360], [730, 360], [730, 342]], tag: [622, 343] },
  { id: 'S5', pts: [[730, 150], [730, 90], [460, 90], [460, 340]], tag: [598, 90], hiOnly: true },
  { id: 'S5', pts: [[730, 150], [730, 90], [858, 90], [858, 70], [880, 70]], tag: [798, 90], bypassOnly: true },
  { id: 'S6', pts: [[400, 340], [400, 32], [858, 32], [858, 70], [880, 70]], tag: [630, 32], hiOnly: true },
  { id: 'S7', pts: [[950, 70], [1030, 70], [1030, 108]], tag: [990, 70] },
  { id: 'H2PROD', pts: [[1060, 140], [1168, 140]], tag: [1114, 140] },
  { id: 'TAILGAS', pts: [[1030, 212], [1030, 468], [750, 468], [750, 418]], tag: [890, 468] },
  { id: 'AIR', pts: [[600, 452], [712, 452], [712, 418]], tag: [640, 452] },
  { id: 'FLUE', pts: [[820, 250], [870, 250]], tag: [845, 250] },
  { id: 'STACK', pts: [[934, 250], [983, 250], [983, 168]], tag: [958, 250] },
]

/** Path through the catalyst bed (inside CRACKER, bottom to top) used to show conversion along the bed. */
export const BED = { x: 712, y: 172, w: 36, h: 150 }
export const BED_PATH: P[] = [[730, BED.y + BED.h], [730, BED.y]]

export const UNITS: { id: string; name: string; tag: string }[] = [
  { id: 'TANK', name: 'Liquid ammonia storage', tag: 'FEED' },
  { id: 'PUMP', name: 'Feed pump', tag: 'PUMP' },
  { id: 'VAPORIZR', name: 'Vaporiser', tag: 'VAPORIZR' },
  { id: 'FEHE', name: 'Feed-effluent heat exchanger', tag: 'FEHE' },
  { id: 'HEATER', name: 'Preheater', tag: 'HEATER' },
  { id: 'CRACKER', name: 'Cracking reactor (packed bed) in the fired furnace', tag: 'CRACKER' },
  { id: 'BURNER', name: 'Furnace burner', tag: 'BURNER' },
  { id: 'COOLER', name: 'Cracked-gas cooler', tag: 'COOLER' },
  { id: 'PSA', name: 'Hydrogen purification', tag: 'PSA' },
  { id: 'FLUEHX', name: 'Flue-gas heat recovery', tag: 'FLUEHX' },
]

export const STREAM_NAMES: Record<string, { name: string; from: string; to: string }> = {
  FEED: { name: 'Liquid ammonia feed', from: 'storage', to: 'PUMP' },
  S1: { name: 'Pressurised liquid ammonia', from: 'PUMP', to: 'VAPORIZR' },
  S2: { name: 'Ammonia vapour', from: 'VAPORIZR', to: 'FEHE (HEATER when heat recovery is off)' },
  S3: { name: 'Preheated ammonia', from: 'FEHE', to: 'HEATER' },
  S4: { name: 'Reactor feed', from: 'HEATER', to: 'CRACKER' },
  S5: { name: 'Hot cracked gas', from: 'CRACKER', to: 'FEHE (COOLER when heat recovery is off)' },
  S6: { name: 'Partly cooled cracked gas', from: 'FEHE', to: 'COOLER' },
  S7: { name: 'Purification feed', from: 'COOLER', to: 'PSA' },
  H2PROD: { name: 'Hydrogen product', from: 'PSA', to: 'battery limit' },
  TAILGAS: { name: 'Nitrogen-rich tail gas (off-gas) to the burner', from: 'PSA', to: 'BURNER' },
  AIR: { name: 'Combustion air', from: 'ambient', to: 'BURNER' },
  FLUE: { name: 'Hot flue gas', from: 'BURNER', to: 'FLUEHX' },
  STACK: { name: 'Stack gas', from: 'FLUEHX', to: 'atmosphere' },
}

export type Species = 'NH3' | 'H2' | 'N2' | 'H2O' | 'O2'
export const SPECIES_COLOR: Record<Species, string> = { NH3: 'var(--c-nh3)', H2: 'var(--c-h2)', N2: 'var(--c-n2)', H2O: 'var(--c-h2o)', O2: 'var(--c-o2)' }

export interface Fact { label: string; value: number | null; unit: string; source: SourceLabel | null; frac?: boolean; note?: string }
export interface StreamView {
  id: string
  /** relative molar flow for the particle density (animation only) */
  flow: number
  /** particle mix (animation only) */
  mix: Partial<Record<Species, number>>
  facts: Fact[]
  note?: string
}

const norm = (m: Partial<Record<Species, number>>) => {
  const t = Object.values(m).reduce((a, b) => a + (b ?? 0), 0)
  return t > 0 ? Object.fromEntries(Object.entries(m).map(([k, v]) => [k, (v ?? 0) / t])) as Partial<Record<Species, number>> : m
}

/** Stream views of one case: flows and mixes for the animation, facts (core outputs only) for the tooltips. */
export function streamViews(c: CaseResult, d: SimData): Record<string, StreamView> {
  const s = c.state, r = c.out
  const xw = d.model.process.inputs_defaults.feed_h2o_mole_frac as number
  const F = s.feed_total_kmol_h
  const nNH3 = F * (1 - xw), nH2O = F * xw
  const X = r.process ? r.process.conversion.value : r.reactor.conversion.value
  const out = { NH3: nNH3 * (1 - X), H2: 1.5 * nNH3 * X, N2: 0.5 * nNH3 * X, H2O: nH2O }
  const outTot = out.NH3 + out.H2 + out.N2 + out.H2O
  const mem = s.purification === 'membrane'
  const p = mem ? null : r.process
  const R = s.psa_h2_recovery
  const h2p = out.H2 * R
  const tail = { NH3: out.NH3, H2: out.H2 - h2p, N2: out.N2, H2O: out.H2O }
  const tailTot = tail.NH3 + tail.H2 + tail.N2 + tail.H2O
  const feedMix = norm({ NH3: nNH3, H2O: nH2O })
  const inFact = (): Fact => ({ label: 'Molar flow (input)', value: F, unit: 'kmol/h', source: 'assumption' })
  const rx = r.reactor
  const kin = s.reactor !== 'equilibrium'
  const fl = (k: string) => (kin ? rx.pfr.outlet.flows_kmol_h[k] ?? null : null)
  const outFacts: Fact[] = [
    { label: 'Temperature', value: rx.outlet_T_C.value, unit: 'degC', source: rx.outlet_T_C.source },
    { label: 'Pressure', value: rx.outlet_P_bar.value, unit: 'bar', source: rx.outlet_P_bar.source },
    { label: 'NH3 conversion', value: rx.conversion.value, unit: '%', source: rx.conversion.source, frac: true },
    { label: 'H2 in cracked gas', value: r.process ? r.process.h2_in_cracked_gas_kmol_h.value : fl('H2'), unit: 'kmol/h', source: r.process ? r.process.h2_in_cracked_gas_kmol_h.source : kin ? rx.label : null },
    ...(kin ? [{ label: 'NH3 slip (unconverted)', value: fl('NH3'), unit: 'kmol/h', source: rx.label === 'aspen' ? 'browser-model' as SourceLabel : rx.label }] : []),
  ]
  const noT = 'Temperature and pressure of this stream are not computed by the browser model (the reduced flowsheet interpolates duties only).'
  const burnerFlow = tailTot * 2.2
  return {
    FEED: { id: 'FEED', flow: F, mix: feedMix, facts: [inFact(), { label: 'NH3 mole fraction', value: 1 - xw, unit: '%', source: 'assumption', frac: true }], note: 'Baseline feed composition (NH3 99.8 / H2O 0.2 mol%); the browser model has no composition control.' },
    S1: { id: 'S1', flow: F, mix: feedMix, facts: [inFact(), { label: 'Pump power', value: p ? p.pump_power_kW.value : null, unit: 'kW', source: p ? p.pump_power_kW.source : null }], note: noT },
    S2: { id: 'S2', flow: F, mix: feedMix, facts: [inFact(), { label: 'Vaporiser duty', value: p ? p.vaporiser_duty_kW.value : null, unit: 'kW', source: p ? p.vaporiser_duty_kW.source : null }], note: noT },
    S3: { id: 'S3', flow: F, mix: feedMix, facts: [inFact(), { label: 'Heat recovered in FEHE', value: p ? p.recovered_heat_kW.value : null, unit: 'kW', source: p ? p.recovered_heat_kW.source : null }], note: noT },
    S4: { id: 'S4', flow: F, mix: feedMix, facts: [inFact(), { label: 'Temperature (reactor inlet, set)', value: s.T_C, unit: 'degC', source: 'assumption' }, { label: 'Pressure (reactor inlet, set)', value: s.P_bar, unit: 'bar', source: 'assumption' }] },
    S5: { id: 'S5', flow: outTot, mix: norm(out), facts: outFacts },
    S6: { id: 'S6', flow: outTot, mix: norm(out), facts: [{ label: 'H2 in cracked gas', value: r.process ? r.process.h2_in_cracked_gas_kmol_h.value : null, unit: 'kmol/h', source: r.process ? r.process.h2_in_cracked_gas_kmol_h.source : null }], note: noT },
    S7: { id: 'S7', flow: outTot, mix: norm(out), facts: [{ label: 'Temperature (PSA feed, assumed)', value: d.model.process.inputs_defaults.psa_feed_temperature_C as number, unit: 'degC', source: 'assumption' }, { label: 'Cooler duty', value: p ? p.cooling_duty_kW.value : null, unit: 'kW', source: p ? p.cooling_duty_kW.source : null }] },
    H2PROD: { id: 'H2PROD', flow: h2p, mix: { H2: 0.995, N2: 0.005 }, facts: [
      { label: 'Hydrogen product', value: p ? p.h2_product_kg_h.value : null, unit: 'kg/h', source: p ? p.h2_product_kg_h.source : null },
      { label: 'Hydrogen product', value: p ? p.h2_product_kmol_h.value : null, unit: 'kmol/h', source: p ? p.h2_product_kmol_h.source : null },
      { label: 'Purity (N2 slip assumed)', value: p ? p.h2_purity_mole_frac.value : null, unit: '%', source: p ? p.h2_purity_mole_frac.source : null, frac: true }], note: mem ? 'Membrane: not modelled in the browser.' : undefined },
    TAILGAS: { id: 'TAILGAS', flow: tailTot, mix: norm(tail), facts: [
      { label: 'Tail-gas heating value (LHV)', value: p ? p.tailgas_lhv_kW.value : null, unit: 'kW', source: p ? p.tailgas_lhv_kW.source : null }], note: 'Unrecovered H2 and NH3 slip are burnt in the furnace burner.' },
    AIR: { id: 'AIR', flow: burnerFlow, mix: { N2: 0.79, O2: 0.21 }, facts: [], note: 'Air flow (15 % excess, assumed) is not reported by the browser model.' },
    FLUE: { id: 'FLUE', flow: burnerFlow, mix: { N2: 0.7, H2O: 0.3 }, facts: [{ label: 'Burner heat to the process', value: p ? p.tailgas_combustion_heat_kW.value : null, unit: 'kW', source: p ? p.tailgas_combustion_heat_kW.source : null }], note: 'Flue-gas flow is not reported by the browser model.' },
    STACK: { id: 'STACK', flow: burnerFlow, mix: { N2: 0.7, H2O: 0.3 }, facts: [{ label: 'Stack temperature (assumed)', value: d.model.process.inputs_defaults.stack_temperature_C as number, unit: 'degC', source: 'assumption' }] },
  }
}

export interface UnitView { id: string; title: string; what: string; facts: Fact[]; bypassed?: boolean; notModelled?: boolean }

export function unitViews(c: CaseResult, d: SimData): Record<string, UnitView> {
  const s = c.state, r = c.out
  const mem = s.purification === 'membrane'
  const p = mem ? null : r.process
  const f = (label: string, v: { value: number; source: SourceLabel } | null | undefined, unit: string, frac = false): Fact =>
    ({ label, value: v && Number.isFinite(v.value) ? v.value : null, unit, source: v ? v.source : null, frac })
  const law = d.model.kinetics.laws[s.catalyst_id]
  const kin = s.reactor !== 'equilibrium'
  const rx = r.reactor
  return {
    TANK: { id: 'TANK', title: 'Liquid ammonia storage (FEED)', what: 'Refrigerated or pressurised liquid ammonia delivered to the cracker. The feed flow is a control input.', facts: [f('Ammonia feed', { value: s.feed_total_kmol_h, source: 'assumption' }, 'kmol/h')] },
    PUMP: { id: 'PUMP', title: 'Feed pump (PUMP)', what: 'Raises the liquid ammonia to the reactor pressure. Pumping a liquid costs far less work than compressing the gas.', facts: [f('Pump power', p?.pump_power_kW, 'kW')] },
    VAPORIZR: { id: 'VAPORIZR', title: 'Vaporiser (VAPORIZR)', what: 'Boils the pressurised ammonia. Heat is supplied externally.', facts: [f('Vaporiser duty', p?.vaporiser_duty_kW, 'kW')] },
    FEHE: { id: 'FEHE', title: 'Feed-effluent heat exchanger (FEHE)', what: s.heat_integration ? 'Preheats the ammonia vapour with the hot cracked gas leaving the reactor (hot-end approach 50 K, assumed).' : 'BYPASSED: heat recovery is switched off, so the vapour goes straight to the preheater and the hot gas straight to the cooler.', facts: [f('Recovered heat', s.heat_integration ? p?.recovered_heat_kW : null, 'kW')], bypassed: !s.heat_integration },
    HEATER: { id: 'HEATER', title: 'Preheater (HEATER)', what: 'Brings the feed to the reactor inlet temperature.', facts: [f('Preheater duty', p?.preheat_duty_kW, 'kW'), f('Outlet temperature (set)', { value: s.T_C, source: 'assumption' }, 'degC')] },
    CRACKER: { id: 'CRACKER', title: `Cracking reactor (CRACKER), ${kin ? 'packed-bed plug flow' : 'equilibrium'}`, what: kin
      ? `2 NH3 -> N2 + 3 H2 over ${law?.label ?? s.catalyst_id}. Endothermic: heat comes from the furnace. ${s.W_kg} kg catalyst in ${d.model.reactor.default_n_tubes} tubes.`
      : '2 NH3 -> N2 + 3 H2 taken to chemical equilibrium at the set temperature and pressure, as the RGibbs cracker of the Aspen baseline.',
      facts: [f('NH3 conversion', rx.conversion, '%', true), f('Heat duty', rx.duty_kW, 'kW'), f('Outlet temperature', rx.outlet_T_C, 'degC'), f('Outlet pressure', rx.outlet_P_bar, 'bar'),
        ...(kin ? [f('Approach to equilibrium (X / X_eq)', rx.approach_to_equilibrium, '%', true), f('Bed length', rx.bed_length_m, 'm')] : [])] },
    BURNER: { id: 'BURNER', title: 'Furnace burner (BURNER)', what: 'Burns the PSA tail gas with air and supplies heat to the reactor and the feed train. Any shortfall is met by extra fuel (ammonia self-firing by default).',
      facts: [f('Tail-gas combustion heat', p?.tailgas_combustion_heat_kW, 'kW'), f('Total external heating', p?.total_external_heating_kW, 'kW'), f('Net fuel heat deficit', p?.net_fuel_heat_deficit_kW, 'kW')] },
    COOLER: { id: 'COOLER', title: 'Cracked-gas cooler (COOLER)', what: 'Cools the cracked gas to the purification feed temperature (40 degC, assumed).', facts: [f('Cooling duty', p?.cooling_duty_kW, 'kW')] },
    PSA: mem
      ? { id: 'PSA', title: 'Pd-Ag membrane (not modelled in the browser)', what: 'The membrane option exists in the Python model (Sieverts law) but is not ported to the browser, so the purification and every downstream number show "not modelled".', facts: [], notModelled: true }
      : { id: 'PSA', title: 'Pressure-swing adsorption (PSA)', what: 'Separates hydrogen from nitrogen and unconverted ammonia. Reduced-order splitter: hydrogen recovery and nitrogen slip are assumed inputs, not an adsorption model.',
        facts: [f('Hydrogen recovery (assumed)', { value: s.psa_h2_recovery, source: 'assumption' }, '%', true), f('Hydrogen purity', p?.h2_purity_mole_frac, '%', true), f('Hydrogen product', p?.h2_product_kg_h, 'kg/h')] },
    FLUEHX: { id: 'FLUEHX', title: 'Flue-gas heat recovery (FLUEHX)', what: 'Cools the flue gas to the stack temperature (150 degC, assumed); the heat is credited to the process in the burner balance.', facts: [f('Burner heat credited', p?.tailgas_combustion_heat_kW, 'kW')] },
  }
}

/** Polyline helpers for the particle animation (no DOM measurement). */
export function polyLength(pts: P[]): number {
  let L = 0
  for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
  return L
}
export function pointAt(pts: P[], s: number): P {
  let rest = s
  for (let i = 1; i < pts.length; i++) {
    const seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
    if (rest <= seg || i === pts.length - 1) {
      const t = seg > 0 ? Math.min(1, Math.max(0, rest / seg)) : 0
      return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t]
    }
    rest -= seg
  }
  return pts[pts.length - 1]
}
export const pathD = (pts: P[]): string => pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]} ${p[1]}`).join(' ')

/** Particle count of a stream: density proportional to molar flow (relative to the largest stream). */
export function particleCount(len: number, flow: number, maxFlow: number, spacing = 26): number {
  if (!(flow > 0) || !(maxFlow > 0)) return 0
  return Math.max(1, Math.min(60, Math.round((len / spacing) * (flow / maxFlow))))
}

/** Species of particle i for a mix (golden-ratio sequence, so the colours spread evenly). */
export function speciesOf(i: number, mix: Partial<Record<Species, number>>): Species {
  const u = (i * 0.6180339887) % 1
  let acc = 0
  const entries = Object.entries(mix) as [Species, number][]
  for (const [k, v] of entries) { acc += v; if (u < acc) return k }
  return entries.length ? entries[entries.length - 1][0] : 'NH3'
}
