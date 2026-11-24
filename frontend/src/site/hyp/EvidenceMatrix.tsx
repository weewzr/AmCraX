import { Link } from 'react-router-dom'
import { GITHUB_URL } from '../../api/url'
import { staticAssetUrl } from '../../api/client'
import { AsyncView } from '../../features/common/Notice'
import { useJson } from '../data'
import { Callout, ExtLink } from '../ui'
import { DTable, SrcTag } from './parts'
import { VerdictChip, WhatChanged } from './phase2'
import { baseName, list, normVerdict, qualifierOf, safeRepoPath, show, thresholdSummary } from './shape'

type Obj = Record<string, unknown>
interface Finding { quantity?: unknown; value?: unknown; unit?: unknown; source_type?: unknown; source_file?: unknown; key?: unknown }
interface MatrixRow extends Obj { row_id?: string; role?: string; component?: string; verdict?: string; verdict_v1?: string; verdict_by_mode?: Obj; numerical_findings?: Finding[]; links?: { data?: unknown[]; figures?: unknown[]; screenshots?: unknown[] }; literature?: unknown[]; case_ids?: unknown[] }
interface Component extends Obj { id?: string; title?: string; verdict?: string; primary_rows?: unknown[]; secondary_rows?: unknown[]; envelope?: unknown; note?: unknown }
interface Hypothesis extends Obj { id?: string; statement?: string; verdict?: string; verdict_v1?: string; primary_hypothesis?: unknown; components?: Component[]; strongest_defensible_statement?: unknown; findings_against_essay?: unknown; cross_claim?: unknown; verdict_conditions?: unknown; summary?: unknown; rows?: MatrixRow[] }
export interface Matrix { provenance?: Obj; hypotheses?: Hypothesis[]; methodology_version?: number; methodology?: string }

export function useMatrix2() { return useJson<Matrix>('/api/research/evidence-matrix') }

/** The v1 verdict of a hypothesis: the stored `verdict_v1` of a v2 file, or the verdict itself in a v1 file. */
export function v1Of(h: Hypothesis, version: unknown): unknown {
  return h.verdict_v1 ?? (version === 2 ? undefined : h.verdict)
}

function RepoLinks({ label, paths }: { label: string; paths: unknown[] }) {
  const ok = paths.map(safeRepoPath).filter((p): p is string => p !== null)
  if (!ok.length) return null
  return (
    <p className="small"><strong>{label}:</strong>{' '}
      {ok.map((p, i) => <span key={p}>{i > 0 ? ', ' : ''}<ExtLink href={`${GITHUB_URL}/blob/main/${p}`}><code>{p}</code></ExtLink></span>)}
    </p>
  )
}

function Literature({ items }: { items: unknown[] }) {
  if (!items.length) return null
  return (
    <p className="small"><strong>Literature:</strong>{' '}
      {items.map((it, i) => {
        const o = (typeof it === 'object' && it !== null ? it : { key: it }) as Obj
        const key = show(o.key ?? o.ref ?? o.citekey ?? '')
        const label = show(o.label ?? o.short ?? '')
        return <span key={`${key}${i}`}>{i > 0 ? '; ' : ''}{key ? <Link to={{ pathname: '/research', hash: `#ref-${key}` }}>{label || key}</Link> : label}{key && label ? <span className="muted"> [{key}]</span> : null}</span>
      })}
    </p>
  )
}

function HList({ title, v }: { title: string; v: unknown }) {
  const xs = list(v)
  return xs.length ? <><h5>{title}</h5><ul className="hyp-list">{xs.map((a, i) => <li key={i}>{a}</li>)}</ul></> : null
}

/** Row threshold: the parameter, then any lists of findings ({quantity, value, unit, source_type}) as tables, other keys as text. */
function Threshold({ t, id }: { t: unknown; id: string }) {
  if (t === null || t === undefined || t === '') return null
  if (typeof t !== 'object' || Array.isArray(t)) return <p><strong>Threshold.</strong> {show(t)}</p>
  const o = t as Obj
  const isFindings = (v: unknown): v is Finding[] => Array.isArray(v) && v.length > 0 && v.every((x) => x && typeof x === 'object' && 'value' in (x as Obj))
  const tables = Object.entries(o).filter(([, v]) => isFindings(v)) as [string, Finding[]][]
  const rest = Object.entries(o).filter(([, v]) => !isFindings(v))
  return (
    <div>
      <p><strong>Threshold.</strong> {rest.map(([k, v], i) => <span key={k}>{i > 0 ? '; ' : ''}{k === 'parameter' ? '' : `${k.replace(/_/g, ' ')}: `}{show(v)}</span>)}</p>
      {tables.map(([k, fs]) => (
        <details key={k} className="hyp-details"><summary>Threshold values of {id}: {k.replace(/_/g, ' ')} ({fs.length})</summary>
          <DTable caption={`Threshold values of ${id} (${k})`} rows={fs} keyOf={(_, i) => String(i)}
            cols={[
              { h: 'Quantity', cell: (f) => show(f.quantity), th: true },
              { h: 'Value', cell: (f) => <>{show(f.value)}{show(f.unit) ? <span className="unit"> {show(f.unit)}</span> : null}</>, right: true },
              { h: 'Source type', cell: (f) => <SrcTag s={f.source_type} /> },
              { h: 'Key', cell: (f) => <code className="small">{show(f.key)}</code> },
            ]} />
        </details>
      ))}
    </div>
  )
}

function RowView({ row }: { row: MatrixRow }) {
  const findings = Array.isArray(row.numerical_findings) ? row.numerical_findings : []
  const figs = (row.links?.figures ?? []).map(safeRepoPath).filter((p): p is string => p !== null && p.toLowerCase().endsWith('.png'))
  const shots = (row.links?.screenshots ?? []).map(safeRepoPath).filter((p): p is string => p !== null && p.toLowerCase().endsWith('.png'))
  const modes = row.verdict_by_mode && typeof row.verdict_by_mode === 'object' ? Object.entries(row.verdict_by_mode) : []
  return (
    <details className="hyp-details hyp-row" id={row.row_id ? `row-${row.row_id}` : undefined}>
      <summary>
        <strong>{show(row.row_id)}</strong>{row.role ? <span className="muted small"> ({show(row.role)}{row.component ? `, component ${show(row.component)}` : ''})</span> : null}{' '}
        {row.verdict ? <VerdictChip v={row.verdict} small /> : null}{row.verdict_v1 ? <span className="muted small"> v1: {show(row.verdict_v1)}</span> : null}{' '}
        {show(row.sub_claim)}
      </summary>
      <div className="hyp-row-body">
        {modes.length ? (
          <p data-testid={`modes-${show(row.row_id)}`}><strong>Verdict by carbon-pricing mode.</strong>{' '}
            {modes.map(([m, v], i) => <span key={m}>{i > 0 ? '; ' : ''}{m === 'actual_sg' ? 'actual Singapore boundary' : m === 'hypothetical_lca' ? 'hypothetical life-cycle price (not Singapore law)' : m}: <VerdictChip v={v} small /></span>)}
            {' '}The verdict that votes is the actual-boundary one.</p>
        ) : null}
        <Threshold t={row.threshold} id={show(row.row_id)} />
        <dl className="hyp-dl">
          {([['Envelope', row.envelope], ['Uncertainty', row.uncertainty ?? row.uncertainty_range], ['Evidence kinds', row.evidence_kinds], ['Validation status', row.validation_status], ['Singapore scenario', row.singapore_scenario], ['Aspen model', row.aspen_model], ['Python model', row.python_model], ['Case ids', row.case_ids], ['Validation method', row.validation_method]] as [string, unknown][])
            .filter(([, v]) => show(v)).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{show(v)}</dd></div>)}
        </dl>
        <HList title="Numerical conclusions" v={row.numerical_conclusions} />
        <HList title="Assumptions" v={row.assumptions ?? row.input_assumptions} />
        <Literature items={Array.isArray(row.literature) ? row.literature : []} />
        {findings.length ? (
          <DTable caption={`Numerical findings of ${show(row.row_id)}`} rows={findings} keyOf={(_, i) => String(i)}
            cols={[
              { h: 'Quantity', cell: (f) => show(f.quantity), th: true },
              { h: 'Value', cell: (f) => <>{show(f.value)}{show(f.unit) ? <span className="unit"> {show(f.unit)}</span> : null}</>, right: true },
              { h: 'Source type', cell: (f) => <SrcTag s={f.source_type} /> },
              { h: 'File and key', cell: (f) => <span className="small"><code>{show(f.source_file)}</code>{show(f.key) ? <> / <code>{show(f.key)}</code></> : null}</span> },
            ]} />
        ) : null}
        <HList title="Limitations" v={row.limitations} />
        {show(row.conclusion) ? <p><strong>Conclusion.</strong> {show(row.conclusion)}{show(row.conclusion_conditions) ? <> <span className="muted">Conditions: {show(row.conclusion_conditions)}</span></> : null}</p> : null}
        <RepoLinks label="Data" paths={row.links?.data ?? []} />
        <RepoLinks label="Figures" paths={row.links?.figures ?? []} />
        <RepoLinks label="Screenshots" paths={row.links?.screenshots ?? []} />
        {figs.length ? <div className="hyp-thumbs">{figs.map((p) => <a key={p} href={staticAssetUrl(`/research-figures/${baseName(p)}`)} target="_blank" rel="noopener noreferrer"><img src={staticAssetUrl(`/research-figures/${baseName(p)}`)} alt={`Figure ${baseName(p)}`} loading="lazy" /></a>)}</div> : null}
        {shots.length ? <p className="small">Genuine Aspen Plus V15 captures for this row: <Link to="/hypotheses/aspen-evidence">open the gallery</Link> ({shots.map(baseName).join(', ')}).</p> : null}
        {show(row.provenance) ? <p className="muted small">Provenance: {show(row.provenance)}</p> : null}
      </div>
    </details>
  )
}

/** Component verdict chips of a hypothesis, printed beside the hypothesis verdict (a bare PARTIALLY SUPPORTED is never shown alone). */
function ComponentChips({ h }: { h: Hypothesis }) {
  const cs = Array.isArray(h.components) ? h.components : []
  if (!cs.length) return null
  return (
    <p className="small hyp-comp-chips" data-testid={`components-${show(h.id)}`}>Components:{' '}
      {cs.map((c, i) => <span key={`${show(c.id)}${i}`}>{i > 0 ? '; ' : ''}<strong>{show(c.id)}</strong> <VerdictChip v={c.verdict} small /></span>)}
    </p>
  )
}

/** The matrix's own qualifier sentence of the hypothesis verdict (first sentence of its summary, when it starts with the verdict). */
function Qualifier({ h }: { h: Hypothesis }) {
  const q = qualifierOf(h.summary, h.verdict)
  return q ? <p className="small" data-testid={`qualifier-${show(h.id)}`}><strong>Qualifier (from the matrix).</strong> {q}</p> : null
}

const fmtV = (v: number) => String(Number(v.toPrecision(3)))
/** Rows whose verdict differs from version 1 (moved after the independent review): their threshold is the finding. */
function MovedRows({ h }: { h: Hypothesis }) {
  const rows = (h.rows ?? []).filter((r) => r.verdict_v1 && normVerdict(r.verdict) !== normVerdict(r.verdict_v1))
  if (!rows.length) return null
  return (
    <div className="p2-against" data-testid={`moved-${show(h.id)}`}>
      <strong>Rows that changed after the independent adversarial review; the threshold is the finding.</strong>
      <ul className="hyp-list">
        {rows.map((r) => {
          const t = thresholdSummary(r.threshold)
          return (
            <li key={show(r.row_id)} data-testid={`threshold-${show(r.row_id)}`}>
              <a href={`#row-${show(r.row_id)}`}><strong>{show(r.row_id)}</strong></a> <VerdictChip v={r.verdict} small /> <span className="muted small">v1: {show(r.verdict_v1)}</span>.{' '}
              {t ? <>Threshold: {t.parameter}: computed {t.computed![1] !== t.computed![0] ? `values span ${fmtV(t.computed![0])} to ${fmtV(t.computed![1])}` : fmtV(t.computed![0])}{t.unit ? ` ${t.unit}` : ''}{t.sourced ? <>; sourced values {fmtV(t.sourced[0])} to {fmtV(t.sourced[1])}{t.unit ? ` ${t.unit}` : ''}</> : null}{t.comparison ? ` (comparison: ${t.comparison})` : ''}. </> : null}
              {show(r.conclusion)}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/** Matrix provenance disclosures (what was fixed before the analyses, what was not, the review that moved three rows), as stored. */
function Disclosures({ p }: { p: Obj | undefined }) {
  const ds = list(p?.disclosures)
  if (!ds.length && !show(p?.fix_pass)) return null
  return (
    <Callout kind="warn" title="How the verdicts were set (matrix provenance).">
      <div data-testid="matrix-disclosures">
        <ul className="hyp-list">{ds.map((x, i) => <li key={i}>{x}</li>)}</ul>
        {show(p?.fix_pass) ? <p className="small">Fix pass: {show(p?.fix_pass)}</p> : null}
      </div>
    </Callout>
  )
}

function Components({ h }: { h: Hypothesis }) {
  const cs = Array.isArray(h.components) ? h.components : []
  if (!cs.length) return null
  return (
    <DTable caption={`Components of ${show(h.id)} and their verdicts`} rows={cs} keyOf={(c, i) => `${show(c.id)}${i}`}
      cols={[
        { h: 'Component', cell: (c) => <><strong>{show(c.id)}</strong> {show(c.title)}</>, th: true },
        { h: 'Verdict', cell: (c) => <VerdictChip v={c.verdict} small /> },
        { h: 'Primary rows', cell: (c) => list(c.primary_rows).map((r, i) => <span key={r}>{i > 0 ? ', ' : ''}<a href={`#row-${r}`}>{r}</a></span>) },
        { h: 'Secondary rows', cell: (c) => list(c.secondary_rows).join(', ') || 'none' },
        { h: 'Envelope', cell: (c) => <span className="small">{show(c.envelope)}</span>, wide: true },
        { h: 'Note', cell: (c) => <span className="small">{show(c.note)}</span> },
      ]} />
  )
}

function RowGroups({ rows }: { rows: MatrixRow[] }) {
  const hasRole = rows.some((r) => r.role)
  if (!hasRole) return <>{rows.map((r, i) => <RowView key={`${r.row_id ?? i}`} row={r} />)}</>
  const prim = rows.filter((r) => String(r.role).toLowerCase() === 'primary'), sec = rows.filter((r) => String(r.role).toLowerCase() !== 'primary')
  return (
    <>
      <h4>Primary rows (they vote)</h4>
      {prim.map((r, i) => <RowView key={`${r.row_id ?? i}`} row={r} />)}
      {sec.length ? <><h4>Secondary rows (reported, they do not vote)</h4>{sec.map((r, i) => <RowView key={`${r.row_id ?? i}`} row={r} />)}</> : null}
    </>
  )
}

export function EvidenceMatrix() {
  const m = useMatrix2()
  return (
    <AsyncView a={m} what="The evidence matrix (results/research/evidence_matrix.json)">{(d) => {
      const hs = Array.isArray(d.hypotheses) ? d.hypotheses : []
      if (!hs.length) return <p className="prose-p">The evidence matrix file is present but lists no hypotheses.</p>
      const v2 = d.methodology_version === 2
      const meth = safeRepoPath(d.methodology) ?? 'docs/research/verdict_methodology_v2.md'
      return (
        <>
          <p className="prose-p" data-testid="matrix-version">
            {v2 ? <>Verdicts follow methodology version 2 (<ExtLink href={`${GITHUB_URL}/blob/main/${meth}`}><code>{meth}</code></ExtLink>). What of it was fixed before the analyses and what was not is stated below. The version 1 verdict is shown beside each one.</>
              : <>This matrix file was written under methodology version 1 (every hypothesis verdict from all of its rows). The version 2 rule is in <ExtLink href={`${GITHUB_URL}/blob/main/${meth}`}><code>{meth}</code></ExtLink>; the version 2 matrix replaces this file when it is generated.</>}
            {' '}Verdict words: SUPPORTED, CONTRADICTED, MIXED, PARTIALLY SUPPORTED, INCONCLUSIVE. Each chip prints its word; colour is not the only carrier.
          </p>
          <Disclosures p={d.provenance} />
          <div className="grid-2s hyp-verdicts" role="list" aria-label="Verdict per hypothesis">
            {hs.map((h) => (
              <a key={h.id} href={`#/hypotheses#${h.id}`} className="card tile hyp-verdict" role="listitem" data-testid={`verdict-${h.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(String(h.id))?.scrollIntoView({ block: 'start' }) }}>
                <h3>{h.id} <VerdictChip v={h.verdict} /></h3>
                {v2 ? <p className="small muted">Version 1 verdict: {show(v1Of(h, d.methodology_version)) || 'not stored'}</p> : null}
                <ComponentChips h={h} />
                <Qualifier h={h} />
                <p>{show(h.primary_hypothesis ?? h.statement)}</p>
              </a>
            ))}
          </div>
          {hs.map((h) => (
            <article key={h.id} id={String(h.id)} className="card hyp-card">
              <header>
                <h3>{h.id}: {show(h.statement)}</h3>
                <span><VerdictChip v={h.verdict} />{v2 ? <span className="muted small"> v1: {show(v1Of(h, d.methodology_version)) || 'not stored'}</span> : null}</span>
              </header>
              <ComponentChips h={h} />
              <Qualifier h={h} />
              {show(h.primary_hypothesis) ? <p><strong>Primary hypothesis.</strong> {show(h.primary_hypothesis)}</p> : null}
              <Components h={h} />
              <MovedRows h={h} />
              {show(h.strongest_defensible_statement) ? <p className="p2-strongest"><strong>Strongest defensible statement.</strong> {show(h.strongest_defensible_statement)}</p> : null}
              {list(h.findings_against_essay).length ? <div className="p2-against"><strong>Findings against the essay.</strong><ul className="hyp-list">{list(h.findings_against_essay).map((x, i) => <li key={i}>{x}</li>)}</ul></div> : null}
              {show(h.cross_claim) ? <p><strong>Cross-claim.</strong> {show(h.cross_claim)}</p> : null}
              {show(h.verdict_v1_rule_on_current_rows) ? <p className="muted small">Version 1 rule applied to the current rows: {show(h.verdict_v1_rule_on_current_rows)}</p> : null}
              {show(h.verdict_conditions) ? <p><strong>Conditions of the verdict.</strong> {show(h.verdict_conditions)}</p> : null}
              {show(h.summary) ? <p>{show(h.summary)}</p> : null}
              <RowGroups rows={h.rows ?? []} />
            </article>
          ))}
          <WhatChanged />
          {d.provenance ? <details className="hyp-details"><summary>Matrix provenance (generator, inputs, checksums)</summary><p className="muted small" style={{ padding: '0 16px', overflowWrap: 'anywhere' }}>{show(d.provenance)}</p></details> : null}
        </>
      )
    }}</AsyncView>
  )
}
