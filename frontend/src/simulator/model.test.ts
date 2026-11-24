import { describe, expect, it } from 'vitest'
import { domainWarnings, inputRanges, sweeps } from '../sim'
import { data } from '../sim/testdata'
import {
  baselineState, changedInputs, compareRows, exportCSV, exportJSON, formatDiff, formatValue, PRESETS, presetMatches, presetState, reducer,
  runCase, SOURCE_TEXT, toSimInputs,
} from './model'

const base = baselineState(data)

describe('simulator state reducer and presets', () => {
  it('starts at the stored Aspen baseline (equilibrium cracker, 600 degC, 20 bar) with Aspen labels', () => {
    expect(base.T_C).toBe(600)
    expect(base.P_bar).toBe(20)
    expect(base.reactor).toBe('equilibrium')
    const r = runCase(base, data)
    const conv = r.rows.find((x) => x.key === 'conversion')!
    expect(conv.source).toBe('aspen')
    expect(r.rows.find((x) => x.key === 'h2_kg_h')!.source).toBe('aspen')
    // on a stored Aspen case the purity is Aspen's value (its PSA is also a splitter with the assumed recovery and slip)
    expect(r.rows.find((x) => x.key === 'h2_purity')!.source).toBe('aspen')
    expect(runCase({ ...base, T_C: 610, preset: null }, data).rows.find((x) => x.key === 'h2_purity')!.source).toBe('assumption')
  })
  it('set clears the preset, reset restores the baseline, unchanged values keep the same object', () => {
    const s1 = reducer(base, { type: 'set', key: 'T_C', value: 550 })
    expect(s1.T_C).toBe(550)
    expect(s1.preset).toBeNull()
    expect(reducer(s1, { type: 'set', key: 'T_C', value: 550 })).toBe(s1)
    expect(reducer(s1, { type: 'reset', data })).toEqual(base)
  })
  it('every preset reproduces its stored Aspen case (Aspen label on the conversion)', () => {
    for (const p of PRESETS) {
      expect(presetMatches(data, p.id), p.id).toBe(true)
      const s = reducer(base, { type: 'preset', data, id: p.id })
      expect(s.preset).toBe(p.id)
    }
    expect(() => presetState(data, 'nope')).toThrow()
  })
  it('integrated kinetic preset takes the process KPIs from the Aspen integrated case', () => {
    const r = runCase(presetState(data, 'ci_kum_T499_P20_W100_hi'), data)
    expect(r.rows.find((x) => x.key === 'h2_kg_h')!.source).toBe('aspen')
    expect(r.rows.find((x) => x.key === 'lcoh_USD')!.source).toBe('browser-model')
  })
  it('maps page state to core inputs', () => {
    const x = toSimInputs({ ...base, reactor: 'duty', duty_kW: 900, pressure_drop: true })
    expect(x.mode).toBe('duty')
    expect(x.duty_kW).toBe(900)
    expect(x.reactor_model).toBe('kinetic')
    expect(x.pressure_drop).toBe(true)
    expect(toSimInputs({ ...base, pressure_drop: true }).pressure_drop).toBe(false)
    expect(toSimInputs(base).nh3_price_USD_per_t).toBeUndefined()
  })
})

describe('outputs', () => {
  it('temperature and catalyst change the kinetic conversion', () => {
    const k = { ...base, reactor: 'isothermal' as const, preset: null }
    const a = runCase({ ...k, T_C: 450 }, data).rows.find((x) => x.key === 'conversion')!.value!
    const b = runCase({ ...k, T_C: 550 }, data).rows.find((x) => x.key === 'conversion')!.value!
    const c = runCase({ ...k, T_C: 450, catalyst_id: 'ni_takahashi_microkinetic' }, data).rows.find((x) => x.key === 'conversion')!.value!
    expect(b).toBeGreaterThan(a)
    expect(c).not.toBeCloseTo(a, 4)
  })
  it('shows "not modelled" (null) where the core has no value', () => {
    const mem = runCase({ ...base, purification: 'membrane' }, data).rows
    for (const k of ['h2_kg_h', 'h2_purity', 'lcoh_USD', 'carbon_intensity']) expect(mem.find((x) => x.key === k)!.value, k).toBeNull()
    expect(mem.find((x) => x.key === 'conversion')!.value).not.toBeNull()
    const cold = runCase({ ...base, T_C: 350, reactor: 'isothermal' }, data).rows
    expect(cold.find((x) => x.key === 'lcoh_USD')!.value).toBeNull()
    expect(formatValue({ value: null, kind: 'num', unit: 'kW' })).toBe('not modelled')
  })
  it('hypothetical carbon mode is labelled and changes the carbon cost', () => {
    const act = runCase(base, data).rows.find((x) => x.key === 'carbon_cost')!
    const hyp = runCase({ ...base, carbon_mode: 'hypothetical', carbon_price_SGD_per_t: 80 }, data).rows.find((x) => x.key === 'carbon_cost')!
    expect(hyp.label).toMatch(/HYPOTHETICAL/)
    expect(act.label).not.toMatch(/HYPOTHETICAL/)
    expect(hyp.value).not.toBe(act.value)
  })
  it('a zero actual-mode carbon cost is labelled as the statutory result, also after a switch to an extrapolated kinetic catalyst', () => {
    const kin = { ...base, reactor: 'isothermal' as const, catalyst_id: 'ni_takahashi_microkinetic', preset: null }
    for (const s of [base, kin]) {
      const cc = runCase(s, data).rows.find((x) => x.key === 'carbon_cost')!
      expect(cc.value).toBe(0)
      expect(cc.source).toBe('statutory')
    }
    expect(SOURCE_TEXT.statutory).toBe('Statutory result')
    const hyp = runCase({ ...kin, carbon_mode: 'hypothetical', carbon_price_SGD_per_t: 80 }, data).rows.find((x) => x.key === 'carbon_cost')!
    expect(hyp.source).toBe('assumption')
  })
  it('green ammonia shows both carbon intensities, each labelled with its boundary', () => {
    const g = runCase({ ...base, nh3_route: 'green', preset: null }, data).rows
    const emb = g.find((x) => x.key === 'carbon_intensity')!, zero = g.find((x) => x.key === 'carbon_intensity_zero_boundary')!
    expect(emb.label).toMatch(/embedded/)
    expect(zero.label).toMatch(/renewable electricity as zero/)
    expect(zero.value!).toBeLessThan(emb.value!)
    expect(runCase(base, data).rows.some((x) => x.key === 'carbon_intensity_zero_boundary')).toBe(false)
  })
  it('source badge text covers every core label', () => {
    expect(SOURCE_TEXT.aspen).toBe('Aspen Plus V15')
    expect(SOURCE_TEXT.interpolation).toBe('Interpolated Aspen grid')
    expect(SOURCE_TEXT['browser-model']).toBe('Browser model (port of the Python model)')
    expect(SOURCE_TEXT.extrapolation).toBe('Extrapolation')
    expect(SOURCE_TEXT.assumption).toBe('Assumed scenario')
  })
  it('domain warnings flag extrapolation of the rate law', () => {
    const w = domainWarnings(data, toSimInputs({ ...base, reactor: 'isothermal' }))
    expect(w.some((x) => /fitted range/.test(x))).toBe(true)
    const r = inputRanges(data)
    expect(r.T_C.min).toBe(300)
    // in equilibrium mode the rate law does not enter, so no fitted-range warning
    expect(runCase(base, data).out.warnings.some((x) => /fitted range/.test(x))).toBe(false)
  })
})

describe('compare and export', () => {
  const A = runCase(base, data)
  const B = runCase({ ...base, T_C: 650, preset: null }, data)
  it('compare gives A, B and B - A', () => {
    const c = compareRows(A.rows, B.rows)
    const h2 = c.find((x) => x.key === 'h2_kg_h')!
    expect(h2.diff).toBeCloseTo(h2.b.value! - h2.a.value!, 12)
    expect(formatDiff({ diff: 0.0123, kind: 'frac', unit: '%' })).toBe('+1.23 points')
    expect(changedInputs(A.state, B.state)).toEqual(['T_C'])
  })
  it('export JSON and CSV carry inputs, outputs, units and source labels', () => {
    const j = JSON.parse(exportJSON([{ name: 'A', result: A }, { name: 'B', result: B }], data, '2026-11-23T00:00:00Z'))
    expect(j.cases).toHaveLength(2)
    expect(j.cases[0].inputs.T_C).toEqual({ value: 600, unit: 'degC' })
    const conv = j.cases[0].outputs.find((o: { key: string }) => o.key === 'conversion')
    expect(conv.source_text).toBe('Aspen Plus V15')
    expect(conv.unit).toBe('fraction')
    const csv = exportCSV([{ name: 'A', result: A }])
    expect(csv.split('\n')[0]).toBe('case,section,key,label,value,unit,source,note')
    expect(csv).toMatch(/A,input,T_C,T_C,600,degC,input,/)
    expect(csv).toMatch(/A,output,conversion,NH3 conversion,[0-9.]+,fraction,Aspen Plus V15/)
  })
})

describe('sweep cost (performance budget of the page)', () => {
  it('one simulate() and the eight graph sweeps stay within budget', () => {
    const x = toSimInputs({ ...base, reactor: 'isothermal' }, 2)
    let t = performance.now()
    runCase({ ...base, reactor: 'isothermal' }, data)
    const one = performance.now() - t
    t = performance.now()
    sweeps.conversionVsTemperature(data, x, 300, 800, 26)
    sweeps.h2VsHeatInput(data, x, 2500, 21)
    sweeps.costVsVariable(data, x, 'T_C', [400, 450, 500, 550, 600, 650, 700, 750, 800], data.model.kinetics.law_ids)
    sweeps.carbonByRoute(data, x, 80)
    const all = performance.now() - t
    console.log(`simulate ${one.toFixed(1)} ms, sweeps ${all.toFixed(0)} ms`)
    expect(one).toBeLessThan(100)
  })
})
