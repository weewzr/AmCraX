import { useId, useMemo, useState } from 'react'
import { equilibriumAt, NASA7_PROVENANCE } from '../calc/equilibrium'
import { XYChart, type XYRow, type XYSeries } from '../features/common/XYChart'
import { ExecLabel } from './ui'
import { useRows } from './data'

interface AspenRow { T_C: number; P_bar: number; property_method: string; nh3_conversion: number }

export const T_MIN = 250
export const T_MAX = 900
export const P_MIN = 1
export const P_MAX = 40
const STEP_T = 5

/** Pure helper: rows of the chart (calculated curve + stored Aspen points + the selected point), conversion in %. */
export function buildChartRows(P: number, T: number, aspen: AspenRow[]): XYRow[] {
  const byT = new Map<number, XYRow>()
  for (let t = T_MIN; t <= T_MAX; t += STEP_T) byT.set(t, { T: t, calc: equilibriumAt(t, P).conversion * 100 })
  for (const r of aspen) {
    if (r.P_bar !== P || r.nh3_conversion === null) continue
    const row = byT.get(r.T_C) ?? { T: r.T_C }
    row[r.property_method === 'IDEAL' ? 'asIdeal' : 'asPR'] = r.nh3_conversion * 100
    byT.set(r.T_C, row)
  }
  const sel = byT.get(T) ?? { T }
  sel.sel = equilibriumAt(T, P).conversion * 100
  byT.set(T, sel)
  return [...byT.values()].sort((a, b) => (a.T as number) - (b.T as number))
}

export function EquilibriumCalculator({ compact = false }: { compact?: boolean }) {
  const [T, setT] = useState(600)
  const [P, setP] = useState(20)
  const id = useId()
  const aspen = useRows<AspenRow>('validation', 'equilibrium_aspen_grid')
  const aspenRows = aspen.phase === 'ready' ? aspen.data.rows : []
  const pressures = useMemo(() => [...new Set(aspenRows.map((r) => r.P_bar))].sort((a, b) => a - b), [aspenRows])
  const hasAspenAtP = pressures.includes(P)
  const nearestP = pressures.length ? pressures.reduce((b, p) => (Math.abs(p - P) < Math.abs(b - P) ? p : b), pressures[0]) : null
  const e = useMemo(() => equilibriumAt(T, P), [T, P])
  const rows = useMemo(() => buildChartRows(P, T, aspenRows), [P, T, aspenRows])

  const aspenAtPoint = aspenRows.filter((r) => r.P_bar === P && r.T_C === T)
  const series: XYSeries[] = [
    { key: 'calc', label: 'Calculated in your browser (ideal gas)', color: '#38bdf8', kind: 'line', source: 'browser' },
    ...(hasAspenAtP ? [
      { key: 'asIdeal', label: 'Aspen Plus RGibbs, IDEAL (pre-computed)', color: '#ff7a3d', kind: 'marker' as const, source: 'aspen_plus_v15' as const },
      { key: 'asPR', label: 'Aspen Plus RGibbs, PENG-ROB (pre-computed)', color: '#4ade80', kind: 'marker' as const, source: 'aspen_plus_v15' as const },
    ] : []),
    { key: 'sel', label: 'Selected point', color: '#f472b6', kind: 'marker', source: 'browser' },
  ]
  const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)} %`
  // largest difference between the browser curve and the stored Aspen points at this pressure
  const diffs = (m: string) => aspenRows.filter((r) => r.P_bar === P && r.property_method === m)
    .map((r) => Math.abs(equilibriumAt(r.T_C, P).conversion - r.nh3_conversion) * 100)
  const dIdeal = diffs('IDEAL')
  const dPR = diffs('PENG-ROB')
  const maxOf = (a: number[]) => (a.length ? Math.max(...a) : null)

  return (
    <div className={`calc card ${compact ? 'calc-compact' : ''}`} aria-label="Equilibrium calculator">
      <div className="calc-head">
        <h3 className="calc-title">Equilibrium calculator</h3>
        <ExecLabel kind="browser" />
      </div>
      <p className="muted calc-note">
        Pure NH<sub>3</sub> feed, ideal gas, NH<sub>3</sub> {'⇄'} 1/2 N<sub>2</sub> + 3/2 H<sub>2</sub>. This page evaluates the closed form
        X<sub>eq</sub> = (1 + (3{'√'}3/4) (P/1 bar) / K(T))<sup>-1/2</sup> with K(T) from {NASA7_PROVENANCE.mechanism} via {NASA7_PROVENANCE.via}.
        It is a thermodynamic limit, not a reactor design, and it does not run Aspen Plus.
      </p>
      <div className="calc-body">
        <div className="calc-controls">
          <div className="slider">
            <label htmlFor={`${id}-t`}>Temperature <output htmlFor={`${id}-t`}>{T} {'°C'}</output></label>
            <input id={`${id}-t`} type="range" min={T_MIN} max={T_MAX} step={STEP_T} value={T} onChange={(ev) => setT(Number(ev.target.value))} />
            <div className="slider-ends"><span>{T_MIN}</span><span>{T_MAX} {'°C'}</span></div>
          </div>
          <div className="slider">
            <label htmlFor={`${id}-p`}>Pressure <output htmlFor={`${id}-p`}>{P} bar</output></label>
            <input id={`${id}-p`} type="range" min={P_MIN} max={P_MAX} step={1} value={P} onChange={(ev) => setP(Number(ev.target.value))} />
            <div className="slider-ends"><span>{P_MIN}</span><span>{P_MAX} bar</span></div>
          </div>
          <div className="preset-row" role="group" aria-label="Pressures with stored Aspen Plus results">
            <span className="muted">Aspen points stored at:</span>
            {pressures.map((p) => (
              <button key={p} type="button" className="chip" aria-pressed={p === P} onClick={() => setP(p)}>{p} bar</button>
            ))}
          </div>
        </div>
        <dl className="calc-results" aria-live="polite">
          <div className="res res-main"><dt>NH<sub>3</sub> conversion</dt><dd>{pct(e.conversion)}</dd></div>
          <div className="res"><dt>y NH<sub>3</sub></dt><dd>{pct(e.y.NH3)}</dd></div>
          <div className="res"><dt>y H<sub>2</sub></dt><dd>{pct(e.y.H2)}</dd></div>
          <div className="res"><dt>y N<sub>2</sub></dt><dd>{pct(e.y.N2)}</dd></div>
          <div className="res"><dt>{'Δ'}H<sub>r</sub> at T</dt><dd>{e.dH_kJ_per_mol_NH3.toFixed(2)} <small>kJ/mol NH<sub>3</sub></small></dd></div>
          <div className="res"><dt>K(T), 1 bar standard state</dt><dd>{e.K < 100 ? e.K.toFixed(2) : e.K.toFixed(1)}</dd></div>
        </dl>
      </div>
      <XYChart
        title={`NH3 conversion versus temperature at ${P} bar`}
        description={`Equilibrium conversion of pure ammonia at ${P} bar from ${T_MIN} to ${T_MAX} degrees Celsius, calculated in the browser for an ideal gas${hasAspenAtP ? ', with stored Aspen Plus RGibbs points for the IDEAL and PENG-ROB property methods' : ''}. At ${T} degrees Celsius the conversion is ${pct(e.conversion)}.`}
        data={rows} xKey="T" xLabel={'Temperature [°C]'} yLabel="Conversion [%]" series={series} yDomain={[0, 100]} xDomain={[T_MIN, T_MAX]} height={compact ? 280 : 340}
      />
      <div className="calc-foot">
        {aspen.phase === 'loading' ? <p className="muted">Loading stored Aspen Plus points ...</p> : null}
        {aspen.phase === 'error' ? <p className="muted">Stored Aspen Plus points are not available here; the browser calculation above does not depend on them.</p> : null}
        {aspen.phase === 'ready' && hasAspenAtP ? (
          <p className="reading">
            <strong>Agreement with Aspen Plus at {P} bar.</strong> Largest difference to the stored RGibbs points: {maxOf(dIdeal)?.toFixed(3)} percentage points (IDEAL),
            {' '}{maxOf(dPR)?.toFixed(2)} percentage points (PENG-ROB, real-gas effect). {aspenAtPoint.length ? `At ${T} °C Aspen gives ${aspenAtPoint.map((r) => `${(r.nh3_conversion * 100).toFixed(2)} % (${r.property_method})`).join(' and ')}.` : 'Aspen points exist every 50 °C.'}
          </p>
        ) : null}
        {aspen.phase === 'ready' && !hasAspenAtP && nearestP !== null ? (
          <p className="reading">
            No Aspen Plus points are stored at {P} bar (stored: {pressures.join(', ')} bar).{' '}
            <button type="button" className="linkbtn inline" onClick={() => setP(nearestP)}>Show the nearest, {nearestP} bar</button>.
          </p>
        ) : null}
      </div>
    </div>
  )
}
