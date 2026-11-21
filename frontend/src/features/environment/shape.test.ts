import { describe, expect, it } from 'vitest'
import type { CiResult } from '../../api/environment'
import { breakdownMismatch, groupedByRoute, needsVerification, uniqueFactors } from './shape'

const mk = (route: string, heat: string, total: number, parts: Record<string, number>): CiResult => ({
  case_id: 'c', source: 'python_model', method: 'm', system_boundary: 'b', scenario: `${route}/${heat}`, nh3_route: route, heating_option: heat, grid: 'g',
  total_kgCO2e_per_kgH2: total, breakdown_kgCO2e_per_kgH2: parts, transport_distance_km: 5000,
})
describe('environment shaping', () => {
  const rs = [mk('green', 'electric', 3, { upstream_ammonia: 0, transport: 1, electricity: 2, external_heat: 0 }), mk('grey', 'electric', 10, { upstream_ammonia: 9, transport: 1 })]
  it('groups by route with a column per heating option', () => {
    const g = groupedByRoute(rs)
    expect(g.map((x) => x.route)).toEqual(['green NH3', 'blue NH3', 'grey NH3'])
    expect(g[0].electric).toBe(3); expect(g[1].electric).toBeUndefined()
  })
  it('breakdown mismatch detects inconsistent sums', () => { expect(breakdownMismatch(rs)).toBe(0); expect(breakdownMismatch([mk('a', 'b', 5, { transport: 1 })])).toBe(4) })
  it('verification flag from the data file text', () => {
    const f = { name: 'x', value: 1, unit: 'u', provenance: 'literature', source: 'glec2023v3', note: 'Secondary listing; primary PDF not opened' }
    expect(needsVerification(f)).toBe(true)
    expect(needsVerification({ ...f, note: 'fine', source: 'lee2022ammonia' })).toBe(false)
    expect(needsVerification({ ...f, note: 'fine', source: 'ema2025ses p.1' }, ['ema2025ses'])).toBe(true)
  })
  it('unique factors', () => {
    const a = { name: 'f1', value: 1, unit: '', provenance: 'literature', source: 's' }
    expect(uniqueFactors([{ ...rs[0], factors: [a] }, { ...rs[1], factors: [a, { ...a, name: 'f0' }] }]).map((f) => f.name)).toEqual(['f0', 'f1'])
  })
})