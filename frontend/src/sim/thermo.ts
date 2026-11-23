/**
 * Ideal-gas thermodynamics (NASA-7, GRI-Mech 3.0) with the coefficients read from model.json.
 * Same functional form as src/calc/equilibrium.ts and backend/amcrax/thermodynamics (nasa7.py, equilibrium.py);
 * the coefficients are NOT duplicated here. Calculated in the browser; not an Aspen result.
 */
import type { SimModel } from './types'

export type Species = string

function coeffs(m: SimModel, s: Species, T: number): number[] {
  const sp = m.thermo.species[s]
  if (!sp) throw new RangeError(`unknown species ${s}`)
  if (!(T >= sp.Tmin - 100 && T <= sp.Tmax)) throw new RangeError(`T = ${T} K outside NASA-7 range of ${s}`)
  return T <= sp.Tmid ? sp.low : sp.high
}

/** cp, J/(mol K). Ar (not in the NASA-7 set) = argon_cp_J_molK from model.json. */
export function cp(m: SimModel, s: Species, T: number): number {
  if (s === 'Ar') return m.thermo.argon_cp_J_molK
  const a = coeffs(m, s, T)
  return m.thermo.R_J_molK * (a[0] + a[1] * T + a[2] * T ** 2 + a[3] * T ** 3 + a[4] * T ** 4)
}

/** Molar enthalpy incl. formation enthalpy, kJ/mol. */
export function enthalpy(m: SimModel, s: Species, T: number): number {
  const a = coeffs(m, s, T)
  const hRT = a[0] + (a[1] * T) / 2 + (a[2] * T ** 2) / 3 + (a[3] * T ** 3) / 4 + (a[4] * T ** 4) / 5 + a[5] / T
  return (m.thermo.R_J_molK * T * hRT) / 1000
}

/** Standard (1 bar) entropy, J/(mol K). */
export function entropy(m: SimModel, s: Species, T: number): number {
  const a = coeffs(m, s, T)
  const sR = a[0] * Math.log(T) + a[1] * T + (a[2] * T ** 2) / 2 + (a[3] * T ** 3) / 3 + (a[4] * T ** 4) / 4 + a[6]
  return m.thermo.R_J_molK * (sR + m.thermo.species[s].ds_R)
}

const NU: Record<string, number> = { NH3: -1, N2: 0.5, H2: 1.5 }

/** Reaction enthalpy per mol NH3 decomposed, kJ/mol. */
export function reactionEnthalpy(m: SimModel, T: number): number {
  return Object.entries(NU).reduce((acc, [s, nu]) => acc + nu * enthalpy(m, s, T), 0)
}

export function reactionGibbs(m: SimModel, T: number): number {
  return Object.entries(NU).reduce((acc, [s, nu]) => acc + nu * (enthalpy(m, s, T) - (T * entropy(m, s, T)) / 1000), 0)
}

/** Kp, 1 bar standard state, per mol NH3. */
export function equilibriumConstant(m: SimModel, T: number): number {
  return Math.exp((-reactionGibbs(m, T) * 1000) / (m.thermo.R_J_molK * T))
}

/** Enthalpy flow, kW, of flows in kmol/h (Ar via constant cp from 298.15 K, as amcrax.reactor.pfr._enthalpy_kW). */
export function enthalpyFlowKW(m: SimModel, n_kmol_h: Record<string, number>, T: number): number {
  let H = 0
  for (const [s, v] of Object.entries(n_kmol_h)) {
    if (!v) continue
    if (s === 'Ar') { H += v * m.thermo.argon_cp_J_molK * 1e-3 * (T - 298.15); continue }
    H += v * enthalpy(m, s, T)
  }
  return (H * 1000) / 3600
}

/**
 * Ideal-gas equilibrium conversion of the NH3 in a feed of NH3/H2/N2 + inerts (any molar unit), at T [K], P [bar].
 * Solves K = y_N2^0.5 y_H2^1.5 P / y_NH3 for the extent by bisection on ln(n_NH3) (same root as
 * amcrax.thermodynamics.solve_equilibrium, eos='ideal').
 */
export function equilibriumConversion(m: SimModel, T: number, P: number, feed: Record<string, number>): number {
  const n0 = feed.NH3 ?? 0
  const h0 = feed.H2 ?? 0
  const N0 = feed.N2 ?? 0
  const inert = Object.entries(feed).filter(([s]) => !(s in NU)).reduce((a, [, v]) => a + v, 0)
  const lnK = Math.log(equilibriumConstant(m, T))
  const lnP = Math.log(P / m.thermo.standard_pressure_bar)
  const nmax = n0 + Math.min(N0 / 0.5, h0 / 1.5)
  const resid = (z: number): number => {
    const nn = Math.exp(z)
    const xi = n0 - nn
    const nN2 = Math.max(N0 + 0.5 * xi, 1e-300)
    const nH2 = Math.max(h0 + 1.5 * xi, 1e-300)
    const tot = nn + nN2 + nH2 + inert
    return lnP - lnK + 0.5 * Math.log(nN2 / tot) + 1.5 * Math.log(nH2 / tot) - Math.log(nn / tot)
  }
  let hi = Math.log(nmax)
  let lo = hi - 690
  for (let i = 0; i < 200; i++) {
    const mid = 0.5 * (lo + hi)
    if (resid(mid) > 0) lo = mid
    else hi = mid
    if (hi - lo < 1e-14) break
  }
  const nn = Math.exp(0.5 * (lo + hi))
  return 1 - nn / n0
}
