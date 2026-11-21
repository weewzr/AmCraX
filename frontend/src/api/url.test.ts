import { describe, expect, it } from 'vitest'
import { stripBase, withBase } from './url'

describe('withBase', () => {
  it('prefixes logical paths with the GitHub Pages base', () => {
    expect(withBase('/snapshot/manifest.json', '/AmCraX/')).toBe('/AmCraX/snapshot/manifest.json')
    expect(withBase('figures/a.png', '/AmCraX/')).toBe('/AmCraX/figures/a.png')
    expect(withBase('/downloads/x.pdf', '/AmCraX')).toBe('/AmCraX/downloads/x.pdf')
  })
  it('is the identity for the root base', () => {
    expect(withBase('/snapshot/flowsheet.json', '/')).toBe('/snapshot/flowsheet.json')
  })
  it('leaves absolute, protocol-relative, data and hash URLs alone', () => {
    expect(withBase('https://github.com/x', '/AmCraX/')).toBe('https://github.com/x')
    expect(withBase('//cdn.example/x.js', '/AmCraX/')).toBe('//cdn.example/x.js')
    expect(withBase('data:image/png;base64,AA', '/AmCraX/')).toBe('data:image/png;base64,AA')
    expect(withBase('#/platform', '/AmCraX/')).toBe('#/platform')
  })
})

describe('stripBase', () => {
  it('removes the base prefix', () => {
    expect(stripBase('/AmCraX/snapshot/a.json', '/AmCraX/')).toBe('/snapshot/a.json')
    expect(stripBase('/AmCraX/', '/AmCraX/')).toBe('/')
    expect(stripBase('/AmCraX', '/AmCraX/')).toBe('/')
    expect(stripBase('/other/a', '/AmCraX/')).toBe('/other/a')
    expect(stripBase('/a', '/')).toBe('/a')
  })
})
