import { lazy, Suspense, useCallback, useEffect, useMemo, useReducer, useState } from 'react'
import { Link } from 'react-router-dom'
import { withBase } from '../api/url'
import { inputRanges, loadSimulatorData, type SimData } from '../sim'
import { Controls } from './Controls'
import { baselineState, exportCSV, exportJSON, PRESETS, presetMatches, reducer, runCase, SOURCE_TEXT, type SimState } from './model'
import { FactList, KpiStrip, OutputList, SimBadge } from './Outputs'
import { Pfd } from './Pfd'
import { STREAM_NAMES, streamViews, UNITS, unitViews } from './pfdData'
import './simulator.css'

// Recharts and the sweeps load as a separate chunk, so the diagram and the controls appear first.
const Graphs = lazy(() => import('./Graphs'))

function useReducedMotion(): boolean {
  const q = '(prefers-reduced-motion: reduce)'
  const [r, setR] = useState(() => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(q).matches)
  useEffect(() => {
    const m = window.matchMedia(q)
    const on = () => setR(m.matches)
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [])
  return r
}

function useNarrow(max: number): boolean {
  const q = `(max-width:${max}px)`
  const [n, setN] = useState(() => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(q).matches)
  useEffect(() => { const m = window.matchMedia(q); const on = () => setN(m.matches); m.addEventListener('change', on); return () => m.removeEventListener('change', on) }, [q])
  return n
}

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = document.createElement('a')
  a.href = url; a.download = name
  document.body.appendChild(a); a.click(); a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 2000)
}

export default function SimulatorPage() {
  const [data, setData] = useState<SimData | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { loadSimulatorData().then(setData, (e: unknown) => setErr(String(e instanceof Error ? e.message : e))) }, [])
  if (err) return <div className="wrap sim-page"><h1 className="sim-h1">AmCraX process simulator</h1><p role="alert">The simulator data could not be loaded ({err}).</p></div>
  if (!data) return <div className="wrap sim-page"><h1 className="sim-h1">AmCraX process simulator</h1><p role="status">Loading the simulator data ...</p></div>
  return <Simulator d={data} />
}

function Simulator({ d }: { d: SimData }) {
  const [s, dispatch] = useReducer(reducer, d, baselineState)
  const [pinned, setPinned] = useState<SimState | null>(null)
  const reduced = useReducedMotion()
  const [playing, setPlaying] = useState(() => !reduced)
  const [selected, setSelected] = useState<string | null>('CRACKER')
  const compact = useNarrow(700)
  const ranges = useMemo(() => inputRanges(d), [d])
  const B = useMemo(() => runCase(s, d), [s, d])
  const A = useMemo(() => (pinned ? runCase(pinned, d) : null), [pinned, d])
  const presets = useMemo(() => PRESETS.filter((p) => presetMatches(d, p.id)), [d])
  const units = useMemo(() => unitViews(B, d), [B, d])
  const streams = useMemo(() => streamViews(B, d), [B, d])
  const onSelect = useCallback((id: string) => setSelected(id), [])
  const preset = PRESETS.find((p) => p.id === s.preset)

  const doExport = (kind: 'csv' | 'json') => {
    const cases = A ? [{ name: 'A', result: A }, { name: 'B', result: B }] : [{ name: 'current', result: B }]
    const stamp = new Date().toISOString()
    if (kind === 'json') download('amcrax_simulator_case.json', exportJSON(cases, d, stamp), 'application/json')
    else download('amcrax_simulator_case.csv', exportCSV(cases), 'text/csv')
  }

  const sel = selected ?? 'CRACKER'
  const isUnit = UNITS.some((u) => u.id === sel)
  const uv = isUnit ? units[sel] : null
  const sv = !isUnit ? streams[sel] : null
  const hiddenStream = !isUnit && !s.heat_integration && (sel === 'S3' || sel === 'S6')

  return (
    <div className="sim-page">
      <div className="wrap sim-top">
        <div className="sim-title">
          <h1 className="sim-h1">AmCraX process simulator</h1>
          <p className="sim-lead">Ammonia cracking to hydrogen, solved in your browser from stored Aspen Plus V15 and Python results. Change a control: every number and graph follows.</p>
        </div>
        <div className="sim-toolbar" role="toolbar" aria-label="Simulator actions">
          <button type="button" className={`btn sim-play ${playing ? 'is-on' : ''}`} aria-pressed={playing} onClick={() => setPlaying((p) => !p)}>
            <svg viewBox="0 0 16 16" aria-hidden="true" width="14" height="14">{playing ? <path d="M4 3v10M12 3v10" stroke="currentColor" strokeWidth="2.6" /> : <path d="M4 2.5v11L13 8z" fill="currentColor" />}</svg>
            {playing ? 'Pause' : 'Play'}<span className="sr-only"> flow animation</span>
          </button>
          <label className="sim-preset">
            <span className="sr-only">Preset scenario</span>
            <select value={s.preset ?? ''} onChange={(e) => { if (e.target.value) dispatch({ type: 'preset', data: d, id: e.target.value }) }} aria-label="Preset scenario (stored Aspen case)">
              <option value="">{s.preset ? 'Preset scenarios' : 'Custom case (edited)'}</option>
              {presets.map((p) => <option key={p.id} value={p.id}>{p.label} [{p.caseId}]</option>)}
            </select>
          </label>
          <button type="button" className="btn" onClick={() => dispatch({ type: 'reset', data: d })}>Reset to baseline</button>
          {pinned
            ? <button type="button" className="btn sim-pin is-on" onClick={() => setPinned(null)}>Stop comparing</button>
            : <button type="button" className="btn sim-pin" onClick={() => setPinned(s)}>Compare: pin as case A</button>}
          <button type="button" className="btn" onClick={() => doExport('csv')}>Export CSV</button>
          <button type="button" className="btn" onClick={() => doExport('json')}>Export JSON</button>
        </div>
      </div>

      <div className="wrap sim-grid">
        <aside className="sim-col sim-col-controls">
          <h2 className="sim-h2">Controls</h2>
          <Controls s={s} d={d} ranges={ranges} warnings={B.out.warnings} dispatch={dispatch} compact={compact} />
        </aside>

        <section className="sim-col sim-col-main" aria-labelledby="sim-pfd-h">
          <h2 id="sim-pfd-h" className="sr-only">Process flow diagram</h2>
          <div className="sim-status">
            {preset ? <span className="sim-case">Preset: {preset.label} <code>{preset.caseId}</code> ({preset.kind})</span> : <span className="sim-case">Custom case</span>}
            {pinned ? <span className="sim-case sim-case-a">Comparing with pinned case A</span> : null}
          </div>
          <KpiStrip c={B} />
          <div className="sim-pfd-box">
            <Pfd c={B} d={d} playing={playing} selected={sel} onSelect={onSelect} />
          </div>
          <p className="sim-scroll-hint">Scroll the diagram sideways to see the whole plant; tap a unit or a stream for its values.</p>
          <p className="sim-caption" id="sim-caption">
            The animation shows the direction and the relative size of the flows of the steady-state solution; it is not a transient simulation.
            Dot colour marks the species, dot density the computed molar flow; in the reactor the colour follows the computed conversion along the bed.
            {reduced ? <strong> Animation paused because your system asks for reduced motion; press Play to start it.</strong> : null}
          </p>
          <div className="sim-detail" aria-live="polite">
            <div className="sim-detail-head">
              <label htmlFor="sim-inspect">Inspect</label>
              <select id="sim-inspect" value={sel} onChange={(e) => setSelected(e.target.value)}>
                <optgroup label="Equipment">{UNITS.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.tag})</option>)}</optgroup>
                <optgroup label="Streams">{Object.entries(STREAM_NAMES).map(([id, n]) => <option key={id} value={id}>{id} - {n.name}</option>)}</optgroup>
              </select>
            </div>
            {uv ? (
              <div className="sim-panel" data-panel={uv.id}>
                <h3>{uv.title}{uv.bypassed ? <span className="sim-flag"> bypassed</span> : null}{uv.notModelled ? <span className="sim-flag"> not modelled</span> : null}</h3>
                <p>{uv.what}</p>
                <FactList facts={uv.facts} />
              </div>
            ) : sv ? (
              <div className="sim-panel" data-panel={sv.id}>
                <h3>Stream {sv.id}: {STREAM_NAMES[sv.id].name}</h3>
                <p>From {STREAM_NAMES[sv.id].from} to {STREAM_NAMES[sv.id].to}.{hiddenStream ? ' Not present: heat recovery is off.' : ''}</p>
                <FactList facts={sv.facts} />
                {sv.note ? <p className="muted small">{sv.note}</p> : null}
              </div>
            ) : null}
          </div>
        </section>

        <section className="sim-col sim-col-out" aria-labelledby="sim-out-h">
          <h2 id="sim-out-h" className="sim-h2">Live outputs{A ? ': case A against case B' : ''}</h2>
          <OutputList b={B} a={A} />
          {B.out.warnings.length ? (
            <details className="sim-warnings" open={!compact}>
              <summary>Domain notes ({B.out.warnings.length})</summary>
              <ul>{B.out.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </details>
          ) : null}
          <p className="sim-basis">Costs: {d.model.economics.basis === 'pre-unification' ? <strong>pre-unification basis</strong> : d.model.economics.basis} (Phase 1 equipment CAPEX), {d.model.economics.cost_basis}. SGD at {d.model.fx.SGD_per_USD} SGD/USD (rate date {String(d.model.fx.date)}).</p>
        </section>
      </div>

      <div className="wrap">
        <Suspense fallback={<p className="sim-graphs-loading" role="status">Preparing the graphs</p>}>
          <Graphs d={d} b={B} a={A} />
        </Suspense>
        <HowProduced d={d} />
      </div>
    </div>
  )
}

interface Parity { browser_vs_python?: { pfr_profiles?: { max_abs_conversion: number; max_abs_T_K: number; n_cases: number }; lcoh_max_rel?: number; process_on_grid_max_rel?: number }
  browser_vs_aspen?: { kinetic_summary?: { n: number; max_abs_conversion_diff_all: number; max_abs_duty_rel_isothermal: number }; equilibrium_grid?: { n: number; max_abs_conversion_diff_ideal_gas_vs_aspen_PR: number } } }

function HowProduced({ d }: { d: SimData }) {
  const [par, setPar] = useState<Parity | null>(null)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!open || par) return
    fetch(withBase('/snapshot/simulator/parity_report.json')).then((r) => (r.ok ? r.json() : null)).then((j) => setPar(j as Parity | null), () => setPar(null))
  }, [open, par])
  const pv = par?.browser_vs_python
  const pa = par?.browser_vs_aspen
  const g = (v: number | undefined, digits = 2) => (typeof v === 'number' ? v.toExponential(digits) : 'n/a')
  return (
    <details className="sim-how card" onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)} id="how-numbers">
      <summary><h2 className="sim-h2">How these numbers are produced</h2></summary>
      <div className="sim-how-body">
        <p>This is a <strong>static website</strong>. No Aspen Plus and no Python run while you use it. Stored on the site: the rate-law parameters and thermodynamic data
          exported from the AmCraX Python model, a grid of Python flowsheet results (17 temperatures x 9 pressures), {d.anchors.kinetic_cases.length} stored Aspen Plus V15 RPlug cases,
          {' '}{d.anchors.core_cases.length} stored Aspen core flowsheet cases and the Aspen RGibbs equilibrium grid.</p>
        <p>Computed in your browser: the plug-flow reactor (TypeScript port of the Python model), equilibrium, the reactor duty, hydrogen, tail gas and burner balance,
          economics and carbon intensity. Interpolated: pump, vaporiser, preheater, exchanger and cooler duties from the Python grid. When your inputs equal a stored Aspen case,
          the Aspen value is shown and labelled <SimBadge s="aspen" />. Labels: {Object.values(SOURCE_TEXT).join('; ')}.</p>
        <p>Check of the browser model against the Python model (numerical verification, not validation):
          {pv ? <> plug-flow profiles in {pv.pfr_profiles?.n_cases} cases agree to {g(pv.pfr_profiles?.max_abs_conversion)} in conversion and {g(pv.pfr_profiles?.max_abs_T_K)} K;
            process balance on grid nodes to {g(pv.process_on_grid_max_rel)} relative; LCOH to {g(pv.lcoh_max_rel)} relative.</> : ' open this section to load the figures from the parity report.'}
          {' '}Against stored Aspen results (comparison of two models, not validation):
          {pa ? <> {pa.kinetic_summary?.n} kinetic cases, largest conversion difference {pa.kinetic_summary?.max_abs_conversion_diff_all.toFixed(3)}, largest isothermal duty difference {((pa.kinetic_summary?.max_abs_duty_rel_isothermal ?? NaN) * 100).toFixed(1)} %;
            ideal-gas against Aspen Peng-Robinson equilibrium up to {pa.equilibrium_grid?.max_abs_conversion_diff_ideal_gas_vs_aspen_PR.toFixed(4)} in conversion.</> : null}
          {' '}<a href={withBase('/snapshot/simulator/parity_report.json')}>Parity report (JSON)</a>.</p>
        <p><strong>None of this is experimental validation.</strong> AmCraX has no independent experimental data. Most rate laws were fitted at 1 atm: every use at higher
          pressure is an extrapolation and is labelled so. Hydrogen purity follows from an assumed PSA recovery and nitrogen slip. Costs use the {d.model.economics.basis} Phase 1 basis.
          Hypothetical carbon prices are not Singapore law. More in <Link to="/methodology">Methodology</Link> and <Link to="/hypotheses/validation">Validation</Link>.</p>
      </div>
    </details>
  )
}
