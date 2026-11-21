import { describe, expect, it } from 'vitest'
import { assumptionRows, breakdownRows, breakevenPrice, consumptionVsFloor, priceGrid, tornadoRows } from './shape'

describe('economics shaping', () => {
  it('breakdown keeps order and shares sum to 1; missing -> null', () => {
    const r = breakdownRows({ capex: 1, ammonia_feed: 3, catalyst: null })
    expect(r.map((x) => x.key)[0]).toBe('capex')
    expect(r.find((x) => x.key === 'ammonia_feed')?.share).toBeCloseTo(0.75)
    expect(r.find((x) => x.key === 'catalyst')?.usd).toBeNull()
    expect(r.find((x) => x.key === 'electricity')?.share).toBeNull()
    expect(breakdownRows(undefined).every((x) => x.usd === null)).toBe(true)
  })
  it('assumption kinds from provenance source', () => {
    const r = assumptionRows({ a: { value: 1, source: 'literature', citekey: 'k', page: '7', locator: 'T4' }, b: { value: 2, source: 'assumption' }, c: { value: 'x', source: 'aspen_plus_v15' } })
    expect(r.map((x) => x.kind)).toEqual(['literature', 'assumption', 'aspen'])
    expect(r[0].where).toBe('p. 7, T4')
  })
  it('tornado sorted by swing', () => {
    const t = tornadoRows([
      { parameter: 'a', base_value: 1, low_value: 0, high_value: 2, lcoh_base: 4, lcoh_at_low: 3.9, lcoh_at_high: 4.1, swing: 0.2 },
      { parameter: 'b', base_value: 1, low_value: 0, high_value: 2, lcoh_base: 4, lcoh_at_low: 5, lcoh_at_high: 3, swing: 2 },
    ])
    expect(t[0].parameter).toBe('b'); expect(t[0].low).toBe(3); expect(t[0].high).toBe(5)
  })
  it('breakeven on a linear curve; null when flat or too short', () => {
    const c = [{ nh3_price_USD_per_t: 0, lcoh_USD_per_kg: 1 }, { nh3_price_USD_per_t: 100, lcoh_USD_per_kg: 2 }]
    expect(breakevenPrice(c, 3)).toBeCloseTo(200)
    expect(breakevenPrice(c, 0)).toBeNull()
    expect(breakevenPrice([], 3)).toBeNull()
    expect(breakevenPrice([c[0], { nh3_price_USD_per_t: 100, lcoh_USD_per_kg: 1 }], 3)).toBeNull()
  })
  it('consumption vs floor', () => {
    const r = consumptionVsFloor(6.77, 5.632)
    expect(r.excess).toBeCloseTo(1.138, 3); expect(r.floorFrac).toBeCloseTo(0.832, 2)
    expect(consumptionVsFloor(null, 5).excess).toBeNull()
  })
  it('price grid', () => { expect(priceGrid(100, 50)).toEqual([0, 50, 100]) })
})