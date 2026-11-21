import { useEffect, useMemo, useState } from 'react'
import '../features/common/features.css'
import '../features/simulation/simulation.css'
import { fetchDataset, fetchDatasets, runSweep, isJob, type Dataset, type DataRow } from '../api/sensitivity'
import { describeError } from '../api/http'
import type { DataSource } from '../api/types'
import { DataTable, type Column } from '../components/DataTable'
import { SourceBadge, StatusPill } from '../components/ui'
import { useData } from '../data/DataContext'
import { fmt } from '../data/format'
import { metricLabel, metricName } from '../data/metrics'
import { AsyncView, ModeGate, Notice, useLive, useReadable } from '../features/common/Notice'
import { useAsync } from '../features/common/useAsync'
import { HeatMap } from '../features/sensitivity/HeatMap'
import { SensChart, type SensSeries } from '../features/sensitivity/SensChart'
import { SweepPanel, type SweepResult } from '../features/sensitivity/SweepPanel'
import { axisLabel, baseInputsFromRows, datasetSource, defaultYs, distinctSorted, inferX, INPUT_KEYS, mergeSeries, numericColumns, splitConverged, unitFor, varyingInputs } from '../features/sensitivity/shape'

export default function SensitivityPage() {
  const readable = useReadable()
  const list = useAsync((s) => fetchDatasets(s), [], readable)
  const [name, setName] = useState<string | null>(null)
  const [sweeps, setSweeps] = useState<SweepResult[]>([])
  useEffect(() => {
    if (!name && list.data) setName(list.data.datasets.find((d) => d.name === 'aspen_temperature')?.name ?? list.data.datasets[0]?.name ?? null)
  }, [list.data, name])
  const ds = useAsync((s) => fetchDataset(name as string, s), [name], readable && !!name)
  const aspenSets = list.data?.datasets.filter((d) => d.name.startsWith('aspen_')) ?? []
  const otherSets = list.data?.datasets.filter((d) => !d.name.startsWith('aspen_')) ?? []

  return (
    <section className="page">
      <h1>Sensitivity Analysis</h1>
      <p className="lead">Parameter studies of the flowsheet. The Aspen studies are series of full Aspen Plus V15 simulation runs, one run per point. Your own sweeps run on the Python model (immediately) or as Aspen jobs.</p>
      <ModeGate what="New sweeps and the Python overlay" />
      <AsyncView a={list} what="Sensitivity dataset list (GET /api/sensitivity/datasets)">
        {() => (
          <div className="card">
            <h2>Datasets</h2>
            <p className="muted">Aspen Plus V15 studies <SourceBadge source="aspen_plus_v15" /></p>
            <div className="chips" role="group" aria-label="Aspen datasets">{aspenSets.map((d) => (
              <button key={d.name} type="button" className="chip" aria-pressed={name === d.name} onClick={() => setName(d.name)} title={`${d.rows} rows`}>{d.name.replace(/^aspen_/, '')} <span className="muted">({d.rows})</span></button>))}</div>
            {otherSets.length ? (<>
              <p className="muted" style={{ marginTop: 10 }}>Python-model and assumption-based analyses (not Aspen runs)</p>
              <div className="chips" role="group" aria-label="Other datasets">{otherSets.map((d) => (
                <button key={d.name} type="button" className="chip" aria-pressed={name === d.name} onClick={() => setName(d.name)} title={`${d.rows} rows`}>{d.name} <span className="muted">({d.rows})</span></button>))}</div></>) : null}
          </div>)}
      </AsyncView>
      <AsyncView a={ds} what={`Dataset ${name ?? ''}`}>{(d) => <DatasetView key={d.name} d={d} sweeps={sweeps} />}</AsyncView>
      <SweepPanel onResult={(r) => setSweeps((p) => [r, ...p].slice(0, 6))} />
      {sweeps.length ? <SweepResults sweeps={sweeps} clear={() => setSweeps([])} /> : null}
    </section>
  )
}

const COL_A = 'var(--primary)'
const COL_P = 'var(--src-python)'
const COL_S = ['var(--accent)', 'var(--c-nh3)', 'var(--c-h2)']

function DatasetView({ d, sweeps }: { d: Dataset; sweeps: SweepResult[] }) {
  const { cases } = useData()
  const src: DataSource = datasetSource(d.name, d.rows)
  const { used, excluded } = useMemo(() => splitConverged(d.rows, d.columns), [d])
  const vary = useMemo(() => varyingInputs(d.columns, used), [d, used])
  const twoD = vary.length >= 2
  const nums = useMemo(() => numericColumns(d.columns, used), [d, used])
  const [x, setX] = useState<string>(() => inferX(d.name, d.columns, used) ?? '')
  const [ys, setYs] = useState<string[]>(() => defaultYs(d.columns, used, inferX(d.name, d.columns, used)))
  const [py, setPy] = useState<{ rows: DataRow[]; err: string | null; busy: boolean } | null>(null)
  const live = useLive()
  const yOptions = nums.filter((c) => c !== x && !INPUT_KEYS.includes(c))
  const baseCase = cases.find((c) => c.case_id === (d.name.includes('no_hi') ? 'baseline_no_hi' : 'baseline'))
  const xBase = baseCase ? (baseCase.inputs as unknown as Record<string, unknown>)[x] : undefined

  const toggleY = (y: string) => setYs((p) => p.includes(y) ? p.filter((k) => k !== y) : [...p, y])
  const overlayPython = async () => {
    const xs = distinctSorted(used, x)
    setPy({ rows: [], err: null, busy: true })
    try {
      const out = await runSweep({ variable: x, values: xs, base_inputs: baseInputsFromRows(used, d.columns, x), engine: 'python' })
      if (isJob(out)) throw new Error('unexpected job response for the python engine')
      setPy({ rows: out.rows, err: null, busy: false })
    } catch (e) { setPy({ rows: [], err: describeError(e), busy: false }) }
  }
  const sweepOnX = sweeps.filter((s) => s.variable === x)
  const tblCols: Column<DataRow>[] = [x, ...ys, ...(d.columns.includes('converged') ? ['converged'] : [])].filter((c, i, a) => c && a.indexOf(c) === i).map((c) => ({
    key: c, label: metricName(c), unit: unitFor(c) && unitFor(c) !== '-' ? unitFor(c) : undefined, align: nums.includes(c) ? 'right' : 'left',
    render: (r: DataRow) => typeof r[c] === 'number' ? <span>{fmt(r[c] as number, Math.abs(r[c] as number) < 10 ? 4 : undefined)}</span> : <span>{r[c] === null ? 'n/a' : String(r[c])}</span>,
    csv: (r: DataRow) => String(r[c] ?? ''),
  }))
  const allCols: Column<DataRow>[] = d.columns.map((c) => ({ key: c, label: c, csv: (r: DataRow) => String(r[c] ?? '') }))
  const [full, setFull] = useState(false)

  return (
    <>
      <div className="card">
        <div className="section-h"><h2>{d.name} <SourceBadge source={src} /></h2>
          <span>{excluded > 0 ? <StatusPill kind="warn">{excluded} non-converged row(s) excluded</StatusPill> : <StatusPill kind="ok">{used.length} of {d.rows.length} rows converged</StatusPill>}</span></div>
        <p className="muted">{src === 'aspen_plus_v15' ? 'Aspen Plus V15 - every point is a simulation run.' : src === 'python_model' ? 'Python model calculation (not an Aspen run).' : 'Assumption-based calculation (not an Aspen run).'}{d.source_note ? ` ${d.source_note}` : ''} {used.length} point(s) shown.</p>
        {twoD ? <p className="muted">Two inputs vary together ({vary.join(', ')}): shown as a heat map instead of line charts.</p> : (
          <div className="controls">
            <label className="field">x variable<select value={x} onChange={(e) => { setX(e.target.value); setYs((p) => p.filter((k) => k !== e.target.value)) }}>
              {nums.map((c) => <option key={c} value={c}>{axisLabel(c)}</option>)}</select></label>
            <div className="field" style={{ flex: 1, minWidth: 280 }}>y variables (one chart each, own unit)
              <div className="chips cols-pick" role="group" aria-label="y variables">{yOptions.map((c) => <button key={c} type="button" className="chip" aria-pressed={ys.includes(c)} title={c} onClick={() => toggleY(c)}>{metricLabel(c)}</button>)}</div></div>
          </div>)}
        {!twoD && src === 'aspen_plus_v15' && INPUT_KEYS.includes(x) ? (
          <div className="controls" style={{ marginTop: 8 }}>
            <button type="button" className="btn btn-sm" disabled={!live || py?.busy} onClick={() => void overlayPython()}>{py?.busy ? 'Running ...' : py && py.rows.length ? 'Refresh Python overlay' : 'Overlay Python model'}</button>
            {py && py.rows.length ? <button type="button" className="btn btn-sm" onClick={() => setPy(null)}>Remove overlay</button> : null}
            <span className="muted">Runs the Python model at the same x values and the dataset's fixed inputs, to compare with the Aspen points.</span>
          </div>) : null}
        {py?.err ? <p className="err-text" role="alert">Python overlay failed - {py.err}</p> : null}
      </div>

      {twoD ? <HeatMap rows={d.rows} columns={d.columns} source={src} /> : (
        <div className="grid-2">
          {ys.map((y) => {
            const series: SensSeries[] = [{ key: `a|${y}`, label: src === 'aspen_plus_v15' ? 'Aspen Plus V15 runs' : d.name, color: COL_A, dots: true, source: src }]
            const sets = [{ prefix: 'a', rows: used }]
            if (py && py.rows.length) { sets.push({ prefix: 'p', rows: splitConverged(py.rows, ['converged']).used }); series.push({ key: `p|${y}`, label: 'Python model (same x, same fixed inputs)', color: COL_P, dots: false, dashed: true, source: 'python_model' }) }
            sweepOnX.forEach((s, i) => { sets.push({ prefix: `s${s.id}`, rows: splitConverged(s.rows, ['converged']).used }); series.push({ key: `s${s.id}|${y}`, label: `New sweep #${s.id} (${s.engine})`, color: COL_S[i % 3], dots: s.engine === 'aspen', dashed: true, source: s.source }) })
            const data = mergeSeries(sets, x, y)
            const kv = baseCase ? (baseCase.kpis as unknown as Record<string, number | null>)[y] : undefined
            const bl = typeof xBase === 'number' ? { x: xBase, y: typeof kv === 'number' ? kv : null, label: `baseline (${baseCase?.case_id}, Aspen)` } : null
            return <SensChart key={y} title={`${metricName(y)} vs ${metricName(x)}`} xLabel={axisLabel(x)} yLabel={axisLabel(y)} data={data} series={series} baseline={bl} />
          })}
          {ys.length === 0 ? <Notice>Select at least one y variable.</Notice> : null}
        </div>)}
      {!twoD && py && py.rows.length ? <Agreement used={used} py={py.rows} x={x} ys={ys} /> : null}

      <DataTable columns={full ? allCols : tblCols} rows={d.rows} caption={`${d.name}: ${d.rows.length} rows (${full ? 'all columns' : 'selected columns'}; non-converged rows included here and flagged)`} filename={`${d.name}.csv`} />
      <label className="check"><input type="checkbox" checked={full} onChange={(e) => setFull(e.target.checked)} /> Show all {d.columns.length} columns in the table and export</label>
    </>
  )
}

/** Quantifies agreement between the Aspen points and the Python overlay at identical x. */
function Agreement({ used, py, x, ys }: { used: DataRow[]; py: DataRow[]; x: string; ys: string[] }) {
  const rows = ys.map((y) => {
    let n = 0, sum = 0, max = 0
    for (const r of used) {
      const pr = py.find((q) => q[x] === r[x]); const a = r[y]; const b = pr?.[y]
      if (typeof a === 'number' && typeof b === 'number' && a !== 0) { const e = Math.abs(b - a) / Math.abs(a); n++; sum += e; max = Math.max(max, e) }
    }
    return { y, n, mean: n ? sum / n : null, max: n ? max : null }
  }).filter((r) => r.n > 0)
  if (!rows.length) return null
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Python vs Aspen at the dataset points</h3>
      <div className="table-scroll"><table className="data"><thead><tr><th scope="col">Quantity</th><th scope="col" className="r">Points</th><th scope="col" className="r">Mean |relative deviation|</th><th scope="col" className="r">Max |relative deviation|</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.y}><td title={r.y}>{metricLabel(r.y)}</td><td className="r">{r.n}</td><td className="r">{r.mean === null ? 'n/a' : `${(r.mean * 100).toFixed(2)} %`}</td><td className="r">{r.max === null ? 'n/a' : `${(r.max * 100).toFixed(2)} %`}</td></tr>)}</tbody></table></div>
      <p className="muted">Deviation of the Python model from the Aspen result, relative to Aspen. Computed in the browser from the plotted data.</p>
    </div>
  )
}

function SweepResults({ sweeps, clear }: { sweeps: SweepResult[]; clear: () => void }) {
  const last = sweeps[0]
  const cols = useMemo(() => Object.keys(last.rows[0] ?? {}), [last])
  const { used, excluded } = useMemo(() => splitConverged(last.rows, cols), [last, cols])
  const ys = useMemo(() => defaultYs(cols, used, last.variable), [cols, used, last])
  const data = (y: string) => mergeSeries([{ prefix: 's', rows: used }], last.variable, y)
  const tbl: Column<DataRow>[] = cols.filter((c) => c !== 'source').map((c) => ({ key: c, label: c, align: typeof last.rows[0][c] === 'number' ? 'right' : 'left',
    render: (r: DataRow) => typeof r[c] === 'number' ? <span>{fmt(r[c] as number)}</span> : <span>{r[c] === null ? 'n/a' : String(r[c])}</span>, csv: (r: DataRow) => String(r[c] ?? '') }))
  return (
    <div className="page-block">
      <div className="card section-h"><h2>New sweep #{last.id}: {last.variable} <SourceBadge source={last.source} /></h2>
        <span>{excluded ? <StatusPill kind="warn">{excluded} non-converged excluded</StatusPill> : <StatusPill kind="ok">{used.length} points</StatusPill>} <button type="button" className="btn btn-sm" onClick={clear}>Clear sweeps</button></span></div>
      <p className="muted">{last.source === 'python_model' ? 'Python model sweep (not an Aspen run).' : 'Aspen Plus V15 sweep.'} If the variable matches the x variable of the dataset above, the sweep is also drawn over its charts.</p>
      <div className="grid-2">{ys.map((y) => (
        <SensChart key={y} title={`${metricName(y)} vs ${metricName(last.variable)}`} xLabel={axisLabel(last.variable)} yLabel={axisLabel(y)} data={data(y)}
          series={[{ key: `s|${y}`, label: `Sweep #${last.id} (${last.engine})`, color: COL_S[0], dots: true, source: last.source }]} />))}</div>
      <DataTable columns={tbl} rows={last.rows} caption={`Sweep #${last.id} results`} filename={`sweep_${last.variable}.csv`} />
    </div>
  )
}

