import { useMemo, useState } from 'react'
import { compareCases, fetchScenarioComparison, fetchScenarioDefinitions, type CompareResponse } from '../../api/simulation'
import { describeError } from '../../api/http'
import { BarChartCard } from '../../components/charts'
import { DataTable, type Column } from '../../components/DataTable'
import { SourceBadge, StatusPill, Value } from '../../components/ui'
import { useData } from '../../data/DataContext'
import { fmt, fmtPct } from '../../data/format'
import { metricName, metricUnit } from '../../data/metrics'
import { ClampCell } from '../common/ClampCell'
import type { DataSource } from '../../api/types'
import { AsyncView, ModeGate, Notice, useLive, useReadable } from '../common/Notice'
import { useAsync } from '../common/useAsync'
import { barData, caseLabel, mixedEngines, shapeCompare, SOURCE_SHORT, type CompareDisplayRow } from './kpis'

const COLORS = ['var(--primary)', 'var(--accent)', 'var(--c-nh3)', 'var(--c-h2)']

export function Compare() {
  const { cases, caseLabel: labelOf } = useData()
  const live = useLive()
  const readable = useReadable()
  const defs = useAsync((s) => fetchScenarioDefinitions(s), [], readable)
  const [sel, setSel] = useState<string[]>([])
  const [res, setRes] = useState<CompareResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const defMap = useMemo(() => new Map((defs.data?.process_scenarios ?? []).map((d) => [d.id, d])), [defs.data])

  const toggle = (id: string) => { setRes(null); setSel((p) => p.includes(id) ? p.filter((x) => x !== id) : p.length >= 4 ? p : [...p, id]) }
  const run = async () => {
    setBusy(true); setErr(null)
    try { setRes(await compareCases(sel)) } catch (e) { setRes(null); setErr(describeError(e)) } finally { setBusy(false) }
  }
  return (
    <div className="page-block">
      <div className="card">
        <div className="section-h"><h2>Scenario comparison</h2><span className="muted">{sel.length} of 4 selected (2-4 needed)</span></div>
        <p className="muted">Pick 2 to 4 stored cases. Deltas are relative to the first case you picked (reference). Named scenarios show their label; hover for the rationale.</p>
        <ModeGate what="Comparing cases side by side (recalculated deltas)" />
        <div className="chips" role="group" aria-label="Cases to compare">
          {cases.map((c) => {
            const d = defMap.get(c.case_id)
            const on = sel.includes(c.case_id)
            const order = sel.indexOf(c.case_id)
            return (
              <button key={c.case_id} type="button" className="chip" aria-pressed={on} onClick={() => toggle(c.case_id)} disabled={!live || (!on && sel.length >= 4)}
                title={d ? `${d.label}: ${d.rationale}` : `${c.case_id} (${SOURCE_SHORT[c.source]})`}>
                {on ? `${order + 1}. ` : ''}{d?.label ?? labelOf(c.case_id)} <span className="muted">[{SOURCE_SHORT[c.source]}]</span>
              </button>)
          })}
        </div>
        {sel.some((id) => defMap.has(id)) ? (
          <ul className="msg-list">{sel.filter((id) => defMap.has(id)).map((id) => <li key={id}><strong>{defMap.get(id)!.label}</strong>: {defMap.get(id)!.rationale}</li>)}</ul>) : null}
        <div className="controls" style={{ marginTop: 10 }}>
          <button type="button" className="btn btn-primary" disabled={!live || sel.length < 2 || busy} onClick={() => void run()}>{busy ? 'Comparing ...' : 'Compare selected cases'}</button>
          {sel.length > 0 ? <button type="button" className="btn btn-sm" onClick={() => { setSel([]); setRes(null) }}>Clear</button> : null}
        </div>
        {err ? <p className="err-text" role="alert">Comparison failed - {err}</p> : null}
      </div>
      {res ? <CompareView r={res} defMap={defMap} /> : null}
      <Overlay live={readable} />
    </div>
  )
}

function CompareView({ r, defMap }: { r: CompareResponse; defMap: Map<string, { label: string }> }) {
  const rows = useMemo(() => shapeCompare(r), [r])
  const mixed = mixedEngines(r)
  const unconverged = r.cases.filter((c) => !c.converged)
  const cols: Column<CompareDisplayRow>[] = [{ key: 'label', label: 'KPI', render: (x) => <span>{x.label}{x.unit && x.unit !== '-' ? <span className="unit"> [{x.unit}]</span> : null}</span>, csv: (x) => `${x.label}${x.unit ? ` [${x.unit}]` : ''}` }]
  for (const c of r.cases) {
    const ref = c.case_id === r.reference_case
    const h = caseLabel(c)
    cols.push({ key: `v_${c.case_id}`, label: h, align: 'right', render: (x) => <Value v={x.cells[c.case_id]?.v} digits={x.digits} source={c.source} showSource={false} />, csv: (x) => String(x.cells[c.case_id]?.v ?? '') })
    cols.push({ key: `d_${c.case_id}`, label: `delta ${c.case_id}`, align: 'right', render: (x) => ref ? <span className="muted">ref</span> : <span>{fmt(x.cells[c.case_id]?.d, x.digits + 1)}</span>, csv: (x) => ref ? '' : String(x.cells[c.case_id]?.d ?? '') })
    cols.push({ key: `r_${c.case_id}`, label: `delta % ${c.case_id}`, align: 'right', render: (x) => ref ? <span className="muted">ref</span> : <span>{fmtPct(x.cells[c.case_id]?.rel, 2)}</span>, csv: (x) => ref ? '' : String(x.cells[c.case_id]?.rel ?? '') })
  }
  const inCols: Column<{ input: string; values: CompareResponse['changed_inputs'][number]['values'] }>[] = [{ key: 'input', label: 'Differing input' },
    ...r.cases.map((c) => ({ key: c.case_id, label: caseLabel(c), render: (x: { values: Record<string, unknown> }) => <span>{String(x.values[c.case_id] ?? 'n/a')}</span>, csv: (x: { values: Record<string, unknown> }) => String(x.values[c.case_id] ?? '') }))]
  const groups: { g: 'performance' | 'product' | 'duty' | 'specific'; title: string; y: string }[] = [
    { g: 'performance', title: 'Conversion, yield, purity, efficiency', y: 'fraction (-)' },
    { g: 'product', title: 'Hydrogen product and cracked gas', y: 'kg/h or kmol/h (see axis labels)' },
    { g: 'duty', title: 'Duties and power', y: 'kW' },
    { g: 'specific', title: 'Specific heat demand', y: 'kWh/kg H2' },
  ]
  const same = new Set(r.cases.map((c) => c.source))
  const badgeSrc = same.size === 1 ? r.cases[0].source : null
  return (
    <div className="page-block">
      {mixed ? <Notice kind="warn" title="Different engines compared.">This comparison mixes {[...same].map((s) => SOURCE_SHORT[s]).join(' and ')} results. Differences between an Aspen case and a Python case include model differences (Aspen: rigorous Peng-Robinson RGibbs; Python: independent reduced model), not only changed inputs. Each column carries its provenance.</Notice> : null}
      {unconverged.length ? <Notice kind="error" title="Not converged.">{unconverged.map((c) => c.case_id).join(', ')} did not converge; its numbers must not be relied on.</Notice> : null}
      <div className="card"><strong>Provenance per column: </strong>{r.cases.map((c) => <span key={c.case_id} className="series-chip"><code>{c.case_id}</code> <SourceBadge source={c.source} />{c.case_id === r.reference_case ? ' (reference)' : ''}{defMap.get(c.case_id) ? ` - ${defMap.get(c.case_id)!.label}` : ''}</span>)}</div>
      {r.changed_inputs.filter((x) => x.input !== 'case_id').length ? (
        <DataTable columns={inCols} rows={r.changed_inputs.filter((x) => x.input !== 'case_id')} caption="Inputs that differ between the cases" filename="compare_inputs.csv" />
      ) : <Notice title="Identical inputs.">The selected cases have the same operating inputs; any KPI differences come from the engines.</Notice>}
      <DataTable columns={cols} rows={rows} caption={`KPIs: value, absolute and relative difference vs ${r.reference_case}`} filename={`scenario_comparison_${r.cases.map((c) => c.case_id).join('_vs_')}.csv`} />
      <div className="grid-2">
        {groups.map((g) => {
          const data = barData(rows, g.g, r)
          if (!data.length) return null
          return <BarChartCard key={g.g} title={g.title} source={badgeSrc} xKey="kpi" xLabel="" yLabel={g.y} data={data}
            description={`Grouped bar chart of ${g.title} for ${r.cases.map((c) => c.case_id).join(', ')}.`}
            series={r.cases.map((c, i) => ({ key: c.case_id, label: caseLabel(c), color: COLORS[i % COLORS.length] }))} />
        })}
      </div>
    </div>
  )
}

interface OverlayRow {
  id: string; label: string; rationale?: string; source: DataSource; converged?: boolean; inputs_differing_from_baseline?: string
  metrics?: Record<string, number | null>; python_metrics?: Record<string, number | null>
  delta_rel_vs_baseline?: Record<string, number | null>
  overlays?: { nh3_origin: string; heat_source: string; nh3_price_USD_per_t?: number | null; price_basis?: string; lcoh_USD_per_kg?: number | null; carbon_intensity_kgCO2e_per_kgH2?: number | null }[]
}
const HEAT_LABEL: Record<string, string> = { tail_gas_plus_ammonia: 'tail gas + NH3 fuel', tail_gas_plus_natural_gas: 'tail gas + natural gas', tail_gas_plus_electric: 'tail gas + electric' }

/** Scenario overlay table from GET /api/scenarios/comparison: one row per named scenario, metrics with units, deltas vs baseline. */
function Overlay({ live }: { live: boolean }) {
  const a = useAsync((s) => fetchScenarioComparison(s), [], live)
  const [sel, setSel] = useState('baseline')
  return (
    <div className="card">
      <div className="section-h"><h2>Scenario overlay: named scenarios with LCOH and carbon intensity</h2><SourceBadge source="aspen_plus_v15" /></div>
      <p className="muted">Process values come from the stored Aspen Plus V15 scenario results; LCOH and carbon intensity are Python-model evaluations of those results with documented assumptions (preliminary LCOH, simplified carbon-intensity accounting; not an LCA). Overlays are not Aspen cases.</p>
      <AsyncView a={a} what="Scenario overlay table">
        {(d) => {
          const o = d as { rows?: OverlayRow[]; notes?: string[]; settings?: Record<string, unknown> }
          const rows = o.rows ?? []
          if (!rows.length) return <Notice kind="warn" title="Unrecognised format.">The overlay response has no scenario rows.</Notice>
          const num = (r: OverlayRow, k: string) => r.metrics?.[k] ?? null
          const cols: Column<OverlayRow>[] = [
            { key: 'label', label: 'Scenario', render: (r) => <span title={r.rationale}><strong>{r.label}</strong> <span className="muted">({r.id})</span></span>, csv: (r) => r.label },
            { key: 'source', label: 'Process source', render: (r) => <SourceBadge source={r.source} />, csv: (r) => r.source },
            { key: 'converged', label: 'Converged', render: (r) => r.converged === false ? <StatusPill kind="error">no</StatusPill> : <StatusPill kind="ok">yes</StatusPill>, csv: (r) => String(r.converged) },
            ...['nh3_conversion', 'h2_product_kg_h', 'total_external_heating_kW', 'specific_heat_demand_kWh_per_kgH2', 'lcoh_USD_per_kg', 'carbon_intensity_kgCO2e_per_kgH2'].map((k): Column<OverlayRow> => ({
              key: k, label: metricName(k), unit: metricUnit(k) === '-' ? undefined : metricUnit(k), align: 'right',
              render: (r) => <Value v={num(r, k)} digits={k === 'nh3_conversion' ? 4 : k.includes('USD') || k.includes('carbon') || k.includes('specific') ? 2 : 1} source={k.includes('lcoh') || k.includes('carbon') ? 'python_model' : r.source} showSource={false} />,
              csv: (r) => String(num(r, k) ?? ''),
            })),
            { key: 'dl', label: 'LCOH vs baseline', align: 'right', render: (r) => <span>{fmtPct(r.delta_rel_vs_baseline?.lcoh_USD_per_kg ?? null, 1)}</span>, csv: (r) => String(r.delta_rel_vs_baseline?.lcoh_USD_per_kg ?? '') },
            { key: 'dc', label: 'CI vs baseline', align: 'right', render: (r) => <span>{fmtPct(r.delta_rel_vs_baseline?.carbon_intensity_kgCO2e_per_kgH2 ?? null, 1)}</span>, csv: (r) => String(r.delta_rel_vs_baseline?.carbon_intensity_kgCO2e_per_kgH2 ?? '') },
          ]
          const chosen = rows.find((r) => r.id === sel) ?? rows[0]
          return (
            <>
              <DataTable columns={cols} rows={rows} caption="Named scenarios (GET /api/scenarios/comparison); LCOH and CI columns are Python-model values (reduced-order, preliminary)" filename="scenario_overlays.csv" />
              <div className="controls" style={{ marginTop: 10 }}>
                <label className="field">Ammonia origin x heat source overlay for<select value={chosen.id} onChange={(e) => setSel(e.target.value)}>{rows.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}</select></label>
              </div>
              {chosen.overlays?.length ? (
                <DataTable<NonNullable<OverlayRow['overlays']>[number]> rows={chosen.overlays} caption={`Overlays on ${chosen.label} (assumption-based, not Aspen cases)`} filename={`overlay_${chosen.id}.csv`}
                  columns={[
                    { key: 'nh3_origin', label: 'NH3 origin' },
                    { key: 'heat_source', label: 'Heat source', render: (r) => <span>{HEAT_LABEL[r.heat_source] ?? r.heat_source}</span>, csv: (r) => r.heat_source },
                    { key: 'lcoh_USD_per_kg', label: 'LCOH (preliminary)', unit: 'USD/kg H2', align: 'right', render: (r) => <Value v={r.lcoh_USD_per_kg} digits={2} source="python_model" showSource={false} /> },
                    { key: 'carbon_intensity_kgCO2e_per_kgH2', label: 'Carbon intensity (simplified)', unit: 'kg CO2e/kg H2', align: 'right', render: (r) => <Value v={r.carbon_intensity_kgCO2e_per_kgH2} digits={2} source="python_model" showSource={false} /> },
                    { key: 'price_basis', label: 'Price basis', render: (r) => <ClampCell text={r.price_basis ?? ''} max={70} />, csv: (r) => r.price_basis ?? '' },
                  ]} />) : null}
              {(o.notes ?? []).length ? <details><summary>Notes ({o.notes?.length})</summary><ul className="msg-list">{o.notes?.map((n, i) => <li key={i}>{n}</li>)}</ul></details> : null}
            </>)
        }}
      </AsyncView>
    </div>
  )
}
