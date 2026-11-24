import { useState } from 'react'
import { staticAssetUrl } from '../../api/client'
import { StatusPill } from '../../components/ui'
import { fmt } from '../../data/format'
import { AsyncView } from '../../features/common/Notice'
import { useJson } from '../data'
import { Lightbox } from '../Lightbox'
import { Callout, Section } from '../ui'
import { DTable } from './parts'
import { baseName } from './shape'

const AREA: Record<string, string> = {
  kinetics: 'Kinetics (rate laws against published data)', aspen_kinetic: 'Aspen RPlug kinetic model against Python', catalyst_comparison: 'Catalyst comparison and heat integration',
  economics: 'Singapore techno-economics', purification: 'Purification', enduse: 'End-use comparison', lca: 'Life-cycle assessment',
}
interface FailItem { id: string; description: string; method?: string; reference_source?: string; observed?: unknown; expected?: unknown; tolerance?: unknown; unit?: string }
interface VArea { n_items: number; by_status: { pass: number; fail: number; informational: number; not_available?: number }; file: string; failures: FailItem[]; informational: { id: string; description: string }[] }
interface VSum { areas: Record<string, VArea>; totals: { pass: number; fail: number; informational: number; not_available?: number }; n_items: number }
const val = (v: unknown) => (typeof v === 'number' ? fmt(v, Math.abs(v) < 1 ? 4 : 2) : v === null || v === undefined ? 'n/a' : String(v))

export function ValidationView() {
  const v = useJson<VSum>('/api/research/validation-summary')
  return (
    <Section id="summary" title="Research validation summary" alt
      intro="Each area of the research expansion records its own checks: reproduction of published values, Aspen against Python, balance closures and arithmetic. A check is pass, fail or informational. Failures are listed by name and are not hidden or retuned.">
      <AsyncView a={v} what="the research validation items">{(d) => (
        <>
          <p className="prose-p"><strong>{d.n_items} checks:</strong> {d.totals.pass} pass, {d.totals.fail} fail, {d.totals.informational} informational{d.totals.not_available ? <>, {d.totals.not_available} not available (no experimental data exist; not counted as evidence)</> : null}.</p>
          <DTable caption="Research validation by area" rows={Object.entries(d.areas)} keyOf={([k]) => k}
            cols={[
              { h: 'Area', cell: ([k]) => AREA[k] ?? k, th: true },
              { h: 'Checks', cell: ([, a]) => a.n_items, right: true },
              { h: 'Pass', cell: ([, a]) => <StatusPill kind="ok">{a.by_status.pass}</StatusPill>, right: true },
              { h: 'Fail', cell: ([, a]) => <StatusPill kind={a.by_status.fail ? 'error' : 'neutral'}>{a.by_status.fail}</StatusPill>, right: true },
              { h: 'Informational', cell: ([, a]) => <StatusPill kind="info">{a.by_status.informational}</StatusPill>, right: true },
              ...(d.totals.not_available ? [{ h: 'Not available', cell: ([, a]: [string, VArea]) => <StatusPill kind="neutral">{a.by_status.not_available ?? 0}</StatusPill>, right: true }] : []),
              { h: 'Item file', cell: ([, a]) => <code className="small">{a.file}</code> },
            ]} />
          <h3>Failed checks</h3>
          {Object.entries(d.areas).filter(([, a]) => a.failures.length).length === 0 ? <p className="prose-p">No check failed.</p> : null}
          {Object.entries(d.areas).filter(([, a]) => a.failures.length).map(([k, a]) => (
            <details key={k} className="hyp-details" open>
              <summary>{AREA[k] ?? k}: {a.failures.length} failed</summary>
              <DTable caption={`Failed checks: ${AREA[k] ?? k}`} rows={a.failures} keyOf={(f) => f.id}
                cols={[
                  { h: 'Check', cell: (f) => <><code>{f.id}</code><div className="small">{f.description}</div></>, th: true },
                  { h: 'Observed', cell: (f) => `${val(f.observed)} ${f.unit ?? ''}`, right: true },
                  { h: 'Expected', cell: (f) => `${val(f.expected)} ${f.unit ?? ''}`, right: true },
                  { h: 'Tolerance', cell: (f) => val(f.tolerance), right: true },
                  { h: 'Reference', cell: (f) => <span className="small">{f.reference_source ?? ''}</span> },
                ]} />
            </details>
          ))}
          <h3>Informational checks</h3>
          <p className="prose-p">Informational items record a value or a model difference with no pass or fail criterion.</p>
          {Object.entries(d.areas).filter(([, a]) => a.informational.length).map(([k, a]) => (
            <details key={k} className="hyp-details">
              <summary>{AREA[k] ?? k}: {a.informational.length} informational</summary>
              <ul className="hyp-list">{a.informational.map((i) => <li key={i.id}><code>{i.id}</code> {i.description}</li>)}</ul>
            </details>
          ))}
        </>
      )}</AsyncView>
    </Section>
  )
}

interface Capture { file: string; case_id: string; title: string; what_is_shown: string; navigation_path?: string; aspen_version?: string; visually_verified?: boolean; status?: string }
interface Gallery { aspen_version?: string; note?: string; n_in_manifest: number; captures: Capture[] }

export function AspenGallery() {
  const g = useJson<Gallery>('/api/research/aspen-evidence')
  const [cid, setCid] = useState('all')
  const [openAt, setOpenAt] = useState<number | null>(null)
  return (
    <Section id="gallery" title="Aspen Plus V15 evidence gallery" alt
      intro="Screenshots of the Aspen Plus V15 window taken during the research runs. Each image is a genuine Aspen Plus V15 capture; user and host names are masked. The public site shows them as stored files and does not run Aspen Plus.">
      <AsyncView a={g} what="the Aspen evidence manifest">{(d) => {
        const cases = [...new Set(d.captures.map((c) => c.case_id))]
        const shown = cid === 'all' ? d.captures : d.captures.filter((c) => c.case_id === cid)
        return (
          <>
            <p className="prose-p">{d.captures.length} captures from {cases.length} cases ({d.aspen_version ?? 'Aspen Plus V15'}). {d.captures.filter((c) => c.visually_verified).length} have been inspected by eye and marked as verified in the manifest.</p>
            <div className="hyp-controls">
              <label className="muted" htmlFor="gal-case">Case:</label>
              <select id="gal-case" value={cid} onChange={(e) => setCid(e.target.value)} className="hyp-select">
                <option value="all">All cases ({d.captures.length})</option>
                {cases.map((c) => <option key={c} value={c}>{c} ({d.captures.filter((x) => x.case_id === c).length})</option>)}
              </select>
            </div>
            <p className="muted small">Select a capture to open it at full size with its caption; the left and right arrow keys step through the captures shown.</p>
            <ul className="hyp-gallery">
              {shown.map((c, i) => {
                const url = staticAssetUrl(`/aspen-evidence/${baseName(c.file)}`)
                return (
                  <li key={c.file} className="card">
                    <button type="button" className="hyp-thumb" onClick={() => setOpenAt(i)} aria-label={`Open full size: ${c.title}`}>
                      <img src={url} alt={`${c.title}: ${c.what_is_shown}`} loading="lazy" />
                    </button>
                    <div className="hyp-cap">
                      <strong>{c.title}</strong>
                      <p>{c.what_is_shown}</p>
                      <p className="muted small">Case <code>{c.case_id}</code>{c.navigation_path ? `; ${c.navigation_path}` : ''}</p>
                      <p className="small"><span className="badge badge-aspen_plus_v15">genuine Aspen Plus V15 capture</span> {c.visually_verified ? <StatusPill kind="ok">inspected</StatusPill> : <span className="muted">not yet marked as inspected</span>}</p>
                    </div>
                  </li>
                )
              })}
            </ul>
            <Lightbox index={openAt} onIndex={setOpenAt} onClose={() => setOpenAt(null)}
              items={shown.map((c) => ({
                src: staticAssetUrl(`/aspen-evidence/${baseName(c.file)}`), alt: `${c.title}: ${c.what_is_shown}`, title: c.title,
                caption: <>
                  <p>{c.what_is_shown}</p>
                  <p className="muted small">Case <code>{c.case_id}</code>{c.navigation_path ? `; ${c.navigation_path}` : ''}. File <code>{baseName(c.file)}</code>.</p>
                  <p className="small"><span className="badge badge-aspen_plus_v15">genuine Aspen Plus V15 capture</span> {c.visually_verified ? <StatusPill kind="ok">inspected</StatusPill> : <span className="muted">not yet marked as inspected</span>}</p>
                </>,
              }))} />
            {d.note ? <Callout>{d.note}</Callout> : null}
          </>
        )
      }}</AsyncView>
    </Section>
  )
}
