import { useEffect, useMemo, useState } from 'react'
import '../features/common/features.css'
import { fetchHeat, type FeheInfo, type HeatConfig, type HeatResult, type HeatTargets } from '../api/heat'
import type { DataSource } from '../api/types'
import { BarChartCard } from '../components/charts'
import { DataTable, type Column } from '../components/DataTable'
import { SourceBadge, StatusPill, Value } from '../components/ui'
import { useData } from '../data/DataContext'
import { fmtPct } from '../data/format'
import { AsyncView, ModeGate, Notice } from '../features/common/Notice'
import { useAsync } from '../features/common/useAsync'
import { XYChart } from '../features/common/XYChart'
import { compositeRows, dutyBreakdown, gccRows, hiComparison, type DutyRow, type HiCompareRow } from '../features/heat/shape'

export default function HeatPage() {
  const { mode, phase, active, cases } = useData()
  const live = mode === 'LIVE' && phase === 'ready' && !!active
  const readable = (mode === 'LIVE' || mode === 'SNAPSHOT') && phase === 'ready' && !!active
  const [dT, setDT] = useState(20)
  const [dTq, setDTq] = useState(20) // debounced value used for the query
  useEffect(() => { const t = setTimeout(() => setDTq(dT), 350); return () => clearTimeout(t) }, [dT])
  const caseId = active?.case_id ?? ''
  const heat = useAsync((s) => fetchHeat(caseId, mode === 'SNAPSHOT' ? 20 : dTq, s), [caseId, dTq, mode], readable)

  return (
    <section className="page">
      <h1>Heat Integration</h1>
      <p className="lead">Pinch targets, composite curves and heat-recovery configurations for the active case. Targets come from the Python heat-integration module (problem table on model enthalpy-temperature curves) fed with the Aspen result; they are thermodynamic minima, not an exchanger-network design.</p>
      <ModeGate what="Changing dT_min (a new pinch calculation); the stored analysis at dT_min = 20 K is shown" />
      <div className="card controls">
        <label className="field">Minimum approach dT_min: <strong>{dT} K</strong>
          <input type="range" min={5} max={60} step={1} value={dT} onChange={(e) => setDT(Number(e.target.value))} disabled={!live} aria-label="dT_min in kelvin" />
        </label>
        <label className="field">dT_min [K]<input type="number" min={1} max={100} value={dT} disabled={!live} onChange={(e) => { const v = Number(e.target.value); if (Number.isFinite(v) && v > 0) setDT(v) }} /></label>
        <span className="muted">Active case: <code>{caseId || 'n/a'}</code>{' '}{active ? <SourceBadge source={active.source} /> : null} - {live ? 're-queries GET /api/heat-integration/{case} when changed.' : 'stored analysis at dT_min = 20 K.'}</span>
      </div>
      <AsyncView a={heat} what="Heat-integration analysis">{(d) => <HeatBody r={d.result} />}</AsyncView>
      {phase === 'ready' && active ? <ActiveDuty c={active} /> : null}
      <WithWithout cases={cases} />
    </section>
  )
}

const tgtCols = (t: HeatTargets, src: DataSource) => (
  <dl className="kv">
    <dt>Minimum hot utility</dt><dd><Value v={t.hot_utility_kW} unit="kW" digits={1} source={src} /></dd>
    <dt>Minimum cold utility</dt><dd><Value v={t.cold_utility_kW} unit="kW" digits={1} source={src} /></dd>
    <dt>Heat recovery (target)</dt><dd><Value v={t.heat_recovery_kW} unit="kW" digits={1} source={src} /></dd>
    <dt>Pinch (shifted)</dt><dd>{t.pinch_shifted_C === null ? <span className="muted">none - threshold problem (no pinch limits recovery)</span> : <Value v={t.pinch_shifted_C} unit="degC" digits={1} source={src} />}</dd>
    <dt>Pinch hot / cold side</dt><dd><Value v={t.pinch_hot_C} unit="degC" digits={1} source={src} showSource={false} /> / <Value v={t.pinch_cold_C} unit="degC" digits={1} source={src} showSource={false} /></dd>
  </dl>
)

function HeatBody({ r }: { r: HeatResult }) {
  const [useFlue, setUseFlue] = useState(true)
  const src: DataSource = r.source
  const t = useFlue ? r.targets_with_flue : r.targets_process
  const comp = useMemo(() => compositeRows(t.hot_composite_H_kW, t.hot_composite_T_C, t.cold_composite_H_kW, t.cold_composite_T_C), [t])
  const gcc = useMemo(() => gccRows(t.gcc_H_kW, t.gcc_T_shifted_C), [t])
  const warn = Array.isArray(r.warnings) ? r.warnings : r.warnings ? [r.warnings] : []
  return (
    <>
      {warn.length ? <Notice kind="warn" title="Analysis warnings.">{warn.join(' ')}</Notice> : null}
      <div className="grid-2">
        <div className="card">
          <div className="section-h"><h2>Pinch targets at dT_min = {r.dT_min_K} K <SourceBadge source={src} /></h2>
            <div className="toggle" role="group" aria-label="Stream set">
              <button type="button" aria-pressed={!useFlue} onClick={() => setUseFlue(false)}>Process streams only</button>
              <button type="button" aria-pressed={useFlue} onClick={() => setUseFlue(true)}>+ tail-gas flue gas</button>
            </div>
          </div>
          <p className="muted">{t.label}. Input case source: <SourceBadge source={r.input_source ?? null} /></p>
          {tgtCols(t, src)}
          <h3>Streams</h3>
          <div className="table-wrap"><div className="table-scroll"><table className="data">
            <thead><tr><th scope="col">Stream</th><th scope="col">Type</th><th scope="col" className="r">Supply [degC]</th><th scope="col" className="r">Target [degC]</th><th scope="col" className="r">Duty [kW]</th><th scope="col">Sets</th></tr></thead>
            <tbody>{r.streams.map((s) => (
              <tr key={s.id}><td>{s.name}</td><td>{s.kind}</td>
                <td className="r"><Value v={s.supply_temperature_C} digits={1} source={src} showSource={false} /></td>
                <td className="r"><Value v={s.target_temperature_C} digits={1} source={src} showSource={false} /></td>
                <td className="r"><Value v={s.duty_kW} digits={1} source={src} showSource={false} /></td>
                <td>{(s.included_in ?? []).join(', ')}</td></tr>))}</tbody>
          </table></div></div>
        </div>
        <XYChart title="Composite curves (T vs cumulative heat)" xKey="H" xLabel="Cumulative heat [kW]" yLabel="Temperature [degC]" data={comp} height={360}
          description="Hot and cold composite curves, temperature on the vertical axis against cumulative heat load."
          series={[
            { key: 'hot', label: 'Hot composite', color: 'var(--c-heat)', kind: 'line', source: src },
            { key: 'cold', label: 'Cold composite', color: 'var(--c-cold)', kind: 'line', source: src },
          ]} />
      </div>
      <div className="grid-2">
        <XYChart title="Grand composite curve (shifted T vs net heat)" xKey="H" xLabel="Net heat flow [kW]" yLabel="Shifted temperature [degC]" data={gcc} height={320}
          description="Grand composite curve; the pinch is where it touches the vertical axis."
          series={[{ key: 'T', label: 'Grand composite', color: 'var(--primary)', kind: 'line', source: src }]} />
        <Configurations cfgs={r.configurations} src={src} />
      </div>
      <FeheCard f={r.fehe} src={src} />
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Model consistency vs Aspen simulation</h3>
        <DataTable columns={[
          { key: 'item', label: 'Duty' },
          { key: 'model_kW', label: 'H-T curve model', unit: 'kW', align: 'right', render: (x) => <Value v={x.model_kW} digits={1} source="python_model" showSource={false} /> },
          { key: 'simulated_kW', label: 'Aspen block duty', unit: 'kW', align: 'right', render: (x) => <Value v={x.simulated_kW} digits={1} source="aspen_plus_v15" showSource={false} /> },
          { key: 'rel_deviation', label: 'Deviation', align: 'right', render: (x) => fmtPct(x.rel_deviation, 2) },
        ]} rows={r.consistency ?? []} caption="Python H-T curve duties against Aspen block duties" filename="heat_consistency.csv" />
        {(r.assumptions?.length || r.notes?.length) ? (
          <details style={{ marginTop: 8 }}><summary>Assumptions and notes ({(r.assumptions?.length ?? 0) + (r.notes?.length ?? 0)})</summary>
            <ul>{[...(r.assumptions ?? []), ...(r.notes ?? [])].map((a, i) => <li key={i}>{a.startsWith('ASSUMPTION') ? <><SourceBadge source="assumption" /> </> : null}{a}</li>)}</ul></details>) : null}
      </div>
    </>
  )
}

function Configurations({ cfgs, src }: { cfgs: HeatConfig[]; src: DataSource }) {
  const data = cfgs.map((c) => ({ cfg: c.id, 'External heating': c.external_heating_kW, 'External cooling': c.external_cooling_kW }))
  const cols: Column<HeatConfig>[] = [
    { key: 'label', label: 'Configuration', render: (c) => <span className="wrap-cell" title={c.basis}>{c.label}</span> },
    { key: 'external_heating_kW', label: 'Ext. heating', unit: 'kW', align: 'right', render: (c) => <Value v={c.external_heating_kW} digits={0} source={src} showSource={false} /> },
    { key: 'external_cooling_kW', label: 'Ext. cooling', unit: 'kW', align: 'right', render: (c) => <Value v={c.external_cooling_kW} digits={0} source={src} showSource={false} /> },
    { key: 'process_heat_recovered_kW', label: 'Recovered', unit: 'kW', align: 'right', render: (c) => <Value v={c.process_heat_recovered_kW} digits={0} source={src} showSource={false} /> },
    { key: 'tailgas_heat_used_kW', label: 'Tail-gas heat', unit: 'kW', align: 'right', render: (c) => <Value v={c.tailgas_heat_used_kW} digits={0} source={src} showSource={false} /> },
    { key: 'reduction_vs_no_recovery', label: 'Heating reduction', align: 'right', render: (c) => fmtPct(c.reduction_vs_no_recovery, 1), csv: (c) => String(c.reduction_vs_no_recovery) },
    { key: 'specific_heat_demand_kWh_per_kgH2', label: 'Specific demand', unit: 'kWh/kg H2', align: 'right', render: (c) => <Value v={c.specific_heat_demand_kWh_per_kgH2} digits={2} source={src} showSource={false} /> },
  ]
  return (
    <div className="page-block">
      <BarChartCard title="Heat-recovery configurations: external duties" source={src} xKey="cfg" xLabel="Configuration (a-d, see table)" yLabel="kW" data={data}
        description="Bar chart of external heating and cooling for each heat-recovery configuration."
        series={[{ key: 'External heating', label: 'External heating', color: 'var(--c-heat)' }, { key: 'External cooling', label: 'External cooling', color: 'var(--c-cold)' }]} />
      <DataTable columns={cols} rows={cfgs} caption="Configuration comparison (hover a name for its basis)" filename="heat_configurations.csv" />
    </div>
  )
}

function FeheCard({ f, src }: { f: FeheInfo | null; src: DataSource }) {
  if (!f || !f.present_in_simulation) return <Notice title="No FEHE in this case.">Heat integration is switched off in the active case, so there is no feed/effluent exchanger to describe.</Notice>
  const prof = (f.profile_duty_kW ?? []).map((q, i) => ({ Q: q, hot: f.profile_hot_T_C?.[i] ?? null, cold: f.profile_cold_T_C?.[i] ?? null }))
  return (
    <div className="grid-2">
      <div className="card">
        <h2>Feed/effluent exchanger (FEHE) <SourceBadge source={src} /></h2>
        <dl className="kv">
          <dt>Duty</dt><dd><Value v={f.duty_kW} unit="kW" digits={1} source="aspen_plus_v15" /> <span className="muted">{f.duty_source}</span></dd>
          <dt>Hot side in / out</dt><dd><Value v={f.hot_in_C} unit="degC" digits={1} source="aspen_plus_v15" showSource={false} /> / <Value v={f.hot_out_C} unit="degC" digits={1} source="aspen_plus_v15" showSource={false} /></dd>
          <dt>Cold side in / out</dt><dd><Value v={f.cold_in_C} unit="degC" digits={1} source="aspen_plus_v15" showSource={false} /> / <Value v={f.cold_out_C} unit="degC" digits={1} source="aspen_plus_v15" showSource={false} /></dd>
          <dt>Hot-end / cold-end approach</dt><dd><Value v={f.hot_end_approach_K} unit="K" digits={1} source={src} showSource={false} /> / <Value v={f.cold_end_approach_K} unit="K" digits={1} source={src} showSource={false} /></dd>
          <dt>Minimum internal approach</dt><dd><Value v={f.min_internal_approach_K} unit="K" digits={1} source={src} />{' '}{f.temperature_cross || f.approach_violation ? <StatusPill kind="error">violation</StatusPill> : <StatusPill kind="ok">no cross</StatusPill>}</dd>
          <dt>LMTD</dt><dd><Value v={f.lmtd_K} unit="K" digits={1} source={src} /></dd>
          <dt>UA (LMTD / segmented)</dt><dd><Value v={f.ua_lmtd_kW_K} unit="kW/K" digits={2} source={src} showSource={false} /> / <Value v={f.ua_segmented_kW_K} unit="kW/K" digits={2} source={src} showSource={false} /></dd>
          <dt>Assumed overall U</dt><dd><Value v={f.U_assumed_W_m2K} unit="W/(m2 K)" digits={0} source="assumption" /> <span className="muted">range {f.U_range_W_m2K?.join(' - ') ?? 'n/a'}</span></dd>
          <dt>Area (UA / U)</dt><dd><Value v={f.area_m2} unit="m2" digits={0} source="assumption" /> <span className="muted">range {f.area_range_m2?.map((x) => x.toFixed(0)).join(' - ') ?? 'n/a'} m2</span></dd>
        </dl>
        <p className="muted"><SourceBadge source="assumption" /> {f.U_note}</p>
      </div>
      <XYChart title="FEHE temperature profile (T vs duty)" xKey="Q" xLabel="Cumulative duty [kW]" yLabel="Temperature [degC]" data={prof} height={320}
        description="Hot and cold side temperature against cumulative exchanger duty."
        series={[{ key: 'hot', label: 'Hot side (cracked gas)', color: 'var(--c-heat)', kind: 'line', source: src }, { key: 'cold', label: 'Cold side (feed)', color: 'var(--c-cold)', kind: 'line', source: src }]} />
    </div>
  )
}

function ActiveDuty({ c }: { c: import('../api/types').SimulationResult }) {
  const rows = dutyBreakdown(c)
  const data = rows.map((r) => ({ block: r.label, 'Duty [kW]': r.duty_kW }))
  const cols: Column<DutyRow>[] = [
    { key: 'label', label: 'Block' }, { key: 'id', label: 'Aspen block' },
    { key: 'duty_kW', label: 'Duty', unit: 'kW', align: 'right', render: (r) => <Value v={r.duty_kW} digits={1} source={c.source} /> },
  ]
  return (
    <div className="grid-2">
      <BarChartCard title={`Duty breakdown of case ${c.case_id}`} source={c.source} xKey="block" xLabel="Block" yLabel="Duty [kW] (+ heat added, - removed)" data={data}
        description="Bar chart of simulated block duties of the active case." series={[{ key: 'Duty [kW]', label: 'Duty [kW]', color: 'var(--primary)' }]} />
      <div className="page-block">
        <DataTable columns={cols} rows={rows} caption="Aspen block duties (sign: positive = heat added to the process stream)" filename={`duties_${c.case_id}.csv`} />
        <p className="muted">Flue-gas heat is the FLUEHX duty (negative = heat removed from the flue gas); tail-gas combustion heat {' '}
          <Value v={c.kpis.tailgas_combustion_heat_kW} unit="kW" digits={0} source={c.source} />.</p>
      </div>
    </div>
  )
}

function WithWithout({ cases }: { cases: import('../api/types').SimulationResult[] }) {
  const a = cases.find((c) => c.case_id === 'baseline')
  const b = cases.find((c) => c.case_id === 'baseline_no_hi')
  if (!a || !b) return <Notice title="With/without heat integration.">Needs both <code>baseline</code> and <code>baseline_no_hi</code> results; {a ? 'baseline_no_hi' : 'baseline'} is not loaded, so no comparison is shown.</Notice>
  const rows = hiComparison(a, b)
  const cols: Column<HiCompareRow>[] = [
    { key: 'label', label: 'Metric' }, { key: 'unit', label: 'Unit' },
    { key: 'withHi', label: 'With heat integration (baseline)', align: 'right', render: (r) => <Value v={r.withHi} digits={r.digits} source={a.source} /> , csv: (r) => String(r.withHi) },
    { key: 'without', label: 'Without (baseline_no_hi)', align: 'right', render: (r) => <Value v={r.without} digits={r.digits} source={b.source} />, csv: (r) => String(r.without) },
  ]
  const bars = rows.slice(0, 3).map((r) => ({ metric: r.label, 'With heat integration': r.withHi, 'Without': r.without }))
  return (
    <div className="grid-2">
      <BarChartCard title="Heating, recovery and cooling: with vs without heat integration" source={a.source} xKey="metric" xLabel="Metric" yLabel="kW" data={bars}
        description="Bar chart comparing total external heating, recovered heat and cooling duty with and without heat integration."
        series={[{ key: 'With heat integration', label: 'With heat integration', color: 'var(--ok)' }, { key: 'Without', label: 'Without', color: 'var(--warn)' }]} />
      <DataTable columns={cols} rows={rows} caption="With vs without heat integration (both Aspen results)" filename="hi_comparison.csv" />
    </div>
  )
}

