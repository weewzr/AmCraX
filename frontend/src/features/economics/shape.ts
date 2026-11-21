import type { PriceCurveRow, Provenance, TornadoItem } from '../../api/economics'

export const BREAKDOWN_LABELS: [string, string][] = [
  ['capex', 'CAPEX annuity'], ['fixed_opex', 'Fixed OPEX'], ['ammonia_feed', 'Ammonia feed'],
  ['imported_heat', 'Imported heat'], ['electricity', 'Electricity'], ['cooling_water', 'Cooling water'], ['catalyst', 'Catalyst'],
]
export interface BreakdownRow { key: string; label: string; usd: number | null; share: number | null }

/** Breakdown rows in fixed order; share is of the sum of the listed components (null when unknown). */
export function breakdownRows(b: Record<string, number | null> | undefined): BreakdownRow[] {
  const src = b ?? {}
  const total = BREAKDOWN_LABELS.reduce((s, [k]) => s + (typeof src[k] === 'number' ? (src[k] as number) : 0), 0)
  return BREAKDOWN_LABELS.map(([key, label]) => {
    const v = typeof src[key] === 'number' ? (src[key] as number) : null
    return { key, label, usd: v, share: v !== null && total > 0 ? v / total : null }
  })
}

export interface AssumptionRow { key: string; value: unknown; unit: string; kind: 'literature' | 'assumption' | 'aspen' | 'python' | 'other'; citekey: string | null; where: string | null; note: string | null }

/** Assumptions table rows from result.provenance; anything that is not literature is shown as an assumption. */
export function assumptionRows(prov: Record<string, Provenance> | undefined): AssumptionRow[] {
  return Object.entries(prov ?? {}).map(([key, p]) => {
    const s = (p.source ?? '').toLowerCase()
    const kind: AssumptionRow['kind'] = s === 'literature' ? 'literature' : s === 'assumption' ? 'assumption' : s.startsWith('aspen') ? 'aspen' : s === 'python_model' ? 'python' : 'other'
    const where = [p.page ? `p. ${p.page}` : null, p.locator ?? null].filter(Boolean).join(', ') || null
    return { key, value: p.value, unit: p.unit ?? '', kind, citekey: p.citekey ?? null, where, note: p.note ?? null }
  })
}

/** Tornado rows sorted by decreasing swing; bar = [min, max] LCOH over the low/high ends. */
export function tornadoRows(items: TornadoItem[] | undefined) {
  return [...(items ?? [])].sort((a, b) => b.swing - a.swing).map((t) => ({
    parameter: t.parameter, low: Math.min(t.lcoh_at_low, t.lcoh_at_high), high: Math.max(t.lcoh_at_low, t.lcoh_at_high),
    base: t.lcoh_base, swing: t.swing, range: `${t.low_value} .. ${t.high_value}`, source: t.source_of_range ?? '',
  }))
}

/** Break-even ammonia price for a target LCOH: LCOH is linear in the ammonia price, so interpolate/extrapolate through the curve ends. */
export function breakevenPrice(curve: PriceCurveRow[], target: number): number | null {
  if (curve.length < 2) return null
  const a = curve[0], b = curve[curve.length - 1]
  const slope = (b.lcoh_USD_per_kg - a.lcoh_USD_per_kg) / (b.nh3_price_USD_per_t - a.nh3_price_USD_per_t)
  if (!Number.isFinite(slope) || slope === 0) return null
  const p = a.nh3_price_USD_per_t + (target - a.lcoh_USD_per_kg) / slope
  return p >= 0 ? p : null
}

/** Specific ammonia consumption vs the stoichiometric floor: excess in kg/kg and as a fraction of the floor. */
export function consumptionVsFloor(feed: number | null, floor: number | null) {
  if (feed === null || floor === null || !(floor > 0)) return { excess: null, excessFrac: null, floorFrac: null }
  return { excess: feed - floor, excessFrac: (feed - floor) / floor, floorFrac: floor / feed }
}

export function priceGrid(max = 700, step = 50): number[] {
  const g: number[] = []
  for (let p = 0; p <= max; p += step) g.push(p)
  return g
}