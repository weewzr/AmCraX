import type { ValidationItem, ValidationStatus } from '../../api/validation'
import { num } from '../reactor/shape'
import type { XYRow } from '../common/XYChart'

export const STATUS_ORDER: ValidationStatus[] = ['pass', 'fail', 'not_run', 'informational']

export function countByStatus(items: ValidationItem[]): Record<ValidationStatus, number> {
  const c: Record<ValidationStatus, number> = { pass: 0, fail: 0, not_run: 0, informational: 0 }
  for (const i of items) c[i.status] += 1
  return c
}

export function filterItems(items: ValidationItem[], status: ValidationStatus | 'all', component: string, text: string): ValidationItem[] {
  const q = text.trim().toLowerCase()
  return items.filter((i) =>
    (status === 'all' || i.status === status) &&
    (component === 'all' || i.model_component === component) &&
    (!q || [i.id, i.model_component, i.validation_method, i.reference, i.expected_behaviour, i.actual_result, i.metric, i.limitations].join(' ').toLowerCase().includes(q)),
  )
}

/** "What is not validated": every not_run or failed item, plus any item that states limitations. */
export function notValidated(items: ValidationItem[]): { item: ValidationItem; why: string }[] {
  const out: { item: ValidationItem; why: string }[] = []
  for (const i of items) {
    if (i.status === 'not_run') out.push({ item: i, why: 'not run' + (i.limitations ? `: ${i.limitations}` : '') })
    else if (i.status === 'fail') out.push({ item: i, why: 'failed' + (i.actual_result ? `: ${i.actual_result}` : '') })
    else if (i.limitations.trim()) out.push({ item: i, why: `limitation: ${i.limitations}` })
  }
  return out
}

export type CmpQuantity = 'nh3_conversion' | 'y_NH3' | 'y_H2' | 'y_N2' | 'heat_duty_kJ_per_mol_NH3_fed'
export const CMP_QUANTITIES: [CmpQuantity, string][] = [
  ['nh3_conversion', 'NH3 conversion [-]'], ['y_NH3', 'y NH3 [-]'], ['y_H2', 'y H2 [-]'], ['y_N2', 'y N2 [-]'],
  ['heat_duty_kJ_per_mol_NH3_fed', 'Heat duty [kJ/mol NH3 fed]'],
]

export const comboKey = (r: Record<string, unknown>) => `${String(r.aspen_property_method)}|${String(r.python_eos)}`

/** Parity rows: one numeric key per Aspen-method/Python-EOS combination. x = Aspen value; y = Python value. */
export function parityData(rows: Record<string, unknown>[], q: CmpQuantity): { combos: string[]; byCombo: Record<string, XYRow[]> } {
  const byCombo: Record<string, XYRow[]> = {}
  for (const r of rows) {
    const a = num(r[`${q}_aspen`]), p = num(r[`${q}_python`])
    if (a === null || p === null) continue
    ;(byCombo[comboKey(r)] ??= []).push({ aspen: a, python: p })
  }
  return { combos: Object.keys(byCombo), byCombo }
}

export interface DevSummary { combo: string; n: number; maxAbs: number; maxAbsAt: string; meanAbs: number }
export function deviationSummary(rows: Record<string, unknown>[], q: CmpQuantity): DevSummary[] {
  const g = new Map<string, { vals: number[]; at: string[] }>()
  for (const r of rows) {
    const d = num(r[`${q}_abs_dev`])
    if (d === null) continue
    const e = g.get(comboKey(r)) ?? { vals: [], at: [] }
    e.vals.push(d); e.at.push(`${r.T_C} degC / ${r.P_bar} bar`)
    g.set(comboKey(r), e)
  }
  return [...g.entries()].map(([combo, { vals, at }]) => {
    let mi = 0
    vals.forEach((v, i) => { if (Math.abs(v) > Math.abs(vals[mi])) mi = i })
    return { combo, n: vals.length, maxAbs: Math.abs(vals[mi]), maxAbsAt: at[mi], meanAbs: vals.reduce((s, v) => s + Math.abs(v), 0) / vals.length }
  })
}

/** Deviation (python - aspen) vs T for one pressure, one key per combo. */
export function deviationVsT(rows: Record<string, unknown>[], q: CmpQuantity, P: number): XYRow[] {
  const byT = new Map<number, XYRow>()
  for (const r of rows) {
    if (num(r.P_bar) !== P) continue
    const T = num(r.T_C), d = num(r[`${q}_abs_dev`])
    if (T === null || d === null) continue
    const row = byT.get(T) ?? { T_C: T }
    row[comboKey(r)] = d
    byT.set(T, row)
  }
  return [...byT.values()].sort((a, b) => (a.T_C as number) - (b.T_C as number))
}

export interface CrossRow { quantity: string; a: number | null; b: number | null; abs_diff: number | null; rel_diff: number | null }
export function crossCheckRows(rows: Record<string, unknown>[]): CrossRow[] {
  return rows.map((r) => ({ quantity: String(r.quantity ?? ''), a: num(r.a), b: num(r.b), abs_diff: num(r.abs_diff), rel_diff: num(r.rel_diff) }))
}
