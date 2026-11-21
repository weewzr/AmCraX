import type { Cell, DataRow } from '../../api/sensitivity'
import type { CaseInputs, DataSource } from '../../api/types'
import { FIELDS } from '../simulation/inputs'
import { metricLabel } from '../../data/metrics'

export const INPUT_KEYS = ['case_id', 'feed_total_kmol_h', 'feed_h2o_mole_frac', 'reactor_temperature_C', 'reactor_pressure_bar', 'heat_integration',
  'fehe_hot_end_approach_K', 'psa_feed_temperature_C', 'psa_h2_recovery', 'psa_n2_slip', 'burner_excess_air', 'stack_temperature_C', 'property_method']

export const num = (c: Cell | undefined): number | null => (typeof c === 'number' && Number.isFinite(c) ? c : null)

export function parseBool(c: Cell | undefined): boolean | null {
  if (typeof c === 'boolean') return c
  if (typeof c === 'number') return c !== 0
  if (typeof c === 'string') { const s = c.trim().toLowerCase(); if (s === 'true' || s === '1') return true; if (s === 'false' || s === '0') return false }
  return null
}

/** A row counts as converged when it has no converged column or the flag is true. Rows with an explicit false/blank flag are excluded. */
export function isConverged(r: DataRow, hasFlag: boolean): boolean {
  if (!hasFlag) return true
  return parseBool(r['converged']) === true
}
export function splitConverged(rows: DataRow[], columns: string[]): { used: DataRow[]; excluded: number } {
  const has = columns.includes('converged')
  const used = rows.filter((r) => isConverged(r, has))
  return { used, excluded: rows.length - used.length }
}

export function numericColumns(columns: string[], rows: DataRow[]): string[] {
  return columns.filter((c) => {
    const vals = rows.map((r) => r[c]).filter((v) => v !== null && v !== undefined && v !== '')
    return vals.length > 0 && vals.every((v) => typeof v === 'number')
  })
}

const distinct = (rows: DataRow[], key: string) => [...new Set(rows.map((r) => num(r[key])).filter((v): v is number => v !== null))].sort((a, b) => a - b)
export const distinctSorted = distinct

/** Input columns that vary within the dataset. */
export function varyingInputs(columns: string[], rows: DataRow[]): string[] {
  return INPUT_KEYS.filter((k) => columns.includes(k) && k !== 'case_id' && distinct(rows, k).length > 1)
}

const X_BY_STUDY: [RegExp, string][] = [
  [/temperature/i, 'reactor_temperature_C'], [/pressure/i, 'reactor_pressure_bar'], [/feed_rate/i, 'feed_total_kmol_h'],
  [/feed_water/i, 'feed_h2o_mole_frac'], [/psa_recovery/i, 'psa_h2_recovery'], [/fehe/i, 'fehe_hot_end_approach_K'],
]
export function inferX(name: string, columns: string[], rows: DataRow[]): string | null {
  const vary = varyingInputs(columns, rows)
  for (const [re, k] of X_BY_STUDY) if (re.test(name) && vary.includes(k)) return k
  if (vary.length) return vary[0]
  const nums = numericColumns(columns, rows)
  return nums[0] ?? columns[0] ?? null
}

const Y_PREF = ['nh3_conversion', 'h2_product_kg_h', 'total_external_heating_kW', 'specific_heat_demand_kWh_per_kgH2', 'lhv_efficiency']
export function defaultYs(columns: string[], rows: DataRow[], x: string | null): string[] {
  const nums = numericColumns(columns, rows).filter((c) => c !== x && !INPUT_KEYS.includes(c))
  const pref = Y_PREF.filter((c) => nums.includes(c))
  return (pref.length ? pref : nums).slice(0, 5)
}

export function unitFor(col: string): string {
  if (/_C$|temperature_C|_outlet_C/.test(col)) return 'degC'
  if (/_bar$/.test(col)) return 'bar'
  if (/_K$/.test(col)) return 'K'
  if (/kmol_h$/.test(col)) return 'kmol/h'
  if (/kg_h$/.test(col)) return 'kg/h'
  if (/kWh_per_kgH2$/.test(col)) return 'kWh/kg H2'
  if (/_kW$/.test(col)) return 'kW'
  if (/time_s$/.test(col)) return 's'
  if (/conversion|yield|efficiency|purity|frac|recovery|slip|closure|excess_air/.test(col)) return '-'
  return ''
}
/** Human-readable axis title with unit (shared map in src/data/metrics.ts); raw keys stay available as tooltips. */
export const axisLabel = (col: string) => metricLabel(col)

/** Provenance of a dataset: Aspen studies carry source "aspen_plus_v15..." in each row; the analysis CSVs are Python/assumption based. */
export function datasetSource(name: string, rows: DataRow[]): DataSource {
  const s = rows.map((r) => r['source']).find((v) => typeof v === 'string') as string | undefined
  if (s) { if (s.startsWith('aspen_plus_v15')) return 'aspen_plus_v15'; if (s.startsWith('python_model')) return 'python_model' }
  if (/^aspen_/.test(name)) return 'aspen_plus_v15'
  if (/^lcoh_/.test(name)) return 'assumption'
  return 'python_model'
}

/** Base inputs for a Python overlay of an Aspen study: the constant (non-swept) input columns of the dataset. */
export function baseInputsFromRows(rows: DataRow[], columns: string[], xKey: string): Partial<CaseInputs> {
  const out: Record<string, unknown> = {}
  const first = rows[0]
  if (!first) return out
  for (const f of FIELDS) {
    if (f.key === xKey || !columns.includes(f.key)) continue
    const v = first[f.key]
    if (f.kind === 'bool') { const b = parseBool(v); if (b !== null) out[f.key] = b }
    else if (f.kind === 'number') { const n = num(v); if (n !== null) out[f.key] = n }
    else if (typeof v === 'string' && v) out[f.key] = v
  }
  return out as Partial<CaseInputs>
}

export interface ChartSet { prefix: string; rows: DataRow[] }
/** Merge several row sets into one x-sorted array with keys `<prefix>|<y>` (null where a set has no point at x). */
export function mergeSeries(sets: ChartSet[], xKey: string, y: string): Record<string, number | null>[] {
  const byX = new Map<number, Record<string, number | null>>()
  for (const s of sets) for (const r of s.rows) {
    const x = num(r[xKey]); const yv = num(r[y])
    if (x === null) continue
    const o = byX.get(x) ?? { x }
    if (yv !== null) o[`${s.prefix}|${y}`] = yv
    byX.set(x, o)
  }
  return [...byX.values()].sort((a, b) => (a.x as number) - (b.x as number))
}

export interface Grid { xs: number[]; ys: number[]; cell: Map<string, { v: number | null; converged: boolean }>; min: number; max: number }
/** T x P (or any two-key) grid for the heat map. Non-converged points keep converged=false and no value. */
export function buildGrid(rows: DataRow[], columns: string[], xKey: string, yKey: string, zKey: string): Grid {
  const has = columns.includes('converged')
  const cell = new Map<string, { v: number | null; converged: boolean }>()
  let min = Infinity, max = -Infinity
  for (const r of rows) {
    const x = num(r[xKey]); const y = num(r[yKey]); if (x === null || y === null) continue
    const ok = isConverged(r, has)
    const z = ok ? num(r[zKey]) : null
    cell.set(`${x}|${y}`, { v: z, converged: ok })
    if (z !== null) { min = Math.min(min, z); max = Math.max(max, z) }
  }
  return { xs: distinct(rows, xKey), ys: distinct(rows, yKey), cell, min: Number.isFinite(min) ? min : 0, max: Number.isFinite(max) ? max : 0 }
}
export function heatFraction(v: number, min: number, max: number): number { return max > min ? (v - min) / (max - min) : 0.5 }

// ---- sweep specification ----
export function rangeValues(from: number, to: number, step: number, maxPoints = 200): { values: number[]; error: string | null } {
  if (![from, to, step].every(Number.isFinite)) return { values: [], error: 'From, to and step must be numbers.' }
  if (step <= 0) return { values: [], error: 'Step must be > 0.' }
  if (to < from) return { values: [], error: 'To must be >= from.' }
  const n = Math.floor((to - from) / step + 1e-9) + 1
  if (n > maxPoints) return { values: [], error: `That is ${n} points; the limit is ${maxPoints}.` }
  const values = Array.from({ length: n }, (_, i) => Number((from + i * step).toPrecision(12)))
  return { values, error: null }
}
export function listValues(text: string): { values: number[]; error: string | null } {
  const parts = text.split(/[\s,;]+/).filter(Boolean)
  if (parts.length === 0) return { values: [], error: 'Enter at least one value.' }
  const values = parts.map(Number)
  if (values.some((v) => !Number.isFinite(v))) return { values: [], error: 'The list contains a non-numeric entry.' }
  if (values.length > 200) return { values: [], error: 'At most 200 values.' }
  return { values, error: null }
}
/** Check each value against the CaseInputs bounds of the swept variable. */
export function checkBounds(variable: string, values: number[]): string | null {
  const f = FIELDS.find((x) => x.key === variable)
  if (!f || f.kind !== 'number') return `${variable} is not a numeric input.`
  for (const v of values) {
    if (f.min !== undefined && (f.minExcl ? v <= f.min : v < f.min)) return `${v} is below the allowed range (${f.minExcl ? '>' : '>='} ${f.min}).`
    if (f.max !== undefined && (f.maxExcl ? v >= f.max : v > f.max)) return `${v} is above the allowed range (${f.maxExcl ? '<' : '<='} ${f.max}).`
  }
  return null
}
