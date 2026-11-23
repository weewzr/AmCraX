import { describe, expect, it } from 'vitest'
import { anchorId, HYPOTHESIS_PAGES, hypothesisPath, isPlatformPath, platformPath, SITE_ROUTES, titleFor } from './routes'

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
  it('covers the ten sections once each, in order, with unique paths', () => {
    expect(SITE_ROUTES.map((r) => r.section)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(new Set(SITE_ROUTES.map((r) => r.path)).size).toBe(10)
    expect(SITE_ROUTES[0].path).toBe('/')
  })
  it('gives each page a title', () => {
    expect(titleFor('/results')).toBe('Engineering results - AmCraX')
    expect(titleFor('/')).toMatch(/^AmCraX - /)
    expect(titleFor('/platform/pfd')).toBe('AmCraX platform')
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
