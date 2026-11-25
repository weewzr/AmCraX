import { describe, expect, it } from 'vitest'
import { activeGroup, anchorId, eyebrowFor, HYPOTHESIS_PAGES, hypothesisPath, isPlatformPath, locate, NAV_GROUPS, pageActive, platformPath, REDIRECTS, sectionOf, SITE_ROUTES, titleFor } from './routes'

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

/** Every public route of App.tsx (the eleven pages and the hypothesis sub-pages). */
const ALL_PUBLIC = ['/', '/overview', '/why', '/pfd', '/methodology', '/results', '/architecture', '/research', '/docs', '/about', ...HYPOTHESIS_PAGES.map((p) => hypothesisPath(p.slug))]

describe('site route table', () => {
  it('five labelled top-level groups', () => {
    expect(NAV_GROUPS.map((g) => g.label)).toEqual(['Simulator', 'Findings', 'Results', 'Methods and validation', 'Docs and downloads'])
    expect(new Set(NAV_GROUPS.map((g) => g.id)).size).toBe(5)
  })
  it('every public route appears exactly once as a page; the simulator is the landing page', () => {
    const pages = SITE_ROUTES.map((r) => r.path)
    expect(new Set(pages).size).toBe(pages.length)
    expect([...pages].sort()).toEqual([...ALL_PUBLIC].sort())
    expect(SITE_ROUTES[0]).toMatchObject({ path: '/', title: 'Process simulator' })
    // anchor shortcuts point into existing pages
    for (const g of NAV_GROUPS) for (const p of g.pages) expect(ALL_PUBLIC.includes(p.to.split('#')[0]), p.to).toBe(true)
  })
  it('derives section numbers from the table, so they cannot go stale', () => {
    expect(sectionOf('/')).toBe('1.1')
    expect(sectionOf('/pfd')).toBe('1.2')
    expect(sectionOf('/hypotheses')).toBe('2.1')
    expect(sectionOf('/hypotheses/end-use')).toBe('2.5')
    expect(sectionOf('/results')).toBe('3.2')
    expect(sectionOf('/about')).toBe('5.2')
    expect(sectionOf('/nowhere')).toBeNull()
    // numbers follow the order of the table: group index + position among the numbered pages
    for (const [gi, g] of NAV_GROUPS.entries()) {
      const numbered = g.pages.filter((p) => !p.to.includes('#'))
      numbered.forEach((p, i) => expect(sectionOf(p.to)).toBe(`${gi + 1}.${i + 1}`))
    }
    for (const r of SITE_ROUTES) expect(r.section).toBe(sectionOf(r.path))
    expect(eyebrowFor('/results')).toBe('Section 3.2 · Results')
    expect(eyebrowFor('/missing')).toBeNull()
  })
  it('gives each page a title', () => {
    expect(titleFor('/results')).toBe('Engineering results - AmCraX')
    expect(titleFor('/')).toMatch(/^AmCraX - .*simulator/)
    expect(titleFor('/overview')).toBe('Overview - AmCraX')
    expect(titleFor('/platform/pfd')).toBe('AmCraX platform')
    for (const p of ALL_PUBLIC) expect(titleFor(p), p).not.toMatch(/optimisation platform$/)
  })
  it('active state: the group of the page; an anchor entry only on its anchor', () => {
    expect(activeGroup('/')).toBe('simulator')
    expect(activeGroup('/hypotheses/catalyst')).toBe('findings')
    expect(activeGroup('/hypotheses/validation')).toBe('methods')
    expect(activeGroup('/platform')).toBeNull()
    const findings = NAV_GROUPS[1].pages
    const endUse = findings.find((p) => p.to === '/hypotheses/end-use')!
    const lca = findings.find((p) => p.to === '/hypotheses/end-use#lca')!
    expect(pageActive(endUse, '/hypotheses/end-use')).toBe(true)
    expect(pageActive(endUse, '/hypotheses/end-use', '#lca')).toBe(false)
    expect(pageActive(lca, '/hypotheses/end-use', '#lca')).toBe(true)
    expect(pageActive(lca, '/hypotheses/end-use')).toBe(false)
    expect(pageActive(findings[0], '/hypotheses/catalyst')).toBe(false)
  })
  it('titles the hypothesis sub-pages', () => {
    expect(hypothesisPath('')).toBe('/hypotheses')
    expect(hypothesisPath('catalyst')).toBe('/hypotheses/catalyst')
    expect(titleFor('/hypotheses/catalyst')).toBe('Catalyst comparison and heat integration - AmCraX')
    expect(titleFor('/hypotheses')).toBe('Hypothesis testing - AmCraX')
    expect(new Set(HYPOTHESIS_PAGES.map((p) => p.slug)).size).toBe(HYPOTHESIS_PAGES.length)
    expect(locate('/hypotheses/aspen-evidence')?.group.id).toBe('methods')
  })
  it('redirects only from paths that are not pages, to existing pages', () => {
    for (const r of REDIRECTS) {
      expect(ALL_PUBLIC.includes(r.from), r.from).toBe(false)
      expect(ALL_PUBLIC.includes(r.to.split('#')[0]), r.to).toBe(true)
    }
  })
  it('decodes anchors', () => {
    expect(anchorId('#lcoh')).toBe('lcoh')
    expect(anchorId('')).toBeNull()
    expect(anchorId('#a%20b')).toBe('a b')
  })
})
