import { Link } from 'react-router-dom'
import { GITHUB_URL } from '../../api/url'
import { staticAssetUrl } from '../../api/client'
import { StatusPill } from '../../components/ui'
import { AsyncView } from '../../features/common/Notice'
import { useJson } from '../data'
import { ExtLink } from '../ui'
import { DTable, SrcTag } from './parts'
import { baseName, list, safeRepoPath, show, verdictKind } from './shape'

type Obj = Record<string, unknown>
interface Finding { quantity?: unknown; value?: unknown; unit?: unknown; source_type?: unknown; source_file?: unknown; key?: unknown }
interface MatrixRow extends Obj { row_id?: string; numerical_findings?: Finding[]; links?: { data?: unknown[]; figures?: unknown[]; screenshots?: unknown[] }; literature?: unknown[]; case_ids?: unknown[] }
interface Hypothesis extends Obj { id?: string; statement?: string; verdict?: string; verdict_conditions?: unknown; summary?: unknown; rows?: MatrixRow[] }
interface Matrix { provenance?: Obj; hypotheses?: Hypothesis[] }

const kindOf = (v: unknown) => verdictKind(v)
const verdictText = (v: unknown) => (typeof v === 'string' && v ? v.toUpperCase() : 'NO VERDICT')

export function useMatrix2() { return useJson<Matrix>('/api/research/evidence-matrix') }

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

function RowView({ row }: { row: MatrixRow }) {
  const findings = Array.isArray(row.numerical_findings) ? row.numerical_findings : []
  const figs = (row.links?.figures ?? []).map(safeRepoPath).filter((p): p is string => p !== null && p.toLowerCase().endsWith('.png'))
  const shots = (row.links?.screenshots ?? []).map(safeRepoPath).filter((p): p is string => p !== null && p.toLowerCase().endsWith('.png'))
  return (
    <details className="hyp-details hyp-row" id={row.row_id ? `row-${row.row_id}` : undefined}>
      <summary><strong>{show(row.row_id)}</strong> {show(row.sub_claim)}</summary>
      <div className="hyp-row-body">
        <dl className="hyp-dl">
          {([['Singapore scenario', row.singapore_scenario], ['Aspen model', row.aspen_model], ['Python model', row.python_model], ['Case ids', row.case_ids], ['Validation method', row.validation_method], ['Uncertainty range', row.uncertainty_range]] as [string, unknown][])
            .filter(([, v]) => show(v)).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{show(v)}</dd></div>)}
        </dl>
        {list(row.input_assumptions).length ? <><h5>Input assumptions</h5><ul className="hyp-list">{list(row.input_assumptions).map((a, i) => <li key={i}>{a}</li>)}</ul></> : null}
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
        {list(row.limitations).length ? <><h5>Limitations</h5><ul className="hyp-list">{list(row.limitations).map((a, i) => <li key={i}>{a}</li>)}</ul></> : null}
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

export function EvidenceMatrix() {
  const m = useMatrix2()
  return (
    <AsyncView a={m} what="The evidence matrix (results/research/evidence_matrix.json)">{(d) => {
      const hs = Array.isArray(d.hypotheses) ? d.hypotheses : []
      if (!hs.length) return <p className="prose-p">The evidence matrix file is present but lists no hypotheses.</p>
      return (
        <>
          <div className="grid-2s hyp-verdicts" role="list" aria-label="Verdict per hypothesis">
            {hs.map((h) => (
              <a key={h.id} href={`#/hypotheses#${h.id}`} className="card tile hyp-verdict" role="listitem" onClick={(e) => { e.preventDefault(); document.getElementById(String(h.id))?.scrollIntoView({ block: 'start' }) }}>
                <h3>{h.id} <StatusPill kind={kindOf(h.verdict)}>{verdictText(h.verdict)}</StatusPill></h3>
                <p>{show(h.statement)}</p>
              </a>
            ))}
          </div>
          {hs.map((h) => (
            <article key={h.id} id={String(h.id)} className="card hyp-card">
              <header>
                <h3>{h.id}: {show(h.statement)}</h3>
                <StatusPill kind={kindOf(h.verdict)}>{verdictText(h.verdict)}</StatusPill>
              </header>
              {show(h.verdict_conditions) ? <p><strong>Conditions of the verdict.</strong> {show(h.verdict_conditions)}</p> : null}
              {show(h.summary) ? <p>{show(h.summary)}</p> : null}
              {(h.rows ?? []).map((r, i) => <RowView key={`${r.row_id ?? i}`} row={r} />)}
            </article>
          ))}
          {d.provenance ? <details className="hyp-details"><summary>Matrix provenance (generator, inputs, checksums)</summary><p className="muted small" style={{ padding: '0 16px', overflowWrap: 'anywhere' }}>{show(d.provenance)}</p></details> : null}
        </>
      )
    }}</AsyncView>
  )
}
