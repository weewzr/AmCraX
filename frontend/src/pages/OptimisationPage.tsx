import { useMemo, useState } from 'react'
import { Legend, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import '../features/common/features.css'
import { fetchData, fetchGrid, runOptimisation, type ConflictPair, type OptResult, type ParetoFile, type Row } from '../api/optimisation'
import { DataTable, type Column } from '../components/DataTable'
import { SourceBadge, StatusPill, Value } from '../components/ui'
import { useData } from '../data/DataContext'
import { fmt, fmtPct } from '../data/format'
import { humaniseKeys, metricLabel, metricName, metricUnit } from '../data/metrics'
import { AsyncView, ModeGate, Notice } from '../features/common/Notice'
import { useAsync } from '../features/common/useAsync'
import { axisProps, ChartFrame, grid, tipStyle } from '../features/economics/charts'
import { atBoundList, frontSeries, heatmap, INPUT_COLS, normaliseGridRows, normaliseSingle, numericColumns } from '../features/optimisation/shape'
import '../features/optimisation/optimisation.css'

const OBJ_LABEL: Record<string, string> = { min_lcoh: 'Minimise LCOH', max_lhv_efficiency: 'Maximise LHV efficiency', min_specific_heat: 'Minimise specific heat demand', max_h2_production: 'Maximise H2 production', max_conversion: 'Maximise NH3 conversion' }
const OBJECTIVES = ['min_lcoh', 'max_lhv_efficiency', 'min_specific_heat', 'max_h2_production', 'max_conversion']

export default function OptimisationPage() {
  const { mode, phase } = useData()
  const live = mode === 'LIVE' && phase === 'ready'
  const readable = (mode === 'LIVE' || mode === 'SNAPSHOT') && phase === 'ready'
  const single = useAsync((s) => fetchData<unknown>('single_objective', s), [], readable)
  const pareto = useAsync((s) => fetchData<ParetoFile>('pareto.json', s), [], readable)
  const conf = useAsync((s) => fetchData<ParetoFile['conflicts']>('objective_conflicts', s), [], readable)
  const gridA = useAsync((s) => fetchGrid(s), [], readable)
  const verif = useAsync((s) => fetchData<unknown>('aspen_verification', s), [], readable)
  const [extra, setExtra] = useState<OptResult[]>([])
  const stored = single.phase === 'ready' ? normaliseSingle(single.data) : []
  return (
    <section className="page">
      <h1>Optimisation</h1>
      <p className="lead">Single-objective optima and multi-objective trade-offs found with the independent Python process model (reduced-order, equilibrium cracker). Optima are candidates: only the table "Verified in Aspen Plus" carries Aspen Plus results.</p>
      <ModeGate what="Running a new optimisation" />
      <AsyncView a={single} what="Single-objective results">{() => stored.length ? <SingleSection list={stored} /> : <Notice kind="warn" title="No results in file.">single_objective.json contains no recognisable optimisation result.</Notice>}</AsyncView>
      <VerifiedSection a={verif} />
      <AsyncView a={gridA} what="Design grid">{(rows) => <HeatCard rows={normaliseGridRows(rows)} />}</AsyncView>
      <AsyncView a={pareto} what="Pareto fronts and objective conflicts">{(p) => <ParetoSection p={{ ...p, conflicts: p.conflicts ?? conf.data ?? undefined }} />}</AsyncView>
      <RunForm live={live} defaults={stored[0]} onResult={(r) => setExtra((e) => [r, ...e])} />
      {extra.map((r) => <div key={`new-${r.created_utc ?? ''}`}><Notice title="New run (not stored).">Result of a run requested from this page; it is not written to results/optimisation.</Notice><ResultCard r={r} /></div>)}
    </section>
  )
}

function SingleSection({ list }: { list: OptResult[] }) {
  const objs = [...new Set(list.map((r) => r.objective))]
  const [sel, setSel] = useState<string>('min_lcoh')
  const shown = list.filter((r) => sel === 'all' || r.objective === sel)
  return (
    <>
      <div className="chips" role="group" aria-label="Objective filter">
        <button type="button" className="chip" aria-pressed={sel === 'all'} onClick={() => setSel('all')}>all ({list.length})</button>
        {objs.map((o) => <button key={o} type="button" className="chip" aria-pressed={sel === o} onClick={() => setSel(o)} title={o}>{OBJ_LABEL[o] ?? o}</button>)}
      </div>
      <div className="opt-cards">{shown.map((r, i) => <ResultCard key={r.id ?? `${r.objective}-${i}`} r={r} />)}</div>
    </>
  )
}

function mval(m: Record<string, unknown> | undefined, k: string): number | null { const v = m?.[k]; return typeof v === 'number' ? v : null }

function ResultCard({ r }: { r: OptResult }) {
  const src = r.source === 'aspen_plus_v15' ? 'aspen_plus_v15' : 'python_model'
  const imp = r.improvement
  const bound = atBoundList(r)
  const lims = [...(r.model_limitation ?? []), ...(r.limitations ?? [])]
  return (
    <article className="card opt-card">
      <div className="section-h"><h2>{humaniseKeys(r.label)} <SourceBadge source={src} /></h2>
        {r.solver ? (r.solver.feasible ? <StatusPill kind="ok">feasible optimum</StatusPill> : <StatusPill kind="error">no feasible point</StatusPill>) : null}</div>
      {r.variant ? <p className="muted" style={{ margin: '4px 0' }}>Variant: {r.variant}</p> : null}
      <dl className="kv">
        <dt>Optimum ({metricLabel(r.metric)})</dt><dd><Value v={imp?.optimum ?? null} digits={3} source={src} /> <span className="muted">vs baseline</span> <Value v={imp?.baseline ?? null} digits={3} source={src} showSource={false} /></dd>
        <dt>Improvement</dt><dd>{imp ? <>{fmtPct(imp.delta_rel, 2)} ({fmt(imp.delta, 3)} absolute) {imp.better ? <StatusPill kind="ok">better than baseline</StatusPill> : <StatusPill kind="warn">not better</StatusPill>}</> : 'n/a'}</dd>
        <dt>Bounds at optimum</dt><dd>{bound.length ? <StatusPill kind="warn">at bound: {bound.map((b) => b.replace(/^[a-zA-Z0-9_]+/, (k) => metricName(k))).join('; ')}</StatusPill> : <StatusPill kind="ok">interior</StatusPill>}</dd>
        {r.driver ? <><dt>What drives it</dt><dd className="wrap-cell">{humaniseKeys(r.driver)}</dd></> : null}
      </dl>
      <table className="data compact"><thead><tr><th scope="col">Decision variable</th><th scope="col" className="r">Lower</th><th scope="col" className="r">Optimum</th><th scope="col" className="r">Upper</th><th scope="col">At bound</th></tr></thead>
        <tbody>{Object.entries(r.decision_variables).map(([k, v]) => (
          <tr key={k}><td title={v.bounds_basis ?? k}>{metricName(k)} <span className="unit">[{v.unit ?? metricUnit(k)}]</span></td>
            <td className="r"><Value v={v.lower} source="assumption" showSource={false} /></td><td className="r"><strong><Value v={v.optimum} source={src} showSource={false} /></strong></td><td className="r"><Value v={v.upper} source="assumption" showSource={false} /></td>
            <td>{v.at_bound ? <StatusPill kind="warn">{String(v.at_bound)}</StatusPill> : <span className="muted">no</span>}</td></tr>))}</tbody></table>
      {r.constraints ? (
        <details><summary>Constraints (g &gt;= 0 satisfied){r.constraints.active?.length ? `; active: ${r.constraints.active.join(', ')}` : '; none active'}</summary>
          <ul>{Object.entries(r.constraints.values_at_optimum ?? {}).map(([k, v]) => <li key={k}><strong>{k}</strong>: g = <Value v={v} digits={4} source={src} showSource={false} /> {typeof v === 'number' && v < -1e-9 ? <StatusPill kind="error">violated</StatusPill> : <StatusPill kind="ok">satisfied</StatusPill>}<div className="muted">{r.constraints?.definitions?.[k]}</div></li>)}</ul>
          <p className="muted">Settings: {Object.entries(r.constraints.settings ?? {}).map(([k, v]) => `${k} = ${v === null ? 'off' : String(v)}`).join('; ')}. Constraint thresholds are design assumptions.</p></details>) : null}
      {r.solver ? <p className="muted">Solver: {r.solver.method}; {r.solver.model_runs ?? 'n/a'} model runs, {r.solver.model_failures ?? 0} failures; {r.solver.de_message ?? ''}</p> : null}
      {r.flatness ? <details><summary>How flat is the optimum? (range of each variable within 1 % of the optimum)</summary>
        <ul>{Object.entries(r.flatness).map(([k, f]) => <li key={k}>{metricName(k)}: {f?.range_within_tol ? `${fmt(f.range_within_tol[0])} to ${fmt(f.range_within_tol[1])} (${fmtPct(f.fraction_of_bound_range, 0)} of the bound range)` : 'n/a'}</li>)}</ul></details> : null}
      {lims.length ? <details className="card notice notice-warn"><summary><strong>Model limitations ({lims.length})</strong> - reduced-order Python model, optimum unverified until re-solved in Aspen</summary><ul>{lims.map((l, k) => <li key={k}>{l}</li>)}</ul></details> : null}
      <p className="muted">Optimum metrics: LCOH <Value v={mval(r.optimum_metrics, 'lcoh_USD_per_kg')} unit="USD/kg" digits={2} source={src} showSource={false} />, carbon intensity <Value v={mval(r.optimum_metrics, 'carbon_intensity_kgCO2e_per_kgH2')} unit="kg CO2e/kg" digits={1} source={src} showSource={false} />, NH3 conversion <Value v={mval(r.optimum_metrics, 'nh3_conversion')} digits={3} source={src} showSource={false} />.</p>
    </article>
  )
}

interface VerifMetric { aspen: number | null; python: number | null; python_minus_aspen?: number | null; relative: number | null; class: 'primary' | 'secondary' | string }
interface VerifCandidate {
  id: string; label: string; case_id?: string; inputs?: Record<string, unknown>; status: string; aspen_converged?: boolean
  max_relative_deviation_primary: number | null; max_relative_deviation_primary_metric?: string
  max_relative_deviation_secondary: number | null; max_relative_deviation_secondary_metric?: string
  metrics?: Record<string, VerifMetric>
}
interface VerifFile { created_utc?: string; description?: string; criterion?: string; tolerance_relative?: number; primary_metrics?: string[]; candidates?: VerifCandidate[] }
const INPUT_SHOW = ['reactor_temperature_C', 'reactor_pressure_bar', 'psa_h2_recovery', 'fehe_hot_end_approach_K']

function VerifiedSection({ a }: { a: ReturnType<typeof useAsync<unknown>> }) {
  const [open, setOpen] = useState<string | null>(null)
  if (a.phase === 'loading') return <Notice>Loading Aspen verification ...</Notice>
  const v = a.phase === 'ready' ? (a.data as VerifFile) : null
  const cands = v?.candidates ?? []
  if (!v || !cands.length) {
    return <Notice kind="warn" title="Verified in Aspen Plus: not yet verified.">{a.phase === 'error' ? `results/optimisation/aspen_verification.json is not available (${a.error}). ` : ''}The optimum candidates have not been re-solved in Aspen Plus, so the Python optima above are unverified model results.</Notice>
  }
  const tol = v.tolerance_relative ?? null
  const nPass = cands.filter((c) => c.status === 'pass').length
  return (
    <div className="card"><div className="section-h"><h2>Verified in Aspen Plus V15 <SourceBadge source="aspen_plus_v15" /></h2>
      <span><StatusPill kind={nPass === cands.length ? 'ok' : 'warn'}>{nPass} of {cands.length} pass</StatusPill></span></div>
      <p className="muted">{v.description} Each candidate was re-solved as a full Aspen Plus V15 case; the Python-model optimum is compared with the Aspen result.</p>
      <p><strong>Criterion</strong> (tolerance {tol === null ? 'n/a' : fmtPct(tol, 1)} relative): {v.criterion}</p>
      <details><summary>Primary metrics judged ({v.primary_metrics?.length ?? 0})</summary><ul>{(v.primary_metrics ?? []).map((m) => <li key={m} title={m}>{metricLabel(m)}</li>)}</ul></details>
      <div className="table-scroll" style={{ maxHeight: 'none' }} tabIndex={0} role="region" aria-label="Aspen verification of optimisation candidates"><table className="data">
        <thead><tr><th scope="col">Candidate</th>{INPUT_SHOW.map((k) => <th key={k} scope="col" className="r" title={k}>{metricName(k)}<span className="unit"> [{metricUnit(k)}]</span></th>)}
          <th scope="col">Status</th><th scope="col" className="r">Max primary deviation</th><th scope="col" className="r">Max secondary deviation</th><th scope="col"><span className="sr-only">Details</span></th></tr></thead>
        <tbody>{cands.map((c) => (
          <VerifRows key={c.id} c={c} open={open === c.id} toggle={() => setOpen(open === c.id ? null : c.id)} tol={tol} />))}</tbody></table></div>
      <p className="muted">Pass = Aspen converged and every primary metric agrees within the tolerance. Secondary metrics are reported, not judged. Created {v.created_utc ?? 'n/a'}.</p>
    </div>
  )
}

function VerifRows({ c, open, toggle, tol }: { c: VerifCandidate; open: boolean; toggle: () => void; tol: number | null }) {
  const pass = c.status === 'pass'
  const ms = Object.entries(c.metrics ?? {})
  return (
    <>
      <tr>
        <td><strong>{humaniseKeys(c.label)}</strong> <span className="muted">({c.id})</span></td>
        {INPUT_SHOW.map((k) => <td key={k} className="r"><Value v={typeof c.inputs?.[k] === 'number' ? (c.inputs?.[k] as number) : null} digits={k === 'psa_h2_recovery' ? 3 : 1} source="python_model" showSource={false} /></td>)}
        <td>{pass ? <StatusPill kind="ok">pass</StatusPill> : <StatusPill kind="error">{c.status}</StatusPill>}</td>
        <td className="r"><span title={c.max_relative_deviation_primary_metric}>{fmtPct(c.max_relative_deviation_primary, 2)}</span><div className="muted small">{c.max_relative_deviation_primary_metric ? metricName(c.max_relative_deviation_primary_metric) : ''}</div></td>
        <td className="r"><span title={c.max_relative_deviation_secondary_metric}>{fmtPct(c.max_relative_deviation_secondary, 2)}</span><div className="muted small">{c.max_relative_deviation_secondary_metric ? metricName(c.max_relative_deviation_secondary_metric) : ''}</div></td>
        <td><button type="button" className="btn btn-sm" aria-expanded={open} onClick={toggle}>{open ? 'Hide metrics' : `Metrics (${ms.length})`}</button></td>
      </tr>
      {open ? (
        <tr><td colSpan={INPUT_SHOW.length + 5}>
          <table className="data compact"><thead><tr><th scope="col">Metric</th><th scope="col">Class</th><th scope="col" className="r">Aspen Plus V15</th><th scope="col" className="r">Python model</th><th scope="col" className="r">Relative deviation</th><th scope="col">Within tolerance</th></tr></thead>
            <tbody>{ms.map(([k, m]) => {
              const ok = tol === null || m.relative === null ? null : Math.abs(m.relative) <= tol
              return (
                <tr key={k}><td title={k}>{metricLabel(k)}</td><td>{m.class}</td>
                  <td className="r"><Value v={m.aspen} digits={4} source="aspen_plus_v15" showSource={false} /></td>
                  <td className="r"><Value v={m.python} digits={4} source="python_model" showSource={false} /></td>
                  <td className="r">{fmtPct(m.relative, 2)}</td>
                  <td>{m.class !== 'primary' ? <span className="muted">not judged</span> : ok === null ? 'n/a' : ok ? <StatusPill kind="ok">pass</StatusPill> : <StatusPill kind="error">fail</StatusPill>}</td></tr>)
            })}</tbody></table>
        </td></tr>) : null}
    </>
  )
}
function HeatCard({ rows }: { rows: Row[] }) {
  const metrics = useMemo(() => numericColumns(rows).filter((k) => !INPUT_COLS.includes(k)), [rows])
  const [xk, setX] = useState(INPUT_COLS[0]); const [yk, setY] = useState(INPUT_COLS[1])
  const [metric, setMetric] = useState('lcoh_USD_per_kg'); const [agg, setAgg] = useState<'min' | 'max' | 'mean'>('min'); const [feas, setFeas] = useState(true)
  const h = useMemo(() => heatmap(rows, xk, yk, metric, agg, feas), [rows, xk, yk, metric, agg, feas])
  if (!rows.length) return <Notice kind="warn">The design grid is empty.</Notice>
  const col = (v: number | null) => v === null || h.min === null || h.max === null ? 'transparent' : `color-mix(in srgb, var(--primary) ${Math.round(12 + 70 * (h.max === h.min ? 0 : (v - h.min) / (h.max - h.min)))}%, var(--surface))`
  return (
    <div className="card"><div className="section-h"><h2>Design landscape <SourceBadge source="python_model" /></h2><span className="muted">{rows.length} grid points, each a Python-model evaluation</span></div>
      <div className="controls">
        <label className="field">X axis<select value={xk} onChange={(e) => setX(e.target.value)}>{INPUT_COLS.map((k) => <option key={k} value={k}>{metricLabel(k)}</option>)}</select></label>
        <label className="field">Y axis<select value={yk} onChange={(e) => setY(e.target.value)}>{INPUT_COLS.map((k) => <option key={k} value={k}>{metricLabel(k)}</option>)}</select></label>
        <label className="field">Metric<select value={metric} onChange={(e) => setMetric(e.target.value)}>{metrics.map((k) => <option key={k} value={k}>{metricLabel(k)}</option>)}</select></label>
        <label className="field">Over other variables<select value={agg} onChange={(e) => setAgg(e.target.value as 'min' | 'max' | 'mean')}><option value="min">minimum</option><option value="max">maximum</option><option value="mean">mean</option></select></label>
        <label className="field"><span>Feasible points only</span><input type="checkbox" checked={feas} onChange={(e) => setFeas(e.target.checked)} style={{ width: 20 }} /></label>
      </div>
      {xk === yk ? <Notice kind="warn">Choose two different variables for the X and Y axes.</Notice> : (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Design landscape heat map"><table className="heat"><thead><tr><th scope="col">{metricName(yk)} \ {metricName(xk)}</th>{h.xs.map((x) => <th scope="col" key={x} className="r">{fmt(x)}</th>)}</tr></thead>
          <tbody>{h.ys.map((y) => <tr key={y}><th scope="row" className="r">{fmt(y)}</th>{h.xs.map((x) => { const c = h.cells.find((q) => q.x === x && q.y === y); return <td key={x} className="r" style={{ background: col(c?.value ?? null) }} title={`n = ${c?.n ?? 0}`}>{c?.value === null || c === undefined ? 'n/a' : fmt(c.value, 3)}</td> })}</tr>)}</tbody></table></div>)}
      <p className="muted">Colour: low to high value of {metricLabel(metric)} ({h.min === null ? 'n/a' : fmt(h.min, 3)} to {h.max === null ? 'n/a' : fmt(h.max, 3)}); "n/a" = no feasible grid point. Numbers are Python-model values, not Aspen.</p>
    </div>
  )
}

function ParetoSection({ p }: { p: ParetoFile }) {
  const fronts = (p.fronts ?? []).filter((f) => f.objectives.length === 2 && f.points.length)
  const [i, setI] = useState(0)
  const f = fronts[Math.min(i, fronts.length - 1)]
  const s = f ? frontSeries(f) : null
  const pairs: ConflictPair[] = p.conflicts?.pairs ?? []
  const pcols: Column<ConflictPair>[] = [
    { key: 'pair', label: 'Objective pair', render: (c) => c.pair.map(metricName).join(' vs '), csv: (c) => c.pair.join(' vs ') },
    { key: 'spearman_rho_min_sense', label: 'Spearman rho', align: 'right', render: (c) => fmt(c.spearman_rho_min_sense, 2) },
    { key: 'n_distinct_non_dominated', label: 'Distinct non-dominated', align: 'right' },
    { key: 'classification', label: 'Classification', render: (c) => <StatusPill kind={c.classification === 'conflict' ? 'warn' : 'neutral'}>{c.classification}</StatusPill> },
  ]
  return (
    <div className="grid-2">
      {f && s ? (
        <div>
          <div className="controls" style={{ marginBottom: 8 }}><label className="field">Front<select value={i} onChange={(e) => setI(Number(e.target.value))}>{fronts.map((x, k) => <option key={k} value={k}>{x.objectives.map(metricName).join(' vs ')} - {x.overlay}</option>)}</select></label></div>
          <ChartFrame title={`Pareto front: ${metricName(s.xk)} vs ${metricName(s.yk)}`} sources={['python_model']} height={340} description="Scatter of non-dominated design-grid points; feasible points as filled circles, constraint-violating points as crosses."
            note="Every point is a Python-model grid evaluation (no interpolation). Infeasible points violate a constraint (e.g. conversion below the design threshold).">
            <ScatterChart margin={{ top: 12, right: 24, bottom: 34, left: 24 }}>
              {grid}
              <XAxis type="number" dataKey="x" name={metricName(s.xk)} domain={['auto', 'auto']} {...axisProps} label={{ value: `${metricLabel(s.xk)} (${f.senses[0] === 'min' ? 'minimise' : 'maximise'})`, position: 'insideBottom', offset: -18, fill: 'var(--muted)' }} />
              <YAxis type="number" dataKey="y" name={metricName(s.yk)} domain={['auto', 'auto']} {...axisProps} label={{ value: `${metricLabel(s.yk)} (${f.senses[1] === 'min' ? 'minimise' : 'maximise'})`, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={tipStyle} />
              <Legend verticalAlign="top" height={36} />
              <Scatter name="feasible" data={s.feas} fill="var(--primary)" shape="circle" isAnimationActive={false} />
              <Scatter name="infeasible (constraint violated)" data={s.infeas} fill="var(--error)" shape="cross" isAnimationActive={false} />
            </ScatterChart>
          </ChartFrame>
        </div>) : <Notice kind="warn" title="No two-objective front in pareto.json.">{(p.fronts ?? []).length} fronts stored, none with two objectives and points.</Notice>}
      <div className="card"><h2>Objective conflicts</h2>
        <p className="muted">{p.conflicts?.method} {p.conflicts?.caveat} Grid: {p.n_grid_points ?? 'n/a'} points, {p.n_feasible ?? 'n/a'} feasible.</p>
        {pairs.length ? <DataTable columns={pcols} rows={pairs} caption="Pairwise conflict test" filename="objective_conflicts.csv" /> : <p className="muted">No conflict table stored.</p>}
      </div>
    </div>
  )
}

function RunForm({ live, defaults, onResult }: { live: boolean; defaults?: OptResult; onResult: (r: OptResult) => void }) {
  const [obj, setObj] = useState('min_lcoh'); const [method, setMethod] = useState('de')
  const [b, setB] = useState<Record<string, [string, string]>>({})
  const [c, setC] = useState({ conv: '', dt: '', self: false })
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null)
  const vars = Object.entries(defaults?.decision_variables ?? {}).map(([k, v]) => [k, v.lower, v.upper] as const)
  const submit = async () => {
    setBusy(true); setErr(null)
    try {
      const bounds: Record<string, [number, number]> = {}
      for (const [k, lo, hi] of vars) { const [l, h] = b[k] ?? ['', '']; if (l !== '' || h !== '') bounds[k] = [l !== '' ? Number(l) : lo, h !== '' ? Number(h) : hi] }
      const constraints: Record<string, number | boolean> = {}
      if (c.conv !== '') constraints.min_nh3_conversion = Number(c.conv)
      if (c.dt !== '') constraints.fehe_min_internal_dT_K = Number(c.dt)
      if (c.self) constraints.thermal_self_sufficiency = true
      const r = await runOptimisation({ objective: obj, method, bounds: Object.keys(bounds).length ? bounds : undefined, constraints: Object.keys(constraints).length ? constraints : undefined })
      onResult(r.result)
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }
  return (
    <div className="card"><h2>Run a new optimisation <SourceBadge source="python_model" /></h2>
      <p className="muted">Calls POST /api/optimisation/run (Python engine, no Aspen). Blank fields use the module defaults. A run takes some seconds.</p>
      <div className="controls">
        <label className="field">Objective<select value={obj} onChange={(e) => setObj(e.target.value)} disabled={!live}>{OBJECTIVES.map((o) => <option key={o} value={o}>{OBJ_LABEL[o] ?? o}</option>)}</select></label>
        <label className="field">Method<select value={method} onChange={(e) => setMethod(e.target.value)} disabled={!live}><option value="de">differential evolution</option><option value="grid">grid + SLSQP</option></select></label>
        {vars.map(([k, lo, hi]) => <span key={k} className="field">{k}
          <span><input type="number" aria-label={`${k} lower`} placeholder={String(lo)} value={b[k]?.[0] ?? ''} disabled={!live} onChange={(e) => setB((p) => ({ ...p, [k]: [e.target.value, p[k]?.[1] ?? ''] }))} style={{ width: 70 }} /> to <input type="number" aria-label={`${k} upper`} placeholder={String(hi)} value={b[k]?.[1] ?? ''} disabled={!live} onChange={(e) => setB((p) => ({ ...p, [k]: [p[k]?.[0] ?? '', e.target.value] }))} style={{ width: 70 }} /></span></span>)}
        <label className="field">Min NH3 conversion [-]<input type="number" step={0.01} min={0} max={1} placeholder="default" value={c.conv} disabled={!live} onChange={(e) => setC({ ...c, conv: e.target.value })} /></label>
        <label className="field">FEHE min dT [K]<input type="number" step={1} placeholder="default" value={c.dt} disabled={!live} onChange={(e) => setC({ ...c, dt: e.target.value })} /></label>
        <label className="field"><span>Thermal self-sufficiency</span><input type="checkbox" checked={c.self} disabled={!live} onChange={(e) => setC({ ...c, self: e.target.checked })} style={{ width: 20 }} /></label>
        <button type="button" className="btn" disabled={!live || busy} onClick={submit}>{busy ? 'Running ...' : 'Run optimisation'}</button>
      </div>
      {!vars.length ? <p className="muted">Bound fields appear once single_objective.json provides the variable list; the run still works with default bounds.</p> : null}
      {err ? <Notice kind="error" title="Run failed.">{err}</Notice> : null}
    </div>
  )
}



