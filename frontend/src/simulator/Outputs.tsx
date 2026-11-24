import type { SourceLabel } from '../sim'
import { compareRows, costBreakdown, formatDiff, formatValue, SOURCE_HELP, SOURCE_SHORT, SOURCE_TEXT, type CaseResult, type OutRow } from './model'
import type { Fact } from './pfdData'

export function SimBadge({ s, short = false }: { s: SourceLabel | null; short?: boolean }) {
  if (!s) return <span className="badge sim-badge src-none" title="The browser model does not compute this value">not modelled</span>
  if (short) return <span className={`badge sim-badge src-${s}`} title={`${SOURCE_TEXT[s]}: ${SOURCE_HELP[s]}`}><span aria-hidden="true">{SOURCE_SHORT[s]}</span><span className="sr-only">{SOURCE_TEXT[s]}</span></span>
  return <span className={`badge sim-badge src-${s}`} title={SOURCE_HELP[s]}>{SOURCE_TEXT[s]}</span>
}

/** Selected output rows of a case as a short list (tour cards). A key without a row shows "not modelled". */
export function OutputValueList({ c, keys }: { c: CaseResult; keys: string[] }) {
  return (
    <dl className="sim-facts">
      {keys.map((k) => {
        const r = c.rows.find((x) => x.key === k)
        return (
          <div key={k} data-row={k}>
            <dt>{r?.label ?? k}</dt>
            <dd>{r ? <Val r={r} /> : <span className="sim-nm">not modelled</span>} <SimBadge s={r?.source ?? null} /></dd>
          </div>
        )
      })}
    </dl>
  )
}

/** One row value: number with unit, or "not modelled" with the reason. */
function Val({ r }: { r: Pick<OutRow, 'value' | 'kind' | 'unit' | 'note'> }) {
  return r.value === null ? <span className="sim-nm" title={r.note}>{r.note?.startsWith('not reached') ? 'not reached' : 'not modelled'}</span> : <span className="sim-num">{formatValue(r)}</span>
}

/** Headline outputs with short card labels; the full row label (with the cost basis) is in the title and the output list. */
export const HEADLINE: { key: string; short: string }[] = [
  { key: 'conversion', short: 'NH3 conversion' }, { key: 'h2_kg_h', short: 'Hydrogen production' },
  { key: 'lcoh_SGD', short: 'Hydrogen cost' }, { key: 'carbon_intensity', short: 'Carbon intensity' },
]

export function KpiStrip({ c }: { c: CaseResult }) {
  return (
    <div className="sim-kpis" aria-live="polite" aria-label="Key results">
      {HEADLINE.map(({ key: k, short }) => {
        const r = c.rows.find((x) => x.key === k)!
        return (
          <div key={k} className="sim-kpi" data-kpi={k} title={r.label}>
            <span className="sim-kpi-l">{short}</span>
            <span className="sim-kpi-v"><Val r={r} /></span>
            <SimBadge s={r.source} short />
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

const COST_COLORS: Record<string, string> = {
  ammonia_feed: 'var(--c-nh3)', capex: 'var(--primary)', fixed_opex: 'var(--c-n2)', heat_fuel: 'var(--c-o2)', catalyst: 'var(--accent)',
  electricity: 'var(--c-h2)', cooling_water: 'var(--c-cold)', carbon_tax: 'var(--muted)',
}

/** Stacked bar and table of the cost components (feed, capital, fixed opex, heat fuel, catalyst, electricity, cooling water, carbon) of
 * the same evaluate call as the headline cost. Case A is added as a column when pinned. */
export function CostBreakdown({ b, a, cur }: { b: CaseResult; a: CaseResult | null; cur: 'USD' | 'SGD' }) {
  const pb = costBreakdown(b.out)
  const pa = a ? costBreakdown(a.out) : null
  if (!pb) return <p className="sim-nm-block">Cost breakdown: not modelled outside the stored process grid or with the membrane selected.</p>
  const val = (p: { usd: number; sgd: number }) => (cur === 'SGD' ? p.sgd : p.usd)
  const fmtc = (v: number) => (v !== 0 && Math.abs(v) < 0.0005 ? v.toExponential(1) : v.toFixed(3))
  const total = pb.reduce((x, p) => x + val(p), 0)
  return (
    <div className="sim-cost" data-testid="cost-breakdown">
      <div className="sim-cost-bar" role="img" aria-label={`Cost of ${total.toFixed(3)} ${cur} per kg hydrogen by component: ${pb.map((p) => `${p.label} ${(p.share * 100).toFixed(1)} %`).join(', ')}`}>
        {pb.filter((p) => p.share > 0).map((p) => <span key={p.key} style={{ width: `${p.share * 100}%`, background: COST_COLORS[p.key] }} title={`${p.label}: ${fmtc(val(p))} ${cur}/kg (${(p.share * 100).toFixed(1)} %)`} />)}
      </div>
      <table className="sim-cmp sim-cost-t" aria-label="Cost breakdown per kg of hydrogen">
        <thead><tr><th scope="col">Component</th><th scope="col">{cur}/kg H2</th><th scope="col">Share</th>{pa ? <th scope="col">Case A, {cur}/kg</th> : null}</tr></thead>
        <tbody>
          {pb.map((p, i) => (
            <tr key={p.key} data-cost={p.key}>
              <th scope="row"><i className="sim-cost-sw" style={{ background: COST_COLORS[p.key] }} aria-hidden="true" />{p.label}</th>
              <td className="sim-num">{fmtc(val(p))}</td><td className="sim-num">{(p.share * 100).toFixed(1)} %</td>
              {pa ? <td className="sim-num">{fmtc(val(pa[i]))}</td> : null}
            </tr>
          ))}
          <tr className="sim-cost-total"><th scope="row">Total (LCOH)</th><td className="sim-num">{fmtc(total)}</td><td className="sim-num">100 %</td>{pa ? <td className="sim-num">{fmtc(pa.reduce((x, p) => x + val(p), 0))}</td> : null}</tr>
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
