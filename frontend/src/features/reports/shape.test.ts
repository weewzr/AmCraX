import { describe, expect, it } from 'vitest'
import { captionOf, doiLink, fmtBytes, groupFigures, groupReports } from './shape'

describe('reports shaping', () => {
  it('caption from file name', () => { expect(captionOf('lcoh_vs_ammonia_price_baseline.png')).toBe('Vs ammonia price baseline'); expect(captionOf('zzz_foo.png')).toBe('Zzz foo') })
  it('groups by prefix in the fixed order and keeps unknown ones under Other', () => {
    const g = groupFigures([{ name: 'ci_a.png', url: '/f/ci_a.png' }, { name: 'aspen_b.png', url: '/f/b' }, { name: 'aspen_a.png', url: '/f/a' }, { name: 'misc.png', url: '/f/m' }])
    expect(g.map((x) => x.prefix)).toEqual(['aspen_', 'ci_', ''])
    expect(g[0].items.map((i) => i.name)).toEqual(['aspen_a.png', 'aspen_b.png'])
  })
  it('groups reports by kind', () => {
    const r = (kind: string) => ({ key: kind, title: kind, kind, file: 'f', path: 'p', bytes: 1, modified_utc: null, url: '/x' })
    expect(groupReports([r('report'), r('deck'), r('report')]).map((x) => [x.kind, x.items.length])).toEqual([['report', 2], ['deck', 1]])
  })
  it('bytes and doi', () => {
    expect(fmtBytes(3427926)).toBe('3.3 MB'); expect(fmtBytes(null)).toBe('n/a')
    expect(doiLink('10.1/x', null)).toBe('https://doi.org/10.1/x'); expect(doiLink(null, 'https://x.org')).toBeNull()
  })
})