import { describe, expect, it } from 'vitest'
import type { SimulationResult } from '../../api/types'
import { compositeRows, dutyBreakdown, gccRows, hiComparison } from './shape'

describe('heat shaping', () => {
  it('merges composite curves by heat and sorts; missing points stay null', () => {
    const rows = compositeRows([0, 10, 20], [100, 80, 60], [5, 20], [30, 50])
    expect(rows.map((r) => r.H)).toEqual([0, 5, 10, 20])
    expect(rows[1]).toEqual({ H: 5, hot: null, cold: 30 })
    expect(rows[3]).toEqual({ H: 20, hot: 60, cold: 50 })
  })
  it('keeps GCC order and drops non-finite points', () => {
    expect(gccRows([1, 2, NaN], [10, 20, 30])).toEqual([{ H: 1, T: 10 }, { H: 2, T: 20 }])
  })
  const mk = (id: string, ext: number | null): SimulationResult => ({
    case_id: id, source: 'aspen_plus_v15',
    blocks: { VAPORIZR: { duty_kW: 700 }, CRACKER: { duty_kW: 1500 } },
    kpis: { total_external_heating_kW: ext, recovered_heat_kW: 600, cooling_duty_kW: null, specific_heat_demand_kWh_per_kgH2: 9, lhv_efficiency: 0.7, h2_product_kg_h: 250, nh3_conversion: 0.99 },
  } as unknown as SimulationResult)
  it('lists only blocks that exist in the case', () => {
    expect(dutyBreakdown(mk('x', 1)).map((r) => r.id)).toEqual(['VAPORIZR', 'CRACKER'])
  })
  it('compares two cases without inventing values (null stays null)', () => {
    const rows = hiComparison(mk('a', 2000), mk('b', null))
    expect(rows[0]).toMatchObject({ withHi: 2000, without: null })
    expect(rows[2]).toMatchObject({ withHi: null, without: null })
  })
})
