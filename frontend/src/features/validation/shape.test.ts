import { describe, expect, it } from 'vitest'
import { normaliseMatrix } from '../../api/validation'
import { countByStatus, crossCheckRows, deviationSummary, filterItems, notValidated, parityData } from './shape'

const matrix = normaliseMatrix({
  items: [
    { id: 'V1', model_component: 'thermo', status: 'pass', actual_result: 'ok', limitations: '' },
    { id: 'V2', model_component: 'kinetics', status: 'not_run', limitations: 'no data' },
    { id: 'V3', model_component: 'thermo', status: 'weird', limitations: 'only 3 species', evidence_files: 'a.csv' },
    { id: 'V4', model_component: 'heat', status: 'fail', actual_result: '3 % off' },
  ],
})

describe('validation matrix shaping', () => {
  it('never turns an unknown status into pass', () => {
    expect(matrix.find((m) => m.id === 'V3')?.status).toBe('not_run')
    expect(matrix.find((m) => m.id === 'V3')?.evidence_files).toEqual(['a.csv'])
  })
  it('accepts a bare array and rejects junk', () => {
    expect(normaliseMatrix([{ id: 'x', status: 'pass' }])).toHaveLength(1)
    expect(normaliseMatrix('nope')).toEqual([])
  })
  it('counts, filters and lists open items', () => {
    expect(countByStatus(matrix)).toEqual({ pass: 1, fail: 1, not_run: 2, informational: 0 })
    expect(filterItems(matrix, 'all', 'thermo', '').map((m) => m.id)).toEqual(['V1', 'V3'])
    expect(filterItems(matrix, 'fail', 'all', '').map((m) => m.id)).toEqual(['V4'])
    expect(filterItems(matrix, 'all', 'all', 'no data').map((m) => m.id)).toEqual(['V2'])
    expect(notValidated(matrix).map((x) => x.item.id)).toEqual(['V2', 'V3', 'V4'])
  })
})

describe('comparison shaping', () => {
  const rows = [
    { T_C: 250, P_bar: 1, aspen_property_method: 'IDEAL', python_eos: 'ideal', nh3_conversion_aspen: 0.9, nh3_conversion_python: 0.89, nh3_conversion_abs_dev: -0.01 },
    { T_C: 300, P_bar: 1, aspen_property_method: 'IDEAL', python_eos: 'ideal', nh3_conversion_aspen: 0.95, nh3_conversion_python: 0.96, nh3_conversion_abs_dev: 0.02 },
  ]
  it('groups parity points and summarises deviation', () => {
    const p = parityData(rows, 'nh3_conversion')
    expect(p.combos).toEqual(['IDEAL|ideal'])
    expect(p.byCombo['IDEAL|ideal']).toHaveLength(2)
    const s = deviationSummary(rows, 'nh3_conversion')[0]
    expect(s.maxAbs).toBeCloseTo(0.02)
    expect(s.maxAbsAt).toBe('300 degC / 1 bar')
    expect(s.meanAbs).toBeCloseTo(0.015)
  })
  it('converts cross-check rows to numbers or null', () => {
    expect(crossCheckRows([{ quantity: 'q', a: '1', b: '', abs_diff: 0, rel_diff: null }])[0]).toEqual({ quantity: 'q', a: 1, b: null, abs_diff: 0, rel_diff: null })
  })
})
