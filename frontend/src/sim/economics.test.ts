/// <reference types="node" />
import { describe, expect, it } from 'vitest'
import { catalystPrice } from './economics'
import { simulate, type SimInputs } from './simulate'
import { data, model } from './testdata'

const baseline: SimInputs = { catalyst_id: 'ru_kum_temkin_pyzhev', T_C: 600, P_bar: 20, W_kg: 100, mode: 'isothermal', reactor_model: 'equilibrium',
  heat_integration: true, psa_h2_recovery: 0.85, feed_total_kmol_h: 100, nh3_route: 'grey', n_points: 2 }
const kinetic: SimInputs = { ...baseline, reactor_model: 'kinetic', T_C: 499 }

describe('unified reference economics in the browser (phase 2, S3)', () => {
  it('names the reference scenario and its version', () => {
    expect(model.economics.basis).toMatch(/^reference_scenario .* v\d/)
    expect(model.economics.capex_mode).toBe('reference')
    expect(model.economics.capex_reference.method).toBe('cho2026_itemised_v1')
    expect(model.economics.basis).not.toMatch(/pre-unification/)
    expect(model.fx.SGD_per_USD).toBeCloseTo(1.288444, 6)
  })

  it('shows the frozen baseline: 4.015 USD/kg and 5.174 SGD/kg (stored Aspen baseline, grey ammonia 450 USD/t)', () => {
    const r = simulate(baseline, data)
    expect(r.process?.h2_product_kg_h.source).toBe('aspen')
    expect(r.economics!.nh3_price_USD_per_t).toBe(450)
    expect(r.economics!.lcoh_USD_per_kg).toBeCloseTo(4.0155, 3)
    expect(r.economics!.lcoh_USD_per_kg.toFixed(3)).toBe('4.015')
    expect(r.economics!.lcoh_SGD_per_kg.toFixed(3)).toBe('5.174')
    expect(r.economics!.capex_method).toBe('cho2026_itemised_v1')
  })

  it('cost components add up to the LCOH and NPV and payback come from the same call', () => {
    const e = simulate(baseline, data).economics!
    const sum = Object.values(e.breakdown_USD_per_kg).reduce((x, y) => x + y, 0)
    expect(sum).toBeCloseTo(e.lcoh_USD_per_kg, 12)
    expect(Object.keys(e.breakdown_USD_per_kg).sort()).toEqual(['ammonia_feed', 'capex', 'carbon_tax', 'catalyst', 'cooling_water', 'electricity', 'fixed_opex', 'heat_fuel'])
    expect(Number.isFinite(e.npv_USD)).toBe(true)
    // revenue at the reference hydrogen price does not cover the cost: no payback (as singapore.evaluate returns None)
    expect(e.payback_yr).toBeNull()
  })

  it('catalyst price source: central > low, high >= central, Phase 1 TEA is its own value; derived prices come from the data file', () => {
    const id = 'ru_kum_temkin_pyzhev'
    const c = catalystPrice(model, id, 'central').usd_per_kg, lo = catalystPrice(model, id, 'low').usd_per_kg, hi = catalystPrice(model, id, 'high').usd_per_kg
    expect(lo).toBeLessThan(c)
    expect(hi).toBeGreaterThanOrEqual(c)
    expect(catalystPrice(model, id, 'phase1_tea').usd_per_kg).toBe(model.economics.catalyst_price_USD_per_kg.Ru)
    expect(c).toBe(model.economics.catalyst_prices.by_law[id].central.usd_per_kg)
    const costOf = (src: 'central' | 'low' | 'high' | 'phase1_tea') => simulate({ ...kinetic, catalyst_price_source: src }, data).economics!.breakdown_USD_per_kg.catalyst
    expect(costOf('low')).toBeLessThan(costOf('central'))
    expect(costOf('central') / costOf('low')).toBeCloseTo(c / lo, 9)
    expect(costOf('phase1_tea')).toBeGreaterThan(0)
  })

  it('an equilibrium reactor ignores the catalyst price selection (no catalyst in the Aspen baseline)', () => {
    const a = simulate({ ...baseline, catalyst_price_source: 'low' }, data).economics!.lcoh_USD_per_kg
    const b = simulate({ ...baseline, catalyst_price_source: 'high' }, data).economics!.lcoh_USD_per_kg
    expect(a).toBe(b)
  })
})
