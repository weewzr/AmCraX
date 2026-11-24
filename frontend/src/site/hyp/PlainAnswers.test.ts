import { describe, expect, it } from 'vitest'
import { answerKind, basisText, chipWord, degC, headlineKind, PLAIN } from './PlainAnswers'

describe('plain answers helpers', () => {
  it('knows exactly the four plain answers', () => {
    expect([...PLAIN]).toEqual(['Yes', 'Yes, under the stated assumption', 'No', 'Not established'])
    expect(answerKind('Yes, under the stated assumption')).toBe('ya')
    expect(chipWord('Yes, under the stated assumption')).toBe('Yes (assumption)')
    expect(chipWord('Yes')).toBe('Yes')
    expect(answerKind('Yes')).toBe('yes')
    expect(answerKind('No')).toBe('no')
    expect(answerKind('Not established')).toBe('ne')
    for (const x of ['SUPPORTED', 'yes', 'Partly', '', null, undefined, 1]) expect(answerKind(x)).toBe('other')
  })
  it('reads the kind of a headline sentence', () => {
    expect(headlineKind('Yes, under the modelled conditions: x')).toBe('ya')
    expect(headlineKind('Yes: x')).toBe('yes')
    expect(headlineKind('Yes for energy: x')).toBe('yes')
    expect(headlineKind('No: x')).toBe('no')
    expect(headlineKind('Not established.')).toBe('ne')
    expect(headlineKind('INCONCLUSIVE')).toBe('other')
  })
  it('prints the basis with its half or mode', () => {
    expect(basisText({ rows: ['H1-a'], half: 'cracking_psa', mode: null })).toBe('H1-a (cracking + PSA half)')
    expect(basisText({ rows: ['H3-d'], half: 'cost' })).toBe('H3-d (cost half)')
    expect(basisText({ rows: ['H2-e'], mode: 'hypothetical_lca' })).toBe('H2-e (hypothetical price, not Singapore law)')
    expect(basisText({ rows: ['H2-a'] })).toBe('H2-a')
    expect(basisText({ rows: ['X-a'], half: 'other' })).toBe('X-a (other)')
    expect(basisText(undefined)).toBe('')
  })
  it('prints the degree sign for degC', () => {
    expect(degC('at 594 degC (extrapolated)')).toBe('at 594 °C (extrapolated)')
    expect(degC('(736, 760 degC)')).toBe('(736, 760 °C)')
    expect(degC('no temperature')).toBe('no temperature')
  })
})
