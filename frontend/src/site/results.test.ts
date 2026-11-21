import { describe, expect, it } from 'vitest'
import { atBoundCount, breakdownRows, ciRows, freeOptimisations, mergeSeries, pivotTP, type OptResult } from './results'

describe('pivotTP', () => {
  it('pivots a T-P sweep into one column per pressure, conversion in percent', () => {
    const { data, pressures } = pivotTP([
      { reactor_temperature_C: 500, reactor_pressure_bar: 5, nh3_conversion: 0.98 },
      { reactor_temperature_C: 450, reactor_pressure_bar: 5, nh3_conversion: 0.9 },
      { reactor_temperature_C: 500, reactor_pressure_bar: 20, nh3_conversion: 0.95 },
      { reactor_temperature_C: 500, reactor_pressure_bar: 40, nh3_conversion: null },
    ])
    expect(pressures).toEqual([5, 20, 40])
    expect(data.map((r) => r.T)).toEqual([450, 500])
    expect(data[1]).toEqual({ T: 500, p5: 98, p20: 95 })
  })
})

describe('mergeSeries', () => {
  it('keeps gaps as missing keys and sorts by x', () => {
    const rows = mergeSeries('T', [
      { key: 'a', points: [{ x: 2, y: 1 }, { x: 1, y: 3 }] },
      { key: 'b', points: [{ x: 2, y: 5 }, { x: 3, y: null }] },
    ])
    expect(rows).toEqual([{ T: 1, a: 3 }, { T: 2, a: 1, b: 5 }])
  })
})

describe('breakdownRows / ciRows', () => {
  it('labels cost items and drops non-finite values', () => {
    expect(breakdownRows({ ammonia_feed: 3, capex: 0.4, odd: Number.NaN })).toEqual([
      { name: 'Ammonia feed', value: 3 }, { name: 'Capital charge', value: 0.4 },
    ])
    expect(breakdownRows(undefined)).toEqual([])
  })
  it('builds stacked carbon-intensity rows with zero for absent parts', () => {
    const r = ciRows([{ nh3_route: 'green', heating_option: 'self_firing', heating_label: 'self-firing', total_kgCO2e_per_kgH2: 0.41, breakdown_kgCO2e_per_kgH2: { transport: 0.37, external_heat: 0.03 } }])
    expect(r[0]).toMatchObject({ name: 'green NH3, self-firing', total: 0.41, transport: 0.37, upstream_ammonia: 0, electricity: 0 })
  })
})

describe('optimisation helpers', () => {
  const dv = { lower: 0, upper: 1, optimum: 1, at_bound: null, unit: '-' }
  const rs: OptResult[] = [
    { id: 'a', label: 'A', metric: 'm', sense: 'min', feasible: true, variant: 'all four decision variables free', decision_variables: { x: dv }, bound_active: ['x=upper'] },
    { id: 'a_TP', label: 'A', metric: 'm', sense: 'min', feasible: true, variant: 'T and P only', decision_variables: { x: dv }, bound_active: [] },
    { id: 'b', label: 'B', metric: 'm', sense: 'min', feasible: true, variant: 'all four decision variables free', decision_variables: { x: dv }, bound_active: [] },
  ]
  it('selects the free-variable runs and counts those at a bound', () => {
    expect(freeOptimisations(rs).map((r) => r.id)).toEqual(['a', 'b'])
    expect(atBoundCount(freeOptimisations(rs))).toBe(1)
  })
})
