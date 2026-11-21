import { useMemo, useState } from 'react'
import { startSimulation, type Engine, type Job } from '../../api/simulation'
import { describeError } from '../../api/http'
import type { SimulationResult } from '../../api/types'
import { StatusPill } from '../../components/ui'
import { useData } from '../../data/DataContext'
import { ModeGate, useLive } from '../common/Notice'
import { FIELDS, changedKeys, defaultValues, isChanged, rangeText, toInputs, validate, valuesFromInputs, type FormValues } from './inputs'
import { JobPanel } from './JobPanel'
import { useJob } from './useJob'

export function SimForm({ onSucceeded }: { onSucceeded: (caseId: string, job: Job) => void }) {
  const { health, cases } = useData()
  const live = useLive()
  const aspen = (health?.['aspen'] ?? null) as { available?: boolean; reason?: string | null } | null
  const aspenOk = live && aspen?.available === true
  const [engine, setEngine] = useState<Engine>('python')
  const [vals, setVals] = useState<FormValues>(defaultValues)
  const [caseId, setCaseId] = useState('user_case_1')
  const [touched, setTouched] = useState(false)
  const [submitErr, setSubmitErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const jt = useJob((j) => { setBusy(false); if (j.state === 'succeeded' && j.case_id) onSucceeded(j.case_id, j) })

  const eff: Engine = engine === 'aspen' && !aspenOk ? 'python' : engine
  const errors = useMemo(() => validate(vals, caseId, eff), [vals, caseId, eff])
  const nErr = Object.keys(errors).length
  const changed = changedKeys(vals)
  const exists = cases.some((c) => c.case_id === caseId.trim())

  const set = (k: string, v: string | boolean) => setVals((p) => ({ ...p, [k]: v }))
  const submit = async () => {
    setTouched(true); setSubmitErr(null)
    if (nErr > 0 || !live) return
    setBusy(true)
    try {
      const job = await startSimulation(toInputs(vals, caseId), eff)
      jt.track(job)
    } catch (e) { setBusy(false); setSubmitErr(describeError(e)) }
  }
  const fromCase = (c: SimulationResult) => { setVals(valuesFromInputs(c.inputs)); setCaseId(`${c.case_id}_copy`.slice(0, 64)) }

  return (
    <div className="card sim-form">
      <div className="section-h"><h2>Operating conditions</h2>
        <span>
          {changed.length > 0 ? <StatusPill kind="info">{changed.length} changed from baseline</StatusPill> : <StatusPill kind="neutral">baseline values</StatusPill>}{' '}
          <button type="button" className="btn btn-sm" onClick={() => { setVals(defaultValues()); setTouched(false) }} disabled={changed.length === 0}>Reset to baseline</button>
        </span>
      </div>
      <ModeGate what="Running a simulation" />
      <div className="controls">
        <label className="field">Case name
          <input value={caseId} onChange={(e) => setCaseId(e.target.value)} aria-invalid={!!errors.case_id} style={{ width: 200 }} />
          {errors.case_id ? <span className="err-text">{errors.case_id}</span> : null}
        </label>
        <div className="field">Engine
          <div className="toggle" role="group" aria-label="Simulation engine">
            <button type="button" aria-pressed={eff === 'aspen'} disabled={!aspenOk} onClick={() => setEngine('aspen')}
              title={aspenOk ? 'Rigorous Aspen Plus V15 simulation, about 15 s to several minutes per run' : `Aspen unavailable: ${aspen?.reason ?? (live ? 'not reported' : 'API not live')}`}>Aspen Plus V15</button>
            <button type="button" aria-pressed={eff === 'python'} onClick={() => setEngine('python')} title="Independent AmCraX Python model, immediate">Python model</button>
          </div>
        </div>
        {cases.length > 0 ? (
          <label className="field">Start from stored case
            <select value="" onChange={(e) => { const c = cases.find((x) => x.case_id === e.target.value); if (c) fromCase(c) }}>
              <option value="">(baseline defaults)</option>
              {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
            </select>
          </label>) : null}
      </div>
      {!aspenOk ? <p className="muted">Aspen Plus engine is disabled: {live ? (aspen?.reason ?? 'GET /api/health does not report it as available') : 'the API is not live'}. The Python model is used.</p>
        : <p className="muted">Aspen Plus V15 is available. Note: the full flowsheet needs at least {3} bar at the cracker outlet. Only one Aspen job runs at a time; others wait in the queue.</p>}
      {exists ? <p className="warn-text">A stored case named <code>{caseId.trim()}</code> exists. Python runs never overwrite Aspen results (the Python result is then stored as <code>{caseId.trim()}_py</code>).</p> : null}
      <div className="field-grid">
        {FIELDS.map((f) => {
          const err = (touched || isChanged(f, vals)) ? errors[f.key] : undefined
          const ch = isChanged(f, vals)
          return (
            <label key={f.key} className={`field ff ${ch ? 'is-changed' : ''}`} title={f.help}>
              <span>{f.label}{f.unit ? ` [${f.unit}]` : ''}{ch ? <span className="chg-mark"> changed</span> : null}</span>
              {f.kind === 'bool' ? (
                <span className="check"><input type="checkbox" checked={Boolean(vals[f.key])} onChange={(e) => set(f.key, e.target.checked)} /> {vals[f.key] ? 'on' : 'off'}</span>
              ) : (
                <input type={f.kind === 'number' ? 'number' : 'text'} step={f.step} value={String(vals[f.key])} onChange={(e) => set(f.key, e.target.value)}
                  aria-invalid={!!err} aria-describedby={`h-${f.key}`} />
              )}
              <span id={`h-${f.key}`} className={err ? 'err-text' : 'hint'}>{err ?? (f.kind === 'number' ? `range ${rangeText(f)}; default ${f.default}` : `default ${String(f.default)}`)}</span>
            </label>)
        })}
      </div>
      <div className="controls" style={{ marginTop: 12 }}>
        <button type="button" className="btn btn-primary" onClick={() => void submit()} disabled={!live || busy}>
          {busy ? 'Running ...' : `Run ${eff === 'aspen' ? 'Aspen Plus' : 'Python model'}`}
        </button>
        {touched && nErr > 0 ? <span className="err-text" role="alert">{nErr} input{nErr > 1 ? 's' : ''} invalid - fix before running.</span> : null}
      </div>
      <JobPanel job={jt.job} elapsedS={jt.elapsedS} lastError={jt.lastError} error={submitErr} title="Simulation job" />
    </div>
  )
}
