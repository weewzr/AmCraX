import type { CaseInputs } from '../../api/types'

/** Field specification mirrored from backend/amcrax/schemas.py (CaseInputs). Keep in sync with the backend. */
export interface FieldSpec {
  key: keyof CaseInputs
  label: string
  unit: string
  kind: 'number' | 'bool' | 'text'
  default: number | boolean | string
  min?: number
  max?: number
  /** bound is exclusive (pydantic gt / lt) */
  minExcl?: boolean
  maxExcl?: boolean
  step?: number
  help: string
}

export const FIELDS: FieldSpec[] = [
  { key: 'feed_total_kmol_h', label: 'Ammonia feed', unit: 'kmol/h', kind: 'number', default: 100, min: 0, minExcl: true, step: 10, help: 'Total liquid ammonia feed (must be > 0).' },
  { key: 'feed_h2o_mole_frac', label: 'Water in feed', unit: 'mole fraction', kind: 'number', default: 0.002, min: 0, max: 0.2, maxExcl: true, step: 0.001, help: 'Water in the ammonia feed, 0 <= x < 0.2.' },
  { key: 'reactor_temperature_C', label: 'Cracker temperature', unit: 'degC', kind: 'number', default: 600, min: 250, max: 1000, step: 10, help: 'Isothermal cracker temperature.' },
  { key: 'reactor_pressure_bar', label: 'Cracker pressure', unit: 'bar', kind: 'number', default: 20, min: 1, max: 100, step: 1, help: 'Cracker outlet pressure (Aspen full flowsheet: at least 3 bar).' },
  { key: 'heat_integration', label: 'Feed/effluent exchanger (FEHE)', unit: '', kind: 'bool', default: true, help: 'On: feed/effluent exchanger present.' },
  { key: 'fehe_hot_end_approach_K', label: 'FEHE hot-end approach', unit: 'K', kind: 'number', default: 50, min: 5, max: 300, step: 5, help: 'Hot inlet minus cold outlet temperature.' },
  { key: 'psa_feed_temperature_C', label: 'PSA feed temperature', unit: 'degC', kind: 'number', default: 40, min: 5, max: 80, step: 5, help: 'Cooler outlet / PSA feed temperature.' },
  { key: 'psa_h2_recovery', label: 'PSA H2 recovery', unit: 'fraction', kind: 'number', default: 0.85, min: 0, minExcl: true, max: 1, step: 0.01, help: 'Reduced-order PSA: fraction of H2 recovered to product, 0 < r <= 1.' },
  { key: 'psa_n2_slip', label: 'PSA N2 slip', unit: 'fraction', kind: 'number', default: 0.001, min: 0, max: 0.05, step: 0.001, help: 'Reduced-order PSA: fraction of N2 slipping to product.' },
  { key: 'burner_excess_air', label: 'Burner excess air', unit: 'fraction', kind: 'number', default: 0.15, min: 0, max: 2, step: 0.05, help: 'Tail-gas burner excess air over stoichiometric.' },
  { key: 'stack_temperature_C', label: 'Stack temperature', unit: 'degC', kind: 'number', default: 150, min: 60, max: 400, step: 10, help: 'Flue-gas temperature leaving heat recovery.' },
  { key: 'property_method', label: 'Property method', unit: '', kind: 'text', default: 'PENG-ROB', help: 'Aspen property method (Python engine: PENG-ROB selects the Peng-Robinson route).' },
]

export type FormValues = Record<string, string | boolean>
export const ASPEN_MIN_PRESSURE_BAR = 3
export const CASE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/

export function defaultValues(): FormValues {
  const v: FormValues = {}
  for (const f of FIELDS) v[f.key] = f.kind === 'bool' ? (f.default as boolean) : String(f.default)
  return v
}

/** Values from an existing case (used to start from a stored case). */
export function valuesFromInputs(i: Partial<CaseInputs>): FormValues {
  const v = defaultValues()
  for (const f of FIELDS) {
    const x = (i as Record<string, unknown>)[f.key]
    if (x === undefined || x === null) continue
    v[f.key] = f.kind === 'bool' ? Boolean(x) : String(x)
  }
  return v
}

export function isChanged(f: FieldSpec, v: FormValues): boolean {
  const x = v[f.key]
  if (f.kind === 'bool') return x !== f.default
  if (f.kind === 'text') return String(x).trim() !== f.default
  const n = Number(x)
  return !(String(x).trim() !== '' && Number.isFinite(n) && n === f.default)
}
export const changedKeys = (v: FormValues): string[] => FIELDS.filter((f) => isChanged(f, v)).map((f) => f.key as string)

export function rangeText(f: FieldSpec): string {
  if (f.kind !== 'number') return ''
  const lo = f.min === undefined ? '' : `${f.minExcl ? '>' : '>='} ${f.min}`
  const hi = f.max === undefined ? '' : `${f.maxExcl ? '<' : '<='} ${f.max}`
  return [lo, hi].filter(Boolean).join(' and ')
}

export type Errors = Record<string, string>

export function validate(v: FormValues, caseId: string, engine: 'aspen' | 'python'): Errors {
  const e: Errors = {}
  if (!CASE_ID_RE.test(caseId.trim())) e.case_id = 'Case name: letters, digits, "_" or "-" (1-64 characters, starting with a letter or digit).'
  for (const f of FIELDS) {
    const raw = v[f.key]
    if (f.kind === 'bool') continue
    if (f.kind === 'text') { if (String(raw).trim() === '') e[f.key] = 'Required.'; continue }
    const s = String(raw).trim()
    const n = Number(s)
    if (s === '' || !Number.isFinite(n)) { e[f.key] = 'Enter a number.'; continue }
    if (f.min !== undefined && (f.minExcl ? n <= f.min : n < f.min)) e[f.key] = `Must be ${f.minExcl ? '>' : '>='} ${f.min} ${f.unit}.`
    else if (f.max !== undefined && (f.maxExcl ? n >= f.max : n > f.max)) e[f.key] = `Must be ${f.maxExcl ? '<' : '<='} ${f.max} ${f.unit}.`
  }
  if (engine === 'aspen' && !e.reactor_pressure_bar && Number(v.reactor_pressure_bar) < ASPEN_MIN_PRESSURE_BAR) {
    e.reactor_pressure_bar = `The Aspen Plus flowsheet needs at least ${ASPEN_MIN_PRESSURE_BAR} bar at the cracker outlet (pump/pressure-drop chain); use the Python model below ${ASPEN_MIN_PRESSURE_BAR} bar.`
  }
  return e
}

/** Convert validated form values to the CaseInputs payload. Call only when validate() returned no errors. */
export function toInputs(v: FormValues, caseId: string): CaseInputs {
  const out: Record<string, unknown> = { case_id: caseId.trim() }
  for (const f of FIELDS) out[f.key] = f.kind === 'bool' ? Boolean(v[f.key]) : f.kind === 'text' ? String(v[f.key]).trim() : Number(v[f.key])
  return out as unknown as CaseInputs
}
