import type { ReactNode } from 'react'
import type { DataSource } from '../api/types'
import { fmt, NA } from '../data/format'

const LABEL: Record<DataSource, string> = {
  aspen_plus_v15: 'Aspen Plus V15',
  python_model: 'Python model',
  literature: 'Literature',
  assumption: 'Assumption',
  demo: 'ILLUSTRATIVE',
}

export function SourceBadge({ source }: { source: DataSource | null | undefined }) {
  if (!source) return <span className="badge badge-none" title="No provenance available">no source</span>
  return (
    <span className={`badge badge-${source}`} title={`Data source: ${source}`}>
      {LABEL[source]}
    </span>
  )
}

interface ValueProps {
  v: number | null | undefined
  unit?: string
  digits?: number
  source: DataSource | null | undefined
  /** hide the badge when provenance is shown once for a whole group (e.g. the PFD header) */
  showSource?: boolean
}

/** Every number shown to a user goes through this component: unit + provenance, "n/a" for null. */
export function Value({ v, unit, digits, source, showSource = true }: ValueProps) {
  const na = v === null || v === undefined || !Number.isFinite(v)
  return (
    <span className="value" title={source ? `Source: ${source}` : undefined}>
      <span className={na ? 'num na' : 'num'}>{na ? NA : fmt(v, digits)}</span>
      {!na && unit ? <span className="unit">{unit}</span> : null}
      {showSource ? <SourceBadge source={source} /> : null}
    </span>
  )
}

export type StatusKind = 'ok' | 'warn' | 'error' | 'info' | 'neutral'
const ICON: Record<StatusKind, string> = { ok: '\u2713', warn: '\u26A0', error: '\u2717', info: 'i', neutral: '\u2013' }

/** Status is never colour-only: icon + text. */
export function StatusPill({ kind, children }: { kind: StatusKind; children: ReactNode }) {
  return (
    <span className={`pill pill-${kind}`}>
      <span aria-hidden="true">{ICON[kind]}</span> {children}
    </span>
  )
}

interface KpiProps { label: string; v: number | null | undefined; unit?: string; digits?: number; source: DataSource | null | undefined; hint?: string }
export function KpiTile({ label, v, unit, digits, source, hint }: KpiProps) {
  return (
    <div className="kpi card" title={hint}>
      <div className="kpi-label">{label}</div>
      <Value v={v} unit={unit} digits={digits} source={source} showSource={false} />
      <div className="kpi-src"><SourceBadge source={source} /></div>
    </div>
  )
}
