import type { CiFactor, CiResult } from '../../api/environment'

export const CI_PARTS: [string, string][] = [
  ['upstream_ammonia', 'Upstream ammonia'], ['transport', 'Transport'], ['electricity', 'Electricity'], ['external_heat', 'External heat'],
]
const ROUTE_ORDER = ['green', 'blue', 'grey']

/** One row per route/heating scenario for grouped bars: x = route, one series per heating option. */
export function groupedByRoute(rs: CiResult[]): Record<string, number | string | null>[] {
  return ROUTE_ORDER.map((route) => {
    const row: Record<string, number | string | null> = { route: `${route} NH3` }
    for (const r of rs.filter((x) => x.nh3_route === route)) row[r.heating_option] = r.total_kgCO2e_per_kgH2
    return row
  })
}

/** Stacked breakdown rows (one per scenario, labelled route + heating). */
export function breakdownRowsCi(rs: CiResult[], label: (h: string) => string) {
  return rs.map((r) => ({ name: `${r.nh3_route} / ${label(r.heating_option)}`, ...Object.fromEntries(CI_PARTS.map(([k]) => [k, r.breakdown_kgCO2e_per_kgH2[k] ?? null])) }))
}

/** Sum of the breakdown parts must equal the total (guards against a wrong mapping); returns the max abs mismatch. */
export function breakdownMismatch(rs: CiResult[]): number {
  let m = 0
  for (const r of rs) {
    if (r.total_kgCO2e_per_kgH2 === null) continue
    const s = CI_PARTS.reduce((a, [k]) => a + (r.breakdown_kgCO2e_per_kgH2[k] ?? 0), 0)
    m = Math.max(m, Math.abs(s - r.total_kgCO2e_per_kgH2))
  }
  return m
}

/**
 * A factor is flagged "to be verified against primary source" when the data file's own text says so:
 * note/source mention re-checking, a secondary listing or an unopened primary document.
 */
export const VERIFY_RE = /to be verified|re-?check|secondary|primary[^.]*not|not (been )?(opened|verified)|unverified/i
export function needsVerification(f: CiFactor, flaggedCites: string[] = []): boolean {
  const text = `${f.note ?? ''} ${f.source ?? ''}`
  return VERIFY_RE.test(text) || flaggedCites.some((c) => f.source?.includes(c))
}

/** Unique factors by name across several scenario results (a scenario lists only the factors it uses). */
export function uniqueFactors(rs: CiResult[]): CiFactor[] {
  const m = new Map<string, CiFactor>()
  for (const r of rs) for (const f of r.factors ?? []) if (!m.has(f.name) || f.overridden) m.set(f.name, f)
  return [...m.values()].sort((a, b) => a.name.localeCompare(b.name))
}