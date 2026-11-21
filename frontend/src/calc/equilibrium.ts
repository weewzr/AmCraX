/**
 * Ideal-gas equilibrium of ammonia cracking, NH3 <-> 1/2 N2 + 3/2 H2, pure NH3 feed.
 *
 * This is a TypeScript port of the independent Python model (backend/amcrax/thermodynamics) restricted to the
 * ideal-gas case. Species data are the NASA-7 polynomials of GRI-Mech 3.0 as shipped with Cantera
 * (src/data/nasa7.json, copied from backend/amcrax/data/nasa7.json; provenance recorded in that file).
 * It is calculated in the browser. It is NOT an Aspen Plus result.
 *
 *   K(T) = exp(-dG(T) / (R T)),   X_eq = (1 + (3 sqrt(3) / 4) (P / 1 bar) / K)^(-1/2)
 *
 * Derivation: docs/technical_report/sections/04_fundamentals.md, Eqs. (4.5)-(4.9).
 */
import nasa7 from '../data/nasa7.json'

/** CODATA 2018 gas constant, J/(mol K): same value as the Python model. */
export const R_J_MOL_K = 8.314462618
export const KELVIN = 273.15
/** (1/2)^(1/2) (3/2)^(3/2) = 3 sqrt(3) / 4 */
export const STOICH_CONST = (3 * Math.sqrt(3)) / 4

export const NASA7_PROVENANCE = {
  mechanism: 'GRI-Mech 3.0 NASA-7 polynomials',
  via: 'Cantera 3.2.0 (gri30.yaml)',
  file: 'backend/amcrax/data/nasa7.json',
} as const

interface Species { T_ranges_K: number[]; coeffs_low: number[]; coeffs_high: number[] }
const SPECIES = nasa7.species as unknown as Record<string, Species>

function coeffs(name: 'NH3' | 'N2' | 'H2', T: number): number[] {
  const sp = SPECIES[name]
  const [tmin, tmid, tmax] = sp.T_ranges_K
  if (!(T >= tmin - 100 && T <= tmax)) throw new RangeError(`T = ${T} K outside the NASA-7 range of ${name}`)
  return T <= tmid ? sp.coeffs_low : sp.coeffs_high
}

/** Molar enthalpy including formation enthalpy, kJ/mol. */
export function enthalpyKJ(name: 'NH3' | 'N2' | 'H2', T: number): number {
  const a = coeffs(name, T)
  const hRT = a[0] + (a[1] * T) / 2 + (a[2] * T ** 2) / 3 + (a[3] * T ** 3) / 4 + (a[4] * T ** 4) / 5 + a[5] / T
  return (R_J_MOL_K * T * hRT) / 1000
}

/** Standard (1 bar) molar entropy, J/(mol K). */
export function entropyJ(name: 'NH3' | 'N2' | 'H2', T: number): number {
  const a = coeffs(name, T)
  const sR = a[0] * Math.log(T) + a[1] * T + (a[2] * T ** 2) / 2 + (a[3] * T ** 3) / 3 + (a[4] * T ** 4) / 4 + a[6]
  return R_J_MOL_K * sR
}

const gibbsKJ = (name: 'NH3' | 'N2' | 'H2', T: number): number => enthalpyKJ(name, T) - (T * entropyJ(name, T)) / 1000

const NU = { NH3: -1, N2: 0.5, H2: 1.5 } as const

/** Standard reaction enthalpy per mol NH3 decomposed, kJ/mol (> 0, endothermic). */
export function reactionEnthalpyKJ(T_K: number): number {
  return NU.NH3 * enthalpyKJ('NH3', T_K) + NU.N2 * enthalpyKJ('N2', T_K) + NU.H2 * enthalpyKJ('H2', T_K)
}

/** Standard (1 bar) reaction Gibbs energy per mol NH3, kJ/mol. */
export function reactionGibbsKJ(T_K: number): number {
  return NU.NH3 * gibbsKJ('NH3', T_K) + NU.N2 * gibbsKJ('N2', T_K) + NU.H2 * gibbsKJ('H2', T_K)
}

/** Equilibrium constant Kp (standard state 1 bar). */
export function equilibriumConstant(T_K: number): number {
  return Math.exp((-reactionGibbsKJ(T_K) * 1000) / (R_J_MOL_K * T_K))
}

export interface EquilibriumPoint {
  T_C: number
  P_bar: number
  K: number
  /** NH3 conversion (fraction, 0-1) */
  conversion: number
  /** equilibrium mole fractions */
  y: { NH3: number; H2: number; N2: number }
  /** reaction enthalpy at T, kJ per mol NH3 decomposed */
  dH_kJ_per_mol_NH3: number
  /** heat to crack the feed at equilibrium conversion, kJ per mol NH3 fed (= X * dH) */
  heat_kJ_per_mol_NH3_fed: number
}

/** X_eq of a pure NH3 feed, closed form (Eq. 4.9). */
export function equilibriumConversion(T_K: number, P_bar: number): number {
  const K = equilibriumConstant(T_K)
  return (1 + (STOICH_CONST * P_bar) / K) ** -0.5
}

export function equilibriumAt(T_C: number, P_bar: number): EquilibriumPoint {
  if (!(P_bar > 0)) throw new RangeError('P must be positive')
  const T = T_C + KELVIN
  const K = equilibriumConstant(T)
  const X = (1 + (STOICH_CONST * P_bar) / K) ** -0.5
  const dH = reactionEnthalpyKJ(T)
  return {
    T_C, P_bar, K, conversion: X,
    y: { NH3: (1 - X) / (1 + X), H2: (1.5 * X) / (1 + X), N2: (0.5 * X) / (1 + X) },
    dH_kJ_per_mol_NH3: dH,
    heat_kJ_per_mol_NH3_fed: X * dH,
  }
}

/** Conversion versus temperature at fixed P. */
export function conversionCurve(P_bar: number, Tmin_C = 250, Tmax_C = 900, step_C = 10): { T_C: number; conversion: number }[] {
  const out: { T_C: number; conversion: number }[] = []
  for (let T = Tmin_C; T <= Tmax_C + 1e-9; T += step_C) out.push({ T_C: T, conversion: equilibriumAt(T, P_bar).conversion })
  return out
}
