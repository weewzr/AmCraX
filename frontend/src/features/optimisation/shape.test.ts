import { describe, expect, it } from 'vitest'
import { atBoundList, flatten, frontSeries, heatmap, normaliseGridRows, normaliseRows, normaliseSingle } from './shape'

const res = { objective: 'min_lcoh', decision_variables: { t: { lower: 1, upper: 2, optimum: 2, at_bound: 'upper' }, p: { lower: 1, upper: 2, optimum: 1.5, at_bound: null } } }
describe('optimisation shaping', () => {
  it('finds results in list, dict or wrapped forms', () => {
    expect(normaliseSingle([res, res]).length).toBe(2)
    expect(normaliseSingle({ min_lcoh: res }).length).toBe(1)
    expect(normaliseSingle({ results: { a: res, b: { ...res, objective: 'x' } } }).length).toBe(2)
    expect(normaliseSingle(null)).toEqual([])
  })
  it('rows under common keys', () => { expect(normaliseRows({ rows: [{ a: 1 }] })).toEqual([{ a: 1 }]); expect(normaliseRows({})).toEqual([]) })
  it('flatten nests with dots', () => { expect(flatten({ a: { b: 1, c: [1, 2] } })).toEqual({ 'a.b': 1, 'a.c': '1; 2' }) })
  it('heatmap aggregates min/max/mean and respects feasibility', () => {
    const rows = normaliseGridRows([
      { x: 1, y: 1, m: 5, feasible: 'True', model_ok: 'True' }, { x: 1, y: 1, m: 3, feasible: 'True', model_ok: 'True' },
      { x: 2, y: 1, m: 1, feasible: 'False', model_ok: 'True' }, { x: 2, y: 1, m: 9, feasible: 'True', model_ok: 'True' },
    ])
    const h = heatmap(rows, 'x', 'y', 'm', 'min', true)
    expect(h.cells.map((c) => c.value)).toEqual([3, 9])
    expect(heatmap(rows, 'x', 'y', 'm', 'min', false).cells[1].value).toBe(1)
    expect(heatmap(rows, 'x', 'y', 'm', 'mean', true).cells[0].value).toBe(4)
    expect(heatmap([], 'x', 'y', 'm', 'min', true).min).toBeNull()
  })
  it('front series split by feasibility', () => {
    const s = frontSeries({ objectives: ['a', 'b'], senses: ['min', 'min'], overlay: '', n_points: 2, points: [{ a: 2, b: 1, feasible: true }, { a: 1, b: 2, feasible: false }], unconstrained_front_infeasible_points: [] })
    expect(s.feas).toEqual([{ x: 2, y: 1 }]); expect(s.infeas).toEqual([{ x: 1, y: 2 }])
  })
  it('at-bound list', () => { expect(atBoundList(res as never)).toEqual(['t (upper)']) })
})