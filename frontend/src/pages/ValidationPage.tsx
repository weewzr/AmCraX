import { useMemo, useState } from 'react'
import { CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import '../features/common/features.css'
import { fetchDataset, fetchValidationMatrix, type ValidationItem, type ValidationStatus } from '../api/validation'
import { DataTable, type Column } from '../components/DataTable'
import { SourceBadge, StatusPill, Value, type StatusKind } from '../components/ui'
import { useData } from '../data/DataContext'
import { fmt } from '../data/format'
import { AsyncView, ModeGate, Notice } from '../features/common/Notice'
import { useAsync } from '../features/common/useAsync'
import { XYChart } from '../features/common/XYChart'
import {
  CMP_QUANTITIES, countByStatus, crossCheckRows, deviationSummary, deviationVsT, filterItems, notValidated, parityData, STATUS_ORDER,
  type CmpQuantity, type CrossRow, type DevSummary,
} from '../features/validation/shape'

const KIND: Record<ValidationStatus, StatusKind> = { pass: 'ok', fail: 'error', not_run: 'warn', informational: 'info' }
const LABEL: Record<ValidationStatus, string> = { pass: 'pass', fail: 'fail', not_run: 'not run', informational: 'informational' }
const COMBO_COLORS = ['#38bdf8', '#ff7a3d', '#4ade80', '#f472b6']

export default function ValidationPage() {
  const { mode } = useData()
  const live = mode === 'LIVE' || mode === 'SNAPSHOT'
  return (
    <section className="page">
      <h1>Validation</h1>
      <p className="lead">What has been checked, against what, with what result - and what has not. Failed and not-run checks are shown as such; nothing is tuned to force agreement.</p>
      <ModeGate what="Re-running the validation checks" />
      {live ? <Matrix /> : null}
      {live ? <EquilibriumParity /> : null}
      {live ? <CrossCheck /> : null}
      <Closures />
    </section>
  )
}

function Matrix() {
  const m = useAsync((s) => fetchValidationMatrix(s), [])
  const [status, setStatus] = useState<ValidationStatus | 'all'>('all')
  const [comp, setComp] = useState('all')
  const [text, setText] = useState('')
  return (
    <AsyncView a={m} what="Validation matrix (/api/validation, results/validation/validation_matrix.json)">{(items) => {
      if (items.length === 0) return <Notice kind="warn" title="Validation matrix is empty.">The file was found but contains no entries.</Notice>
      const counts = countByStatus(items)
      const comps = [...new Set(items.map((i) => i.model_component))].sort()
      const rows = filterItems(items, status, comp, text)
      const cols: Column<ValidationItem>[] = [
        { key: 'status', label: 'Status', render: (i) => <StatusPill kind={KIND[i.status]}>{LABEL[i.status]}</StatusPill>, csv: (i) => i.status },
        { key: 'id', label: 'ID' }, { key: 'model_component', label: 'Component' },
        { key: 'validation_method', label: 'Method', render: (i) => <span className="wrap-cell">{i.validation_method}</span> },
        { key: 'reference', label: 'Reference', render: (i) => <span className="wrap-cell">{i.reference}</span> },
        { key: 'expected_behaviour', label: 'Expected', render: (i) => <span className="wrap-cell">{i.expected_behaviour}</span> },
        { key: 'actual_result', label: 'Actual result', render: (i) => <span className="wrap-cell">{i.actual_result}</span> },
        { key: 'metric', label: 'Metric', render: (i) => <span className="wrap-cell">{i.metric}</span> },
        { key: 'tolerance', label: 'Tolerance' },
        { key: 'limitations', label: 'Limitations', render: (i) => <span className="wrap-cell">{i.limitations}</span> },
        { key: 'evidence_files', label: 'Evidence', render: (i) => <span className="wrap-cell">{i.evidence_files.join(', ')}</span>, csv: (i) => i.evidence_files.join('; ') },
      ]
      const nv = notValidated(items)
      return (
        <>
          <div className="section-h"><h2>Validation matrix</h2>
            <span className="chips" aria-label="Summary counts">
              {STATUS_ORDER.map((s) => <StatusPill key={s} kind={KIND[s]}>{counts[s]} {LABEL[s]}</StatusPill>)}
              <span className="muted">of {items.length}</span>
            </span>
          </div>
          <div className="card controls">
            <label className="field">Status<select value={status} onChange={(e) => setStatus(e.target.value as ValidationStatus | 'all')}>
              <option value="all">All</option>{STATUS_ORDER.map((s) => <option key={s} value={s}>{LABEL[s]}</option>)}</select></label>
            <label className="field">Component<select value={comp} onChange={(e) => setComp(e.target.value)}>
              <option value="all">All</option>{comps.map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
            <label className="field">Search<input type="search" style={{ width: 220 }} value={text} onChange={(e) => setText(e.target.value)} placeholder="text in any field" /></label>
            <span className="muted">{rows.length} of {items.length} shown</span>
          </div>
          <DataTable columns={cols} rows={rows} caption="Validation matrix" filename="validation_matrix.csv" />
          <div className="card notice notice-warn">
            <h3 style={{ marginTop: 0 }}>What is not validated ({nv.length})</h3>
            {nv.length === 0 ? <p>No open items are recorded in the matrix.</p> : (
              <ul>{nv.map(({ item, why }) => (
                <li key={item.id}><StatusPill kind={KIND[item.status]}>{LABEL[item.status]}</StatusPill> <strong>{item.id}</strong> ({item.model_component}) - {why}</li>))}</ul>)}
            <p className="muted">Taken verbatim from the matrix (not-run and failed checks, and every stated limitation).</p>
          </div>
        </>
      )
    }}</AsyncView>
  )
}

function EquilibriumParity() {
  const cmp = useAsync((s) => fetchDataset('validation', 'equilibrium_comparison', s), [])
  const [q, setQ] = useState<CmpQuantity>('nh3_conversion')
  const [P, setP] = useState(20)
  return (
    <>
      <div className="section-h"><h2>Aspen RGibbs vs independent Python equilibrium</h2></div>
      <AsyncView a={cmp} what="Equilibrium comparison (validation/equilibrium_comparison)">{(d) => {
        const par = parityData(d.rows, q)
        const summary = deviationSummary(d.rows, q)
        const dev = deviationVsT(d.rows, q, P)
        const combos = par.combos
        const label = (c: string) => { const [a, e] = c.split('|'); return `Aspen ${a} vs Python ${e}` }
        const all = combos.flatMap((c) => par.byCombo[c].flatMap((r) => [r.aspen as number, r.python as number]))
        const lo = all.length ? Math.min(...all) : 0, hi = all.length ? Math.max(...all) : 1
        const pressures = [...new Set(d.rows.map((r) => Number(r.P_bar)).filter(Number.isFinite))].sort((a, b) => a - b)
        const cols: Column<DevSummary>[] = [
          { key: 'combo', label: 'Aspen method vs Python EOS', render: (r) => label(r.combo) },
          { key: 'n', label: 'Points', align: 'right' },
          { key: 'maxAbs', label: 'Max |deviation|', align: 'right', render: (r) => fmt(r.maxAbs, 5), csv: (r) => String(r.maxAbs) },
          { key: 'maxAbsAt', label: 'at' },
          { key: 'meanAbs', label: 'Mean |deviation|', align: 'right', render: (r) => fmt(r.meanAbs, 5), csv: (r) => String(r.meanAbs) },
        ]
        return (
          <>
            <div className="card controls">
              <label className="field">Quantity<select value={q} onChange={(e) => setQ(e.target.value as CmpQuantity)}>{CMP_QUANTITIES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
              <label className="field">Pressure for deviation plot<select value={P} onChange={(e) => setP(Number(e.target.value))}>{pressures.map((p) => <option key={p} value={p}>{p} bar</option>)}</select></label>
              <span className="muted">Deviation = Python minus Aspen. Both EOS pairings shown; matched pairs are Aspen IDEAL vs Python ideal and Aspen PENG-ROB vs Python pr.</span>
            </div>
            <div className="grid-2">
              <figure className="card chart-card" aria-label="Parity plot">
                <figcaption><span>Parity plot: Python vs Aspen</span></figcaption>
                <div className="chart-box" role="img" aria-label="Scatter of Python equilibrium value against Aspen RGibbs value; points on the diagonal mean agreement.">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 8, right: 16, bottom: 56, left: 8 }}>
                      <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
                      <XAxis type="number" dataKey="aspen" name="Aspen" domain={[lo, hi]} stroke="var(--muted)" tick={{ fill: 'var(--muted)', fontSize: 12 }} tickFormatter={(v: number) => fmt(v, 3)}
                        label={{ value: 'Aspen RGibbs', position: 'insideBottom', offset: -14, fill: 'var(--muted)' }} />
                      <YAxis type="number" dataKey="python" name="Python" domain={[lo, hi]} stroke="var(--muted)" tick={{ fill: 'var(--muted)', fontSize: 12 }} tickFormatter={(v: number) => fmt(v, 3)}
                        label={{ value: 'Python model', angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
                      <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }} />
                      <Legend verticalAlign="bottom" height={28} />
                      <ReferenceLine segment={[{ x: lo, y: lo }, { x: hi, y: hi }]} stroke="var(--muted)" strokeDasharray="4 4" />
                      {combos.map((c, i) => <Scatter key={c} name={label(c)} data={par.byCombo[c]} fill={COMBO_COLORS[i % 4]} />)}
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
                <div className="series-src">Aspen axis <SourceBadge source="aspen_plus_v15" /> Python axis <SourceBadge source="python_model" /></div>
              </figure>
              <XYChart title={`Deviation (Python - Aspen) at ${P} bar`} xKey="T_C" xLabel="Temperature [degC]" yLabel="Absolute deviation" data={dev}
                description="Absolute deviation of the Python equilibrium from the Aspen RGibbs value against temperature."
                series={combos.map((c, i) => ({ key: c, label: label(c), color: COMBO_COLORS[i % 4], kind: 'line' as const, source: 'python_model' as const }))} />
            </div>
            <DataTable columns={cols} rows={summary} caption="Deviation summary (absolute, same units as the quantity)" filename="equilibrium_deviation_summary.csv" />
            {d.source_note ? <p className="muted">{d.source_note}</p> : null}
          </>
        )
      }}</AsyncView>
    </>
  )
}

function CrossCheck() {
  const [which, setWhich] = useState('aspen_vs_python_flowsheet')
  const flow = useAsync((s) => fetchDataset('validation', 'aspen_vs_python_flowsheet', s), [])
  const base = useAsync((s) => fetchDataset('validation', 'aspen_vs_python_baseline', s), [])
  const [onlyBig, setOnlyBig] = useState(true)
  const a = flow.phase === 'ready' && which === 'aspen_vs_python_flowsheet' ? flow : base
  const rows = useMemo(() => (a.phase === 'ready' ? crossCheckRows(a.data.rows) : []), [a])
  const shown = onlyBig ? rows.filter((r) => r.rel_diff !== null && Math.abs(r.rel_diff) >= 1e-3) : rows
  const cols: Column<CrossRow>[] = [
    { key: 'quantity', label: 'Quantity' },
    { key: 'a', label: 'a (Aspen)', align: 'right', render: (r) => <Value v={r.a} source="aspen_plus_v15" showSource={false} />, csv: (r) => String(r.a) },
    { key: 'b', label: 'b (Python)', align: 'right', render: (r) => <Value v={r.b} source="python_model" showSource={false} />, csv: (r) => String(r.b) },
    { key: 'abs_diff', label: 'b - a', align: 'right', render: (r) => fmt(r.abs_diff, 4), csv: (r) => String(r.abs_diff) },
    { key: 'rel_diff', label: 'Relative', align: 'right', render: (r) => (r.rel_diff === null ? 'n/a' : <span className={Math.abs(r.rel_diff) >= 1e-2 ? 'dev-bad' : ''}>{(r.rel_diff * 100).toFixed(3)} %</span>), csv: (r) => String(r.rel_diff) },
  ]
  return (
    <>
      <div className="section-h"><h2>Flowsheet cross-check: Aspen vs Python process model</h2>
        <div className="toggle" role="group" aria-label="Dataset">
          <button type="button" aria-pressed={which === 'aspen_vs_python_flowsheet'} onClick={() => setWhich('aspen_vs_python_flowsheet')}>Flowsheet</button>
          <button type="button" aria-pressed={which === 'aspen_vs_python_baseline'} onClick={() => setWhich('aspen_vs_python_baseline')}>Baseline</button>
        </div>
      </div>
      {which === 'aspen_vs_python_flowsheet' && flow.phase === 'error' ? <Notice kind="warn" title="aspen_vs_python_flowsheet not available.">Showing the baseline cross-check instead ({flow.error}).</Notice> : null}
      <AsyncView a={a} what="Flowsheet cross-check dataset">{(d) => (
        <>
          <label className="field" style={{ flexDirection: 'row', gap: 8 }}><input type="checkbox" style={{ width: 'auto' }} checked={onlyBig} onChange={(e) => setOnlyBig(e.target.checked)} />
            Only show deviations of 0.1 % or more ({shown.length} of {rows.length} quantities)</label>
          <DataTable columns={cols} rows={shown} caption={`${d.name}: column a = first operand (Aspen), b = second (Python model)`} filename={`${d.name}.csv`} />
        </>
      )}</AsyncView>
    </>
  )
}

function Closures() {
  const { active, phase } = useData()
  if (phase !== 'ready' || !active) return null
  const b = active.balances
  const src = active.source
  const ratio = (x: number | null, y: number | null) => (x !== null && y !== null && x !== 0 ? (y - x) / x : null)
  return (
    <div className="card">
      <h2>Balance closures of case <code>{active.case_id}</code> <SourceBadge source={src} /></h2>
      <dl className="kv">
        <dt>Mass closure (relative)</dt><dd><Value v={b.mass_closure_rel} digits={6} source={src} /> <span className="muted">in <Value v={b.mass_in_kg_h} unit="kg/h" digits={1} source={src} showSource={false} />, out <Value v={b.mass_out_kg_h} unit="kg/h" digits={1} source={src} showSource={false} /></span></dd>
        <dt>Energy closure (relative)</dt><dd><Value v={b.energy_closure_rel} digits={6} source={src} /> <span className="muted">in <Value v={b.energy_in_kW} unit="kW" digits={1} source={src} showSource={false} />, out <Value v={b.energy_out_kW} unit="kW" digits={1} source={src} showSource={false} /></span></dd>
        <dt>N atoms out/in - 1</dt><dd><Value v={ratio(b.n_atoms_in_kmol_h, b.n_atoms_out_kmol_h)} digits={6} source={src} /></dd>
        <dt>H atoms out/in - 1</dt><dd><Value v={ratio(b.h_atoms_in_kmol_h, b.h_atoms_out_kmol_h)} digits={6} source={src} /></dd>
        <dt>Run status</dt><dd>{active.status.converged ? <StatusPill kind="ok">converged</StatusPill> : <StatusPill kind="error">not converged</StatusPill>}{' '}{active.status.has_warnings ? <StatusPill kind="warn">warnings</StatusPill> : null}</dd>
      </dl>
    </div>
  )
}

