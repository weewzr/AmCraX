import { describe, expect, it } from 'vitest'
import { equilibriumAt } from '../calc/equilibrium'
import { rate } from './kinetics'
import { simulatePFR } from './pfr'
import { model, vectors } from './testdata'
import { equilibriumConversion } from './thermo'

const tol = vectors.tolerances
const rel = (a: number, b: number) => Math.abs(a - b) / Math.max(Math.abs(b), 1e-30)

describe('thermo (model.json coefficients) agrees with src/calc/equilibrium.ts', () => {
  it('pure-NH3 equilibrium conversion', () => {
    for (const [T, P] of [[400, 1], [600, 20], [800, 50]]) {
      const ref = equilibriumAt(T, P).conversion
      expect(Math.abs(equilibriumConversion(model, T + 273.15, P, { NH3: 1 }) - ref)).toBeLessThan(1e-10)
    }
  })
})

describe('rate laws against the Python registry (amcrax.kinetics.rate_mol_per_kgcat_s)', () => {
  const vs = vectors.vectors.filter((v) => v.kind === 'rate')
  it('has a vector for every law in model.json', () => {
    for (const id of model.kinetics.law_ids) expect(vs.some((v) => v.inputs.catalyst_id === id)).toBe(true)
  })
  for (const v of vs) {
    it(v.id, () => {
      const r = rate(model, v.inputs.catalyst_id, v.inputs.T_K, v.inputs.p_bar, { keqBasis: 'amcrax_thermo' })
      expect(rel(r, v.python.rate)).toBeLessThan(tol.rate_rel as number)
    })
  }
})

describe('PFR against the Python model (amcrax.reactor.pfr.simulate_pfr)', () => {
  const vs = vectors.vectors.filter((v) => v.kind === 'pfr')
  for (const v of vs) {
    it(v.id, () => {
      const i = v.inputs
      const r = simulatePFR(model, { catalyst_id: i.catalyst_id, W_kg: i.W_kg, T_in_C: i.T_in_C, P_in_bar: i.P_in_bar, mode: i.mode,
        pressure_drop: i.pressure_drop, n_tubes: i.n_tubes, T_wall_C: i.T_wall_C ?? undefined, U_W_m2K: i.U_W_m2K ?? undefined,
        n_points: v.python.W_kg.length })
      const p = v.python
      expect(r.profiles.W_kg.length).toBe(p.W_kg.length)
      for (let k = 0; k < p.W_kg.length; k++) {
        expect(Math.abs(r.profiles.conversion[k] - p.conversion[k])).toBeLessThan(tol.conversion_abs as number)
        expect(Math.abs(r.profiles.T_K[k] - p.T_K[k])).toBeLessThan(tol.temperature_K_abs as number)
        expect(Math.abs(r.profiles.P_bar[k] - p.P_bar[k])).toBeLessThan(tol.pressure_bar_abs as number)
      }
      const o = p.outlet
      if (Math.abs(o.heat_input_kW) > 1) expect(rel(r.outlet.heat_input_kW, o.heat_input_kW)).toBeLessThan(tol.duty_rel as number)
      expect(Math.abs(r.outlet.X_eq_outlet - o.X_eq_outlet)).toBeLessThan(tol.conversion_abs as number)
    }, 60_000)
  }
})
