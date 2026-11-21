import { describe, expect, it } from 'vitest'
import { citeLabel, parseApa, refLink } from './cite'

const CECHETTO = 'Cechetto, V., Di Felice, L., & Gallucci, F. (2023). Advances and perspectives of H2 production from NH3 decomposition in membrane reactors. Energy & Fuels, 37(15), 10775-10798. https://doi.org/10.1021/acs.energyfuels.3c00760'
const BELL = 'Bell, I. H., Wronski, J., Quoilin, S., & Lemort, V. (2014). Pure and pseudo-pure fluid thermophysical property evaluation. Ind. Eng. Chem. Res., 53(6).'
const TWO = 'Peng, D.-Y., & Robinson, D. B. (1976). A new two-constant equation of state. Industrial & Engineering Chemistry Fundamentals, 15(1), 59-64.'
const ONE = 'Bartels, J. R. (2008). A feasibility study of implementing an ammonia economy [Master\'s thesis]. Iowa State University.'

describe('citation labels', () => {
  it('uses et al. for three or more authors', () => {
    expect(citeLabel(CECHETTO, 'k')).toBe('Cechetto et al., 2023')
    expect(citeLabel(BELL, 'k')).toBe('Bell et al., 2014')
  })
  it('handles one and two authors', () => {
    expect(citeLabel(TWO, 'k')).toBe('Peng & Robinson, 1976')
    expect(citeLabel(ONE, 'k')).toBe('Bartels, 2008')
  })
  it('falls back to the key when the string cannot be parsed or is missing', () => {
    expect(citeLabel(undefined, 'fallback_key')).toBe('fallback_key')
    expect(citeLabel('not an apa string', 'x')).toBe('x')
    expect(parseApa(CECHETTO)?.authors).toEqual(['Cechetto', 'Di Felice', 'Gallucci'])
  })
  it('builds DOI links', () => {
    expect(refLink('10.1/abc')).toBe('https://doi.org/10.1/abc')
    expect(refLink('https://doi.org/10.1/abc')).toBe('https://doi.org/10.1/abc')
    expect(refLink(null, 'https://example.org/x')).toBe('https://example.org/x')
    expect(refLink(null, null)).toBeNull()
  })
})
