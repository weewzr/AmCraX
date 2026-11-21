import { describe, expect, it } from 'vitest'
import { countAspenRuns, exportDate } from './data'

describe('countAspenRuns', () => {
  it('adds Aspen cases, Aspen sensitivity rows (not native-STEMP re-runs, not Python studies) and the RGibbs grid', () => {
    const cases = [{ source: 'aspen_plus_v15' as const }, { source: 'aspen_plus_v15' as const }, { source: 'python_model' as const }]
    const sens = [
      { name: 'aspen_temperature', rows: 17 }, { name: 'aspen_tp_map', rows: 35 }, { name: 'aspen_native_STEMP_baseline', rows: 10 },
      { name: 'lcoh_vs_ammonia_price_baseline', rows: 41 }, { name: 'pfr_temperature_sweep', rows: 45 },
    ]
    expect(countAspenRuns(cases, sens, 168)).toEqual({ aspenCases: 2, sensitivityRuns: 52, equilibriumPoints: 168, total: 222 })
  })
  it('handles missing row counts', () => {
    expect(countAspenRuns([], [{ name: 'aspen_x' }], 0).total).toBe(0)
  })
})

describe('exportDate', () => {
  it('takes the date part of an ISO timestamp', () => {
    expect(exportDate('2026-11-21T12:52:07+00:00')).toBe('2026-11-21')
    expect(exportDate(undefined)).toBeNull()
    expect(exportDate('garbage')).toBeNull()
  })
})
