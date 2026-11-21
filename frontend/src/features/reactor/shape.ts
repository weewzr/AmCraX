import type { GridPoint, GridResponse } from '../../api/reactor'
import type { XYRow } from '../common/XYChart'

export const num = (v: unknown): number | null => {
  if (v === null || v === undefined || v === '') return null
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : null
}

/** Aspen RGibbs property method that corresponds to the Python EOS toggle. */
export const aspenMethodFor = (eos: 'ideal' | 'pr'): string => (eos === 'ideal' ? 'IDEAL' : 'PENG-ROB')

export type Quantity = 'conversion' | 'y_NH3' | 'y_H2' | 'y_N2'

const pyValue = (p: GridPoint, q: Quantity): number | null =>
  q === 'conversion' ? num(p.conversion) : num(p.result?.y?.[q.slice(2)])

const aspenCol: Record<Quantity, string> = { conversion: 'nh3_conversion', y_NH3: 'y_NH3', y_H2: 'y_H2', y_N2: 'y_N2' }

/**
 * Merge Python grid points and Aspen rows into rows keyed by T_C.
 * Series keys: `py_<P>` (Python line) and `as_<P>` (Aspen marker) for each pressure.
 */
export function mergeEquilibriumRows(
  points: GridPoint[], aspenRows: Record<string, unknown>[], pressures: number[], q: Quantity, aspenMethod: string,
): XYRow[] {
  const byT = new Map<number, XYRow>()
  const row = (T: number): XYRow => {
    let r = byT.get(T)
    if (!r) { r = { T_C: T }; byT.set(T, r) }
    return r
  }
  for (const p of points) {
    if (!pressures.includes(p.P_bar)) continue
    const v = pyValue(p, q)
    row(p.T_C)[`py_${p.P_bar}`] = v === null ? null : q === 'conversion' ? v * 100 : v
  }
  for (const a of aspenRows) {
    if (String(a.property_method).toUpperCase() !== aspenMethod) continue
    const P = num(a.P_bar), T = num(a.T_C), v = num(a[aspenCol[q]])
    if (P === null || T === null || v === null || !pressures.includes(P)) continue
    row(T)[`as_${P}`] = q === 'conversion' ? v * 100 : v
  }
  return [...byT.values()].sort((x, y) => (x.T_C as number) - (y.T_C as number))
}

/** Reaction enthalpy rows from equilibrium_python_grid.csv (python) and Aspen duty markers at one pressure. */
export function enthalpyRows(
  pyRows: Record<string, unknown>[], aspenRows: Record<string, unknown>[], P: number, eos: 'ideal' | 'pr', aspenMethod: string,
): XYRow[] {
  const byT = new Map<number, XYRow>()
  const row = (T: number): XYRow => { let r = byT.get(T); if (!r) { r = { T_C: T }; byT.set(T, r) } return r }
  for (const r of pyRows) {
    if (num(r.P_bar) !== P || String(r.eos).toLowerCase() !== eos) continue
    const T = num(r.T_C), d = num(r.dH_rxn_kJ_per_mol_NH3)
    if (T !== null && d !== null) row(T).py_dH = d
    const du = num(r.heat_duty_kJ_per_mol_NH3_fed)
    if (T !== null && du !== null) row(T).py_duty = du
  }
  for (const r of aspenRows) {
    if (String(r.property_method).toUpperCase() !== aspenMethod || num(r.P_bar) !== P) continue
    const T = num(r.T_C), d = num(r.heat_duty_kJ_per_mol_NH3_fed)
    if (T !== null && d !== null) row(T).as_duty = d
  }
  return [...byT.values()].sort((x, y) => (x.T_C as number) - (y.T_C as number))
}

/** Exact lookup of the python reaction enthalpy at a tabulated (T, P, eos) point; null when off-grid. */
export function lookupEnthalpy(pyRows: Record<string, unknown>[], T: number, P: number, eos: 'ideal' | 'pr'): number | null {
  const r = pyRows.find((x) => num(x.T_C) === T && num(x.P_bar) === P && String(x.eos).toLowerCase() === eos)
  return r ? num(r.dH_rxn_kJ_per_mol_NH3) : null
}

// ---------- kinetics payloads (tolerant: the module's response schema is not fixed in OpenAPI) ----------
const pick = (o: Record<string, unknown>, keys: string[]): string => {
  for (const k of keys) {
    const v = o[k]
    if (v !== undefined && v !== null && v !== '') return typeof v === 'string' ? v : JSON.stringify(v)
  }
  return ''
}

export interface CatalystRow {
  id: string; catalyst: string; rate_law: string; parameters: string; validity: string; source: string; limitations: string
}

export function normaliseCatalysts(body: unknown): CatalystRow[] {
  let arr: unknown[] = []
  if (Array.isArray(body)) arr = body
  else if (body && typeof body === 'object') {
    const o = body as Record<string, unknown>
    const hit = ['catalysts', 'items', 'models'].map((k) => o[k]).find((v) => Array.isArray(v) || (v && typeof v === 'object'))
    if (Array.isArray(hit)) arr = hit
    else if (hit && typeof hit === 'object') arr = Object.entries(hit as object).map(([k, v]) => ({ id: k, ...(v as object) }))
  }
  return arr.filter((r): r is Record<string, unknown> => !!r && typeof r === 'object').map((r) => ({
    id: pick(r, ['id', 'catalyst_id', 'key']),
    catalyst: pick(r, ['label', 'name', 'catalyst', 'title', 'id']),
    rate_law: pick(r, ['rate_law_text', 'rate_law', 'rate_expression', 'rate', 'equation', 'kinetic_model', 'model']),
    parameters: text(r.parameters ?? r.params ?? r.constants),
    validity: text(r.validity_range ?? r.validity ?? r.valid_range ?? r.range ?? r.conditions),
    source: text(r.source ?? r.citation ?? r.reference ?? r.citation_key ?? r.references),
    limitations: text([...(Array.isArray(r.limitations) ? r.limitations : r.limitations ? [r.limitations] : []),
      ...(Array.isArray(r.amcrax_extensions) ? r.amcrax_extensions : [])]),
  }))
}

/** Readable one-string rendering of nested kinetics metadata (objects -> "k = v unit" lines, arrays -> lines). */
export function text(v: unknown): string {
  if (v === null || v === undefined || v === '') return ''
  if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (Array.isArray(v)) return v.map(text).filter(Boolean).join('\n')
  const o = v as Record<string, unknown>
  if ('value' in o) return [text(o.value), text(o.unit)].filter(Boolean).join(' ')
  return Object.entries(o).map(([k, x]) => `${k}: ${text(x)}`).join('\n')
}

export interface PfrProfile {
  rows: XYRow[]
  xKey: string
  conv: string | null; eq: string | null; temp: string | null; press: string | null
  meta: Record<string, string>
}

const findKey = (keys: string[], res: RegExp[]): string | null => {
  for (const re of res) { const k = keys.find((x) => re.test(x)); if (k) return k }
  return null
}

/** Locate an axial profile (array of row objects, or object of equal-length numeric arrays) in an arbitrary payload. */
export function extractProfile(body: unknown): PfrProfile | null {
  const candidates: unknown[] = []
  const visit = (o: unknown, d: number) => {
    if (!o || typeof o !== 'object' || d > 3) return
    candidates.push(o)
    if (!Array.isArray(o)) Object.values(o as object).forEach((v) => visit(v, d + 1))
  }
  visit(body, 0)
  for (const c of candidates) {
    let rows: Record<string, number | null>[] | null = null
    if (Array.isArray(c) && c.length > 1 && c.every((r) => r && typeof r === 'object' && !Array.isArray(r))) {
      rows = (c as Record<string, unknown>[]).map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, num(v)])))
    } else if (c && typeof c === 'object' && !Array.isArray(c)) {
      const ents = Object.entries(c as Record<string, unknown>).filter(([, v]) => Array.isArray(v) && v.length > 1 && v.every((x) => typeof x === 'number' || x === null))
      const len = ents[0] ? (ents[0][1] as unknown[]).length : 0
      const same = ents.filter(([, v]) => (v as unknown[]).length === len)
      if (same.length >= 2) rows = Array.from({ length: len }, (_, i) => Object.fromEntries(same.map(([k, v]) => [k, num((v as unknown[])[i])])))
    }
    if (!rows) continue
    const keys = Object.keys(rows[0])
    const conv = findKey(keys, [/^(x_?nh3|conversion|nh3_conversion|x)$/i, /conv(?!.*eq)/i])
    const eq = findKey(keys, [/(eq|equilib).*conv|conv.*(eq|equilib)|x_?eq/i])
    if (!conv) continue
    const xKey = findKey(keys, [/catalyst_mass|^w(_kg)?$|mass/i, /^(z|length|axial|x_?pos|position)/i, /volume|^v/i]) ?? keys.find((k) => k !== conv) ?? conv
    const meta: Record<string, string> = {}
    if (body && typeof body === 'object' && !Array.isArray(body)) {
      for (const [k, v] of Object.entries(body as Record<string, unknown>)) if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') meta[k] = String(v)
    }
    return { rows, xKey, conv, eq, temp: findKey(keys, [/^t(_c|emperature)?/i]), press: findKey(keys, [/^p(_bar|ressure)?/i]), meta }
  }
  return null
}

/** Build a GridResponse-compatible point list from the stored equilibrium_python_grid rows (SNAPSHOT mode). */
export function gridFromRows(rows: Record<string, unknown>[], eos: 'ideal' | 'pr'): GridResponse {
  const points: GridPoint[] = []
  for (const r of rows) {
    if (String(r.eos).toLowerCase() !== eos) continue
    const T = num(r.T_C), P = num(r.P_bar), x = num(r.nh3_conversion)
    if (T === null || P === null || x === null) continue
    points.push({ T_C: T, P_bar: P, conversion: x, result: { T_K: T + 273.15, P_bar: P, eos, conversion: x, extent: x, n_out: {}, K_eq: num(r.K_eq), phi: {}, residual: null,
      y: { NH3: num(r.y_NH3) ?? NaN, H2: num(r.y_H2) ?? NaN, N2: num(r.y_N2) ?? NaN } } })
  }
  return { eos, source: 'python_model', count: points.length, points }
}

