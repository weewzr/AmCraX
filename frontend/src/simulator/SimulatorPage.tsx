import { lazy, Suspense, useCallback, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { withBase } from '../api/url'
import { useJson } from '../site/data'
import { inputRanges, loadSimulatorData, type SimData } from '../sim'
import { Controls } from './Controls'
import { baselineState, exportCSV, exportJSON, exportName, INPUT_UNITS, PRESETS, presetMatches, presetState, reducer, runCase, SOURCE_TEXT, type SimState } from './model'
import { FactList, KpiStrip, OutputList, SimBadge } from './Outputs'
import { Pfd } from './Pfd'
import { itemStatus, SPECIES_COLOR, STREAM_NAMES, streamViews, UNIT_LIMITS, UNITS, unitViews } from './pfdData'
import { StoredPurification } from './StoredPurification'
import { Tour } from './Tour'
import { TOUR_STEPS } from './tourSteps'
import './simulator.css'
import './print.css'

// Recharts and the sweeps load as a separate chunk, and only when the graphs come near the viewport (or on request),
// so the landing page does not download the chart library before the visitor scrolls to it.
const Graphs = lazy(() => import('./Graphs'))

function WhenNear({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const [near, setNear] = useState(() => typeof IntersectionObserver === 'undefined')
  useEffect(() => {
    const el = ref.current
    if (near || !el) return
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) setNear(true) }, { rootMargin: '400px 0px' })
    io.observe(el)
    return () => io.disconnect()
  }, [near])
  if (near) return <>{children}</>
  return (
    <section ref={ref} className="sim-graphs-wait" aria-label="Graphs">
      <p>Eight graphs follow the controls: conversion and duties against temperature, reactor profiles, the catalyst comparison and the cost breakdown. They load when you scroll here, so that the page opens without the chart library.</p>
      <button type="button" className="btn" onClick={() => setNear(true)}>Load the graphs now</button>
    </section>
  )
}

interface FuelCase { fuel_efficiency?: number; lcoh_USD_per_kg?: number; lcoh_SGD_per_kg?: number }
interface PsaCase { psa_recovery?: number; lcoh_USD_per_kg?: number; lcoh_SGD_per_kg?: number }
/** The stored fuel-efficiency envelope of the frozen baseline (reference_scenario/baseline.json, key fuel_efficiency_sensitivity)
 *  and its PSA-recovery sensitivity (key psa_recovery_sensitivity): the reference cost counts the supplementary ammonia fuel
 *  at 100 % of its LHV (optimistic) and assumes a PSA recovery of 0.85. Nothing is computed here. */
function FuelEnvelopeNote() {
  const b = useJson<{ fuel_efficiency_sensitivity?: { cases?: FuelCase[] }; psa_recovery_sensitivity?: { cases?: PsaCase[] } }>('/api/research/reference_scenario/baseline.json')
  const cases = b.phase === 'ready' ? (b.data.fuel_efficiency_sensitivity?.cases ?? []).filter((c) => typeof c.fuel_efficiency === 'number' && typeof c.lcoh_USD_per_kg === 'number') : []
  const psa = b.phase === 'ready' ? (b.data.psa_recovery_sensitivity?.cases ?? []).filter((c) => typeof c.psa_recovery === 'number' && typeof c.lcoh_USD_per_kg === 'number') : []
  if (!cases.length) return null
  const pc = (x: number) => `${Number((x * 100).toFixed(2))} %`
  return (
    <div className="sim-basis" data-testid="sim-fuel-envelope">
      <p className="sim-basis">The reference cost counts the supplementary ammonia fuel at 100 % of its lower heating value (optimistic). Stored envelope of the baseline cost:</p>
      <table className="sim-cmp sim-fuel-t" aria-label="Fuel-efficiency envelope of the baseline hydrogen cost">
        <thead><tr><th scope="col">Fuel heat delivered</th><th scope="col">USD/kg H2</th><th scope="col">SGD/kg H2</th></tr></thead>
        <tbody>{cases.map((c) => (
          <tr key={c.fuel_efficiency}><th scope="row">{pc(c.fuel_efficiency!)}{c.fuel_efficiency === 1 ? ' (reference, optimistic)' : ''}</th>
            <td className="sim-num">{c.lcoh_USD_per_kg!.toFixed(3)}</td><td className="sim-num">{typeof c.lcoh_SGD_per_kg === 'number' ? c.lcoh_SGD_per_kg.toFixed(3) : 'n/a'}</td></tr>
        ))}</tbody>
      </table>
      {psa.length ? (
        <div data-testid="sim-psa-sensitivity">
          <p className="sim-basis">PSA-recovery sensitivity of the same baseline: reference 0.85; 0.82 and 0.77 from the only published front for this gas composition, simulated at 8 to 12 bar.</p>
          <table className="sim-cmp sim-fuel-t" aria-label="PSA-recovery sensitivity of the baseline hydrogen cost">
            <thead><tr><th scope="col">PSA H2 recovery</th><th scope="col">USD/kg H2</th><th scope="col">SGD/kg H2</th></tr></thead>
            <tbody>{psa.map((c) => (
              <tr key={c.psa_recovery}><th scope="row">{c.psa_recovery!.toFixed(4)}{c.psa_recovery === 0.85 ? ' (reference assumption)' : ' (simulated front)'}</th>
                <td className="sim-num">{c.lcoh_USD_per_kg!.toFixed(3)}</td><td className="sim-num">{typeof c.lcoh_SGD_per_kg === 'number' ? c.lcoh_SGD_per_kg.toFixed(3) : 'n/a'}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}

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
  return <SimulatorFromUrl d={data} />
}

/** "#/?preset=<id>" (used by the command palette) opens a stored scenario; an unknown or non-matching id opens the baseline. */
function SimulatorFromUrl({ d }: { d: SimData }) {
  const [params] = useSearchParams()
  const want = params.get('preset')
  const preset = want && presetMatches(d, want) ? want : null
  return <Simulator key={preset ?? 'baseline'} d={d} preset={preset} />
}

function Simulator({ d, preset: initialPreset }: { d: SimData; preset: string | null }) {
  const [s, dispatch] = useReducer(reducer, d, (dd: SimData) => (initialPreset ? presetState(dd, initialPreset) : baselineState(dd)))
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
  const preset = PRESETS.find((p) => p.id === s.preset)
  const [showValues, setShowValues] = useState(() => !(typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia('(max-width:700px)').matches))
  const [tour, setTour] = useState<number | null>(null)
  const [auto, setAuto] = useState(false)
  const tourBtn = useRef<HTMLButtonElement>(null)
  const box = useRef<HTMLDivElement>(null)
  const [overflow, setOverflow] = useState(false)

  // the diagram box is a named, focusable scroll region only when it overflows (C11)
  useEffect(() => {
    const el = box.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => setOverflow(el.scrollWidth - el.clientWidth > 1))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  /** select an item and bring it into view inside the diagram box (list view, Inspect select, tour) */
  const reveal = useCallback((id: string) => {
    const el = box.current?.querySelector<SVGGElement>(`[data-unit="${id}"], [data-stream="${id}"]`)
    if (el && box.current && box.current.scrollWidth > box.current.clientWidth + 1) {
      const br = box.current.getBoundingClientRect(), er = el.getBoundingClientRect()
      const target = box.current.scrollLeft + (er.left - br.left) - (br.width - er.width) / 2
      box.current.scrollTo({ left: Math.max(0, target), behavior: reduced ? 'auto' : 'smooth' })
    }
  }, [reduced])
  const onSelect = useCallback((id: string) => setSelected(id), [])
  const pick = (id: string) => { setSelected(id); window.requestAnimationFrame(() => reveal(id)) }

  const setStep = useCallback((n: number) => { setTour(n); const st = TOUR_STEPS[n]; setSelected(st.unit); window.requestAnimationFrame(() => reveal(st.unit)) }, [reveal])
  const exitTour = useCallback(() => { setTour(null); setAuto(false); window.requestAnimationFrame(() => tourBtn.current?.focus()) }, [])

  const doExport = (kind: 'csv' | 'json') => {
    const cases = A ? [{ name: 'A', result: A }, { name: 'B', result: B }] : [{ name: 'current', result: B }]
    const stamp = new Date().toISOString()
    if (kind === 'json') download(exportName(s.preset, stamp, 'json'), exportJSON(cases, d, stamp), 'application/json')
    else download(exportName(s.preset, stamp, 'csv'), exportCSV(cases), 'text/csv')
  }

  const sel = selected ?? 'CRACKER'
  const isUnit = UNITS.some((u) => u.id === sel)
  const uv = isUnit ? units[sel] : null
  const sv = !isUnit ? streams[sel] : null
  const hiddenStream = !isUnit && !s.heat_integration && (sel === 'S3' || sel === 'S6')
  const tourFocus = tour !== null ? TOUR_STEPS[tour].focus : null

  return (
    <div className="sim-page">
      <div className="wrap sim-top">
        <div className="sim-title">
          <h1 className="sim-h1">AmCraX process simulator</h1>
          <p className="sim-lead">Ammonia cracking to hydrogen, solved in your browser from stored Aspen Plus V15 and Python results. Change a control: every number and graph follows.</p>
        </div>
        <div className="sim-toolbar" role="toolbar" aria-label="Simulator actions">
          {/* the scenario selector comes first (own full-width row on a phone); the buttons follow in .sim-actions */}
          <label className="sim-preset">
            <span className="sr-only">Preset scenario</span>
            <select value={s.preset ?? ''} onChange={(e) => { if (e.target.value) dispatch({ type: 'preset', data: d, id: e.target.value }) }} aria-label="Preset scenario (stored Aspen case)">
              <option value="">{s.preset ? 'Preset scenarios' : 'Custom case (edited)'}</option>
              {presets.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
          </label>
          <div className="sim-actions">
          <button type="button" className={`btn sim-play ${playing ? 'is-on' : ''}`} aria-pressed={playing} onClick={() => setPlaying((p) => !p)}>
            <svg viewBox="0 0 16 16" aria-hidden="true" width="14" height="14">{playing ? <path d="M4 3v10M12 3v10" stroke="currentColor" strokeWidth="2.6" /> : <path d="M4 2.5v11L13 8z" fill="currentColor" />}</svg>
            {playing ? 'Pause animation' : 'Play animation'}
          </button>
          <button type="button" ref={tourBtn} className={`btn sim-tour-btn ${tour !== null ? 'is-on' : ''}`} aria-pressed={tour !== null} onClick={() => (tour === null ? setStep(0) : exitTour())}>
            {tour === null ? `Take the tour (${TOUR_STEPS.length} steps)` : 'Exit the tour'}
          </button>
          <label className="sim-valtoggle">
            <input type="checkbox" role="switch" checked={showValues} aria-checked={showValues} onChange={(e) => setShowValues(e.target.checked)} />
            <span>Show values</span>
          </label>
          <button type="button" className="btn" onClick={() => dispatch({ type: 'reset', data: d })}>Reset to baseline</button>
          {pinned
            ? <button type="button" className="btn sim-pin is-on" onClick={() => setPinned(null)}>Stop comparing</button>
            : <button type="button" className="btn sim-pin" onClick={() => setPinned(s)}>Compare: pin as case A</button>}
          <button type="button" className="btn" onClick={() => doExport('csv')} title="CSV: inputs and outputs, one row each, with the source of every output" aria-describedby="sim-exp-help">Export CSV</button>
          <button type="button" className="btn" onClick={() => doExport('json')} title="JSON: inputs, outputs with sources, fixed values, basis and warnings" aria-describedby="sim-exp-help">Export JSON</button>
          <span id="sim-exp-help" className="sr-only">CSV: inputs and outputs with the source of every output. JSON: the same plus fixed values, cost basis and warnings. Case A and case B when comparing.</span>
          </div>
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
          {preset ? <p className="sim-preset-about" data-preset-about={preset.id}>{preset.about}</p> : null}
          <table className="sim-print-only sim-print-inputs" aria-hidden="true">
            <caption>Inputs of this case (steady state, computed in the browser)</caption>
            <tbody>{(Object.keys(s) as (keyof SimState)[]).filter((k) => k !== 'preset').map((k) => <tr key={k}><th>{k}</th><td>{String(s[k])}{INPUT_UNITS[k] ? ` ${INPUT_UNITS[k]}` : ''}</td></tr>)}</tbody>
          </table>
          <KpiStrip c={B} route={s.nh3_route} />
          <p className="sim-scroll-hint">Scroll sideways; tap an item for its values.</p>
          <ul className="sim-legend-html" aria-label="Diagram legend">
            {(['NH3', 'H2', 'N2', 'H2O', 'O2'] as const).map((k) => <li key={k}><i style={{ background: SPECIES_COLOR[k] }} aria-hidden="true" />{k}</li>)}
            <li className="sim-legend-txt">Dots: colour shows the species, density the molar flow.{showValues ? ' Values: streams kmol/h, units kW; A Aspen, G Aspen grid, B browser model, E extrapolation, S assumed, L statutory. The flue-gas cooler shows the burner heat credited, not an exchanger duty.' : ''}</li>
          </ul>
          <div className="sim-pfd-box" ref={box} {...(overflow ? { tabIndex: 0, role: 'region', 'aria-label': 'Process flow diagram, scrolls sideways' } : {})}>
            <Pfd c={B} d={d} playing={playing} selected={sel} onSelect={onSelect} showValues={showValues} focus={tourFocus} />
          </div>
          <p className="sim-caption" id="sim-caption">
            The animation shows the direction and the relative size of the flows of the steady-state solution; it is not a transient simulation.
            Dot colour marks the species, dot density the computed molar flow; in the reactor the colour follows the computed conversion along the bed.
            {reduced ? <strong> Animation paused because your system asks for reduced motion; press Play to start it.</strong> : null}
          </p>
          {tour !== null ? <Tour step={tour} setStep={setStep} onExit={exitTour} c={B} units={units} auto={auto} setAuto={setAuto} reduced={reduced} /> : null}
          <div className="sim-detail" aria-live="polite">
            <div className="sim-detail-head">
              <label htmlFor="sim-inspect">Inspect</label>
              <select id="sim-inspect" value={sel} onChange={(e) => pick(e.target.value)}>
                <optgroup label="Equipment">{UNITS.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.tag})</option>)}</optgroup>
                <optgroup label="Streams">{Object.entries(STREAM_NAMES).map(([id, n]) => <option key={id} value={id}>{id} - {n.name}</option>)}</optgroup>
              </select>
            </div>
            <details className="sim-list">
              <summary>List view: every unit and stream with its status</summary>
              <ul>
                {[...UNITS.map((u) => ({ id: u.id, name: `${u.name} (${u.tag})` })), ...Object.entries(STREAM_NAMES).map(([id, n]) => ({ id, name: `${id}: ${n.name}` }))].map((it) => (
                  <li key={it.id}><button type="button" className={`sim-list-btn ${sel === it.id ? 'is-on' : ''}`} aria-pressed={sel === it.id} onClick={() => pick(it.id)}>
                    <span>{it.name}</span><span className="sim-list-st">{itemStatus(it.id, B, units, streams)}</span></button></li>
                ))}
              </ul>
            </details>
            {uv ? (
              <div className="sim-panel" data-panel={uv.id}>
                <h3>{uv.title}{uv.bypassed ? <span className="sim-flag"> bypassed</span> : null}{uv.notModelled ? <span className="sim-flag"> not modelled</span> : null}</h3>
                <p>{uv.what}</p>
                <FactList facts={uv.facts} />
                <p className="sim-unit-lim"><strong>Limitation.</strong> {UNIT_LIMITS[uv.id]} <strong>Sources.</strong> <Link to="/methodology">Methodology</Link>, <Link to="/hypotheses/aspen-evidence">Aspen Evidence</Link>.</p>
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
          {s.purification === 'membrane' ? <StoredPurification sp={d.model.purification.stored_comparison} /> : null}
          <p className="sim-print-row"><button type="button" className="btn sim-print-btn" onClick={() => window.print()}>Print summary</button>
            <span>A4 page: inputs, key results with sources, outputs, warnings and basis.</span></p>
          {B.out.warnings.length ? (
            <details className="sim-warnings" open={!compact}>
              <summary>Domain notes ({B.out.warnings.length})</summary>
              <ul>{B.out.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </details>
          ) : null}
          <p className="sim-basis">Costs: <strong>{d.model.economics.basis_short}</strong>, CAPEX method {d.model.economics.capex_reference.method} (cost year {d.model.economics.capex_reference.cost_year}); {d.model.economics.cost_basis}.
            {' '}SGD at {d.model.fx.SGD_per_USD} SGD/USD (ECB reference rate of {String(d.model.fx.date)}). Catalyst prices in the kinetic modes are derived from metal content, not supplier quotations; the equilibrium reactor has no catalyst choice and uses the reference inventory at the Phase 1 TEA Ni price, as the reference scenario does.</p>
          <FuelEnvelopeNote />
        </section>
      </div>

      <div className="wrap">
        <WhenNear>
          <Suspense fallback={<p className="sim-graphs-loading" role="status">Preparing the graphs</p>}>
            <Graphs d={d} b={B} a={A} />
          </Suspense>
        </WhenNear>
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
          pressure is an extrapolation and is labelled so. Hydrogen purity follows from an assumed PSA recovery and nitrogen slip. Costs follow the {d.model.economics.basis_short} (CAPEX method {d.model.economics.capex_reference.method}, cost year {d.model.economics.capex_reference.cost_year}), at {d.model.fx.SGD_per_USD} SGD/USD (ECB reference rate of {String(d.model.fx.date)}); the browser calculation is a port of <code>amcrax.economics.singapore.evaluate</code>. Catalyst prices are derived from metal content (a price per kg of metal times the loading, plus a non-metal term from one published cost estimate); no supplier quotation exists for any of these catalysts.
          Hypothetical carbon prices are not Singapore law. More in <Link to="/methodology">Methodology</Link> and <Link to="/hypotheses/validation">Validation</Link>.</p>
      </div>
    </details>
  )
}
