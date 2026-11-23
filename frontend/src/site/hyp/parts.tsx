import { useMemo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { SourceBadge } from '../../components/ui'
import { fmt } from '../../data/format'
import { useJson } from '../data'
import { HYPOTHESIS_PAGES, hypothesisPath } from '../routes'
import { Callout } from '../ui'
import { frac, srcOf } from './shape'

/* ---- data hooks: every file is read through /api/research/... (LIVE API or the static mirror) ---- */
export interface RRows<R> { rows: R[]; columns: string[]; count: number; source_note?: string }
export const rUrl = (area: string, file: string) => `/api/research/${area}/${file}`
export const useRRows = <R,>(area: string, file: string) => useJson<RRows<R>>(rUrl(area, file))
export const useRJson = <T,>(area: string, file: string) => useJson<T>(rUrl(area, file))

export interface Prov { provenance?: { source_type?: string; generated_utc?: string; script?: string; inputs_summary?: string } }
export interface Assumption { name: string; value: unknown; unit?: string; source_type?: string; source?: string; applicability_note?: string }
export type Row = Record<string, unknown>

/** Source label for a source_type string of the data files; unknown or mixed types are shown as text, never hidden. */
export function SrcTag({ s }: { s: unknown }) {
  const d = srcOf(s)
  if (d) return <SourceBadge source={d} />
  return <span className="badge badge-none" title="Mixed or unlabelled source type in the data file">{typeof s === 'string' && s ? s.slice(0, 40) : 'source not stated'}</span>
}

/** Stored-results statement shown on every Hypotheses page. */
export function StoredNote({ extrapolated = false }: { extrapolated?: boolean }) {
  return (
    <Callout title="Stored results.">
      This page shows stored results of Aspen Plus V15 runs made offline and of the independent Python models; the public site does not run Aspen Plus.
      Every plotted or tabulated value carries its source type: Aspen Plus V15, independent Python model, published literature, or explicit assumption.
      {extrapolated ? <> <strong>Catalyst results at 20 bar are extrapolated beyond the fitted ranges of the rate laws</strong> where the data say so (marked below); they show what the fitted rate laws imply, not measured conversions.</> : null}
    </Callout>
  )
}

export function SubNav({ current }: { current: string }) {
  return (
    <nav className="chip-nav" aria-label="Hypothesis pages">
      {HYPOTHESIS_PAGES.map((p) => (
        <Link key={p.slug} to={hypothesisPath(p.slug)} className={`btn ${p.slug === current ? 'btn-primary' : ''}`} aria-current={p.slug === current ? 'page' : undefined}>{p.label}</Link>
      ))}
    </nav>
  )
}

export interface Col<R> { h: string; cell: (r: R) => ReactNode; right?: boolean; th?: boolean }

/** Plain accessible data table in the site style. */
export function DTable<R>({ caption, cols, rows, keyOf }: { caption: string; cols: Col<R>[]; rows: R[]; keyOf: (r: R, i: number) => string }) {
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label={caption}>
      <table className="data simple">
        <caption>{caption}</caption>
        <thead><tr>{cols.map((c) => <th key={c.h} scope="col" className={c.right ? 'r' : undefined}>{c.h}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={keyOf(r, i)}>{cols.map((c) => (c.th ? <th key={c.h} scope="row">{c.cell(r)}</th> : <td key={c.h} className={c.right ? 'r' : undefined}>{c.cell(r)}</td>))}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Colour-scaled value grid (rows x columns). Colour is never the only carrier: every cell prints its value. */
export function HeatGrid({ title, rowLabel, colLabel, rowKeys, colKeys, value, digits = 2, source, unit, ariaDescription }: {
  title: string; rowLabel: string; colLabel: string; rowKeys: (string | number)[]; colKeys: (string | number)[]
  value: (r: string | number, c: string | number) => number | null; digits?: number; source: unknown; unit: string; ariaDescription: string
}) {
  const all = useMemo(() => rowKeys.flatMap((r) => colKeys.map((c) => value(r, c))).filter((v): v is number => v !== null), [rowKeys, colKeys, value])
  const lo = all.length ? Math.min(...all) : 0, hi = all.length ? Math.max(...all) : 1
  return (
    <figure className="card chart-card" aria-label={title}>
      <figcaption><span>{title}</span><SrcTag s={source} /></figcaption>
      <div className="table-scroll" tabIndex={0} role="region" aria-label={ariaDescription}>
        <table className="data simple hyp-heat">
          <caption className="sr-only">{ariaDescription}</caption>
          <thead><tr><th scope="col">{rowLabel} \ {colLabel}</th>{colKeys.map((c) => <th key={c} scope="col" className="r">{c}</th>)}</tr></thead>
          <tbody>
            {rowKeys.map((r) => (
              <tr key={r}><th scope="row">{r}</th>
                {colKeys.map((c) => {
                  const v = value(r, c)
                  return <td key={c} className="r" style={v === null ? undefined : { background: `color-mix(in srgb, var(--primary) ${Math.round(6 + frac(v, lo, hi) * 48)}%, transparent)` }}>{v === null ? 'n/a' : fmt(v, digits)}</td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">Cell values in {unit}; darker cells are higher values (range {fmt(lo, digits)} to {fmt(hi, digits)}).</p>
    </figure>
  )
}

/** Assumptions register of one area: name, value, unit, source type, source. */
export function AssumptionsTable({ rows, caption, only }: { rows: Assumption[]; caption: string; only?: (a: Assumption) => boolean }) {
  const shown = only ? rows.filter(only) : rows
  return (
    <details className="hyp-details">
      <summary>{caption} ({shown.length} entries)</summary>
      <DTable caption={caption} rows={shown} keyOf={(a) => a.name}
        cols={[
          { h: 'Assumption', cell: (a) => <><code>{a.name}</code>{a.applicability_note ? <div className="muted small">{a.applicability_note}</div> : null}</>, th: true },
          { h: 'Value', cell: (a) => (typeof a.value === 'number' ? fmt(a.value) : typeof a.value === 'string' ? a.value : JSON.stringify(a.value)), right: true },
          { h: 'Unit', cell: (a) => a.unit ?? '' },
          { h: 'Source type', cell: (a) => <SrcTag s={a.source_type} /> },
          { h: 'Source', cell: (a) => <span className="small">{a.source ?? ''}</span> },
        ]} />
    </details>
  )
}

/** Where the numbers on a chart come from: one line with the provenance of the file. */
export function FileNote({ prov, file }: { prov?: Prov['provenance']; file: string }) {
  return (
    <p className="muted small">
      Data file <code>{file}</code>{prov?.generated_utc ? `, generated ${prov.generated_utc.slice(0, 10)}` : ''}{prov?.script ? ` by ${prov.script}` : ''}.
    </p>
  )
}

export const COLORS = ['#38bdf8', '#ff7a3d', '#4ade80', '#f472b6', '#a5b4fc', '#f5b73b', '#22d3ee', '#fbbf24']

/** Share of rows beyond the fitted range, for the extrapolation sentence. */
export function countBeyond(rows: Row[]): number {
  return rows.filter((r) => r.within_fitted_range === false || r.within_fitted_range === 'False').length
}
