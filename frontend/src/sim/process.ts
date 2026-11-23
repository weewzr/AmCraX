/**
 * Reduced port of the Python process model (backend/amcrax/process_model/flowsheet.py, eos='ideal').
 *
 * Computed in the browser (exact port, ideal gas NASA-7):
 *   - cracker duty  Q_R = H_out(T, X) - H_in(T)  (isothermal; or the kinetic PFR heat input)
 *   - H2 in cracked gas, PSA split (H2 recovery, N2 slip: assumed inputs), H2 product and purity
 *   - tail-gas LHV = LHV(H2 to tail gas) + LHV(unconverted NH3)
 *   - total external heating = vaporiser + preheater + cracker; net fuel heat deficit = external - tail-gas combustion heat
 * Interpolated (bilinear in T and P) from the Python flowsheet grid in model.json, scaled linearly with feed flow, at
 * EQUILIBRIUM conversion (deliberate reduction: the FEHE and liquid-ammonia sections use CoolProp / Peng-Robinson in Python):
 *   - pump power, vaporiser duty, preheater (HEATER) duty, recovered FEHE heat, cooler duty, burner combustion/LHV ratio
 */
import { enthalpyFlowKW, equilibriumConversion } from './thermo'
import type { ProcessGridNode, SimModel } from './types'

export interface ProcessInputs {
  T_C: number
  P_bar: number
  heat_integration: boolean
  feed_total_kmol_h?: number
  psa_h2_recovery?: number
  psa_n2_slip?: number
  /** reactor conversion; default = ideal-gas equilibrium at (T, P) (as the Python flowsheet cracker) */
  conversion?: number
  /** reactor heat duty, kW; default = isothermal duty at `conversion` */
  reactor_duty_kW?: number
}

export interface ProcessResult {
  conversion: number
  equilibrium_conversion: number
  h2_in_cracked_gas_kmol_h: number
  h2_product_kmol_h: number
  h2_product_kg_h: number
  h2_purity_mole_frac: number
  reactor_duty_kW: number
  preheat_duty_kW: number
  vaporiser_duty_kW: number
  recovered_heat_kW: number
  total_external_heating_kW: number
  cooling_duty_kW: number
  pump_power_kW: number
  tailgas_lhv_kW: number
  tailgas_combustion_heat_kW: number
  net_fuel_heat_deficit_kW: number
  nh3_feed_kmol_h: number
  /** true when (T, P) lies outside the Python grid or on an infeasible node (values then clamped / null) */
  grid_extrapolated: boolean
  grid_on_node: boolean
}

function locate(xs: number[], x: number) {
  const n = xs.length
  let i = 0
  while (i < n - 2 && x > xs[i + 1]) i++
  const xc = Math.min(Math.max(x, xs[0]), xs[n - 1])
  return { i, t: (xc - xs[i]) / (xs[i + 1] - xs[i]), outside: x < xs[0] || x > xs[n - 1] }
}

export function processGrid(m: SimModel, T_C: number, P_bar: number, hi: boolean): { node: ProcessGridNode | null; outside: boolean; onNode: boolean } {
  const g = m.process.grid
  const tab = hi ? g.per_kmol_h_total_feed.hi : g.per_kmol_h_total_feed.nohi
  const a = locate(g.T_C, T_C), b = locate(g.P_bar, P_bar)
  const corners = [tab[a.i][b.i], tab[a.i][b.i + 1], tab[a.i + 1][b.i], tab[a.i + 1][b.i + 1]]
  const onNode = g.T_C.includes(T_C) && g.P_bar.includes(P_bar)
  if (corners.some((c) => c === null)) return { node: null, outside: a.outside || b.outside, onNode }
  const [c00, c01, c10, c11] = corners as ProcessGridNode[]
  const node = {} as ProcessGridNode
  for (const k of Object.keys(c00) as (keyof ProcessGridNode)[]) {
    node[k] = (1 - a.t) * ((1 - b.t) * c00[k] + b.t * c01[k]) + a.t * ((1 - b.t) * c10[k] + b.t * c11[k])
  }
  return { node, outside: a.outside || b.outside, onNode }
}

export function simulateProcess(m: SimModel, inp: ProcessInputs): ProcessResult {
  const d = m.process.inputs_defaults
  const F = inp.feed_total_kmol_h ?? (d.feed_total_kmol_h as number)
  const xw = d.feed_h2o_mole_frac as number
  const R = inp.psa_h2_recovery ?? (d.psa_h2_recovery as number)
  const slip = inp.psa_n2_slip ?? (d.psa_n2_slip as number)
  const nNH3 = F * (1 - xw), nH2O = F * xw
  const T = inp.T_C + 273.15
  const feed = { NH3: nNH3, H2O: nH2O }
  const Xeq = equilibriumConversion(m, T, inp.P_bar, feed)
  const X = inp.conversion ?? Xeq
  const out = { NH3: nNH3 * (1 - X), H2: 1.5 * nNH3 * X, N2: 0.5 * nNH3 * X, H2O: nH2O }
  const QR = inp.reactor_duty_kW ?? (enthalpyFlowKW(m, out, T) - enthalpyFlowKW(m, feed, T))
  const g = processGrid(m, inp.T_C, inp.P_bar, inp.heat_integration)
  const nan = NaN
  const s = (k: keyof ProcessGridNode) => (g.node ? g.node[k] * F : nan)
  const h2c = out.H2
  const h2p = h2c * R
  const n2p = out.N2 * slip
  const lhv = m.thermo.lhv_kJ_per_mol
  const tailLHV = ((h2c - h2p) * lhv.H2 + out.NH3 * lhv.NH3) * 1000 / 3600
  // burner + flue-gas cooler (as flowsheet.py BURNER/FLUEHX, ideal gas): Q = H(tail gas, T_psa) + H(air, T_air) - H(flue, T_stack)
  const ex = d.burner_excess_air as number
  const tail: Record<string, number> = { H2: h2c - h2p, NH3: out.NH3, N2: out.N2 - n2p, H2O: out.H2O }
  const o2 = (0.5 * tail.H2 + 0.75 * tail.NH3) * (1 + ex)
  const air = m.process.air
  const airN2 = (o2 * air.N2) / air.O2
  const flue = { H2O: tail.H2O + tail.H2 + 1.5 * tail.NH3, N2: tail.N2 + 0.5 * tail.NH3 + airN2, O2: o2 - 0.5 * tail.H2 - 0.75 * tail.NH3 }
  const comb = enthalpyFlowKW(m, tail, (d.psa_feed_temperature_C as number) + 273.15) + enthalpyFlowKW(m, { O2: o2, N2: airN2 }, air.T_C + 273.15)
    - enthalpyFlowKW(m, flue, (d.stack_temperature_C as number) + 273.15)
  const vap = s('vaporiser_kW'), pre = s('preheat_kW')
  const ext = vap + pre + QR
  return {
    conversion: X, equilibrium_conversion: Xeq, h2_in_cracked_gas_kmol_h: h2c, h2_product_kmol_h: h2p,
    h2_product_kg_h: h2p * m.thermo.molar_mass_g_mol.H2, h2_purity_mole_frac: h2p / (h2p + n2p),
    reactor_duty_kW: QR, preheat_duty_kW: pre, vaporiser_duty_kW: vap, recovered_heat_kW: s('recovered_kW'),
    total_external_heating_kW: ext, cooling_duty_kW: s('cooling_kW'), pump_power_kW: s('pump_kW'),
    tailgas_lhv_kW: tailLHV, tailgas_combustion_heat_kW: comb, net_fuel_heat_deficit_kW: ext - comb,
    nh3_feed_kmol_h: nNH3, grid_extrapolated: g.outside || g.node === null, grid_on_node: g.onNode,
  }
}
