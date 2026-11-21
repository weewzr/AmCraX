import { useMemo, useState } from 'react'
import { fetchEquilibrium, fetchGrid, type EquilibriumResponse, type Eos } from '../../api/reactor'
import { fetchDataset } from '../../api/validation'
import { SourceBadge, Value } from '../../components/ui'
import { AsyncView, Notice } from '../common/Notice'
import { mapAsync, useAsync } from '../common/useAsync'
import { XYChart, type XYSeries } from '../common/XYChart'
import { aspenMethodFor, gridFromRows, enthalpyRows, lookupEnthalpy, mergeEquilibriumRows, type Quantity } from './shape'

const ALL_P = [1, 5, 10, 20, 30, 40]
const COLORS = ['#38bdf8', '#ff7a3d', '#4ade80', '#f472b6', '#a5b4fc', '#f5b73b']
const QTY: [Quantity, string][] = [['conversion', 'NH3 conversion [%]'], ['y_NH3', 'y NH3 [mol/mol]'], ['y_H2', 'y H2 [mol/mol]'], ['y_N2', 'y N2 [mol/mol]']]

export function EquilibriumExplorer({ live, readable }: { live: boolean; readable: boolean }) {
  const [eos, setEos] = useState<Eos>('ideal')
  const [pressures, setPressures] = useState<number[]>([1, 20])
  const [qty, setQty] = useState<Quantity>('conversion')
  const [enthP, setEnthP] = useState(20)
  const method = aspenMethodFor(eos)

  const aspen = useAsync((s) => fetchDataset('validation', 'equilibrium_aspen_grid', s), [], readable)
  const pyGrid = useAsync((s) => fetchDataset('validation', 'equilibrium_python_grid', s), [], readable)
  // LIVE: any pressure / EOS from the API. SNAPSHOT: the stored Python grid (results/validation/equilibrium_python_grid.csv), same model, tabulated points only.
  const liveGrid = useAsync((s) => fetchGrid(eos, pressures, 250, 900, 14, s), [eos, pressures.join(',')], live && pressures.length > 0)
  const grid = live ? liveGrid : mapAsync(pyGrid, (d) => gridFromRows(d.rows, eos))

  const toggleP = (p: number) => setPressures((cur) => (cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p].sort((a, b) => a - b)))

  const aspenRows = aspen.phase === 'ready' ? aspen.data.rows : []
  const rows = useMemo(
    () => (grid.phase === 'ready' ? mergeEquilibriumRows(grid.data.points, aspenRows, pressures, qty, method) : []),
    [grid, aspenRows, pressures, qty, method],
  )
  const series: XYSeries[] = pressures.flatMap((p): XYSeries[] => {
    const c = COLORS[ALL_P.indexOf(p) % COLORS.length]
    return [
      { key: `py_${p}`, label: `Python ${eos === 'ideal' ? 'ideal gas' : 'Peng-Robinson'}, ${p} bar`, color: c, kind: 'line', source: 'python_model' },
      ...(aspen.phase === 'ready' ? [{ key: `as_${p}`, label: `Aspen RGibbs ${method}, ${p} bar`, color: c, kind: 'marker', source: 'aspen_plus_v15' } as XYSeries] : []),
    ]
  })
  const qLabel = QTY.find(([k]) => k === qty)?.[1] ?? ''

  const enth = useMemo(
    () => (pyGrid.phase === 'ready' ? enthalpyRows(pyGrid.data.rows, aspenRows, enthP, eos, method) : []),
    [pyGrid, aspenRows, enthP, eos, method],
  )

  return (
    <div className="page-block">
      <div className="card controls" role="group" aria-label="Equilibrium controls">
        <div className="field">Equation of state
          <div className="toggle">
            <button type="button" aria-pressed={eos === 'ideal'} onClick={() => setEos('ideal')}>Ideal gas</button>
            <button type="button" aria-pressed={eos === 'pr'} onClick={() => setEos('pr')}>Peng-Robinson</button>
          </div>
        </div>
        <div className="field">Pressures [bar]
          <div className="chips">{ALL_P.map((p) => (
            <button key={p} type="button" className="chip" aria-pressed={pressures.includes(p)} onClick={() => toggleP(p)}>{p}</button>))}
          </div>
        </div>
        <label className="field">Quantity
          <select value={qty} onChange={(e) => setQty(e.target.value as Quantity)}>{QTY.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </label>
        <span className="muted">Aspen overlay: RGibbs with {method} (results/validation/equilibrium_aspen_grid.csv)</span>
      </div>
      {pressures.length === 0 ? <Notice kind="warn">Select at least one pressure.</Notice> : null}
      {!live && readable ? <Notice title="SNAPSHOT mode.">Curves are read from the stored equilibrium grid (tabulated pressures and temperatures); the point calculator needs the live API.</Notice> : null}
      <AsyncView a={grid} what="Python equilibrium grid">{() => (
        <>
          {aspen.phase === 'error' ? <Notice kind="warn" title="Aspen RGibbs points not available.">{aspen.error}. Python curves are shown without the Aspen overlay.</Notice> : null}
          <XYChart title={`${qLabel} vs temperature`} xKey="T_C" xLabel="Temperature [degC]" yLabel={qLabel} data={rows} series={series} yDomain={qty === 'conversion' ? ['auto', 100] : undefined}
            description={`Line chart of ${qLabel} against temperature for pressures ${pressures.join(', ')} bar. Lines are the independent Python model, markers are Aspen Plus RGibbs results.`} />
        </>
      )}</AsyncView>

      <h3>Reaction enthalpy</h3>
      <div className="controls">
        <div className="field">Pressure [bar]
          <div className="chips">{ALL_P.map((p) => (<button key={p} type="button" className="chip" aria-pressed={enthP === p} onClick={() => setEnthP(p)}>{p}</button>))}</div>
        </div>
      </div>
      <AsyncView a={pyGrid} what="Python reaction-enthalpy table (validation/equilibrium_python_grid)">{() => (
        <XYChart title={`Heat of reaction per mol NH3 at ${enthP} bar (${eos === 'ideal' ? 'ideal' : 'Peng-Robinson'})`} xKey="T_C" xLabel="Temperature [degC]"
          yLabel="kJ per mol NH3" data={enth} description="Python standard-state-corrected reaction enthalpy per mole of ammonia cracked, with the Aspen RGibbs heat duty per mole NH3 fed shown as markers."
          series={[
            { key: 'py_dH', label: 'Python reaction enthalpy dH_rxn', color: '#a78bfa', kind: 'line', source: 'python_model' },
            { key: 'py_duty', label: 'Python duty per mol NH3 fed (conversion x dH_rxn)', color: '#c4b5fd', kind: 'line', dashed: true, source: 'python_model' },
            { key: 'as_duty', label: `Aspen RGibbs duty per mol NH3 fed (${method})`, color: '#38bdf8', kind: 'marker', source: 'aspen_plus_v15' },
          ]} />
      )}</AsyncView>
      <p className="muted">dH_rxn is per mol NH3 converted; the duty curves are per mol NH3 fed (equilibrium conversion x dH_rxn), the quantity Aspen RGibbs reports.</p>

      <PointCalculator live={live} pyRows={pyGrid.phase === 'ready' ? pyGrid.data.rows : []} />
    </div>
  )
}

function PointCalculator({ live, pyRows }: { live: boolean; pyRows: Record<string, unknown>[] }) {
  const [T, setT] = useState('600')
  const [P, setP] = useState('20')
  const [eos, setEos] = useState<Eos>('ideal')
  const [res, setRes] = useState<{ r: EquilibriumResponse; eos: Eos } | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const go = async () => {
    setErr(null); setBusy(true)
    try { setRes({ r: await fetchEquilibrium(Number(T), Number(P), eos), eos }) } catch (e) { setErr(e instanceof Error ? e.message : String(e)); setRes(null) } finally { setBusy(false) }
  }
  const valid = Number.isFinite(Number(T)) && Number.isFinite(Number(P)) && Number(P) > 0
  const r = res?.r.result
  const dH = res ? lookupEnthalpy(pyRows, Number(res.r.T_C), Number(res.r.P_bar), res.eos) : null
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Point calculator <SourceBadge source="python_model" /></h3>
      <form className="controls" onSubmit={(e) => { e.preventDefault(); void go() }}>
        <label className="field">T [degC]<input type="number" step="10" value={T} onChange={(e) => setT(e.target.value)} /></label>
        <label className="field">P [bar abs]<input type="number" step="1" min="0.1" value={P} onChange={(e) => setP(e.target.value)} /></label>
        <label className="field">EOS<select value={eos} onChange={(e) => setEos(e.target.value as Eos)}><option value="ideal">Ideal gas</option><option value="pr">Peng-Robinson</option></select></label>
        <button type="submit" className="btn" disabled={!live || !valid || busy} title={live ? undefined : 'Needs the live API'}>{busy ? 'Calculating ...' : 'Calculate'}</button>
        {!live ? <span className="muted">Disabled: API not live.</span> : null}
      </form>
      {err ? <Notice kind="error">{err}</Notice> : null}
      {r ? (
        <dl className="kv" style={{ marginTop: 10 }}>
          <dt>NH3 conversion</dt><dd><Value v={r.conversion * 100} unit="%" digits={3} source="python_model" /></dd>
          <dt>Outlet mole fractions</dt>
          <dd>
            {(['NH3', 'H2', 'N2'] as const).map((k) => (<span key={k} style={{ marginRight: 14 }}>y {k}: <Value v={r.y[k]} digits={4} source="python_model" showSource={false} /></span>))}
          </dd>
          <dt>Equilibrium constant K (NH3 decomposition)</dt><dd><Value v={r.K_eq} digits={4} source="python_model" /></dd>
          <dt>Reaction enthalpy dH_rxn</dt>
          <dd>{dH === null ? <span className="muted">n/a (the equilibrium endpoint does not return it; shown only at tabulated grid points)</span> : <Value v={dH} unit="kJ/mol NH3" digits={2} source="python_model" />}</dd>
          <dt>Basis</dt><dd className="muted">{res?.r.basis}; fugacity coefficients {Object.entries(r.phi).map(([k, v]) => `${k} ${v.toFixed(3)}`).join(', ')}</dd>
        </dl>
      ) : null}
    </div>
  )
}

