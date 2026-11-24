/// <reference types="node" />
/**
 * Parity of the browser carbon model (carbon.ts) with the Python carbon-pricing model
 * (amcrax.economics.carbon_pricing, vectors of scripts/research/carbon_pricing_run.py, copied by
 * scripts/research/export_simulator_data.py to results/research/simulator/carbon_pricing_vectors.json).
 * Numerical verification of a port, not validation.
 */
import { existsSync, readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { carbonCost, carbonIntensity, crossoverPrice, type Heating } from './carbon'
import type { EconResult } from './economics'
import { model, resultsDir } from './testdata'
import type { SimModel } from './types'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type V = { id: string; function: string; inputs: any; expected: any }
const file = new URL('carbon_pricing_vectors.json', resultsDir)
const src = existsSync(file) ? (JSON.parse(readFileSync(file, 'utf-8')) as { tolerance_relative: number; vectors: V[] }) : null

const close = (got: number, want: number, rel: number) => {
  // relative tolerance as stored; an absolute floor of 1e-15 only for expected values of exactly zero
  const tol = Math.max(rel * Math.abs(want), 1e-15)
  expect(Math.abs(got - want), `got ${got}, want ${want}`).toBeLessThanOrEqual(tol)
}

describe('carbon model parity with Python (carbon_pricing_vectors.json)', () => {
  it('the exported vector file exists with 18 vectors', () => {
    expect(src).not.toBeNull()
    expect(src!.vectors.length).toBe(18)
    expect(src!.tolerance_relative).toBeLessThanOrEqual(1e-9)
  })
  const vs = src?.vectors ?? []
  const tol = src?.tolerance_relative ?? 1e-9

  for (const v of vs.filter((x) => x.function === 'carbonIntensity')) {
    it(`${v.id} carbonIntensity (${v.inputs.heating}, EF ${v.inputs.nh3_ef_kg_per_kg})`, () => {
      const f = v.inputs.factors
      const m: SimModel = { ...model, carbon: { ...model.carbon, accounting: { ...model.carbon.accounting,
        ship_ef_kg_per_tkm: f.ship_ef_kg_per_tkm, distance_km: f.distance_km, natural_gas_kg_per_TJ: f.natural_gas_kg_per_TJ,
        fired_heater_efficiency_lhv: f.fired_heater_efficiency_lhv, electric_heater_efficiency: f.electric_heater_efficiency,
        electricity: { ...model.carbon.accounting.electricity, vector_grid: f.grid_kg_per_kWh } } } }
      const r = carbonIntensity(m, v.inputs.x, 'grey', v.inputs.heating as Heating,
        { grid: 'vector_grid', distance_km: v.inputs.distance_km, nh3_ef_kg_per_kg: v.inputs.nh3_ef_kg_per_kg })
      close(r.total_kgCO2e_per_kgH2, v.expected.total_kgCO2e_per_kgH2, tol)
      for (const k of ['upstream_ammonia', 'transport', 'electricity', 'external_heat'] as const) close(r.breakdown_kgCO2e_per_kgH2[k], v.expected.breakdown_kgCO2e_per_kgH2[k], tol)
      close(r.nh3_fuel_kg_h, v.expected.nh3_fuel_kg_h, tol)
      expect(r.statement).toBe(v.expected.statement)
    })
  }

  for (const v of vs.filter((x) => x.function === 'carbonCost')) {
    it(`${v.id} carbonCost (${v.inputs.mode}, ${v.inputs.price_SGD_per_t} SGD/t)`, () => {
      const e = v.inputs.econ
      const m: SimModel = { ...model, fx: { ...model.fx, SGD_per_USD: e.fx_SGD_per_USD } }
      const econ = { lcoh_USD_per_kg: e.lcoh_USD_per_kg, lcoh_SGD_per_kg: e.lcoh_SGD_per_kg, breakdown_USD_per_kg: { carbon_tax: e.breakdown_USD_per_kg.carbon_tax } } as unknown as EconResult
      const ci = { total_kgCO2e_per_kgH2: v.inputs.ci_total_kgCO2e_per_kgH2 } as Parameters<typeof carbonCost>[2]
      const r = carbonCost(m, econ, ci, v.inputs.ts_mode, v.inputs.price_SGD_per_t)
      close(r.USD_per_kg_H2, v.expected.USD_per_kg_H2, tol)
      close(r.SGD_per_kg_H2, v.expected.SGD_per_kg_H2, tol)
      close(r.lcoh_USD_per_kg, v.expected.lcoh_USD_per_kg, tol)
      close(r.lcoh_SGD_per_kg, v.expected.lcoh_SGD_per_kg, tol)
      expect(r.label).toContain(v.expected.label_contains)
      expect(/HYPOTHETICAL/.test(r.label)).toBe(v.expected.hypothetical)
      if (v.expected.hypothetical) expect(r.label).toMatch(/not Singapore law/)
    })
  }

  for (const v of vs.filter((x) => x.function === 'crossoverPrice')) {
    it(`${v.id} crossoverPrice`, () => {
      const i = v.inputs
      const r = crossoverPrice(i.lcoh_a, i.ci_a, i.lcoh_b, i.ci_b, i.fx)
      if (v.expected === null) expect(r).toBeNull()
      else close(r as number, v.expected, tol)
    })
  }
})
