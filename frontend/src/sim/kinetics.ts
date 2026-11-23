/**
 * Port of backend/amcrax/kinetics/rate_laws.py: every rate law of kinetics.yaml (parameters read from model.json).
 * Rate returned in mol NH3 / (kg_cat s). Calculated in the browser; not an Aspen result.
 */
import { equilibriumConstant } from './thermo'
import type { RateLaw, SimModel } from './types'

const pv = (law: RateLaw, k: string): number => {
  const p = law.parameters[k]
  if (!p) throw new Error(`parameter ${k} missing for ${law.id}`)
  return p.value
}

export function law(m: SimModel, id: string): RateLaw {
  const l = m.kinetics.laws[id]
  if (!l) throw new RangeError(`unknown catalyst_id ${id}`)
  return l
}

/** Q = p_N2^0.5 p_H2^1.5 / p_NH3 (bar). */
export function reactionQuotient(p: Record<string, number>): number {
  const pn = p.NH3 ?? 0
  if (pn <= 0) return Infinity
  return Math.max(p.N2 ?? 0, 0) ** 0.5 * Math.max(p.H2 ?? 0, 0) ** 1.5 / pn
}

/** Keq of Kum Eq. 2 per mol NH3: 'published' (Eq. 4, AmCraX reading) or 'amcrax_thermo'. */
export function kumKeq(m: SimModel, l: RateLaw, T: number, basis: 'published' | 'amcrax_thermo'): number {
  if (basis === 'amcrax_thermo') return equilibriumConstant(m, T)
  const c = l.equilibrium_constant?.dGr_coefficients_J
  if (!c) throw new Error('dGr coefficients missing')
  const dG = c[0] + c[1] * T + c[2] * T ** 2 + c[3] * T ** 3
  return Math.sqrt(Math.exp(-dG / (m.kinetics.unit_conversions.gas_constant_J_per_mol_K * T)))
}

export function takahashiConstants(m: SimModel, l: RateLaw, T: number) {
  const RT = m.kinetics.unit_conversions.gas_constant_J_per_mol_K * T
  const k1 = pv(l, 'A1')
  const k2 = pv(l, 'A2') * Math.exp((-pv(l, 'Ea2') * 1e3) / RT)
  const k3 = pv(l, 'A3') * Math.exp((-pv(l, 'Ea3') * 1e3) / RT)
  const k4 = pv(l, 'A4') * Math.exp((-pv(l, 'Ea4') * 1e3) / RT)
  const K1 = pv(l, 'A5') * Math.exp((-pv(l, 'Ea5') * 1e3) / RT)
  const K4 = pv(l, 'A6') * Math.exp((-pv(l, 'Ea4') * 1e3) / RT)
  return { k1, k_minus1: k1 / K1, k2, k3, k4, k_minus4: k4 / K4, K1, K4 }
}

/** Brent root finder (as scipy.optimize.brentq), f(a) and f(b) of opposite sign. */
export function brent(f: (x: number) => number, a: number, b: number, xtol = 1e-14, rtol = 1e-13, maxiter = 500): number {
  let fa = f(a), fb = f(b)
  if (fa === 0) return a
  if (fb === 0) return b
  if (fa * fb > 0) throw new Error('brent: root not bracketed')
  let c = a, fc = fa, d = b - a, e = d
  for (let i = 0; i < maxiter; i++) {
    if (fb * fc > 0) { c = a; fc = fa; d = b - a; e = d }
    if (Math.abs(fc) < Math.abs(fb)) { a = b; b = c; c = a; fa = fb; fb = fc; fc = fa }
    const tol = 2 * Number.EPSILON * Math.abs(b) + 0.5 * (xtol + rtol * Math.abs(b))
    const mm = 0.5 * (c - b)
    if (Math.abs(mm) <= tol || fb === 0) return b
    if (Math.abs(e) >= tol && Math.abs(fa) > Math.abs(fb)) {
      const s = fb / fa
      let p: number, q: number
      if (a === c) { p = 2 * mm * s; q = 1 - s } else {
        const qq = fa / fc, r = fb / fc
        p = s * (2 * mm * qq * (qq - r) - (b - a) * (r - 1))
        q = (qq - 1) * (r - 1) * (s - 1)
      }
      if (p > 0) q = -q; else p = -p
      if (2 * p < Math.min(3 * mm * q - Math.abs(tol * q), Math.abs(e * q))) { e = d; d = p / q } else { d = mm; e = d }
    } else { d = mm; e = d }
    a = b; fa = fb
    b += Math.abs(d) > tol ? d : (mm > 0 ? tol : -tol)
    fb = f(b)
  }
  return b
}

/** Quasi-steady-state coverages of the Takahashi model and r = r2 [mol s^-1 g^-1]. */
export function takahashiCoverages(m: SimModel, l: RateLaw, T: number, yNH3: number, yH2: number) {
  const c = takahashiConstants(m, l, T)
  yNH3 = Math.max(yNH3, 0); yH2 = Math.max(yH2, 0)
  const parts = (ths: number) => {
    const thNH3 = (c.k1 * yNH3 * ths) / (c.k_minus1 + c.k2 * ths ** 3)
    const r2 = c.k2 * thNH3 * ths ** 3
    const thN = Math.sqrt(r2 / (2 * c.k3))
    const thH = Math.sqrt((1.5 * r2 + c.k_minus4 * yH2 * ths ** 2) / c.k4)
    return [thNH3, thN, thH, r2] as const
  }
  const resid = (u: number) => { const ths = Math.exp(u); const [a, b, h] = parts(ths); return ths + a + b + h - 1 }
  const [lo, hi] = m.kinetics.takahashi_root_bracket_ln_theta_s
  const u = resid(hi) <= 0 ? hi : brent(resid, lo, hi)
  const ths = Math.exp(u)
  const [a, b, h, r2] = parts(ths)
  return { theta_s: ths, theta_NH3: a, theta_N: b, theta_H: h, r_mol_per_g_s: r2 }
}

export function lucentiniRatePerG(m: SimModel, l: RateLaw, T: number, p: Record<string, number>): number {
  const RT = m.kinetics.unit_conversions.gas_constant_J_per_mol_K * T
  const cNH3 = (Math.max(p.NH3 ?? 0, 0) * 1e5) / RT
  const cH2 = (Math.max(p.H2 ?? 0, 0) * 1e5) / RT
  const k = pv(l, 'k0') * Math.exp((-pv(l, 'Ek') * 1e3) / RT)
  const K1 = pv(l, 'K1')
  const den = 1 + K1 * cNH3 + Math.sqrt(cH2 / pv(l, 'K4'))
  return (k * K1 * cNH3) / den ** 2
}

export interface RateOptions { approachFactor?: boolean; keqBasis?: 'published' | 'amcrax_thermo' }

/** Net NH3 consumption rate [mol NH3 / (kg_cat s)] at T [K] and partial pressures p [bar]. */
export function rate(m: SimModel, id: string, T: number, p: Record<string, number>, opt: RateOptions = {}): number {
  const l = law(m, id)
  if (!l.usable) throw new Error(`catalyst ${id} is flagged usable=false`)
  const P = Object.values(p).reduce((a, v) => a + Math.max(v, 0), 0)
  if (!(P > 0)) throw new Error('total pressure must be > 0')
  const gkg = m.kinetics.unit_conversions.g_per_kg
  const useAF = opt.approachFactor ?? m.kinetics.equilibrium_approach_factor.default_on
  if (l.form === 'takahashi_microkinetic') {
    const yN = Math.max(p.NH3 ?? 0, 0) / P
    const yH = Math.max(p.H2 ?? 0, 0) / P
    if (yN <= 0) return 0
    let r = takahashiCoverages(m, l, T, yN, yH).r_mol_per_g_s
    if (useAF) r *= 1 - reactionQuotient(p) / equilibriumConstant(m, T)
    return r * gkg
  }
  if (l.form === 'temkin_pyzhev') {
    const pn = p.NH3 ?? 0, ph = p.H2 ?? 0, pn2 = Math.max(p.N2 ?? 0, 0)
    if (pn <= 0 || ph <= 0) throw new Error('Temkin-Pyzhev form is singular for p_NH3 <= 0 or p_H2 <= 0')
    const beta = pv(l, 'beta')
    const k = pv(l, 'ko') * Math.exp(-pv(l, 'Ea') / (m.kinetics.unit_conversions.gas_constant_J_per_mol_K * T))
    const keq = kumKeq(m, l, T, opt.keqBasis ?? 'amcrax_thermo')
    const lnr = 2 * Math.log(pn) - 3 * Math.log(ph)
    return k * (Math.exp(beta * lnr) - (pn2 / keq ** 2) * Math.exp(-(1 - beta) * lnr)) * gkg
  }
  if (l.form === 'lhhw_lucentini') {
    if (Math.max(p.NH3 ?? 0, 0) <= 0) return 0
    let r = lucentiniRatePerG(m, l, T, p)
    if (useAF) r *= 1 - reactionQuotient(p) / equilibriumConstant(m, T)
    return r * gkg
  }
  throw new Error(`unknown rate-law form ${(l as RateLaw).form}`)
}
