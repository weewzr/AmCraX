/** Pure helpers for the Hypotheses pages: data-file source types, pivoting, ISO checks, evidence-matrix tolerance. No numbers are defined here. */
import type { DataSource } from '../../api/types'
import type { XYRow } from '../../features/common/XYChart'

/** Source type string of a result file ("aspen", "python", "literature", "assumption", or longer text starting with one of them). */
export function srcOf(s: unknown): DataSource | null {
  if (typeof s !== 'string') return null
  const t = s.trim().toLowerCase()
  if (t.startsWith('aspen')) return 'aspen_plus_v15'
  if (t.startsWith('python')) return 'python_model'
  if (t.startsWith('literature')) return 'literature'
  if (t.startsWith('assumption')) return 'assumption'
  return null
}

export const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

/** Group rows by the string value of a key, keeping first-seen order. */
export function groupBy<R extends Record<string, unknown>>(rows: R[], key: string): Map<string, R[]> {
  const m = new Map<string, R[]>()
  for (const r of rows) {
    const k = String(r[key])
    const a = m.get(k)
    if (a) a.push(r)
    else m.set(k, [r])
  }
  return m
}

export interface PivotSeries { key: string; rows: Record<string, unknown>[]; y: string }

/** Merge several row sets on a shared numeric x into XYChart rows ({x, <series key>: y}); y values that are not finite become null. */
export function pivotXY(xKey: string, series: PivotSeries[], scaleY: Record<string, number> = {}): XYRow[] {
  const m = new Map<number, XYRow>()
  for (const s of series) {
    for (const r of s.rows) {
      const x = num(r[xKey])
      if (x === null) continue
      const row = m.get(x) ?? { [xKey]: x }
      const y = num(r[s.y])
      row[s.key] = y === null ? null : y * (scaleY[s.key] ?? 1)
      m.set(x, row)
    }
  }
  return [...m.values()].sort((a, b) => (a[xKey] as number) - (b[xKey] as number))
}

/** Split one catalyst's rows into points inside and beyond the fitted range of its rate law (the data flag them as within_fitted_range). */
export function splitFitted<R extends Record<string, unknown>>(rows: R[]): { inside: R[]; beyond: R[] } {
  const inside: R[] = [], beyond: R[] = []
  for (const r of rows) (r.within_fitted_range === false || r.within_fitted_range === 'False' ? beyond : inside).push(r)
  return { inside, beyond }
}

/** True for the values the CSV reader leaves as strings ("True"/"False") or as booleans. */
export const truthy = (v: unknown): boolean => v === true || v === 'True' || v === 'true'

/** ISO 14687 check of one contaminant: returns 'pass' | 'fail' | 'not_modelled'. */
export function isoCheck(valuePpm: unknown, limitPpm: unknown): 'pass' | 'fail' | 'not_modelled' {
  const v = num(valuePpm), l = num(limitPpm)
  if (v === null || l === null) return 'not_modelled'
  return v <= l ? 'pass' : 'fail'
}

/** Upper-case verdict with "_" read as a space ("PARTIALLY_SUPPORTED" -> "PARTIALLY SUPPORTED"); '' when not a string. */
export function normVerdict(v: unknown): string {
  return typeof v === 'string' ? v.trim().toUpperCase().replace(/_/g, ' ').replace(/\s+/g, ' ') : ''
}

/** Verdict vocabulary of the evidence matrix (v1 and v2) mapped to a status pill kind. Text that adds a qualifier
 *  after the verdict word ("SUPPORTED (necessity)") keeps the kind of the verdict word. Unknown strings stay neutral. */
export function verdictKind(v: unknown): 'ok' | 'error' | 'warn' | 'partial' | 'mixed' | 'neutral' {
  const s = normVerdict(v)
  if (s.startsWith('PARTIALLY SUPPORTED')) return 'partial'
  if (s.startsWith('SUPPORTED')) return 'ok'
  if (s.startsWith('CONTRADICTED')) return 'error'
  if (s.startsWith('MIXED')) return 'mixed'
  if (s.startsWith('INCONCLUSIVE')) return 'warn'
  return 'neutral'
}

/**
 * Linear interpolation in a stored grid (rows sorted or not by xKey). Returns null outside the grid or when a neighbour
 * value is missing; an exact grid point returns the stored value unchanged. Used for Mode B of the carbon-pricing control.
 */
export function interpRows(rows: Record<string, unknown>[], xKey: string, yKey: string, x: number): number | null {
  const pts = rows.map((r) => [num(r[xKey]), num(r[yKey])] as const).filter((p): p is readonly [number, number] => p[0] !== null && p[1] !== null)
    .sort((a, b) => a[0] - b[0])
  if (!pts.length || !Number.isFinite(x) || x < pts[0][0] || x > pts[pts.length - 1][0]) return null
  for (let i = 0; i < pts.length; i++) {
    if (pts[i][0] === x) return pts[i][1]
    if (i > 0 && pts[i][0] > x) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i]
      return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0)
    }
  }
  return null
}

/** Stored row at the grid point nearest to x (for text columns such as the cheapest route). */
export function nearestRow<R extends Record<string, unknown>>(rows: R[], xKey: string, x: number): R | null {
  let best: R | null = null, d = Infinity
  for (const r of rows) { const v = num(r[xKey]); if (v !== null && Math.abs(v - x) < d) { d = Math.abs(v - x); best = r } }
  return best
}

/** Defensive text of any JSON value (the evidence matrix is written by another agent; fields can be strings, numbers, lists or objects). */
export function show(v: unknown): string {
  if (v === null || v === undefined || v === '') return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number') return Number.isFinite(v) ? String(Number(v.toPrecision(5))) : ''
  if (typeof v === 'boolean') return v ? 'yes' : 'no'
  if (Array.isArray(v)) return v.map(show).filter(Boolean).join('; ')
  if (typeof v === 'object') return Object.entries(v as Record<string, unknown>).map(([k, x]) => `${k}: ${show(x)}`).join('; ')
  return String(v)
}

/** String list from a field that may be a list, a single string or missing. */
export function list(v: unknown): string[] {
  if (Array.isArray(v)) return v.map(show).filter(Boolean)
  const s = show(v)
  return s ? [s] : []
}

/** File name of a repo-relative path ("results/figures/research/x.png" -> "x.png"). */
export const baseName = (p: string): string => p.replace(/\\/g, '/').split('/').pop() ?? p

/** Repo-relative path hardening: only plain relative paths are turned into links (no scheme, no "..", no absolute or drive paths). */
export function safeRepoPath(p: unknown): string | null {
  if (typeof p !== 'string') return null
  const s = p.replace(/\\/g, '/').trim()
  if (!s || /^([a-z][a-z0-9+.-]*:|\/|~)/i.test(s) || s.split('/').includes('..')) return null
  return s
}

/** The matrix's own qualifier of a hypothesis verdict: the first sentence of its summary when that sentence starts with the
 *  verdict word (for example "PARTIALLY SUPPORTED, resting only on H3-T (...)."); '' otherwise. Nothing is composed here. */
export function qualifierOf(summary: unknown, verdict: unknown): string {
  const s = typeof summary === 'string' ? summary.trim() : ''
  const v = normVerdict(verdict)
  if (!s || !v || !normVerdict(s).startsWith(v)) return ''
  const m = s.match(/^(.+?\.)(\s|$)/)
  return m ? m[1] : s
}

export interface ThresholdSummary { parameter: string; computed: [number, number] | null; sourced: [number, number] | null; unit: string; comparison: string }
/** Compact reading of a row threshold of the evidence matrix ({parameter, values[], sourced_values[], comparison}). Null when
 *  the threshold holds no computed values. The comparison is printed as stored ("straddle", or "key: value" pairs). */
export function thresholdSummary(t: unknown): ThresholdSummary | null {
  if (!t || typeof t !== 'object' || Array.isArray(t)) return null
  const o = t as Record<string, unknown>
  const vals = (k: string) => (Array.isArray(o[k]) ? (o[k] as Record<string, unknown>[]).map((x) => num(x?.value)) : [])
  const computed = extent(vals('values'))
  if (!computed) return null
  const first = Array.isArray(o.values) ? (o.values as Record<string, unknown>[])[0] : undefined
  return { parameter: show(o.parameter), computed, sourced: extent(vals('sourced_values')), unit: show(first?.unit), comparison: show(o.comparison) }
}

/** Min/max over finite numbers (null when none). */
export function extent(vals: (number | null | undefined)[]): [number, number] | null {
  const f = vals.filter((x): x is number => typeof x === 'number' && Number.isFinite(x))
  return f.length ? [Math.min(...f), Math.max(...f)] : null
}

/** Position of v inside [lo, hi] as 0..1 (0.5 when the range is empty). */
export function frac(v: number, lo: number, hi: number): number {
  return hi > lo ? Math.min(1, Math.max(0, (v - lo) / (hi - lo))) : 0.5
}
