import type { SourceLabel } from '../sim'
import { compareRows, formatDiff, formatValue, SOURCE_HELP, SOURCE_TEXT, type CaseResult, type OutRow } from './model'
import type { Fact } from './pfdData'

export function SimBadge({ s }: { s: SourceLabel | null }) {
  if (!s) return <span className="badge sim-badge src-none" title="The browser model does not compute this value">not modelled</span>
  return <span className={`badge sim-badge src-${s}`} title={SOURCE_HELP[s]}>{SOURCE_TEXT[s]}</span>
}

/** One row value: number with unit, or "not modelled" with the reason. */
function Val({ r }: { r: Pick<OutRow, 'value' | 'kind' | 'unit' | 'note'> }) {
  return r.value === null ? <span className="sim-nm" title={r.note}>not modelled</span> : <span className="sim-num">{formatValue(r)}</span>
}

const HEADLINE = ['conversion', 'h2_kg_h', 'lcoh_SGD', 'carbon_intensity']

export function KpiStrip({ c }: { c: CaseResult }) {
  return (
    <div className="sim-kpis" aria-live="polite" aria-label="Key results">
      {HEADLINE.map((k) => {
        const r = c.rows.find((x) => x.key === k)!
        return (
          <div key={k} className="sim-kpi" data-kpi={k}>
            <span className="sim-kpi-l">{r.label}</span>
            <span className="sim-kpi-v"><Val r={r} /></span>
            <SimBadge s={r.source} />
          </div>
        )
      })}
    </div>
  )
}

export function OutputList({ b, a }: { b: CaseResult; a: CaseResult | null }) {
  if (!a) {
    return (
      <dl className="sim-out" aria-label="Live outputs">
        {b.rows.map((r) => (
          <div key={r.key} className="sim-out-row" data-out={r.key}>
            <dt>{r.label}{r.kind === 'frac' || r.value === null ? '' : ''}</dt>
            <dd><Val r={r} /> <SimBadge s={r.source} />{r.value === null && r.note ? <span className="sim-why">{r.note.replace(/^not modelled: /, '')}</span> : null}</dd>
          </div>
        ))}
      </dl>
    )
  }
  const rows = compareRows(a.rows, b.rows)
  return (
    <div className="sim-cmp-wrap">
      <table className="sim-cmp" aria-label="Outputs of case A and case B">
        <thead><tr><th scope="col">Output</th><th scope="col">Case A (pinned)</th><th scope="col">Case B (current)</th><th scope="col">B - A</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} data-out={r.key}>
              <th scope="row">{r.label}</th>
              <td><Val r={r.a} /><br /><SimBadge s={r.a.source} /></td>
              <td><Val r={r.b} /><br /><SimBadge s={r.b.source} /></td>
              <td className="sim-num">{formatDiff(r)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function FactList({ facts }: { facts: Fact[] }) {
  if (!facts.length) return <p className="muted small">No computed values for this item.</p>
  return (
    <dl className="sim-facts">
      {facts.map((f, i) => (
        <div key={`${f.label}-${i}`}>
          <dt>{f.label}</dt>
          <dd>{f.value === null || !Number.isFinite(f.value) ? <span className="sim-nm">not modelled</span> : <span className="sim-num">{formatValue({ value: f.value, kind: f.frac ? 'frac' : 'num', unit: f.unit })}</span>} <SimBadge s={f.value === null ? null : f.source} /></dd>
        </div>
      ))}
    </dl>
  )
}
