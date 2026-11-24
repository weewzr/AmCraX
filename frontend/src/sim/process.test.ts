import { describe, expect, it } from 'vitest'
import { carbonCost, carbonIntensity, type Heating } from './carbon'
import { evaluateEconomics, type CostKey } from './economics'
import { simulateProcess, type ProcessResult } from './process'
import { simulate } from './simulate'
import * as sweeps from './sweeps'
import { data, model, vectors } from './testdata'

const tol = vectors.tolerances as Record<string, number>
/** Economics parity (fix plan C-m13): the vectors are Python-generated and the browser is an exact port, so agreement is
 *  asserted to 1e-9 relative (tighter than the file's cost_rel, which is the general port tolerance). */
const ECON_REL = 1e-9
const rel = (a: number, b: number) => Math.abs(a - b) / Math.max(Math.abs(b), 1e-12)

// computed in the browser (exact port) vs interpolated from the Python grid (asserted on grid nodes only)
const COMPUTED: (keyof ProcessResult)[] = ['nh3_conversion' as keyof ProcessResult, 'h2_in_cracked_gas_kmol_h', 'h2_product_kg_h', 'reactor_duty_kW', 'tailgas_lhv_kW']
const INTERPOLATED = ['preheat_duty_kW', 'vaporiser_duty_kW', 'recovered_heat_kW', 'cooling_duty_kW', 'pump_power_kW',
  'tailgas_combustion_heat_kW', 'total_external_heating_kW', 'net_fuel_heat_deficit_kW'] as const

function run(i: Record<string, number | boolean>) {
  return simulateProcess(model, { T_C: i.T_C as number, P_bar: i.P_bar as number, heat_integration: i.heat_integration as boolean,
    feed_total_kmol_h: i.feed_total_kmol_h as number | undefined, psa_h2_recovery: i.psa_h2_recovery as number, psa_n2_slip: i.psa_n2_slip as number | undefined })
}

describe('process energy balance against amcrax.process_model.flowsheet (eos=ideal)', () => {
  for (const v of vectors.vectors.filter((x) => x.kind === 'process')) {
    it(v.id, () => {
      const r = run(v.inputs)
      const p = v.python
      expect(Math.abs(r.conversion - p.nh3_conversion)).toBeLessThan(tol.conversion_abs)
      for (const k of COMPUTED.slice(1)) expect(rel(r[k] as number, p[k])).toBeLessThan(tol.duty_rel)
      expect(Math.abs(r.h2_purity_mole_frac - p.h2_purity_mole_frac)).toBeLessThan(1e-6)
      if (v.on_grid) for (const k of INTERPOLATED) expect(rel(r[k] as number, p[k]), k).toBeLessThan(tol.duty_rel)
    })
  }
})

describe('purification (reduced-order PSA) against the Python flowsheet', () => {
  for (const v of vectors.vectors.filter((x) => x.kind === 'purification')) {
    it(v.id, () => {
      const r = run(v.inputs)
      expect(rel(r.h2_product_kg_h, v.python.h2_product_kg_h)).toBeLessThan(tol.duty_rel)
      expect(Math.abs(r.h2_purity_mole_frac - v.python.h2_purity_mole_frac)).toBeLessThan(1e-6)
      expect(rel(r.tailgas_lhv_kW, v.python.tailgas_lhv_kW)).toBeLessThan(tol.duty_rel)
    })
  }
})

describe('economics against amcrax.economics.singapore.evaluate', () => {
  for (const v of vectors.vectors.filter((x) => x.kind === 'economics')) {
    it(v.id, () => {
      const s = v.inputs.summary
      const r = evaluateEconomics(model, { h2_kg_h: s.h2_kg_h, nh3_feed_kmol_h: s.nh3_feed_kmol_h, heat_deficit_kW: s.heat_deficit_kW,
        cooling_kW: s.cooling_kW, pump_kW: s.pump_kW }, v.inputs.scenario, v.inputs.overrides)
      const p = v.python
      expect(ECON_REL).toBeLessThanOrEqual(tol.cost_rel)
      expect(rel(r.lcoh_USD_per_kg, p.lcoh_USD_per_kg)).toBeLessThan(ECON_REL)
      expect(rel(r.rec_USD_per_kg, p.rec_USD_per_kg)).toBeLessThan(ECON_REL)
      for (const k of Object.keys(p.breakdown_USD_per_kg) as CostKey[]) {
        const b = p.breakdown_USD_per_kg[k]
        if (b === 0) expect(r.breakdown_USD_per_kg[k]).toBe(0)
        else expect(rel(r.breakdown_USD_per_kg[k], b), k).toBeLessThan(ECON_REL)
      }
      expect(rel(r.catalyst_mass_kg, p.catalyst_mass_kg)).toBeLessThan(ECON_REL)
      expect(rel(r.capex_total_USD, p.capex_total_USD)).toBeLessThan(ECON_REL)
      expect(Math.abs(r.npv_USD - p.npv_USD)).toBeLessThan(ECON_REL * Math.max(Math.abs(p.npv_USD), r.capex_total_USD))
      expect(r.carbon_tax_liable).toBe(p.carbon_tax_liable)
      expect(rel(r.lcoh_SGD_per_kg, p.lcoh_USD_per_kg * model.fx.SGD_per_USD)).toBeLessThan(1e-12)
    })
  }
})

describe('carbon intensity against amcrax.environmental.carbon_intensity', () => {
  for (const v of vectors.vectors.filter((x) => x.kind === 'carbon')) {
    it(v.id, () => {
      const [route, heat] = (v.inputs.scenario as string).split('/')
      const r = carbonIntensity(model, { h2_kg_h: v.inputs.h2_kg_h, nh3_feed_kg_h: v.inputs.nh3_feed_kg_h, heat_deficit_kW: v.inputs.heat_deficit_kW,
        pump_kW: v.inputs.pump_kW }, route, heat as Heating)
      expect(rel(r.total_kgCO2e_per_kgH2, v.python.total)).toBeLessThan(tol.carbon_rel)
      for (const [k, b] of Object.entries(v.python.breakdown as Record<string, number>)) {
        const x = (r.breakdown_kgCO2e_per_kgH2 as Record<string, number>)[k]
        if (b === 0) expect(x).toBe(0)
        else expect(rel(x, b)).toBeLessThan(tol.carbon_rel)
      }
    })
  }
  it('hypothetical carbon price replaces (does not add to) the actual tax term', () => {
    const v = vectors.vectors.find((x) => x.id === 'econ_base_ng_nothreshold')!
    const s = v.inputs.summary
    const summ = { h2_kg_h: s.h2_kg_h, nh3_feed_kmol_h: s.nh3_feed_kmol_h, heat_deficit_kW: s.heat_deficit_kW, cooling_kW: s.cooling_kW, pump_kW: s.pump_kW }
    const e = evaluateEconomics(model, summ, 'grey', v.inputs.overrides)
    const ci = carbonIntensity(model, { h2_kg_h: s.h2_kg_h, nh3_feed_kg_h: s.nh3_feed_kmol_h * model.thermo.molar_mass_g_mol.NH3,
      heat_deficit_kW: s.heat_deficit_kW, pump_kW: s.pump_kW }, 'grey', 'natural_gas')
    expect(e.breakdown_USD_per_kg.carbon_tax).toBeGreaterThan(0)
    const h = carbonCost(model, e, ci, 'hypothetical', 0)
    expect(h.lcoh_USD_per_kg).toBeCloseTo(e.lcoh_USD_per_kg - e.breakdown_USD_per_kg.carbon_tax, 12)
  })
})

describe('simulate() and sweeps', () => {
  const base = { catalyst_id: 'ru_kum_temkin_pyzhev', T_C: 499, P_bar: 20, W_kg: 100, mode: 'isothermal' as const, heat_integration: true,
    nh3_route: 'grey' as const }
  it('labels an exact stored Aspen case as aspen', () => {
    const r = simulate(base, data)
    expect(r.reactor.conversion.source).toBe('aspen')
    expect(r.process?.h2_product_kg_h.source).toBe('aspen')
    expect(r.process?.h2_purity_mole_frac.source).toBe('aspen')
  })
  it('labels a 20 bar Kum case off the stored set as extrapolation (fit 1-10 bar)', () => {
    const r = simulate({ ...base, T_C: 505 }, data)
    expect(r.reactor.conversion.source).toBe('extrapolation')
    expect(r.economics?.label).toBe('extrapolation')
    expect(r.warnings.some((w) => w.includes('extrapolation'))).toBe(true)
  })
  it('labels a case inside the fitted range as browser-model and purity as assumption', () => {
    const r = simulate({ ...base, T_C: 420, P_bar: 5, W_kg: 37 }, data)
    expect(r.reactor.conversion.source).toBe('browser-model')
    expect(r.process?.h2_purity_mole_frac.source).toBe('assumption')
  })
  it('Aspen equilibrium grid: node = aspen, inside = interpolation, outside = null', () => {
    expect(simulate({ ...base, T_C: 600 }, data).equilibrium.aspen?.source).toBe('aspen')
    expect(simulate({ ...base, T_C: 612, P_bar: 22 }, data).equilibrium.aspen?.source).toBe('interpolation')
    expect(simulate({ ...base, P_bar: 50 }, data).equilibrium.aspen).toBeNull()
  })
  it('produces the eight graph series', () => {
    const r = simulate({ ...base, T_C: 550 }, data)
    expect(sweeps.conversionVsTemperature(data, base, 400, 700, 4).kinetic).toHaveLength(4)
    expect(Object.keys(sweeps.rateVsTemperature(data, model.kinetics.law_ids, 20).series)).toHaveLength(model.kinetics.law_ids.length)
    const ax = sweeps.axialProfiles(r)
    expect(ax.conversion_vs_length.length).toBeGreaterThan(2)
    expect(ax.temperature_vs_length.length).toBe(ax.conversion_vs_length.length)
    expect(sweeps.h2VsHeatInput(data, { ...base, T_C: 550 }, 2000, 3)).toHaveLength(3)
    expect(sweeps.costVsVariable(data, base, 'T_C', [500, 600], ['ru_kum_temkin_pyzhev', 'ni_takahashi_microkinetic']).series.ni_takahashi_microkinetic).toHaveLength(2)
    expect(sweeps.energyBalance(r)).not.toBeNull()
    const c = sweeps.carbonByRoute(data, base, 80)
    expect(c.map((x) => x.route)).toEqual(['grey', 'blue', 'green'])
    expect(c[0].ci_kgCO2e_per_kgH2!).toBeGreaterThan(c[2].ci_kgCO2e_per_kgH2!)
  })
  it("mode 'duty' closes the energy balance (heat input = specified duty)", () => {
    const r = simulate({ ...base, mode: 'duty', duty_kW: 1000, T_C: 600 }, data)
    expect(Math.abs(r.reactor.pfr.outlet.heat_input_kW - 1000)).toBeLessThan(1000 * tol.duty_rel)
  })
})
