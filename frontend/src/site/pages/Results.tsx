import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { DataSource, SimulationResult } from '../../api/types'
import { Value } from '../../components/ui'
import { fmt } from '../../data/format'
import { useData } from '../../data/DataContext'
import { equilibriumAt } from '../../calc/equilibrium'
import { AsyncView } from '../../features/common/Notice'
import { XYChart, type XYRow, type XYSeries } from '../../features/common/XYChart'
import { platformPath } from '../routes'
import { HBarChart } from '../charts'
import { useJson, useRows } from '../data'
import { atBoundCount, breakdownRows, CI_PARTS, ciRows, freeOptimisations, mergeSeries, pivotTP, type CiRow, type OptResult } from '../results'
import { humaniseKeys, metricName } from '../../data/metrics'
import { Callout, Cite, ExecLabel, PageHero, Reading, Section } from '../ui'

const COLORS = ['#38bdf8', '#ff7a3d', '#4ade80', '#f472b6', '#a5b4fc', '#f5b73b']
const DEG = '°C'

type SweepRow = Record<string, number | string | null>
const n = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

const SUBNAV: [string, string][] = [
  ['conversion', 'Conversion and duties'], ['tpmap', 'T-P map'], ['heat', 'Heat integration'], ['reactor', 'Reactor'],
  ['purification', 'Purification'], ['optimisation', 'Optimisation'], ['economics', 'Cost'], ['carbon', 'Carbon intensity'],
]

/* ---- 1. conversion and duties versus temperature ---- */
function ConversionDuties() {
  const t = useRows<SweepRow>('sensitivity', 'aspen_temperature')
  return (
    <AsyncView a={t} what="Aspen temperature sweep">{({ rows }) => {
      const P = n(rows[0]?.reactor_pressure_bar) ?? 20
      const xs = rows.map((r) => n(r.reactor_temperature_C)).filter((x): x is number => x !== null)
      const Tlo = Math.min(...xs), Thi = Math.max(...xs)
      const conv = mergeSeries('T', [
        { key: 'aspen', points: rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.nh3_conversion) !== null ? (n(r.nh3_conversion) as number) * 100 : null })) },
        { key: 'calc', points: Array.from({ length: Math.round((Thi - Tlo) / 10) + 1 }, (_, i) => Tlo + i * 10).map((T) => ({ x: T, y: equilibriumAt(T, P).conversion * 100 })) },
      ])
      const duties = mergeSeries('T', [
        { key: 'reactor', points: rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.reactor_duty_kW) })) },
        { key: 'vap', points: rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.vaporiser_duty_kW) })) },
        { key: 'pre', points: rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.preheat_duty_kW) })) },
        { key: 'rec', points: rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.recovered_heat_kW) })) },
        { key: 'ext', points: rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.total_external_heating_kW) })) },
      ])
      const first = rows[0], last = rows[rows.length - 1]
      const gaps = rows.map((r) => (n(r.nh3_conversion) !== null && n(r.reactor_temperature_C) !== null ? Math.abs((n(r.nh3_conversion) as number) * 100 - equilibriumAt(n(r.reactor_temperature_C) as number, P).conversion * 100) : null)).filter((x): x is number => x !== null)
      const maxGap = gaps.length ? Math.max(...gaps) : null
      const e0 = n(first?.total_external_heating_kW), e1 = n(last?.total_external_heating_kW), c0 = n(first?.reactor_duty_kW), c1 = n(last?.reactor_duty_kW), r0 = n(first?.recovered_heat_kW), r1 = n(last?.recovered_heat_kW)
      const cs: XYSeries[] = [
        { key: 'aspen', label: 'Aspen Plus V15 (pre-computed)', color: COLORS[1], kind: 'marker', source: 'aspen_plus_v15' },
        { key: 'calc', label: 'Ideal-gas equilibrium, calculated in your browser', color: COLORS[0], kind: 'line', source: 'browser' },
      ]
      const ds: XYSeries[] = [
        { key: 'reactor', label: 'Cracker duty', color: COLORS[1], kind: 'line', source: 'aspen_plus_v15' },
        { key: 'vap', label: 'Vaporiser duty', color: COLORS[2], kind: 'line', source: 'aspen_plus_v15' },
        { key: 'pre', label: 'Trim heater duty', color: COLORS[3], kind: 'line', source: 'aspen_plus_v15' },
        { key: 'rec', label: 'Heat recovered in the exchanger', color: COLORS[4], kind: 'line', source: 'aspen_plus_v15', dashed: true },
        { key: 'ext', label: 'Total external heating', color: COLORS[0], kind: 'line', source: 'aspen_plus_v15' },
      ]
      return (
        <div className="chart-grid">
          <div>
            <XYChart title={`NH3 conversion versus reactor temperature at ${P} bar`} data={conv} xKey="T" xLabel={`Reactor temperature [${DEG}]`} yLabel="Conversion [%]" series={cs} yDomain={[0, 100]}
              description={`Aspen Plus RGibbs conversion of ammonia from ${Tlo} to ${Thi} degrees Celsius at ${P} bar, with the ideal-gas equilibrium curve calculated in the browser.`} />
            <Reading>Conversion rises from {fmt(((n(first?.nh3_conversion) ?? NaN)) * 100, 1)} % at {Tlo} {DEG} to {fmt(((n(last?.nh3_conversion) ?? NaN)) * 100, 1)} % at {Thi} {DEG}{maxGap !== null ? <>; the Aspen points differ from the independent ideal-gas curve by at most {fmt(maxGap, 2)} percentage points, which is the real-gas effect of the Peng-Robinson model at {P} bar.</> : '.'}</Reading>
          </div>
          <div>
            <XYChart title="Heat duties versus reactor temperature" data={duties} xKey="T" xLabel={`Reactor temperature [${DEG}]`} yLabel="Duty [kW]" series={ds}
              description="Cracker, vaporiser and trim-heater duties, heat recovered in the feed/effluent exchanger and total external heating, as functions of reactor temperature, from the Aspen Plus sweep." />
            <Reading>{e0 !== null && e1 !== null && c0 !== null && c1 !== null ? <>From {Tlo} to {Thi} {DEG} the cracker duty goes from {fmt(c0, 0)} to {fmt(c1, 0)} kW and the total external heating from {fmt(e0, 0)} to {fmt(e1, 0)} kW{r0 !== null && r1 !== null ? <>, while the heat recovered in the exchanger goes from {fmt(r0, 0)} to {fmt(r1, 0)} kW</> : null}.</> : 'Duties versus temperature from the Aspen sweep.'}</Reading>
          </div>
        </div>
      )
    }}</AsyncView>
  )
}

/* ---- 2. T-P map ---- */
function TPMap() {
  const t = useRows<SweepRow>('sensitivity', 'aspen_tp_map')
  return (
    <AsyncView a={t} what="Aspen temperature-pressure map">{({ rows }) => {
      const { data, pressures } = pivotTP(rows)
      const series: XYSeries[] = pressures.map((p, i) => ({ key: `p${p}`, label: `${p} bar`, color: COLORS[i % COLORS.length], kind: 'line', source: 'aspen_plus_v15' }))
      const at = (T: number, P: number) => data.find((r) => r.T === T)?.[`p${P}`]
      const lo = pressures[0], hi = pressures[pressures.length - 1]
      const Tmid = data.length ? (data[Math.floor(data.length / 2)].T as number) : null
      const a = Tmid !== null ? at(Tmid, lo) : null, b = Tmid !== null ? at(Tmid, hi) : null
      return (
        <div className="chart-single">
          <XYChart title="NH3 conversion over the temperature-pressure map" data={data} xKey="T" xLabel={`Reactor temperature [${DEG}]`} yLabel="Conversion [%]" series={series} yDomain={['auto', 100]}
            description={`Aspen Plus conversion of ammonia versus reactor temperature, one curve per pressure from ${lo} to ${hi} bar.`} />
          <Reading>
            Higher pressure costs conversion at every temperature{typeof a === 'number' && typeof b === 'number' && Tmid !== null ? <>: at {Tmid} {DEG} it falls from {fmt(a, 1)} % at {lo} bar to {fmt(b, 1)} % at {hi} bar</> : null}, which is why the cracker needs a high temperature rather than a low pressure.
          </Reading>
        </div>
      )
    }}</AsyncView>
  )
}

/* ---- 3. heat integration ---- */
function HeatIntegration() {
  const { cases } = useData()
  const a = cases.find((c) => c.case_id === 'baseline')
  const b = cases.find((c) => c.case_id === 'baseline_no_hi')
  const withHi = useRows<SweepRow>('sensitivity', 'aspen_temperature')
  const noHi = useRows<SweepRow>('sensitivity', 'aspen_no_hi_temperature')
  const rows: XYRow[] = useMemo(() => {
    if (withHi.phase !== 'ready' || noHi.phase !== 'ready') return []
    return mergeSeries('T', [
      { key: 'hi', points: withHi.data.rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.total_external_heating_kW) })) },
      { key: 'nohi', points: noHi.data.rows.map((r) => ({ x: n(r.reactor_temperature_C), y: n(r.total_external_heating_kW) })) },
    ])
  }, [withHi, noHi])
  const kpi = (c: SimulationResult | undefined, key: 'total_external_heating_kW' | 'recovered_heat_kW' | 'lhv_efficiency' | 'specific_heat_demand_kWh_per_kgH2', scale = 1, unit = '', digits?: number) =>
    <Value v={c?.kpis[key] == null ? null : (c.kpis[key] as number) * scale} unit={unit} digits={digits} source={c?.source ?? null} showSource={false} />
  const heatReading = useMemo(() => {
    const ok = rows.filter((r) => typeof r.hi === 'number' && typeof r.nohi === 'number')
    if (ok.length === 0) return 'Total external heating with and without the exchanger.'
    const d = ok.map((r) => (r.nohi as number) - (r.hi as number))
    const all = d.every((x) => x > 0)
    return <>{all ? 'Recovering the product\u2019s sensible heat in the feed/effluent exchanger lowers the external heating at every swept temperature' : 'The exchanger does not lower the external heating at every swept temperature'}: by {fmt(d[0], 0)} kW at {ok[0].T} {DEG} and by {fmt(d[d.length - 1], 0)} kW at {ok[ok.length - 1].T} {DEG}.</>
  }, [rows])
  const series: XYSeries[] = [
    { key: 'hi', label: 'With feed/effluent exchanger', color: COLORS[0], kind: 'line', source: 'aspen_plus_v15' },
    { key: 'nohi', label: 'Without exchanger', color: COLORS[1], kind: 'line', source: 'aspen_plus_v15' },
  ]
  return (
    <>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Baseline with and without the feed/effluent exchanger">
        <table className="data simple">
          <caption>Baseline with and without heat integration <ExecLabel kind="aspen" /></caption>
          <thead><tr><th scope="col">Quantity</th><th scope="col" className="r">With exchanger</th><th scope="col" className="r">Without exchanger</th></tr></thead>
          <tbody>
            <tr><th scope="row">External heating</th><td className="r">{kpi(a, 'total_external_heating_kW', 1, 'kW', 0)}</td><td className="r">{kpi(b, 'total_external_heating_kW', 1, 'kW', 0)}</td></tr>
            <tr><th scope="row">Heat recovered in the exchanger</th><td className="r">{kpi(a, 'recovered_heat_kW', 1, 'kW', 0)}</td><td className="r">{kpi(b, 'recovered_heat_kW', 1, 'kW', 0)}</td></tr>
            <tr><th scope="row">Specific heat demand</th><td className="r">{kpi(a, 'specific_heat_demand_kWh_per_kgH2', 1, 'kWh/kg H2', 2)}</td><td className="r">{kpi(b, 'specific_heat_demand_kWh_per_kgH2', 1, 'kWh/kg H2', 2)}</td></tr>
            <tr><th scope="row">LHV efficiency</th><td className="r">{kpi(a, 'lhv_efficiency', 100, '%', 1)}</td><td className="r">{kpi(b, 'lhv_efficiency', 100, '%', 1)}</td></tr>
          </tbody>
        </table>
      </div>
      <AsyncView a={withHi} what="Aspen temperature sweep with the exchanger">{() => (
        <AsyncView a={noHi} what="Aspen temperature sweep without the exchanger">{() => (
          <div className="chart-single">
            <XYChart title="External heating versus reactor temperature, with and without the exchanger" data={rows} xKey="T" xLabel={`Reactor temperature [${DEG}]`} yLabel="Heating [kW]" series={series}
              description="Total external heating demand versus reactor temperature for the flowsheet with and without the feed/effluent heat exchanger, from Aspen Plus sweeps." />
            <Reading>{heatReading}</Reading>
          </div>
        )}</AsyncView>
      )}</AsyncView>
      <p className="muted small">Pinch analysis of the same case and a comparison of configurations are on the <Link to={platformPath('/heat')}>platform's Heat Integration page</Link>.</p>
    </>
  )
}

/* ---- 4. reactor: equilibrium + kinetic catalyst mass ---- */
function ReactorSection() {
  const k = useRows<SweepRow>('sensitivity', 'pfr_temperature_sweep')
  return (
    <>
      <p className="prose-p">
        The equilibrium side of the reactor is the calculator on the <Link to="/#try">overview page</Link>: ideal-gas curves with the stored Aspen RGibbs points for IDEAL and PENG-ROB. The kinetic side is a separate, Python-only model.
      </p>
      <AsyncView a={k} what="Plug-flow catalyst sweep">{({ rows }) => {
        const cats = [...new Set(rows.map((r) => String(r.catalyst_id)))]
        const label: Record<string, string> = { ni_takahashi_microkinetic: 'Ni/MgO microkinetic', ru_takahashi_microkinetic: 'Ru/MgO microkinetic', ru_kum_temkin_pyzhev: 'Ru/Al2O3 Temkin-Pyzhev' }
        const data = mergeSeries('T', cats.map((c) => ({ key: c, points: rows.filter((r) => r.catalyst_id === c).map((r) => ({ x: n(r.T_C), y: n(r.W_95pct_eq_kg) })) })))
        const series: XYSeries[] = cats.map((c, i) => ({ key: c, label: label[c] ?? c, color: COLORS[i], kind: 'line', source: 'python_model' }))
        const P = n(rows[0]?.P_bar)
        const Ts = [...new Set(rows.map((r) => n(r.T_C)).filter((x): x is number => x !== null))].sort((a, b) => a - b)
        const spread = Ts.map((T) => { const v = cats.map((c) => n(rows.find((r) => r.catalyst_id === c && n(r.T_C) === T)?.W_95pct_eq_kg)).filter((x): x is number => x !== null && x > 0); return v.length === cats.length && v.length > 1 ? { T, ratio: Math.max(...v) / Math.min(...v) } : null }).filter((x): x is { T: number; ratio: number } => x !== null)
        const sp = spread.length ? spread[Math.floor(spread.length / 2)] : null
        return (
          <div className="chart-single">
            <XYChart title={`Catalyst mass for 95 % of equilibrium conversion${P ? ` at ${P} bar` : ''}`} data={data} xKey="T" xLabel={`Isothermal bed temperature [${DEG}]`} yLabel="Catalyst mass [kg]" series={series} yLog
              description="Catalyst mass needed to reach 95 percent of the equilibrium conversion in an isothermal plug-flow reactor, versus temperature, for three literature rate laws, on a logarithmic axis."
              height={320} />
            <Reading>Catalyst demand rises as the bed temperature falls{sp ? <>, and at {sp.T} {DEG} the highest and lowest of the three literature rate laws differ by a factor of {fmt(sp.ratio, 1)}</> : null}; a series is missing where the model returned no mass for that target.</Reading>
            <Callout kind="warn" title="Model-based, not Aspen.">These rate laws were fitted at 1 atm and are extrapolated to the stated pressure; they imply no catalyst design.
              Sources: <Cite k="takahashi2016kinetic" /> and <Cite k="kum2026heatintegrated" />.</Callout>
          </div>
        )
      }}</AsyncView>
    </>
  )
}

/* ---- 5. purification ---- */
interface SepRow { option: string; h2_recovery: number | null; h2_purity_mole_frac: number | null; product_h2_kg_h: number | null; h2_loss_fraction: number | null }
function Purification() {
  const s = useJson<{ rows: SepRow[]; input_source?: DataSource; model?: string }>('/api/data/analysis/separation_baseline')
  return (
    <AsyncView a={s} what="Separation study">{(d) => {
      const baseRow = d.rows.find((r) => /amcrax_baseline/.test(r.option))
      const lit = d.rows.filter((r) => /^PSA/.test(r.option) && !/amcrax_baseline/.test(r.option) && r.h2_recovery !== null).map((r) => r.h2_recovery as number)
      const litMax = lit.length ? Math.max(...lit) : null
      return (
      <>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Hydrogen purification options on the baseline cracked gas">
          <table className="data simple">
            <caption>Hydrogen purification options applied to the baseline cracked gas ({d.model ?? 'reduced-order model'}; <ExecLabel kind="python" />)</caption>
            <thead><tr><th scope="col">Option</th><th scope="col" className="r">H2 recovery [-]</th><th scope="col" className="r">H2 purity [mol%]</th><th scope="col" className="r">Product H2 [kg/h]</th><th scope="col" className="r">H2 lost [%]</th></tr></thead>
            <tbody>{d.rows.map((r) => (
              <tr key={r.option}>
                <th scope="row">{r.option}</th>
                <td className="r">{fmt(r.h2_recovery, 3)}</td>
                <td className="r">{r.h2_purity_mole_frac === null ? 'n/a' : fmt(r.h2_purity_mole_frac * 100, 2)}</td>
                <td className="r">{fmt(r.product_h2_kg_h, 1)}</td>
                <td className="r">{r.h2_loss_fraction === null ? 'n/a' : fmt(r.h2_loss_fraction * 100, 1)}</td>
              </tr>))}
            </tbody>
          </table>
        </div>
        <Reading>{baseRow && litMax !== null ? <>The baseline splitter assumes a recovery of {fmt(baseRow.h2_recovery, 2)}, above every literature PSA row (up to {fmt(litMax, 2)}), so its product flow is optimistic by comparison.</> : 'Recovery and purity of each option are inputs, not results.'}</Reading>
        <Callout kind="warn" title="Reduced order.">None of these is a designed PSA or membrane unit: recovery and purity are inputs or literature points, and NH3 polishing to fuel-cell limits is not modelled.</Callout>
      </>
      )
    }}</AsyncView>
  )
}

/* ---- 6. optimisation ---- */
interface VerCand { id: string; label: string; status: string; aspen_converged: boolean; max_relative_deviation_primary: number; max_relative_deviation_primary_metric: string; tolerance: number }
function Optimisation() {
  const so = useJson<{ results: OptResult[] }>('/api/data/optimisation/single_objective')
  const av = useJson<{ candidates: VerCand[]; tolerance_relative: number; criterion: string }>('/api/data/optimisation/aspen_verification')
  return (
    <>
      <AsyncView a={so} what="Single-objective optimisation results">{(d) => {
        const free = freeOptimisations(d.results)
        const bound = atBoundCount(free)
        return (
          <>
            <div className="table-scroll" tabIndex={0} role="region" aria-label="Single-objective optimum for each objective">
              <table className="data simple">
                <caption>Optimum of each single objective, four decision variables free (differential evolution + SLSQP on the Python model; <ExecLabel kind="python" />)</caption>
                <thead><tr><th scope="col">Objective</th><th scope="col" className="r">Optimum / baseline</th><th scope="col" className="r">T [{DEG}]</th><th scope="col" className="r">P [bar]</th><th scope="col" className="r">PSA recovery [-]</th><th scope="col" className="r">FEHE approach [K]</th><th scope="col">At a bound</th></tr></thead>
                <tbody>{free.map((r) => {
                  const v = r.decision_variables
                  return (
                    <tr key={r.id}>
                      <th scope="row">{humaniseKeys(r.label)}</th>
                      <td className="r">{r.improvement ? `${fmt(r.improvement.optimum, 3)} / ${fmt(r.improvement.baseline, 3)}` : 'n/a'}</td>
                      <td className="r">{fmt(v.reactor_temperature_C?.optimum, 0)}</td>
                      <td className="r">{fmt(v.reactor_pressure_bar?.optimum, 1)}</td>
                      <td className="r">{fmt(v.psa_h2_recovery?.optimum, 2)}</td>
                      <td className="r">{fmt(v.fehe_hot_end_approach_K?.optimum, 0)}</td>
                      <td>{(r.bound_active ?? []).length ? (r.bound_active ?? []).map((b) => <span key={b} className="pill pill-warn bound-pill">{b.replace('reactor_', '').replace('psa_h2_', '').replace('fehe_hot_end_', '').replace(/_(bar|C|K)=/, ' ')}</span>) : <span className="muted">none</span>}</td>
                    </tr>
                  )
                })}</tbody>
              </table>
            </div>
            <Callout kind="warn" title="Read these optima with care.">
              {bound} of {free.length} optima sit on a bound of at least one decision variable. They are bound-driven, not discovered interior optima: the cost model does not see exchanger area, PSA size or catalyst volume, and recoveries above the published 0.71 to 0.81 are not demonstrated. The objectives largely do not conflict in this model, so the optima cluster rather than trade off. The minimum-LCOH point sits on the recovery and approach bounds for the same reason.
              The T-and-P-only variants, which keep recovery and approach at baseline, are on the <Link to={platformPath('/optimisation')}>platform's Optimisation page</Link>.
            </Callout>
          </>
        )
      }}</AsyncView>
      <AsyncView a={av} what="Aspen Plus re-verification of the optimisation candidates">{(d) => (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Aspen Plus re-verification of the optimisation candidates">
          <table className="data simple">
            <caption>Optimisation candidates re-solved in Aspen Plus V15 <ExecLabel kind="aspen" /></caption>
            <thead><tr><th scope="col">Candidate</th><th scope="col">Aspen converged</th><th scope="col" className="r">Largest primary-metric deviation from the Python model [%]</th><th scope="col">Metric</th><th scope="col">Verdict (tolerance {fmt(d.tolerance_relative * 100, 1)} %)</th></tr></thead>
            <tbody>{d.candidates.map((c) => (
              <tr key={c.id}>
                <th scope="row">{humaniseKeys(c.label)}</th>
                <td>{c.aspen_converged ? 'yes' : 'no'}</td>
                <td className="r">{fmt(c.max_relative_deviation_primary * 100, 2)}</td>
                <td>{metricName(c.max_relative_deviation_primary_metric)}</td>
                <td><span className={`pill ${c.status === 'pass' ? 'pill-ok' : 'pill-error'}`}>{c.status}</span></td>
              </tr>))}
            </tbody>
          </table>
          <p className="muted small table-note">{d.criterion} {d.candidates.every((c) => c.aspen_converged) ? <>All {d.candidates.length} candidates converged in Aspen Plus;</> : 'Not every candidate converged;'} the largest primary-metric deviation from the Python model is {fmt(Math.max(...d.candidates.map((c) => c.max_relative_deviation_primary)) * 100, 2)} %. The optimisation itself ran on the Python model; Aspen Plus only re-solved the resulting points.</p>
        </div>
      )}</AsyncView>
    </>
  )
}

/* ---- 7. cost ---- */
function priceReading(data: XYRow[], base: number | null) {
  const ok = data.filter((r) => typeof r.hi === 'number' && typeof r.nohi === 'number')
  if (ok.length < 2) return 'LCOH versus the price of ammonia.'
  const a = ok[0], b = ok[ok.length - 1]
  const at = base === null ? b : ok.reduce((m, r) => (Math.abs((r.price as number) - base) < Math.abs((m.price as number) - base) ? r : m), ok[0])
  const slope = ((b.hi as number) - (a.hi as number)) / ((b.price as number) - (a.price as number)) * 100
  return <>Across {a.price}-{b.price} USD/t, LCOH with the exchanger goes from {fmt(a.hi as number, 2)} to {fmt(b.hi as number, 2)} USD/kg H2 ({fmt(slope, 2)} USD/kg per 100 USD/t); the exchanger lowers it by {fmt((at.nohi as number) - (at.hi as number), 2)} USD/kg at {at.price} USD/t.</>
}
function torReading(rows: { name: string; swing: number }[]) {
  if (rows.length < 2) return 'One-at-a-time swings of LCOH over the range of each input.'
  const rest = rows.slice(1).reduce((s, r) => s + r.swing, 0)
  return <>Varying one input at a time over its published range, the input "{rows[0].name}" moves LCOH by {fmt(rows[0].swing, 2)} USD/kg, {rows[0].swing > rest ? 'more than' : 'less than'} the next {rows.length - 1} inputs together ({fmt(rest, 2)} USD/kg).</>
}

interface Econ { kg_nh3_feed_per_kg_h2?: number; kg_nh3_fuel_per_kg_h2?: number; stoichiometric_floor_kg_nh3_per_kg_h2?: number; assumptions?: { nh3_price_USD_per_t?: number }; lcoh_USD_per_kg: number; breakdown_USD_per_kg: Record<string, number>; source?: DataSource; input_source?: string; capex?: { estimate_class?: string } }
function Economics() {
  const e = useJson<Econ>('/api/data/analysis/economics_baseline')
  const price = useRows<SweepRow>('sensitivity', 'lcoh_vs_ammonia_price_baseline')
  const priceNo = useRows<SweepRow>('sensitivity', 'lcoh_vs_ammonia_price_baseline_no_hi')
  const tor = useRows<SweepRow>('sensitivity', 'lcoh_tornado_baseline')
  return (
    <>
      <AsyncView a={e} what="Techno-economic result">{(d) => {
        const rows = breakdownRows(d.breakdown_USD_per_kg)
        const total = rows.reduce((a, r) => a + r.value, 0)
        const feed = d.breakdown_USD_per_kg.ammonia_feed
        return (
          <div className="chart-single">
            <HBarChart title={`Levelised cost of hydrogen: ${fmt(d.lcoh_USD_per_kg, 2)} USD/kg H2`} source={d.source ?? 'python_model'} data={rows} catKey="name" series={[{ key: 'value', label: 'USD/kg H2', color: COLORS[0] }]}
              xLabel="Contribution to LCOH [USD/kg H2]" description={`Breakdown of the levelised cost of hydrogen, total ${fmt(total, 2)} USD per kg of hydrogen, into capital charge, fixed operating cost, ammonia feed, imported heat and small items.`} />
            <Reading>The ammonia feed is {fmt((feed / total) * 100, 0)} % of the cost, so the price of ammonia, not the plant, decides the result, as in the published studies <Cite k={['cho2026nickel', 'richard2024technoeconomic']} />.</Reading>
            <p className="reading"><strong>Basis.</strong> Ammonia at {fmt(d.assumptions?.nh3_price_USD_per_t, 0)} USD/t, priced on the NH<sub>3</sub> it contains: {fmt(d.kg_nh3_feed_per_kg_h2, 3)} kg NH<sub>3</sub> per kg H<sub>2</sub> as feed plus {fmt(d.kg_nh3_fuel_per_kg_h2, 3)} as fuel, against a stoichiometric floor of {fmt(d.stoichiometric_floor_kg_nh3_per_kg_h2, 3)}. Capital cost from a plant-level correlation.</p>
          </div>
        )
      }}</AsyncView>
      <AsyncView a={price} what="LCOH versus ammonia price">{(p) => (
        <AsyncView a={priceNo} what="LCOH versus ammonia price without heat integration">{(q) => {
          const data = mergeSeries('price', [
            { key: 'hi', points: p.rows.map((r) => ({ x: n(r.nh3_price_USD_per_t), y: n(r.lcoh_USD_per_kg) })) },
            { key: 'nohi', points: q.rows.map((r) => ({ x: n(r.nh3_price_USD_per_t), y: n(r.lcoh_USD_per_kg) })) },
          ])
          const series: XYSeries[] = [
            { key: 'hi', label: 'With feed/effluent exchanger', color: COLORS[0], kind: 'line', source: 'python_model' },
            { key: 'nohi', label: 'Without exchanger', color: COLORS[1], kind: 'line', source: 'python_model' },
          ]
          return (
            <div className="chart-single">
              <XYChart title="LCOH versus ammonia price" data={data} xKey="price" xLabel="Ammonia price [USD/t]" yLabel="LCOH [USD/kg H2]" series={series}
                description="Levelised cost of hydrogen versus the price of ammonia for the flowsheet with and without the feed/effluent exchanger; the relation is nearly linear." />
              <Reading>{priceReading(data, e.phase === 'ready' ? (e.data.assumptions?.nh3_price_USD_per_t ?? null) : null)}</Reading>
            </div>
          )
        }}</AsyncView>
      )}</AsyncView>
      <AsyncView a={tor} what="LCOH tornado">{(t) => {
        const rows = t.rows.map((r) => ({ name: String(r.parameter).replace(/^nh3/, 'NH3').replace(/^./, (ch) => ch.toUpperCase()).replace(/_/g, ' ').replace(/ USD per t| USD per kg| USD per kWh| frac capex per yr| h per yr| yr$/, ''), swing: n(r.swing_USD_per_kg) ?? 0 })).sort((a, b) => b.swing - a.swing).slice(0, 5)
        return (
          <div className="chart-single">
            <HBarChart title="Largest LCOH swings over the literature ranges of each input" source="python_model" data={rows} catKey="name" series={[{ key: 'swing', label: 'Swing in LCOH [USD/kg H2]', color: COLORS[1] }]}
              xLabel="Swing in LCOH [USD/kg H2]" description="One-at-a-time swing of the levelised cost of hydrogen over the range of each input; the ammonia price has by far the largest swing." />
            <Reading>{torReading(rows)}</Reading>
          </div>
        )
      }}</AsyncView>
      <Callout kind="warn" title="Preliminary estimate.">The cost model uses a plant-level capital correlation with mixed cost years, no equipment sizing, and leaves out NOx treatment, NH3 polishing and compression. Treat it as an order of magnitude and compare it with published values before quoting.</Callout>
    </>
  )
}

/* ---- 8. carbon intensity ---- */
interface EnvFile { comparison?: { rows: CiRow[]; reference_lines?: { label: string; value_kgCO2e_per_kgH2: number }[]; method?: string; system_boundary?: string; source?: DataSource } }
function Carbon() {
  const env = useJson<EnvFile>('/api/data/analysis/environmental_baseline')
  return (
    <AsyncView a={env} what="Carbon-intensity scenarios">{(d) => {
      const c = d.comparison
      if (!c) return <p className="muted">No carbon-intensity comparison in the stored results.</p>
      const rows = ciRows(c.rows)
      const colors = [COLORS[4], COLORS[1], COLORS[3], COLORS[5]]
      return (
        <div className="chart-single">
          <HBarChart title="Carbon intensity of hydrogen by ammonia route and heating option" source={c.source ?? 'python_model'} data={rows} catKey="name"
            series={CI_PARTS.map((p, i) => ({ key: p.key, label: p.label, color: colors[i] }))} stacked xLabel="Carbon intensity [kg CO2e / kg H2]"
            refLines={(c.reference_lines ?? []).map((r) => ({ x: r.value_kgCO2e_per_kgH2, label: '' }))}
            description="Stacked cradle-to-gate carbon intensity of hydrogen for green, blue and grey ammonia with different heating options, split into upstream ammonia, transport, electricity and external heat, with the EU RFNBO threshold and the IEA low-emission limit as reference lines." height={Math.max(420, rows.length * 52 + 110)}>
            <p className="series-src">Dashed vertical lines: {(c.reference_lines ?? []).map((r) => `${r.label.split('(')[0].trim()} ${fmt(r.value_kgCO2e_per_kgH2, 2)}`).join('; ')} kg CO2e / kg H2.</p>
          </HBarChart>
          <Reading>{carbonReading(c.rows, c.reference_lines ?? [])}</Reading>
          <Callout kind="warn" title="Simplified accounting, not a life-cycle assessment.">{c.system_boundary ?? c.method}</Callout>
        </div>
      )
    }}</AsyncView>
  )
}

function carbonReading(rows: CiRow[], refs: { label: string; value_kgCO2e_per_kgH2: number }[]) {
  const t = rows.filter((r) => r.total_kgCO2e_per_kgH2 !== null)
  const span = (xs: number[]) => (xs.length > 1 ? Math.max(...xs) - Math.min(...xs) : 0)
  const group = (other: 'nh3_route' | 'heating_option') =>
    Math.max(0, ...[...new Set(t.map((r) => r[other]))].map((o) => span(t.filter((r) => r[other] === o).map((r) => r.total_kgCO2e_per_kgH2 as number))))
  const byRoute = group('heating_option'), byHeat = group('nh3_route')
  const lowest = refs.length ? Math.min(...refs.map((r) => r.value_kgCO2e_per_kgH2)) : null
  const below = lowest === null ? null : [...new Set(t.filter((r) => (r.total_kgCO2e_per_kgH2 as number) < lowest).map((r) => r.nh3_route))]
  return <>For a given heating option, changing the ammonia route moves the total by up to {fmt(byRoute, 1)} kg CO2e/kg H2; for a given route, changing the heating option moves it by up to {fmt(byHeat, 1)}.{below !== null ? (below.length ? <> Only the {below.join(' and ')} route{below.length > 1 ? 's are' : ' is'} below the lowest reference line in some heating option.</> : ' No route falls below the lowest reference line.') : null}</>
}

export default function Results() {
  return (
    <>
      <PageHero title="What the simulations say"
        lead="Every chart is drawn in your browser from the stored results of the Aspen Plus V15 runs or of the independent Python models, and carries a label for the model behind it. Nothing here is recomputed except the labelled ideal-gas curves.">
        <nav className="chip-nav" aria-label="On this page">
          {SUBNAV.map(([id, label]) => <Link key={id} to={{ pathname: '/results', hash: `#${id}` }} className="chip-link">{label}</Link>)}
        </nav>
      </PageHero>
      <Section id="conversion" title="Conversion and duties versus temperature" intro="Aspen Plus RGibbs sweeps of the baseline flowsheet; the ideal-gas curve is an independent calculation.">
        <ConversionDuties />
      </Section>
      <Section id="tpmap" alt title="Temperature-pressure map" intro="The same reactor over temperature and pressure.">
        <TPMap />
      </Section>
      <Section id="heat" title="Heat integration" intro="With and without the feed/effluent exchanger.">
        <HeatIntegration />
      </Section>
      <Section id="reactor" alt title="Reactor: equilibrium and kinetics" intro="Thermodynamic limit from Aspen and Python; catalyst demand from literature kinetics.">
        <ReactorSection />
      </Section>
      <Section id="purification" title="Purification" intro="What the hydrogen separator achieves under different assumptions.">
        <Purification />
      </Section>
      <Section id="optimisation" alt title="Optimisation" intro="Single-objective optima on the Python model, each candidate re-solved in Aspen Plus.">
        <Optimisation />
      </Section>
      <Section id="economics" title="Cost: levelised cost of hydrogen" intro="Order-of-magnitude, assumption-based, computed from the Aspen baseline.">
        <Economics />
      </Section>
      <Section id="carbon" alt title="Carbon intensity" intro="Cradle-to-gate, simplified accounting, Singapore grid as stored.">
        <Carbon />
      </Section>
    </>
  )
}
