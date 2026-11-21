import { useState } from 'react'
import '../features/common/features.css'
import '../features/reports/reports.css'
import { assetUrl, fetchFigures, fetchRefs, fetchReports, fetchShots, fetchTrace, type ReportItem } from '../api/reports'
import { GITHUB_URL, IS_PAGES } from '../api/url'
import { downloadByKey, downloadUrl } from '../site/downloads'
import { StatusPill } from '../components/ui'
import { useData } from '../data/DataContext'
import { AsyncView, ModeGate, Notice } from '../features/common/Notice'
import { useAsync } from '../features/common/useAsync'
import { ClampCell } from '../features/common/ClampCell'
import { doiLink, fmtBytes, groupFigures, groupReports, limitationsText, REPRODUCE_STEPS } from '../features/reports/shape'

/** Static site: the deliverables copied by scripts/prepare_site.mjs are downloadable; everything else points at the repository. Local snapshot: needs the API. */
function SnapshotReportLink({ r }: { r: ReportItem }) {
  if (!IS_PAGES) return <span title="Needs the live API">{r.title}</span>
  const d = downloadByKey(r.key)
  if (d) return <a href={downloadUrl(d.file)} download={d.file}>{r.title}</a>
  return <a href={`${GITHUB_URL}/blob/main/${r.path}`} target="_blank" rel="noreferrer">{r.title} (on GitHub)</a>
}

export default function ReportsPage() {
  const { mode, phase } = useData()
  const live = (mode === 'LIVE' || mode === 'SNAPSHOT') && phase === 'ready'
  const snap = mode === 'SNAPSHOT'
  const reports = useAsync((s) => fetchReports(s), [], live)
  const figs = useAsync((s) => fetchFigures(s), [], live)
  const shots = useAsync((s) => fetchShots(s), [], live)
  const refs = useAsync((s) => fetchRefs(s), [], live)
  const trace = useAsync((s) => fetchTrace(s), [], live)
  const [open, setOpen] = useState<string | null>(null)
  return (
    <section className="page">
      <h1>Reports</h1>
      <p className="lead">Deliverables, generated figures, genuine Aspen Plus screenshots, references and model traceability. Files are served by the API (LIVE) or, on the published site, from the copies bundled with it; nothing here is regenerated in the browser.</p>
      <ModeGate what="Downloading the deliverable files (report, deck, Aspen model files)" />
      <div className="card"><h2>Deliverables</h2>
        <AsyncView a={reports} what="Deliverables list">{(rs) => (
          <div className="grid-2">{groupReports(rs).map((g) => (
            <div key={g.kind}><h3 style={{ marginTop: 0 }}>{g.title}</h3>
              <ul>{g.items.map((r) => <li key={r.key}>{snap ? <SnapshotReportLink r={r} /> : <a href={assetUrl(r.url)} download={r.file}>{r.title}</a>} <span className="muted">{r.file}, {fmtBytes(r.bytes)}{r.modified_utc ? `, ${r.modified_utc.slice(0, 16).replace('T', ' ')} UTC` : ''}</span></li>)}</ul></div>))}
          </div>)}</AsyncView>
      </div>
      <div className="card"><h2>Genuine Aspen Plus screenshots</h2>
        <AsyncView a={shots} what="Aspen screenshots">{(s) => (
          <>
            <p className="muted">{s.aspen_manifest?.aspen_version}; {s.aspen_manifest?.note}</p>
            <div className="shot-grid">{s.aspen.map((x) => (
              <figure key={x.file} className="shot">
                {x.status === 'captured' ? <a href={assetUrl(x.url)} target="_blank" rel="noreferrer"><img src={assetUrl(x.url)} alt={`${x.title}: ${x.what_is_shown ?? ''}`} loading="lazy" /></a>
                  : <div className="shot-missing">Not captured: {x.reason_if_not ?? 'no reason recorded'}</div>}
                <figcaption><strong>{x.title}</strong> {x.visually_verified ? <StatusPill kind="ok">visually verified</StatusPill> : <StatusPill kind="neutral">not verified</StatusPill>}
                  <div className="muted">{x.navigation_path}</div><div>{x.what_is_shown}</div></figcaption>
              </figure>))}</div>
            {s.dashboard?.length ? <details style={{ marginTop: 10 }}><summary>Dashboard (AmCraX web UI) captures - these are not Aspen screenshots</summary>
              <div className="shot-grid">{s.dashboard.map((d) => <figure key={d.file} className="shot"><a href={assetUrl(d.url)} target="_blank" rel="noreferrer"><img src={assetUrl(d.url)} alt={d.file} loading="lazy" /></a><figcaption>{d.file}</figcaption></figure>)}</div></details> : null}
          </>)}</AsyncView>
      </div>
      <div className="card"><h2>Figures gallery</h2>
        <AsyncView a={figs} what="Figures">{(fs) => (
          <>{groupFigures(fs).map((g) => (
            <details key={g.prefix || 'other'} open={open === g.prefix} onToggle={(e) => { if ((e.target as HTMLDetailsElement).open) setOpen(g.prefix) }} style={{ marginBottom: 8 }}>
              <summary><strong>{g.title}</strong> <span className="muted">({g.items.length})</span></summary>
              <div className="shot-grid">{g.items.map((f) => (
                <figure key={f.name} className="shot"><a href={assetUrl(f.url)} target="_blank" rel="noreferrer"><img src={assetUrl(f.url)} alt={f.caption} loading="lazy" /></a><figcaption>{f.caption} <span className="muted">({f.name})</span></figcaption></figure>))}</div>
            </details>))}</>)}</AsyncView>
      </div>
      <div className="card"><h2>Model traceability</h2>
        <AsyncView a={trace} what="Traceability table">{(ts) => (
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Model traceability"><table className="data"><thead><tr><th scope="col">Model component</th><th scope="col">Source</th><th scope="col">Operating range</th><th scope="col">Limitations</th><th scope="col">Implemented in</th></tr></thead>
            <tbody>{ts.map((t) => <tr key={t.model_component}><td className="clamp-cell"><ClampCell text={t.model_component} max={80} /></td><td><code>{t.source_citekey}</code>{t.page ? `, p. ${t.page}` : ''}{t.locator ? `, ${t.locator}` : ''}</td><td className="clamp-cell"><ClampCell text={t.operating_range ?? ""} /></td><td className="clamp-cell"><ClampCell text={limitationsText(t)} /></td><td className="clamp-cell"><ClampCell text={t.implemented_in ?? ""} max={60} /></td></tr>)}</tbody></table></div>)}</AsyncView>
      </div>
      <div className="card"><h2>References</h2>
        <AsyncView a={refs} what="Reference list">{(rs) => (
          <ol className="refs">{rs.map((r) => { const d = doiLink(r.doi, r.url); return (
            <li key={r.citekey} id={`ref-${r.citekey}`}><code>{r.citekey}</code> {r.apa7.replace(/https?:\/\/\S+$/, '').trim()}{' '}
              {d ? <a href={d} target="_blank" rel="noreferrer">{d}</a> : <span className="muted">no DOI</span>}{' '}
              {r.doi_verified ? <StatusPill kind="ok">DOI verified</StatusPill> : <StatusPill kind="warn">DOI not verified</StatusPill>}</li>) })}</ol>)}</AsyncView>
      </div>
      <div className="card"><h2>How to reproduce</h2>
        <ol>{REPRODUCE_STEPS.map((s) => <li key={s.title}><strong>{s.title}.</strong> <code>{s.cmd}</code><div className="muted">{s.note}</div></li>)}</ol>
        <Notice title="Aspen results.">Aspen Plus V15 results are stored files; regenerating them needs a licensed Aspen installation. The stored files and their provenance are the source of every Aspen number in this dashboard.</Notice>
      </div>
    </section>
  )
}
