import { useState } from 'react'
import { isJob, runSweep, type DataRow } from '../../api/sensitivity'
import { describeError } from '../../api/http'
import type { DataSource } from '../../api/types'
import { useData } from '../../data/DataContext'
import { ModeGate, useLive } from '../common/Notice'
import { FIELDS } from '../simulation/inputs'
import { JobPanel } from '../simulation/JobPanel'
import { useJob } from '../simulation/useJob'
import { checkBounds, listValues, rangeValues } from './shape'

export interface SweepResult { id: number; variable: string; engine: 'python' | 'aspen'; source: DataSource; rows: DataRow[] }
const NUMERIC = FIELDS.filter((f) => f.kind === 'number')
let seq = 0

export function SweepPanel({ onResult }: { onResult: (r: SweepResult) => void }) {
  const live = useLive()
  const { health } = useData()
  const aspenOk = live && (health?.['aspen'] as { available?: boolean } | undefined)?.available === true
  const [variable, setVariable] = useState<string>('reactor_temperature_C')
  const spec = NUMERIC.find((f) => f.key === variable)!
  const [mode, setMode] = useState<'range' | 'list'>('range')
  const [from, setFrom] = useState('450'); const [to, setTo] = useState('750'); const [step, setStep] = useState('50')
  const [list, setList] = useState('450, 500, 600, 700')
  const [engine, setEngine] = useState<'python' | 'aspen'>('python')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [info, setInfo] = useState<string | null>(null)
  const eff = engine === 'aspen' && !aspenOk ? 'python' : engine
  const jt = useJob((j) => {
    setBusy(false)
    const rows = (j.result as { rows?: DataRow[] } | null)?.rows
    if (j.state === 'succeeded' && Array.isArray(rows)) onResult({ id: ++seq, variable, engine: 'aspen', source: 'aspen_plus_v15', rows })
    else if (j.state === 'succeeded') setErr('The Aspen sweep job finished but returned no rows (job.result is empty); nothing to plot.')
  })

  const pick = (v: string) => {
    setVariable(v)
    const f = NUMERIC.find((x) => x.key === v)!
    const d = f.default as number
    const lo = f.min !== undefined && !f.minExcl ? Math.max(f.min, d * 0.8) : d * 0.5
    setFrom(String(Number(lo.toPrecision(4)))); setTo(String(Number((d * 1.2).toPrecision(4)))); setStep(String(Number(((d * 0.4) / 4).toPrecision(3))))
    setList([0.8, 0.9, 1, 1.1, 1.2].map((m) => Number((d * m).toPrecision(4))).join(', '))
  }

  const submit = async () => {
    setErr(null); setInfo(null)
    const r = mode === 'range' ? rangeValues(Number(from), Number(to), Number(step)) : listValues(list)
    if (r.error) { setErr(r.error); return }
    const bad = checkBounds(variable, r.values)
    if (bad) { setErr(bad); return }
    if (eff === 'python' && r.values.length > 200) { setErr('At most 200 points.'); return }
    setBusy(true)
    try {
      const out = await runSweep({ variable, values: r.values, engine: eff })
      if (isJob(out)) { jt.track(out); setInfo(`Aspen sweep started: ${r.values.length} runs (~15 s each, one at a time).`) }
      else { setBusy(false); onResult({ id: ++seq, variable, engine: eff, source: eff === 'aspen' ? 'aspen_plus_v15' : 'python_model', rows: out.rows }) }
    } catch (e) { setBusy(false); setErr(describeError(e)) }
  }

  return (
    <div className="card">
      <h2>New sweep</h2>
      <p className="muted">One-variable sweep around the baseline inputs. Python engine: immediate. Aspen engine: a job that runs one simulation per point (single licence seat).</p>
      <ModeGate what="A new sweep" />
      <div className="controls">
        <label className="field">Variable<select value={variable} onChange={(e) => pick(e.target.value)} style={{ width: 260 }}>{NUMERIC.map((f) => <option key={f.key} value={f.key}>{f.label} [{f.unit}]</option>)}</select></label>
        <div className="field">Points
          <div className="toggle" role="group" aria-label="Value specification">
            <button type="button" aria-pressed={mode === 'range'} onClick={() => setMode('range')}>Range / step</button>
            <button type="button" aria-pressed={mode === 'list'} onClick={() => setMode('list')}>List</button>
          </div></div>
        {mode === 'range' ? (<>
          <label className="field">From<input type="number" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
          <label className="field">To<input type="number" value={to} onChange={(e) => setTo(e.target.value)} /></label>
          <label className="field">Step<input type="number" value={step} onChange={(e) => setStep(e.target.value)} /></label>
        </>) : <label className="field">Values (comma separated)<input value={list} onChange={(e) => setList(e.target.value)} style={{ width: 280 }} /></label>}
        <div className="field">Engine
          <div className="toggle" role="group" aria-label="Sweep engine">
            <button type="button" aria-pressed={eff === 'python'} onClick={() => setEngine('python')}>Python model</button>
            <button type="button" aria-pressed={eff === 'aspen'} disabled={!aspenOk} onClick={() => setEngine('aspen')} title={aspenOk ? 'Aspen Plus V15 job' : 'Aspen unavailable'}>Aspen Plus V15</button>
          </div></div>
        <button type="button" className="btn btn-primary" disabled={!live || busy} onClick={() => void submit()}>{busy ? 'Running ...' : 'Run sweep'}</button>
      </div>
      <p className="hint muted">Allowed range for {spec.label}: {spec.min !== undefined ? `${spec.minExcl ? '>' : '>='} ${spec.min}` : ''} {spec.max !== undefined ? `${spec.maxExcl ? '<' : '<='} ${spec.max}` : ''} {spec.unit}</p>
      {err ? <p className="err-text" role="alert">{err}</p> : null}
      {info ? <p className="muted">{info}</p> : null}
      <JobPanel job={jt.job} elapsedS={jt.elapsedS} lastError={jt.lastError} title="Sweep job" />
    </div>
  )
}
