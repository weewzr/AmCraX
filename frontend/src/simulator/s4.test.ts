/** Tests of the NUS-H2 pattern additions (gap plan waves 1 and 2): tooltip, diagram values, tour, table view, fixed values, exports. */
import { describe, expect, it } from 'vitest'
import { sweeps } from '../sim'
import { data } from '../sim/testdata'
import { controlBasis } from './Controls'
import { tableRows, type TSeries } from './Graphs'
import { baselineState, exportJSON, exportName, fixedValues, PRESETS, runCase, type SimState } from './model'
import { ITEM_ORDER, tooltipModel } from './Pfd'
import { itemStatus, labelValue, SOURCE_MARK, STREAM_NAMES, streamViews, UNIT_LIMITS, UNITS, unitViews } from './pfdData'
import { TOUR_STEPS } from './tourSteps'

const base = baselineState(data)
const kin: SimState = { ...base, reactor: 'isothermal', preset: null }

describe('diagram tooltip and printed values (C2, C4)', () => {
  for (const s of [base, kin, { ...base, heat_integration: false, preset: null }]) {
    const c = runCase(s, data)
    const units = unitViews(c, data), streams = streamViews(c, data)
    it(`tooltip facts equal the panel facts for every unit and stream (${s.reactor}, hi ${s.heat_integration})`, () => {
      for (const u of UNITS) expect(tooltipModel(u.id, units, streams)!.facts).toEqual(units[u.id].facts)
      for (const id of Object.keys(STREAM_NAMES)) expect(tooltipModel(id, units, streams)!.facts).toEqual(streams[id].facts)
    })
    it('every printed value is a panel fact with its source marker', () => {
      for (const id of Object.keys(STREAM_NAMES)) {
        const lv = labelValue(streams[id].facts, 'kmol/h')
        if (!lv) continue
        expect(streams[id].facts).toContain(lv.fact)
        expect(lv.mark).toBe(SOURCE_MARK[lv.fact.source!])
        expect(lv.text).toMatch(/kmol\/h$/)
      }
      for (const u of UNITS) {
        const lv = labelValue(units[u.id].facts, 'kW')
        if (lv) expect(units[u.id].facts).toContain(lv.fact)
      }
    })
  }
  it('stream compositions by stoichiometry sum to at most 1 and follow the conversion', () => {
    const c = runCase(base, data)
    const s5 = streamViews(c, data).S5.facts.filter((f) => /mole fraction \(stoichiometry\)/.test(f.label))
    expect(s5).toHaveLength(3)
    const sum = s5.reduce((a, f) => a + (f.value ?? 0), 0)
    expect(sum).toBeGreaterThan(0.99)
    expect(sum).toBeLessThanOrEqual(1 + 1e-12)
    const X = c.out.process!.conversion.value
    const h2 = s5.find((f) => f.label.startsWith('H2'))!.value!, nh3 = s5.find((f) => f.label.startsWith('NH3'))!.value!
    expect(h2 / nh3).toBeCloseTo((1.5 * X) / (1 - X), 8)
  })
  it('membrane mode: tail-gas values are not modelled', () => {
    const c = runCase({ ...base, purification: 'membrane', preset: null }, data)
    const t = streamViews(c, data).TAILGAS.facts
    expect(t.every((f) => f.value === null)).toBe(true)
  })
  it('every unit has a stated limitation (C5)', () => {
    for (const u of UNITS) expect(UNIT_LIMITS[u.id]?.length ?? 0).toBeGreaterThan(20)
  })
  it('keyboard order reaches every unit and every stream once', () => {
    expect(new Set(ITEM_ORDER).size).toBe(ITEM_ORDER.length)
    expect(ITEM_ORDER).toEqual([...UNITS.map((u) => u.id), ...Object.keys(STREAM_NAMES)])
  })
  it('list view status: FEHE bypassed and S3 absent without heat recovery', () => {
    const c = runCase({ ...base, heat_integration: false, preset: null }, data)
    const u = unitViews(c, data), s = streamViews(c, data)
    expect(itemStatus('FEHE', c, u, s)).toMatch(/bypassed/)
    expect(itemStatus('S3', c, u, s)).toMatch(/not present/)
  })
})

describe('guided tour (C3)', () => {
  const c = runCase(base, data)
  it('has seven steps, every unit and focus id exists, every row key resolves', () => {
    expect(TOUR_STEPS).toHaveLength(7)
    const ids = new Set([...UNITS.map((u) => u.id), ...Object.keys(STREAM_NAMES)])
    for (const st of TOUR_STEPS) {
      expect(ids.has(st.unit)).toBe(true)
      for (const f of st.focus) expect(ids.has(f)).toBe(true)
      for (const k of st.rows) expect(c.rows.some((r) => r.key === k)).toBe(true)
      expect(st.text).not.toMatch(/minute|second/i)
    }
  })
})

describe('graph table view (C1)', () => {
  it('table rows equal the plotted series of graph 1 (conversion against temperature)', () => {
    const g = sweeps.conversionVsTemperature(data, { ...runCase(kin, data).out.inputs, n_points: 2 }, 300, 800, 11)
    const series: TSeries[] = [{ name: 'k', xLabel: 'T', yLabel: '%', pts: g.kinetic.map((p) => ({ x: p.x, y: p.y === null ? null : p.y * 100, source: p.source })) }]
    const rows = tableRows(series)
    const plotted = g.kinetic.filter((p) => p.y !== null)
    expect(rows).toHaveLength(plotted.length)
    rows.forEach((r, i) => { expect(r.x).toBe(plotted[i].x); expect(r.y).toBe(plotted[i].y! * 100); expect(r.source).toBe(plotted[i].source) })
  })
  it('table rows equal the plotted series of graph 3 (conversion along the reactor)', () => {
    const prof = sweeps.axialProfiles(runCase(kin, data).out)
    const rows = tableRows([{ name: 'b', xLabel: 'z', yLabel: '%', pts: prof.conversion_vs_length.map((p) => ({ x: p.x, y: p.y === null ? null : p.y * 100, source: p.source })) }])
    const plotted = prof.conversion_vs_length.filter((p) => p.y !== null)
    expect(rows.map((r) => r.y)).toEqual(plotted.map((p) => p.y! * 100))
  })
})

describe('presets, fixed values, control basis and exports (C7, C8, C9, C12)', () => {
  it('every preset has a one-sentence description', () => {
    for (const p of PRESETS) { expect(p.about.length).toBeGreaterThan(30); expect(p.about).not.toMatch(/—/) }
  })
  it('fixed values equal the exported Python defaults', () => {
    const def = data.model.process.inputs_defaults
    const f = fixedValues(data)
    expect(f.length).toBeGreaterThanOrEqual(5)
    for (const x of f) expect(x.value).toBe(def[x.key])
  })
  it('control basis chips come from the rate-law and grid metadata', () => {
    const v = data.model.kinetics.laws[kin.catalyst_id].validity
    expect(controlBasis(data, kin, 'T_C')).toContain(`${(v.T_min_K - 273.15).toFixed(0)}-${(v.T_max_K - 273.15).toFixed(0)} degC`)
    const g = data.model.process.grid
    expect(controlBasis(data, base, 'P_bar')).toContain(`${g.P_bar[0]}-${g.P_bar[g.P_bar.length - 1]} bar`)
    expect(controlBasis(data, base, 'psa_h2_recovery')).toBe('Assumed')
  })
  it('export names carry the case and a UTC stamp', () => {
    expect(exportName('baseline', '2026-11-23T11:52:07.123Z', 'csv')).toBe('amcrax_sim_baseline_20261123T1152.csv')
    expect(exportName(null, '2026-11-23T11:52:07.123Z', 'json')).toBe('amcrax_sim_custom_20261123T1152.json')
  })
  it('JSON export adds fixed values and keeps the old keys', () => {
    const j = JSON.parse(exportJSON([{ name: 'current', result: runCase(base, data) }], data, 'x'))
    for (const k of ['tool', 'generated_utc', 'note', 'source_labels', 'fx', 'economics_basis', 'economics_note', 'catalyst_prices', 'cases']) expect(j).toHaveProperty(k)
    expect(j.fixed_values.length).toBe(fixedValues(data).length)
    expect(j.fixed_values.every((f: { source: string }) => f.source === 'assumption')).toBe(true)
    expect(Array.isArray(j.controls_not_offered)).toBe(true)
  })
})
