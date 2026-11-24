import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { NAV_GROUPS } from './routes'
import { basisSentence, filterItems, pageItems, sentences, splitShared } from './siteHelpers'
import { show } from './hyp/shape'

const snap = (rel: string) => JSON.parse(readFileSync(new URL(`../../public/snapshot/${rel}`, import.meta.url), 'utf8')) as Record<string, unknown>

describe('command palette items', () => {
  const items = pageItems()
  it('lists every page and shortcut of the route table once, plus the platform', () => {
    const n = NAV_GROUPS.reduce((a, g) => a + g.pages.length, 0)
    expect(items.length).toBe(n + 1)
    expect(new Set(items.map((i) => i.id)).size).toBe(items.length)
    expect(items.at(-1)?.to).toBe('/platform/pfd')
  })
  it('filters by every word, case-insensitive, over label, hint and group', () => {
    expect(filterItems(items, '')).toBe(items)
    expect(filterItems(items, 'PURIF').map((i) => i.to)).toEqual(['/hypotheses/purification'])
    expect(filterItems(items, 'findings h3').map((i) => i.to)).toEqual(['/hypotheses/catalyst'])
    expect(filterItems(items, 'no such page')).toEqual([])
  })
})

describe('headline basis', () => {
  it('takes the basis sentence from the stored description of the unified baseline', () => {
    const b = snap('research/reference_scenario/baseline.json.json')
    const s = basisSentence(b.description, b.scenario)
    expect(s.length).toBeGreaterThan(10)
    expect(String(b.description)).toContain(s)
    expect(s).not.toMatch(/AUTHORITATIVE/)
  })
  it('falls back to the scenario name', () => {
    expect(basisSentence('One sentence only.', 'grey')).toBe('grey NH3 scenario')
    expect(basisSentence(undefined, undefined)).toBe('reference scenario')
  })
})

describe('aggregation rule printed once', () => {
  it('splits sentences after a full stop followed by a capital letter', () => {
    expect(sentences('Rule A; x if y. Components: H1-P SUPPORTED. Row outcomes: H1-a.')).toEqual(['Rule A; x if y.', 'Components: H1-P SUPPORTED.', 'Row outcomes: H1-a.'])
    expect(sentences('(methodology v2) a. b')).toEqual(['(methodology v2) a. b'])
  })
  it('keeps every sentence: shared once, the rest with its item', () => {
    const r = splitShared(['Rule. Own one. Rule two.', 'Rule. Own two. Rule two.'])
    expect(r.shared).toEqual(['Rule.', 'Rule two.'])
    expect(r.own).toEqual([['Own one.'], ['Own two.']])
    expect(splitShared(['Only one. Item.']).shared).toEqual([])
    expect(splitShared(['A.', 'B.']).shared).toEqual([])
  })
  it('on the stored matrix nothing is lost: shared plus own sentences rebuild each stored text', () => {
    const m = snap('research/evidence_matrix.json') as { hypotheses: Record<string, unknown>[] }
    const texts = m.hypotheses.map((h) => show(h.verdict_conditions))
    const { shared, own } = splitShared(texts)
    texts.forEach((t, i) => {
      const all = sentences(t)
      expect([...all].sort()).toEqual([...shared, ...own[i]].sort())
    })
  })
})
