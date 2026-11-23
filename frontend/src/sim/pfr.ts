/**
 * Port of backend/amcrax/reactor/pfr.py (1-D pseudo-homogeneous packed-bed PFR over catalyst mass W).
 *
 *   dX/dW = r / F_NH3,0
 *   dT/dW = [ -dH_r(T) r + q_W ] / sum F_i cp_i       q_W = 0 (adiabatic), U (4/D) (T_wall - T) / rho_bed (external),
 *                                                     Q / W_total (mode 'duty', browser-only: heat duty spread evenly)
 *   dP/dW = (dP/dz)_Ergun / (rho_bed A_total)         dtau/dW = eps_b / (rho_bed Q_actual)
 *
 * Integration: adaptive Dormand-Prince 5(4) (Python: LSODA). Deliberate reduction: the gas viscosity in the Ergun
 * term is a bilinear interpolation in (T, X) of a Cantera table exported to model.json (Python calls Cantera at
 * every step); valid for the baseline feed composition (NH3 99.8 / H2O 0.2 mol%) only, which is the only feed
 * composition the simulator offers (total flow may change).
 */
import { rate as rateLaw } from './kinetics'
import { cp, enthalpyFlowKW, equilibriumConstant, equilibriumConversion, reactionEnthalpy } from './thermo'
import type { SimModel } from './types'

export type ThermalMode = 'isothermal' | 'adiabatic' | 'external' | 'duty'

export interface PFRInputs {
  catalyst_id: string
  W_kg: number
  T_in_C: number
  P_in_bar: number
  /** total liquid feed, kmol/h, baseline composition (default: reactor.baseline_feed_kmol_h) */
  feed_kmol_h?: Record<string, number>
  mode: ThermalMode
  T_wall_C?: number
  U_W_m2K?: number
  /** mode 'duty': total heat added to the bed, kW, spread evenly over the catalyst mass */
  duty_kW?: number
  eps_b?: number
  rho_particle_kg_m3?: number
  dp_m?: number
  tube_inner_diameter_m?: number
  n_tubes?: number
  pressure_drop?: boolean
  approach_factor?: boolean
  keq_basis?: 'published' | 'amcrax_thermo'
  n_points?: number
  rtol?: number
}

export interface PFRProfiles {
  W_kg: number[]; z_m: number[]; conversion: number[]; T_K: number[]; P_bar: number[]; rate_mol_per_kgcat_s: number[]
  X_eq_local: number[]; approach_to_equilibrium: number[]; residence_time_s: number[]
}

export interface PFRResult {
  inputs: Required<Pick<PFRInputs, 'catalyst_id' | 'W_kg' | 'T_in_C' | 'P_in_bar' | 'mode'>> & Record<string, unknown>
  profiles: PFRProfiles
  outlet: {
    conversion: number; T_C: number; P_bar: number; pressure_drop_bar: number; X_eq_outlet: number
    approach_to_equilibrium: number; flows_kmol_h: Record<string, number>; H2_kmol_h: number
    /** H_out - H_in (kW, > 0 = heat added); for isothermal = required reactor duty */
    heat_input_kW: number
    residence_time_s: number; W_reached_kg: number; hydraulic_limit: boolean
  }
  bed_length_m: number
  bed_volume_m3: number
  GHSV_h_inv: number
  steps: number
  assumptions: string[]
}

const KMOLH_TO_MOLS = 1000 / 3600

function viscosity(m: SimModel, T: number, X: number): number {
  const v = m.reactor.viscosity
  const bil = (xs: number[], x: number) => {
    const n = xs.length
    let i = 0
    while (i < n - 2 && x > xs[i + 1]) i++
    const t = (x - xs[i]) / (xs[i + 1] - xs[i])
    return [i, t] as const
  }
  const [i, ti] = bil(v.T_K, T)
  const [j, tj] = bil(v.X, Math.min(Math.max(X, 0), 1))
  const g = v.mu_Pa_s
  return (1 - ti) * ((1 - tj) * g[i][j] + tj * g[i][j + 1]) + ti * ((1 - tj) * g[i + 1][j] + tj * g[i + 1][j + 1])
}

export function simulatePFR(m: SimModel, inp: PFRInputs): PFRResult {
  const bed = m.reactor.default_bed
  const eps = inp.eps_b ?? bed.eps_b
  const rhoP = inp.rho_particle_kg_m3 ?? bed.rho_particle_kg_m3
  const dp = inp.dp_m ?? bed.dp_m
  const D = inp.tube_inner_diameter_m ?? bed.tube_inner_diameter_m
  const nt = inp.n_tubes ?? 1
  const usePD = inp.pressure_drop ?? true
  const mode = inp.mode
  if (mode === 'external' && (inp.T_wall_C === undefined || inp.U_W_m2K === undefined)) throw new Error('external mode requires T_wall_C and U_W_m2K')
  if (mode === 'duty' && inp.duty_kW === undefined) throw new Error("mode 'duty' requires duty_kW")
  const l = m.kinetics.laws[inp.catalyst_id]
  if (!l) throw new RangeError(`unknown catalyst ${inp.catalyst_id}`)
  const feed = { ...(inp.feed_kmol_h ?? m.reactor.baseline_feed_kmol_h) }
  const Ff: Record<string, number> = {}
  for (const [s, v] of Object.entries(feed)) if (v > 0) Ff[s] = v * KMOLH_TO_MOLS
  Ff.N2 = Ff.N2 ?? 0; Ff.H2 = Ff.H2 ?? 0
  const species = Object.keys(Ff)
  const MM = m.reactor.molar_mass_kg_mol
  const F0 = Ff.NH3
  const mdot = species.reduce((a, s) => a + Ff[s] * MM[s], 0)
  const rhoBed = (1 - eps) * rhoP
  const A = (nt * Math.PI * D ** 2) / 4
  const G = mdot / A
  const Tin = inp.T_in_C + 273.15
  const Tw = inp.T_wall_C !== undefined ? inp.T_wall_C + 273.15 : NaN
  const R = m.thermo.R_J_molK
  const W = inp.W_kg
  const qDuty = mode === 'duty' && W > 0 ? ((inp.duty_kW as number) * 1000) / W : 0
  const opt = { approachFactor: inp.approach_factor, keqBasis: inp.keq_basis ?? (m.reactor.default_keq_basis as 'amcrax_thermo') }
  const assumptions: string[] = []
  let X0 = 0
  if (l.form === 'temkin_pyzhev' && Ff.H2 <= 0) {
    X0 = m.reactor.x_seed_temkin
    assumptions.push(`numerical: H2 seed, integration starts at X0=${X0} (rate singular at p_H2=0)`)
  }
  if (l.form !== 'temkin_pyzhev') assumptions.push(`AmCraX extension: equilibrium approach factor (1-Q/K) ${(inp.approach_factor ?? m.kinetics.equilibrium_approach_factor.default_on) ? 'ON' : 'OFF'}`)
  assumptions.push('effectiveness factor = 1; no radial gradients; no axial dispersion (as the Python PFR)')
  if (usePD) assumptions.push('Ergun viscosity: bilinear interpolation of the exported Cantera table (browser reduction)')
  if (mode === 'duty') assumptions.push('browser-only thermal mode: specified duty spread evenly over the catalyst mass (no Python counterpart)')

  const flows = (X: number) => {
    const F: Record<string, number> = { ...Ff }
    F.NH3 = F0 * (1 - X)
    F.N2 = Ff.N2 + 0.5 * F0 * X
    F.H2 = Ff.H2 + 1.5 * F0 * X
    return F
  }
  const partial = (X: number, P: number) => {
    const F = flows(X)
    const Ft = species.reduce((a, s) => a + F[s], 0)
    const p: Record<string, number> = {}
    for (const s of species) p[s] = (F[s] / Ft) * P
    return { F, Ft, p }
  }
  const rhs = (u: number[]): number[] => {
    const X = Math.min(Math.max(u[0], 0), 1 - 1e-15)
    const T = u[1], P = u[2]
    const { F, Ft, p } = partial(X, P)
    if (l.form === 'temkin_pyzhev' && p.H2 <= 0) p.H2 = 1e-300
    const r = rateLaw(m, inp.catalyst_id, T, p, opt)
    const dX = r / F0
    let dT = 0
    if (mode !== 'isothermal') {
      const Fcp = species.reduce((a, s) => a + F[s] * cp(m, s, T), 0)
      let q = -reactionEnthalpy(m, T) * 1e3 * r
      if (mode === 'external') q += ((inp.U_W_m2K as number) * (4 / D) * (Tw - T)) / rhoBed
      if (mode === 'duty') q += qDuty
      dT = q / Fcp
    }
    let dP = 0
    if (usePD) {
      const Mw = species.reduce((a, s) => a + (F[s] / Ft) * MM[s], 0)
      const rhoG = (P * 1e5 * Mw) / (R * T)
      const mu = viscosity(m, T, X)
      const e = m.reactor.ergun
      const dPdz = -(G / (rhoG * dp)) * ((1 - eps) / eps ** 3) * ((e.viscous * (1 - eps) * mu) / dp + e.inertial * G)
      dP = dPdz / (rhoBed * A) / 1e5
    }
    const Q = (Ft * R * T) / (P * 1e5)
    return [dX, dT, dP, eps / (rhoBed * Q)]
  }

  // ---- Dormand-Prince 5(4), dense output at n_points uniformly spaced W
  const nP = Math.max(inp.n_points ?? 101, 2)
  const rtol = inp.rtol ?? 1e-8
  const atol = [1e-12, 1e-8, 1e-10, 1e-12]
  const Pstop = m.reactor.hydraulic_stop_fraction_of_inlet_pressure * inp.P_in_bar
  const Wout = Array.from({ length: nP }, (_, i) => (W * i) / (nP - 1))
  const outU: number[][] = [[X0, Tin, inp.P_in_bar, 0]]
  const outW: number[] = [0]
  let u = [X0, Tin, inp.P_in_bar, 0]
  let w = 0
  let h = W > 0 ? 1e-9 * W : 0
  let steps = 0
  let hydraulic = false
  const c = [0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1, 1]
  const a = [[], [1 / 5], [3 / 40, 9 / 40], [44 / 45, -56 / 15, 32 / 9], [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
    [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656], [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84]]
  const b5 = [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0]
  const b4 = [5179 / 57600, 0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40]
  void c
  let k1 = rhs(u)
  let next = 1
  while (next < nP && W > 0) {
    const target = Wout[next]
    let hh = Math.min(h, target - w)
    if (hh <= 0) { outW.push(w); outU.push(u.slice()); next++; continue }
    const ks: number[][] = [k1]
    let failed = false
    for (let s = 1; s < 7 && !failed; s++) {
      const us = u.map((ui, q) => ui + hh * a[s].reduce((acc, aj, j) => acc + aj * ks[j][q], 0))
      try {
        const k = rhs(us)
        if (k.some((x) => !Number.isFinite(x))) failed = true
        else ks.push(k)
      } catch {
        failed = true // trial state outside the property range: reject the step and shrink it
      }
    }
    steps++
    if (failed) {
      if (hh < 1e-15 * Math.max(W, 1)) throw new Error('PFR integration: step size underflow')
      h = hh * 0.1
      continue
    }
    const u5 = u.map((ui, q) => ui + hh * b5.reduce((acc, bj, j) => acc + bj * ks[j][q], 0))
    const u4 = u.map((ui, q) => ui + hh * b4.reduce((acc, bj, j) => acc + bj * ks[j][q], 0))
    let err = 0
    for (let q = 0; q < 4; q++) {
      const sc = atol[q] + rtol * Math.max(Math.abs(u[q]), Math.abs(u5[q]))
      err = Math.max(err, Math.abs(u5[q] - u4[q]) / sc)
    }
    if (steps > 2_000_000) throw new Error('PFR integration: too many steps')
    if (err <= 1 || hh < 1e-14 * Math.max(W, 1)) {
      if (u5[2] < Pstop) {
        // hydraulic stop inside this step: locate by linear interpolation of P (Python: terminal event)
        const f = (u[2] - Pstop) / (u[2] - u5[2])
        const uStop = u.map((ui, q) => ui + f * (u5[q] - ui))
        outW.push(w + f * hh); outU.push(uStop)
        hydraulic = true
        assumptions.push(`integration stopped (hydraulic limit): pressure fell to 5 % of inlet at W = ${(w + f * hh).toPrecision(6)} kg`)
        break
      }
      w += hh; u = u5; k1 = ks[6]
      if (Math.abs(w - target) <= 1e-12 * Math.max(W, 1)) { w = target; outW.push(w); outU.push(u.slice()); next++ }
      const fac = err === 0 ? 5 : Math.min(5, Math.max(0.2, 0.9 * err ** -0.2))
      h = hh * fac
    } else {
      h = hh * Math.max(0.2, 0.9 * err ** -0.25)
    }
  }

  const prof: PFRProfiles = { W_kg: [], z_m: [], conversion: [], T_K: [], P_bar: [], rate_mol_per_kgcat_s: [], X_eq_local: [],
    approach_to_equilibrium: [], residence_time_s: [] }
  for (let i = 0; i < outW.length; i++) {
    const [Xr, T, P, tau] = outU[i]
    const X = Math.min(Math.max(Xr, 0), 1)
    const { p } = partial(X, P)
    let r = NaN
    if (!(l.form === 'temkin_pyzhev' && p.H2 <= 0)) r = rateLaw(m, inp.catalyst_id, T, p, opt)
    const xeq = equilibriumConversion(m, T, P, feed)
    prof.W_kg.push(outW[i]); prof.z_m.push(outW[i] / (rhoBed * A)); prof.conversion.push(Xr); prof.T_K.push(T); prof.P_bar.push(P)
    prof.rate_mol_per_kgcat_s.push(r); prof.X_eq_local.push(xeq); prof.approach_to_equilibrium.push(xeq > 0 ? X / xeq : NaN)
    prof.residence_time_s.push(tau)
  }
  const last = outU[outU.length - 1]
  const Xo = last[0]
  const Fout: Record<string, number> = {}
  for (const [s, v] of Object.entries(flows(Math.min(Math.max(Xo, 0), 1)))) Fout[s] = v / KMOLH_TO_MOLS
  const Fin: Record<string, number> = {}
  for (const [s, v] of Object.entries(Ff)) Fin[s] = v / KMOLH_TO_MOLS
  const Vbed = W / rhoBed
  const Fn = species.reduce((acc, s) => acc + Ff[s], 0)
  const Qn = (Fn * R * m.reactor.normal_T_K) / m.reactor.normal_P_Pa
  const xeqOut = prof.X_eq_local[prof.X_eq_local.length - 1]
  void equilibriumConstant
  return {
    inputs: { ...inp, eps_b: eps, rho_particle_kg_m3: rhoP, rho_bed_kg_m3: rhoBed, dp_m: dp, tube_inner_diameter_m: D, n_tubes: nt, pressure_drop: usePD },
    profiles: prof,
    outlet: {
      conversion: Xo, T_C: last[1] - 273.15, P_bar: last[2], pressure_drop_bar: inp.P_in_bar - last[2], X_eq_outlet: xeqOut,
      approach_to_equilibrium: xeqOut > 0 ? Xo / xeqOut : NaN, flows_kmol_h: Fout, H2_kmol_h: Fout.H2,
      heat_input_kW: enthalpyFlowKW(m, Fout, last[1]) - enthalpyFlowKW(m, Fin, Tin),
      residence_time_s: last[3], W_reached_kg: outW[outW.length - 1], hydraulic_limit: hydraulic,
    },
    bed_length_m: W / (rhoBed * A),
    bed_volume_m3: Vbed,
    GHSV_h_inv: Vbed > 0 ? (Qn * 3600) / Vbed : Infinity,
    steps,
    assumptions,
  }
}
