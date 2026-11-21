/** Number formatting. Null/undefined/NaN always yield "n/a" - never a made-up fallback. */
export const NA = 'n/a'

export function fmt(v: number | null | undefined, digits?: number): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return NA
  let d = digits
  if (d === undefined) {
    const a = Math.abs(v)
    d = a === 0 ? 0 : a >= 1000 ? 0 : a >= 100 ? 1 : a >= 1 ? 2 : a >= 0.01 ? 3 : 4
  }
  return v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  return v === null || v === undefined || !Number.isFinite(v) ? NA : `${(v * 100).toFixed(digits)} %`
}
