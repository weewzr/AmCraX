import { useEffect, useMemo, useState } from 'react'
import '../features/common/features.css'
import { fetchEconStored, fetchLiveCurve, fetchStoredPriceCurve, postLcoh, type EconOverrides, type EconResponse, type EconResult, type LitBenchmark } from '../api/economics'
import { DataTable, type Column } from '../components/DataTable'
import { KpiTile, SourceBadge, StatusPill, Value } from '../components/ui'
import { useData } from '../data/DataContext'
import { fmt, fmtPct } from '../data/format'
import { AsyncView, ModeGate, Notice } from '../features/common/Notice'
import { mapAsync, useAsync } from '../features/common/useAsync'
import { BarsChart, ChartFrame, PriceCurveChart, TornadoChart } from '../features/economics/charts'
import {
  assumptionRows, breakdownRows, breakevenPrice, consumptionVsFloor, priceGrid, tornadoRows, type AssumptionRow, type BreakdownRow,
} from '../features/economics/shape'

const DEFAULTS = { nh3: 450, rate: 10, life: 25, hours: 8000, capex: 1, catalyst: 'Ni' as 'Ni' | 'Ru' }

export default function EconomicsPage() {
  const { mode, phase, active } = useData()
  const live = mode === 'LIVE' && phase === 'ready' && !!active
  const readable = (mode === 'LIVE' || mode === 'SNAPSHOT') && phase === 'ready' && !!active
  const caseId = active?.case_id ?? ''
  const [f, setF] = useState(DEFAULTS)
  const [q, setQ] = useState(DEFAULTS) // debounced query state
  useEffect(() => { const t = setTimeout(() => setQ(f), 400); return () => clearTimeout(t) }, [f])
  const overrides: EconOverrides = useMemo(() => ({
    nh3_price_USD_per_t: q.nh3, discount_rate: q.rate / 100, plant_life_yr: q.life, operating_hours_h_per_yr: q.hours, capex_multiplier: q.capex, catalyst: q.catalyst,
  }), [q])
  const lcoh = useAsync((s) => postLcoh(caseId, overrides, s), [caseId, overrides], live)
  const stored = useAsync((s) => fetchEconStored(caseId, s), [caseId], readable)
  const curveStored = useAsync((s) => fetchStoredPriceCurve(caseId, s), [caseId], readable)
  const curveLive = useAsync((s) => fetchLiveCurve(caseId, overrides, priceGrid(), s), [caseId, overrides], live)
  // SNAPSHOT: the stored default-assumption analysis stands in for the live calculation
  const view = mode === 'SNAPSHOT' ? mapAsync(stored, (r): EconResponse => ({ case_id: caseId, overrides: {}, result: r })) : lcoh
  const changed = JSON.stringify(f) !== JSON.stringify(DEFAULTS)
  const num = (k: keyof typeof DEFAULTS, min: number, max: number) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value); if (Number.isFinite(v) && v >= min && v <= max) setF((p) => ({ ...p, [k]: v }))
  }
  return (
    <section className="page">
      <h1>Techno-Economics</h1>
      <p className="lead">Levelised cost of hydrogen (LCOH) of the active case from the Python economics module, fed with the Aspen result. CAPEX is capacity-factored from published plant-level data and all prices are literature or assumption values; the result is an order-of-magnitude estimate, not an engineering cost estimate.</p>
      <ModeGate what="Re-calculating LCOH with changed what-if inputs" />
      <div className="card controls" role="group" aria-label="What-if inputs">
        <label className="field">NH3 price [USD/t]<input type="number" min={0} max={2000} step={10} value={f.nh3} disabled={!live} onChange={num('nh3', 0, 2000)} /></label>
        <label className="field">Discount rate [%]<input type="number" min={0.5} max={30} step={0.5} value={f.rate} disabled={!live} onChange={num('rate', 0.5, 30)} /></label>
        <label className="field">Plant life [yr]<input type="number" min={1} max={60} step={1} value={f.life} disabled={!live} onChange={num('life', 1, 60)} /></label>
        <label className="field">Operating hours [h/yr]<input type="number" min={1000} max={8760} step={100} value={f.hours} disabled={!live} onChange={num('hours', 1000, 8760)} /></label>
        <label className="field">CAPEX multiplier [-]<input type="number" min={0.1} max={3} step={0.1} value={f.capex} disabled={!live} onChange={num('capex', 0.1, 3)} /></label>
        <label className="field">Catalyst<select value={f.catalyst} disabled={!live} onChange={(e) => setF((p) => ({ ...p, catalyst: e.target.value as 'Ni' | 'Ru' }))}><option value="Ni">Ni</option><option value="Ru">Ru</option></select></label>
        <button type="button" className="btn" disabled={!live || !changed} onClick={() => setF(DEFAULTS)}>Reset to defaults</button>
        <span className="muted">Case <code>{caseId || 'n/a'}</code> {active ? <SourceBadge source={active.source} /> : null}; {live ? 'every change re-queries POST /api/economics/lcoh.' : 'stored default-assumption analysis (what-if recalculation needs the live API).'}</span>
      </div>
      {changed && live ? <Notice kind="warn" title="What-if values active.">The headline, breakdown and curve below use your modified inputs; the tornado and literature table are computed at the default assumptions.</Notice> : null}
      <AsyncView a={view} what="LCOH">{(d) => <Body r={d.result} stored={stored.data} curveStored={curveStored.data} curveLive={curveLive.data} nh3Price={q.nh3} changed={changed} />}</AsyncView>
      {stored.phase === 'error' ? <Notice kind="warn" title="Stored analysis not available.">Tornado, break-even target and literature values come from results/simulations/economics_{caseId}.json ({stored.error}).</Notice> : null}
    </section>
  )
}

function Body(p: { r: EconResult; stored: EconResult | null; curveStored: { nh3_price_USD_per_t: number; lcoh_USD_per_kg: number }[] | null; curveLive: { nh3_price_USD_per_t: number; lcoh_USD_per_kg: number }[] | null; nh3Price: number; changed: boolean }) {
  const { r, stored } = p
  const src = r.source
  const bd = useMemo(() => breakdownRows(r.breakdown_USD_per_kg), [r])
  const stack = [Object.fromEntries([['name', 'LCOH'], ...bd.map((b) => [b.key, b.usd])])]
  const cf = consumptionVsFloor(r.kg_nh3_feed_per_kg_h2, r.stoichiometric_floor_kg_nh3_per_kg_h2)
  const target = stored?.breakeven?.target_lcoh_USD_per_kg ?? 5
  const curve = p.curveLive ?? p.curveStored ?? []
  const be = breakevenPrice(curve, target)
  const lit = (stored?.literature_benchmarks ?? []).filter((l) => l.value !== null)
  const litPts = lit.filter((l) => l.nh3_price_USD_per_t !== null && l.nh3_price_USD_per_t !== undefined && l.kind !== 'reconversion').map((l) => ({ x: l.nh3_price_USD_per_t as number, y: l.value as number, label: l.label }))
  const torn = tornadoRows(stored?.tornado)
  const rows: AssumptionRow[] = assumptionRows(r.provenance)
  const aCols: Column<AssumptionRow>[] = [
    { key: 'key', label: 'Parameter' },
    { key: 'value', label: 'Value', align: 'right', render: (a) => typeof a.value === 'number' ? <Value v={a.value} unit={a.unit} source={null} showSource={false} /> : <span>{String(a.value ?? 'n/a')} {a.unit}</span>, csv: (a) => String(a.value ?? '') },
    { key: 'kind', label: 'Source', render: (a) => a.kind === 'literature' ? <span><SourceBadge source="literature" /> <code>{a.citekey}</code> {a.where ?? ''}</span> : a.kind === 'aspen' ? <SourceBadge source="aspen_plus_v15" /> : a.kind === 'python' ? <SourceBadge source="python_model" /> : <SourceBadge source="assumption" />, csv: (a) => `${a.kind} ${a.citekey ?? ''}` },
    { key: 'note', label: 'Note', render: (a) => <span className="wrap-cell muted">{a.note ?? ''}</span> },
  ]
  const bCols: Column<BreakdownRow>[] = [
    { key: 'label', label: 'Component' },
    { key: 'usd', label: 'Cost', unit: 'USD/kg H2', align: 'right', render: (b) => <Value v={b.usd} digits={4} source={src} showSource={false} /> },
    { key: 'share', label: 'Share', align: 'right', render: (b) => fmtPct(b.share, 1), csv: (b) => String(b.share ?? '') },
  ]
  const lCols: Column<LitBenchmark>[] = [
    { key: 'label', label: 'Published value' },
    { key: 'value', label: 'LCOH', unit: 'USD/kg', align: 'right', render: (l) => <Value v={l.value} digits={2} source="literature" showSource={false} /> },
    { key: 'nh3_price_USD_per_t', label: 'NH3 price', unit: 'USD/t', align: 'right', render: (l) => <Value v={l.nh3_price_USD_per_t ?? null} digits={0} source="literature" showSource={false} /> },
    { key: 'citekey', label: 'Citation', render: (l) => <span><code>{l.citekey}</code>, p. {l.page ?? 'n/a'}{l.locator ? `, ${l.locator}` : ''}</span>, csv: (l) => `${l.citekey} p.${l.page ?? ''}` },
    { key: 'kind', label: 'Kind', render: (l) => l.kind === 'reconversion' ? 'reconversion cost only' : 'total LCOH' },
  ]
  return (
    <>
      <div className="kpi-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 'var(--gap)' }}>
        <KpiTile label="LCOH (preliminary estimate)" v={r.lcoh_USD_per_kg} unit="USD/kg H2" digits={2} source={src} hint="preliminary estimate (order of magnitude)" />
        <KpiTile label="Total CAPEX (indicative)" v={r.capex.total_capex_USD} unit="USD" digits={0} source="literature" hint={r.capex.estimate_class} />
        <KpiTile label="Annual H2" v={r.annual_h2_kg} unit="kg/yr" digits={0} source={r.input_source ?? src} />
        <KpiTile label="Reconversion cost (LCOH less NH3 feed)" v={r.reconversion_cost_USD_per_kg} unit="USD/kg H2" digits={2} source={src} />
      </div>
      <Notice kind="warn" title="Preliminary estimate (order of magnitude) - not a detailed engineering estimate.">{r.capex.estimate_class} {r.cost_basis}. Method: <code>{r.capex.method}</code>{r.capex.selected?.citekey ? <> (<code>{r.capex.selected.citekey}</code>)</> : null}; CAPEX multiplier {r.capex.capex_multiplier}. {p.changed ? 'What-if inputs are active.' : ''}</Notice>
      <div className="grid-2">
        <ChartFrame title="LCOH breakdown (stacked)" sources={[src]} height={300} description="Single stacked bar of the LCOH contributions: CAPEX annuity, fixed OPEX, ammonia feed, imported heat, electricity, cooling water, catalyst."
          note="Ammonia feed dominates; CAPEX annuity and fixed OPEX follow. Electricity, cooling water and catalyst are barely visible.">
          <BarsChart data={stack} xKey="name" stacked xLabel="Case" yLabel="USD/kg H2" series={bd.map((b) => ({ key: b.key, label: b.label }))} />
        </ChartFrame>
        <DataTable columns={bCols} rows={bd} caption={`LCOH breakdown, total ${fmt(r.lcoh_USD_per_kg, 3)} USD/kg H2`} filename="lcoh_breakdown.csv" />
      </div>
      <div className="grid-2">
        <div className="card">
          <h2>Specific ammonia consumption vs stoichiometric floor <SourceBadge source={src} /></h2>
          <dl className="kv">
            <dt>Ammonia feed</dt><dd><Value v={r.kg_nh3_feed_per_kg_h2} unit="kg NH3/kg H2" digits={3} source={r.input_source ?? src} /></dd>
            <dt>Stoichiometric floor</dt><dd><Value v={r.stoichiometric_floor_kg_nh3_per_kg_h2} unit="kg NH3/kg H2" digits={3} source="python_model" /> <span className="muted">(2 NH3 -&gt; N2 + 3 H2, no losses)</span></dd>
            <dt>Excess over floor</dt><dd><Value v={cf.excess} unit="kg/kg" digits={3} source={src} showSource={false} /> ({fmtPct(cf.excessFrac, 1)}); floor / feed = {fmtPct(cf.floorFrac, 1)}</dd>
            <dt>Of which fuel ammonia</dt><dd><Value v={r.kg_nh3_fuel_per_kg_h2} unit="kg/kg H2" digits={3} source={r.input_source ?? src} showSource={false} /></dd>
          </dl>
          <div className="meter" role="img" aria-label={`Floor is ${fmtPct(cf.floorFrac, 1)} of the actual feed`} style={{ marginTop: 10, height: 12, background: 'var(--surface-2)', borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)' }}>
            <div style={{ width: `${Math.min(100, (cf.floorFrac ?? 0) * 100)}%`, height: '100%', background: 'var(--primary)' }} />
          </div>
          <p className="muted" style={{ fontSize: 12 }}>Bar: stoichiometric minimum as a share of the actual feed; the rest is ammonia lost to slip, PSA tail gas and fuel.</p>
        </div>
        <ChartFrame title={`LCOH vs ammonia price${p.curveLive ? ' (current what-if inputs)' : ' (stored, default assumptions)'}`} sources={[src, 'literature']} height={320}
          description="Line of LCOH against ammonia price with the break-even marker for the target LCOH, and published literature LCOH values as separate triangle markers."
          note={`Break-even for target ${target} USD/kg: ${be === null ? 'n/a' : `${fmt(be, 0)} USD/t NH3`} (linear interpolation of the curve; the target is the stored reference value, an assumption). Triangles are published literature values at their own plant and cost basis - not AmCraX results.`}>
          <PriceCurveChart data={curve.map((c) => ({ x: c.nh3_price_USD_per_t, y: c.lcoh_USD_per_kg }))} lineLabel="AmCraX LCOH (python model)" xLabel="Ammonia price [USD/t]" yLabel="LCOH [USD/kg H2]"
            breakeven={be === null ? null : { x: be, y: target }} literature={litPts} target={target} />
        </ChartFrame>
      </div>
      {torn.length ? (
        <div className="grid-2">
          <ChartFrame title="LCOH tornado (default assumptions)" sources={[stored?.source ?? 'python_model']} height={Math.max(260, torn.length * 46 + 70)} description="Horizontal bars of the LCOH range when each parameter moves between its low and high literature range, sorted by swing."
            note="Ranges are literature or library ranges (see table); base case is the dashed line.">
            <TornadoChart rows={torn} base={stored?.lcoh_USD_per_kg ?? r.lcoh_USD_per_kg ?? 0} />
          </ChartFrame>
          <DataTable columns={[
            { key: 'parameter', label: 'Parameter' }, { key: 'range', label: 'Range (low .. high)' },
            { key: 'low', label: 'LCOH low-end', unit: 'USD/kg', align: 'right', render: (t) => <Value v={t.low} digits={2} source="python_model" showSource={false} /> },
            { key: 'high', label: 'LCOH high-end', unit: 'USD/kg', align: 'right', render: (t) => <Value v={t.high} digits={2} source="python_model" showSource={false} /> },
            { key: 'swing', label: 'Swing', unit: 'USD/kg', align: 'right', render: (t) => <Value v={t.swing} digits={2} source="python_model" showSource={false} /> },
            { key: 'source', label: 'Range source' },
          ]} rows={torn} caption="Tornado data" filename="lcoh_tornado.csv" />
        </div>) : null}
      {lit.length ? (
        <div className="card">
          <h2>Published literature LCOH (reference only) <SourceBadge source="literature" /></h2>
          <p className="muted">These are values reported by other studies for different plants, scales, catalysts and cost years. They are context, not validation, and are never part of an AmCraX series.</p>
          <DataTable columns={lCols} rows={lit} caption="Published values" filename="literature_lcoh.csv" />
        </div>) : null}
      <div className="card">
        <h2>Assumptions <StatusPill kind="info">{rows.filter((a) => a.kind === 'assumption').length} marked as assumption</StatusPill></h2>
        <DataTable columns={aCols} rows={rows} caption="Every economic input with unit and source" filename="economics_assumptions.csv" />
        {r.notes?.length ? <details style={{ marginTop: 8 }}><summary>Notes and exclusions ({r.notes.length})</summary><ul>{r.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></details> : null}
      </div>
    </>
  )
}

