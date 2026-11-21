import { describe, expect, it } from 'vitest'
import { changedKeys, defaultValues, toInputs, validate } from './inputs'
import { mixedEngines, parseOverlay, shapeCompare } from './kpis'
import type { CompareResponse } from '../../api/simulation'

describe('operating-conditions form', () => {
  it('baseline defaults are valid and unchanged', () => {
    const v = defaultValues()
    expect(validate(v, 'my_case', 'python')).toEqual({})
    expect(changedKeys(v)).toEqual([])
  })
  it('flags out-of-range and non-numeric values', () => {
    const v = { ...defaultValues(), reactor_temperature_C: '1200', psa_h2_recovery: '0', feed_h2o_mole_frac: '0.2', burner_excess_air: 'abc' }
    const e = validate(v, 'x', 'python')
    expect(Object.keys(e).sort()).toEqual(['burner_excess_air', 'feed_h2o_mole_frac', 'psa_h2_recovery', 'reactor_temperature_C'])
  })
  it('accepts the inclusive bounds and rejects exclusive ones', () => {
    const v = { ...defaultValues(), reactor_temperature_C: '250', psa_h2_recovery: '1', reactor_pressure_bar: '100' }
    expect(validate(v, 'x', 'python')).toEqual({})
  })
  it('requires 3 bar for the Aspen engine only', () => {
    const v = { ...defaultValues(), reactor_pressure_bar: '2' }
    expect(validate(v, 'x', 'python').reactor_pressure_bar).toBeUndefined()
    expect(validate(v, 'x', 'aspen').reactor_pressure_bar).toMatch(/3 bar/)
  })
  it('validates the case name', () => {
    expect(validate(defaultValues(), 'bad name!', 'python').case_id).toBeDefined()
    expect(validate(defaultValues(), '', 'python').case_id).toBeDefined()
  })
  it('counts changed fields and builds the payload', () => {
    const v = { ...defaultValues(), reactor_temperature_C: '650', heat_integration: false }
    expect(changedKeys(v)).toEqual(['reactor_temperature_C', 'heat_integration'])
    const i = toInputs(v, ' c1 ')
    expect(i.case_id).toBe('c1'); expect(i.reactor_temperature_C).toBe(650); expect(i.heat_integration).toBe(false)
  })
})

const resp: CompareResponse = {
  cases: [{ case_id: 'a', source: 'aspen_plus_v15', converged: true }, { case_id: 'b', source: 'python_model', converged: true }],
  reference_case: 'a', columns: [], changed_inputs: [],
  table: [{ kpi: 'nh3_conversion', a: 0.98, delta_a: 0, delta_rel_a: 0, b: 0.99, delta_b: 0.01, delta_rel_b: 0.0102 }],
}
describe('comparison shaping', () => {
  it('shapes table rows per case and detects mixed engines', () => {
    const r = shapeCompare(resp)
    expect(r[0].label).toBe('NH3 conversion')
    expect(r[0].cells.b).toEqual({ v: 0.99, d: 0.01, rel: 0.0102 })
    expect(mixedEngines(resp)).toBe(true)
  })
  it('parses an overlay table defensively', () => {
    expect(parseOverlay(null)).toBeNull()
    expect(parseOverlay({ x: 1 })).toBeNull()
    const t = parseOverlay({ rows: [{ id: 'a', lcoh: 3.2 }], assumptions: ['gas price'] })
    expect(t?.columns).toEqual(['id', 'lcoh']); expect(t?.notes).toEqual(['gas price'])
  })
})
