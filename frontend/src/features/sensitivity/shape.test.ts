import { describe, expect, it } from 'vitest'
import type { DataRow } from '../../api/sensitivity'
import { baseInputsFromRows, buildGrid, checkBounds, datasetSource, defaultYs, inferX, listValues, mergeSeries, parseBool, rangeValues, splitConverged, varyingInputs } from './shape'

const cols = ['case_id', 'reactor_temperature_C', 'reactor_pressure_bar', 'heat_integration', 'nh3_conversion', 'h2_product_kg_h', 'converged', 'source']
const rows: DataRow[] = [
  { case_id: 't1', reactor_temperature_C: 500, reactor_pressure_bar: 20, heat_integration: 'False', nh3_conversion: 0.95, h2_product_kg_h: 240, converged: 'True', source: 'aspen_plus_v15' },
  { case_id: 't2', reactor_temperature_C: 600, reactor_pressure_bar: 20, heat_integration: 'False', nh3_conversion: 0.98, h2_product_kg_h: 251, converged: 'True', source: 'aspen_plus_v15' },
  { case_id: 't3', reactor_temperature_C: 700, reactor_pressure_bar: 20, heat_integration: 'False', nh3_conversion: null, h2_product_kg_h: null, converged: 'False', source: 'aspen_plus_v15' },
]

describe('sensitivity data shaping', () => {
  it('parses string booleans from CSV', () => {
    expect(parseBool('True')).toBe(true); expect(parseBool('false')).toBe(false); expect(parseBool(null)).toBeNull()
  })
  it('excludes and counts non-converged rows', () => {
    const r = splitConverged(rows, cols)
    expect(r.used).toHaveLength(2); expect(r.excluded).toBe(1)
    expect(splitConverged(rows, ['x']).excluded).toBe(0) // no flag column: all rows used
  })
  it('infers x and default y variables', () => {
    const { used } = splitConverged(rows, cols)
    expect(varyingInputs(cols, used)).toEqual(['reactor_temperature_C'])
    expect(inferX('aspen_temperature', cols, used)).toBe('reactor_temperature_C')
    expect(defaultYs(cols, used, 'reactor_temperature_C')).toEqual(['nh3_conversion', 'h2_product_kg_h'])
  })
  it('labels provenance by dataset', () => {
    expect(datasetSource('aspen_x', rows)).toBe('aspen_plus_v15')
    expect(datasetSource('lcoh_tornado', [{ a: 1 }])).toBe('assumption')
    expect(datasetSource('pfr_temperature_sweep', [{ a: 1 }])).toBe('python_model')
  })
  it('derives fixed inputs for a python overlay', () => {
    const b = baseInputsFromRows(rows, cols, 'reactor_temperature_C') as Record<string, unknown>
    expect(b.heat_integration).toBe(false); expect(b.reactor_pressure_bar).toBe(20); expect(b.reactor_temperature_C).toBeUndefined()
  })
  it('merges series on x', () => {
    const m = mergeSeries([{ prefix: 'a', rows }, { prefix: 'p', rows: [{ reactor_temperature_C: 600, nh3_conversion: 0.97 }] }], 'reactor_temperature_C', 'nh3_conversion')
    expect(m.map((o) => o.x)).toEqual([500, 600, 700])
    expect(m[1]).toEqual({ x: 600, 'a|nh3_conversion': 0.98, 'p|nh3_conversion': 0.97 })
  })
  it('builds a grid and hides non-converged values', () => {
    const g = buildGrid(rows, cols, 'reactor_temperature_C', 'reactor_pressure_bar', 'nh3_conversion')
    expect(g.xs).toEqual([500, 600, 700]); expect(g.cell.get('700|20')).toEqual({ v: null, converged: false }); expect(g.max).toBe(0.98)
  })
  it('builds sweep values and checks bounds', () => {
    expect(rangeValues(500, 700, 100).values).toEqual([500, 600, 700])
    expect(rangeValues(0.1, 0.3, 0.1).values).toEqual([0.1, 0.2, 0.3])
    expect(rangeValues(1, 2, 0).error).toBeTruthy(); expect(rangeValues(0, 1000, 1).error).toMatch(/limit/)
    expect(listValues('1, 2;3').values).toEqual([1, 2, 3]); expect(listValues('1, x').error).toBeTruthy()
    expect(checkBounds('reactor_temperature_C', [300, 1100])).toMatch(/above/)
    expect(checkBounds('reactor_pressure_bar', [1, 100])).toBeNull()
  })
})
