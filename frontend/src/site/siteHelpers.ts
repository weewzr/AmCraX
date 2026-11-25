/** Pure helpers of the site frame (command palette, headline basis, on-this-page list, evidence matrix); unit-tested in siteHelpers.test.ts. */
import { NAV_GROUPS, platformPath } from './routes'

export interface PaletteItem { id: string; group: string; label: string; hint?: string; to: string }

/** Items that match every word of the query (case-insensitive, over label, hint and group), in the given order. */
export function filterItems(items: PaletteItem[], query: string): PaletteItem[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return items
  return items.filter((it) => {
    const hay = `${it.label} ${it.hint ?? ''} ${it.group}`.toLowerCase()
    return words.every((w) => hay.includes(w))
  })
}

/** Page items from the route table (the single source of the site structure), plus the engineering platform. */
export function pageItems(): PaletteItem[] {
  const pages = NAV_GROUPS.flatMap((g) => g.pages.map((p) => ({ id: `page:${p.to}`, group: g.label, label: p.label, hint: p.hint, to: p.to })))
  return [...pages, { id: 'page:platform', group: 'Engineering platform', label: 'Open the engineering platform', hint: 'Dashboard: flowsheet, reactor, heat, economics', to: platformPath('/pfd') }]
}

/** "AUTHORITATIVE ... baseline (Phase 2). Grey NH3 scenario, heat integration on, ..." -> the sentences after the first. */
export function basisSentence(description: unknown, scenario: unknown): string {
  const d = typeof description === 'string' ? description.trim() : ''
  const rest = d.split(/(?<=\.)\s+/).slice(1).join(' ').replace(/\.$/, '')
  if (rest) return rest
  return typeof scenario === 'string' && scenario ? `${scenario} NH3 scenario` : 'reference scenario'
}

export interface PageEntry { id: string; label: string }

/** Headed blocks of a page, in document order: sections (h2) and hypothesis cards (h3) that carry an id. */
export function collectEntries(root: ParentNode): PageEntry[] {
  const out: PageEntry[] = []
  root.querySelectorAll<HTMLElement>('section.section[id], article.hyp-card[id]').forEach((el) => {
    const h = el.querySelector('h2, h3')
    const full = h?.textContent?.trim()
    // hypothesis cards: "H1: End-use suitability: cracking is ..." -> "H1: End-use suitability"
    const label = full && el.classList.contains('hyp-card') ? full.split(':').slice(0, 2).join(':') : full
    if (label && !out.some((e) => e.id === el.id)) out.push({ id: el.id, label })
  })
  return out
}

/** Sentences of a stored text ("... INCONCLUSIVE. Components: ..."): split after a full stop that is followed by a capital letter. */
export function sentences(text: string): string[] {
  return text.split(/(?<=\.)\s+(?=[A-Z])/).map((s) => s.trim()).filter(Boolean)
}

/**
 * Split texts stored once per item (for example the verdict conditions of each hypothesis, which repeat the aggregation rule
 * and then name that hypothesis's components and row outcomes) into the sentences every item shares, in the order of the
 * first text, and each item's own sentences. Nothing is dropped: shared + own of item i is the whole of text i.
 * With fewer than two items, or no sentence in common, everything stays with its item.
 */
export function splitShared(texts: string[]): { shared: string[]; own: string[][] } {
  const per = texts.map(sentences)
  if (per.length < 2 || per.some((p) => !p.length)) return { shared: [], own: per }
  const shared = per[0].filter((s) => per.every((p) => p.includes(s)))
  return { shared, own: per.map((p) => p.filter((s) => !shared.includes(s))) }
}
