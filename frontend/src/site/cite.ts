/** In-text citation labels derived from the APA 7 strings of research/references.json (no hand-typed author lists). */

/** First segment of an APA reference up to the year: "Cechetto, V., Di Felice, L., & Gallucci, F." and the year. */
export function parseApa(apa7: string): { authors: string[]; year: string } | null {
  const m = apa7.match(/^(.*?)\s\((\d{4})[a-z]?\)/) ?? apa7.match(/^(.*?)\s\((n\.d\.)\)/)
  if (!m) return null
  const head = m[1].replace(/\s*\(Eds?\.\)\.?$/, '')
  // "Surname, A. B., Surname2, C., & Surname3, D." -> split after an initial's full stop
  const parts = head.split(/\.,\s+(?:&\s+)?/).map((p) => p.replace(/^&\s+/, '').replace(/\.$/, '').trim()).filter(Boolean)
  const authors = parts.map((p) => (p.includes(',') ? p.slice(0, p.indexOf(',')).trim() : p))
  return authors.length ? { authors, year: m[2] } : null
}

/** "Cechetto et al., 2023" / "Bell & Wronski, 2014" / "Bartels, 2008". Falls back to the key. */
export function citeLabel(apa7: string | undefined, fallback: string): string {
  const p = apa7 ? parseApa(apa7) : null
  if (!p) return fallback
  const [a, b] = p.authors
  const who = p.authors.length === 1 ? a : p.authors.length === 2 ? `${a} & ${b}` : `${a} et al.`
  return `${who}, ${p.year}`
}

/** DOI link from the explicit doi field, else a doi.org url. */
export function refLink(doi?: string | null, url?: string | null): string | null {
  if (doi) return `https://doi.org/${doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')}`
  return url ?? null
}
