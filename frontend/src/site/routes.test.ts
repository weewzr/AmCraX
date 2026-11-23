import { describe, expect, it } from 'vitest'
import { anchorId, HYPOTHESIS_PAGES, hypothesisPath, isPlatformPath, NAV_MORE, NAV_PRIMARY, navActive, platformPath, SITE_ROUTES, titleFor } from './routes'

describe('platform routing helpers', () => {
  it('builds platform paths under /platform', () => {
    expect(platformPath('/')).toBe('/platform')
    expect(platformPath('')).toBe('/platform')
    expect(platformPath('/pfd')).toBe('/platform/pfd')
    expect(platformPath('simulation')).toBe('/platform/simulation')
  })
  it('recognises platform locations', () => {
    expect(isPlatformPath('/platform')).toBe(true)
    expect(isPlatformPath('/platform/heat')).toBe(true)
    expect(isPlatformPath('/platformer')).toBe(false)
    expect(isPlatformPath('/pfd')).toBe(false)
    expect(isPlatformPath('/')).toBe(false)
  })
})

describe('site route table', () => {
  it('covers the eleven pages once each, in order, with unique paths; the simulator is the landing page', () => {
    expect(SITE_ROUTES.map((r) => r.section)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    expect(new Set(SITE_ROUTES.map((r) => r.path)).size).toBe(11)
    expect(SITE_ROUTES[0]).toMatchObject({ path: '/', label: 'Simulator' })
    expect(SITE_ROUTES.find((r) => r.label === 'Overview')?.path).toBe('/overview')
    for (const p of ['/why', '/pfd', '/methodology', '/results', '/architecture', '/research', '/docs', '/about', '/hypotheses']) expect(SITE_ROUTES.some((r) => r.path === p), p).toBe(true)
  })
  it('gives each page a title', () => {
    expect(titleFor('/results')).toBe('Engineering results - AmCraX')
    expect(titleFor('/')).toMatch(/^AmCraX - .*simulator/)
    expect(titleFor('/overview')).toBe('Overview - AmCraX')
    expect(titleFor('/platform/pfd')).toBe('AmCraX platform')
  })
  it('navigation: eleven primary items on existing routes, the other pages under "More"', () => {
    expect(NAV_PRIMARY.map((n) => n.label)).toEqual(['Simulator', 'Hypotheses', 'Catalysts', 'Singapore Economics', 'Purification', 'End Use', 'Environmental Analysis',
      'Validation', 'Aspen Evidence', 'Technical Report', 'Documentation'])
    const known = new Set([...SITE_ROUTES.map((r) => r.path), ...HYPOTHESIS_PAGES.map((p) => hypothesisPath(p.slug))])
    for (const n of [...NAV_PRIMARY, ...NAV_MORE]) expect(known.has(n.to.split('#')[0]), n.to).toBe(true)
    expect(NAV_PRIMARY.find((n) => n.label === 'Environmental Analysis')?.to).toBe('/hypotheses/end-use#lca')
    expect(NAV_MORE.map((n) => n.to)).toEqual(['/overview', '/why', '/pfd', '/methodology', '/results', '/architecture', '/research', '/about'])
    expect(navActive(NAV_PRIMARY[0], '/')).toBe(true)
    expect(navActive(NAV_PRIMARY[1], '/hypotheses/catalyst')).toBe(false)
    expect(navActive(NAV_PRIMARY[5], '/hypotheses/end-use', '#lca')).toBe(false)
  })
  it('titles the hypothesis sub-pages', () => {
    expect(hypothesisPath('')).toBe('/hypotheses')
    expect(hypothesisPath('catalyst')).toBe('/hypotheses/catalyst')
    expect(titleFor('/hypotheses/catalyst')).toBe('Catalyst comparison and heat integration - AmCraX')
    expect(titleFor('/hypotheses')).toBe('Hypothesis testing - AmCraX')
    expect(new Set(HYPOTHESIS_PAGES.map((p) => p.slug)).size).toBe(HYPOTHESIS_PAGES.length)
  })
  it('decodes anchors', () => {
    expect(anchorId('#lcoh')).toBe('lcoh')
    expect(anchorId('')).toBeNull()
    expect(anchorId('#a%20b')).toBe('a b')
  })
})
