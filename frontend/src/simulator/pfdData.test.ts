import { describe, expect, it } from 'vitest'
import { data } from '../sim/testdata'
import { baselineState, runCase, splitExtrapolation } from './model'
import { particleCount, pointAt, polyLength, speciesOf, STREAM_NAMES, STREAMS, streamViews, UNITS, unitViews } from './pfdData'

const base = baselineState(data)

describe('process flow diagram data', () => {
  it('uses the Aspen stream and block names', () => {
    expect([...new Set(STREAMS.map((s) => s.id))].sort()).toEqual(['AIR', 'FEED', 'FLUE', 'H2PROD', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'STACK', 'TAILGAS'])
    expect(Object.keys(STREAM_NAMES).sort()).toEqual([...new Set(STREAMS.map((s) => s.id))].sort())
    expect(UNITS.map((u) => u.tag)).toEqual(['FEED', 'PUMP', 'VAPORIZR', 'FEHE', 'HEATER', 'CRACKER', 'BURNER', 'COOLER', 'PSA', 'FLUEHX'])
  })
  it('without heat recovery S3 and S6 disappear and S2 / S5 take the bypass routes', () => {
    const hi = STREAMS.filter((s) => !s.bypassOnly).map((s) => s.id)
    const no = STREAMS.filter((s) => !s.hiOnly).map((s) => s.id)
    expect(hi).toContain('S3'); expect(hi).toContain('S6')
    expect(no).not.toContain('S3'); expect(no).not.toContain('S6')
    expect(no.filter((x) => x === 'S2')).toHaveLength(1)
    const u = unitViews(runCase({ ...base, heat_integration: false }, data), data)
    expect(u.FEHE.bypassed).toBe(true)
    expect(u.FEHE.facts[0].value).toBeNull()
  })
  it('particle density scales with the computed molar flow', () => {
    expect(particleCount(260, 100, 100)).toBe(10)
    expect(particleCount(260, 50, 100)).toBe(5)
    expect(particleCount(260, 0, 100)).toBe(0)
    const c = runCase(base, data)
    const v = streamViews(c, data)
    expect(v.H2PROD.flow).toBeCloseTo(c.out.process!.h2_product_kmol_h.value, 6)
    expect(v.S5.mix.H2! + v.S5.mix.N2! + v.S5.mix.NH3! + (v.S5.mix.H2O ?? 0)).toBeCloseTo(1, 12)
    expect(v.FEED.mix.NH3).toBeGreaterThan(0.99)
  })
  it('tooltip facts are core outputs (or null), never computed in the diagram', () => {
    const c = runCase(base, data)
    const v = streamViews(c, data)
    expect(v.H2PROD.facts[0].value).toBe(c.out.process!.h2_product_kg_h.value)
    expect(v.S5.facts.find((f) => f.label === 'NH3 conversion')!.value).toBe(c.out.reactor.conversion.value)
    const mem = streamViews(runCase({ ...base, purification: 'membrane' }, data), data)
    expect(mem.H2PROD.facts.every((f) => f.value === null)).toBe(true)
    expect(unitViews(runCase({ ...base, purification: 'membrane' }, data), data).PSA.notModelled).toBe(true)
  })
  it('polyline helpers and species sequence', () => {
    expect(polyLength([[0, 0], [3, 4], [3, 10]])).toBe(11)
    expect(pointAt([[0, 0], [10, 0], [10, 10]], 15)).toEqual([10, 5])
    const n = Array.from({ length: 100 }, (_, i) => speciesOf(i, { H2: 0.75, N2: 0.25 })).filter((s) => s === 'H2').length
    expect(n).toBeGreaterThan(65); expect(n).toBeLessThan(85)
  })
  it('splits extrapolated segments for dashed drawing with shared boundary points', () => {
    const s = splitExtrapolation([{ x: 1, y: 1, source: 'browser-model' }, { x: 2, y: 2, source: 'browser-model' }, { x: 3, y: 3, source: 'extrapolation' }])
    expect(s.fit.map((p) => p.y)).toEqual([1, 2, null])
    expect(s.ext.map((p) => p.y)).toEqual([null, 2, 3])
  })
})
