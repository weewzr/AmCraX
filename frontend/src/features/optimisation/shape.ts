import type { ConflictPair, OptResult, ParetoFile, Row } from '../../api/optimisation'

/** Collect every object that has `decision_variables` (single_objective.json may be a list, a dict keyed by objective or wrapped). */
export function normaliseSingle(x: unknown, depth = 0): OptResult[] {
  if (!x || typeof x !== 'object' || depth > 3) return []
  if (Array.isArray(x)) return x.flatMap((i) => normaliseSingle(i, depth + 1))
  const o = x as Record<string, unknown>
  if (o.decision_variables && typeof o.decision_variables === 'object') return [o as unknown as OptResult]
  return Object.values(o).flatMap((v) => normaliseSingle(v, depth + 1))
}

/** Rows (array of objects) from a JSON file that may be a bare array or wrap it under a common key. */
export function normaliseRows(x: unknown): Row[] {
  if (Array.isArray(x)) return x.filter((i) => i && typeof i === 'object') as Row[]
  if (x && typeof x === 'object') {
    for (const k of ['rows', 'candidates', 'items', 'verification', 'results', 'verifications']) {
      const v = (x as Record<string, unknown>)[k]
      if (Array.isArray(v)) return v.filter((i) => i && typeof i === 'object') as Row[]
    }
  }
  return []
}

/** Flatten nested objects to dotted scalar columns (arrays are joined). */
export function flatten(o: unknown, prefix = '', out: Record<string, number | string | boolean | null> = {}): Record<string, number | string | boolean | null> {
  if (o === null || o === undefined) { if (prefix) out[prefix] = null; return out }
  if (Array.isArray(o)) { out[prefix] = o.every((v) => typeof v !== 'object') ? o.join('; ') : `[${o.length} items]`; return out }
  if (typeof o === 'object') { for (const [k, v] of Object.entries(o)) flatten(v, prefix ? `${prefix}.${k}` : k, out); return out }
  out[prefix] = o as number | string | boolean
  return out
}

export const INPUT_COLS = ['reactor_temperature_C', 'reactor_pressure_bar', 'psa_h2_recovery', 'fehe_hot_end_approach_K']

export interface HeatCell { x: number; y: number; value: number | null; n: number }
/** Aggregate a metric over the other design variables on the (x, y) plane. */
export function heatmap(rows: Row[], xk: string, yk: string, metric: string, agg: 'min' | 'max' | 'mean', feasibleOnly: boolean) {
  const used = rows.filter((r) => r.model_ok !== false && (!feasibleOnly || r.feasible === true) && typeof r[metric] === 'number' && typeof r[xk] === 'number' && typeof r[yk] === 'number')
  const xs = [...new Set(used.map((r) => r[xk] as number))].sort((a, b) => a - b)
  const ys = [...new Set(used.map((r) => r[yk] as number))].sort((a, b) => a - b)
  const cells: HeatCell[] = []
  for (const y of ys) for (const x of xs) {
    const v = used.filter((r) => r[xk] === x && r[yk] === y).map((r) => r[metric] as number)
    cells.push({ x, y, n: v.length, value: v.length === 0 ? null : agg === 'min' ? Math.min(...v) : agg === 'max' ? Math.max(...v) : v.reduce((a, b) => a + b, 0) / v.length })
  }
  const vals = cells.map((c) => c.value).filter((v): v is number => v !== null)
  return { xs, ys, cells, min: vals.length ? Math.min(...vals) : null, max: vals.length ? Math.max(...vals) : null }
}

export function numericColumns(rows: Row[]): string[] {
  if (!rows.length) return []
  return Object.keys(rows[0]).filter((k) => rows.some((r) => typeof r[k] === 'number'))
}

/** Parse CSV-ish booleans that survive a CSV round trip ("True"/"False" strings). */
export function normaliseGridRows(rows: Row[]): Row[] {
  return rows.map((r) => {
    const o: Row = { ...r }
    for (const k of ['feasible', 'model_ok']) { const v = o[k]; if (typeof v === 'string') o[k] = v.toLowerCase() === 'true' }
    return o
  })
}

/** Points of a front split into feasible / infeasible series for the scatter. */
export function frontSeries(f: ParetoFile['fronts'][number]) {
  const [xk, yk] = f.objectives
  const pick = (rs: Row[]) => rs.filter((r) => typeof r[xk] === 'number' && typeof r[yk] === 'number').map((r) => ({ x: r[xk] as number, y: r[yk] as number }))
  const feas = pick(f.points.filter((p) => p.feasible !== false))
  const infeas = pick([...f.points.filter((p) => p.feasible === false), ...(f.unconstrained_front_infeasible_points ?? [])])
  return { xk, yk, feas: feas.sort((a, b) => a.x - b.x), infeas }
}

export const classLabel = (p: ConflictPair): string => p.classification
export function atBoundList(r: OptResult): string[] {
  return Object.entries(r.decision_variables).filter(([, v]) => v.at_bound).map(([k, v]) => `${k} (${v.at_bound})`)
}