import { useEffect, useState } from 'react'
import '../features/common/features.css'
import '../features/simulation/simulation.css'
import { useData } from '../data/DataContext'
import { Notice } from '../features/common/Notice'
import { Compare } from '../features/simulation/Compare'
import { Results } from '../features/simulation/Results'
import { SimForm } from '../features/simulation/SimForm'
import { SourceBadge } from '../components/ui'

export default function SimulationPage() {
  const { cases, activeId, setActiveId, reload, phase, caseLabel } = useData()
  const [viewId, setViewId] = useState<string | null>(null)
  const [fresh, setFresh] = useState<string | null>(null)
  const [pendingActive, setPendingActive] = useState<string | null>(null)

  // a finished job: reload the case list, then offer the new case
  useEffect(() => {
    if (fresh && phase === 'ready' && cases.some((c) => c.case_id === fresh)) { setViewId(fresh) }
  }, [fresh, phase, cases])
  // reload() resets the shell's active case to baseline; re-apply the one the user chose once the list is back
  useEffect(() => {
    if (pendingActive && phase === 'ready' && cases.some((c) => c.case_id === pendingActive)) { setActiveId(pendingActive); setPendingActive(null) }
  }, [pendingActive, phase, cases, setActiveId])

  const shownId = viewId && cases.some((c) => c.case_id === viewId) ? viewId : activeId
  const shown = cases.find((c) => c.case_id === shownId) ?? null
  const isActive = shownId !== null && shownId === activeId

  return (
    <section className="page">
      <h1>Simulation</h1>
      <p className="lead">Run a flowsheet case with the Aspen Plus V15 model or the independent Python model, inspect stored results, and compare scenarios. Every number carries its provenance; Aspen runs are never replaced by Python results.</p>
      <SimForm onSucceeded={(id) => { setFresh(id); setPendingActive(id); reload() }} />
      {fresh ? <Notice kind="info" title="New case stored.">Case <code>{fresh}</code> is in the case list{shownId === fresh ? ' and shown below' : ' (loading ...)'}.</Notice> : null}
      <div className="card controls">
        <label className="field">Case shown below
          <select value={shownId ?? ''} onChange={(e) => setViewId(e.target.value)} disabled={cases.length === 0} style={{ width: 280 }}>
            {cases.length === 0 ? <option value="">no cases</option> : null}
            {cases.map((c) => <option key={c.case_id} value={c.case_id}>{caseLabel(c.case_id)} ({c.source === 'aspen_plus_v15' ? 'Aspen' : 'Python'})</option>)}
          </select>
        </label>
        {shown ? <SourceBadge source={shown.source} /> : null}
        <button type="button" className="btn btn-sm" disabled={!shown || isActive} onClick={() => shown && setActiveId(shown.case_id)}>
          {isActive ? 'This is the active case' : 'Make active case'}
        </button>
        <span className="muted">The active case drives the other pages (header selector).</span>
      </div>
      {shown ? <Results c={shown} /> : <Notice kind="warn" title="No case loaded.">{phase === 'loading' ? 'Loading cases ...' : 'No stored case is available; run one above. No placeholder numbers are shown.'}</Notice>}
      <Compare />
    </section>
  )
}

