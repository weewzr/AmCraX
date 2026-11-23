import { describe, expect, it } from 'vitest'
import { baseName, extent, frac, groupBy, isoCheck, list, pivotXY, safeRepoPath, show, splitFitted, srcOf, truthy, verdictKind } from './shape'

describe('srcOf', () => {
  it('maps the source_type strings of the result files', () => {
    expect(srcOf('aspen')).toBe('aspen_plus_v15')
    expect(srcOf('aspen (duties) + python (economics)')).toBe('aspen_plus_v15')
    expect(srcOf('python')).toBe('python_model')
    expect(srcOf('Literature')).toBe('literature')
    expect(srcOf('assumption')).toBe('assumption')
    expect(srcOf('mixed (per row)')).toBeNull()
    expect(srcOf(undefined)).toBeNull()
  })
})

describe('pivotXY', () => {
  it('merges series on x, sorts, nulls non-finite values and scales', () => {
    const a = [{ x: 2, y: 0.5 }, { x: 1, y: 0.25 }]
    const b = [{ x: 2, y: 3 }, { x: 3, y: null }]
    const out = pivotXY('x', [{ key: 'a', rows: a, y: 'y' }, { key: 'b', rows: b, y: 'y' }], { a: 100 })
    expect(out).toEqual([{ x: 1, a: 25 }, { x: 2, a: 50, b: 3 }, { x: 3, b: null }])
  })
})

describe('fitted-range split and groups', () => {
  it('separates points flagged beyond the fitted range', () => {
    const s = splitFitted([{ within_fitted_range: true }, { within_fitted_range: 'False' }, { within_fitted_range: false }])
    expect(s.inside.length).toBe(1)
    expect(s.beyond.length).toBe(2)
  })
  it('groups in first-seen order', () => {
    expect([...groupBy([{ k: 'b' }, { k: 'a' }, { k: 'b' }], 'k').keys()]).toEqual(['b', 'a'])
  })
  it('reads boolean-like cells', () => {
    expect(truthy('True')).toBe(true)
    expect(truthy(false)).toBe(false)
  })
})

describe('isoCheck', () => {
  it('compares against the limit and reports missing values as not modelled', () => {
    expect(isoCheck(0.05, 0.1)).toBe('pass')
    expect(isoCheck(2.9, 0.1)).toBe('fail')
    expect(isoCheck(0.1, 0.1)).toBe('pass')
    expect(isoCheck(null, 0.1)).toBe('not_modelled')
    expect(isoCheck(1, undefined)).toBe('not_modelled')
  })
})

describe('evidence-matrix helpers', () => {
  it('maps the verdict vocabulary', () => {
    expect(verdictKind('SUPPORTED')).toBe('ok')
    expect(verdictKind('contradicted')).toBe('error')
    expect(verdictKind('INCONCLUSIVE')).toBe('warn')
    expect(verdictKind('maybe')).toBe('neutral')
    expect(verdictKind(undefined)).toBe('neutral')
  })
  it('shows any JSON value as text', () => {
    expect(show(null)).toBe('')
    expect(show(['a', 'b'])).toBe('a; b')
    expect(show({ low: 1, high: 2 })).toBe('low: 1; high: 2')
    expect(show(1.23456789)).toBe('1.2346')
    expect(list('x')).toEqual(['x'])
    expect(list(undefined)).toEqual([])
  })
  it('only links plain repo-relative paths', () => {
    expect(safeRepoPath('results/research/a.csv')).toBe('results/research/a.csv')
    expect(safeRepoPath('results\\research\\a.csv')).toBe('results/research/a.csv')
    expect(safeRepoPath('../secret')).toBeNull()
    expect(safeRepoPath('C:\\Users\\x\\a.csv')).toBeNull()
    expect(safeRepoPath('/etc/passwd')).toBeNull()
    expect(safeRepoPath('https://example.org/a')).toBeNull()
    expect(baseName('results/figures/research/x.png')).toBe('x.png')
  })
})

describe('range helpers', () => {
  it('computes extent and fraction', () => {
    expect(extent([3, null, 1, NaN, 2])).toEqual([1, 3])
    expect(extent([])).toBeNull()
    expect(frac(5, 0, 10)).toBe(0.5)
    expect(frac(5, 5, 5)).toBe(0.5)
    expect(frac(20, 0, 10)).toBe(1)
  })
})
