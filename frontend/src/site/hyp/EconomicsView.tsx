import { useState } from 'react'
import { fmt } from '../../data/format'
import { AsyncView } from '../../features/common/Notice'
import { XYChart } from '../../features/common/XYChart'
import { HBarChart } from '../charts'
import { Reading, Section } from '../ui'
import { AssumptionsTable, COLORS, DTable, FileNote, HeatGrid, SrcTag, useRJson, useRRows, type Assumption, type Prov, type Row } from './parts'
import { num, pivotXY, show, srcOf } from './shape'

const SCEN_LABEL: Record<string, string> = { grey: 'Grey NH3', blue: 'Blue NH3', green_current: 'Green NH3 (current price)', green_2030: 'Green NH3 (2030 price)', green_2050: 'Green NH3 (2050 price)' }
const PARTS: [string, string, string][] = [
  ['ammonia_feed', 'Ammonia feed', COLORS[1]], ['heat_fuel', 'Heat fuel', COLORS[5]], ['capex', 'Capex', COLORS[0]], ['fixed_opex', 'Fixed opex', COLORS[4]],
  ['catalyst', 'Catalyst', COLORS[2]], ['electricity', 'Electricity', COLORS[3]], ['cooling_water', 'Cooling water', COLORS[6]], ['carbon_tax', 'Carbon tax', COLORS[7]],
]
interface Scen { scenario: string; nh3_price_USD_per_t: number; lcoh_USD_per_kg: number; rec_USD_per_kg: number; breakdown_USD_per_kg: Record<string, number>; npv_USD: number; irr: number | null; payback_yr: number | null; kg_nh3_feed_per_kg_h2: number; annual_h2_kg: number; capex_total_USD: number }

function Scenarios() {
  const sr = useRJson<{ results: Record<string, Scen> } & Prov>('singapore', 'scenario_results.json')
  const [hi, setHi] = useState(true)
  return (
    <AsyncView a={sr} what="the scenario results">{(d) => {
      const suffix = hi ? 'heat_integration_on' : 'heat_integration_off'
      const rows = Object.entries(d.results).filter(([k]) => k.endsWith(suffix)).map(([, v]) => v)
      const src = srcOf(d.provenance?.source_type) ?? 'python_model'
      const data = rows.map((r) => ({ scenario: `${SCEN_LABEL[r.scenario] ?? r.scenario} (${fmt(r.nh3_price_USD_per_t, 0)} USD/t)`, ...Object.fromEntries(PARTS.map(([k, l]) => [l, r.breakdown_USD_per_kg[k] ?? 0])) }))
      const rec = rows.map((r) => ({ scenario: `${SCEN_LABEL[r.scenario] ?? r.scenario}`, 'REC (USD/kg H2)': r.rec_USD_per_kg }))
      return (
        <>
          <div className="hyp-controls" role="group" aria-label="Heat integration">
            <span className="muted">Heat integration:</span>
            <button type="button" className={`btn ${hi ? 'btn-primary' : ''}`} aria-pressed={hi} onClick={() => setHi(true)}>On</button>
            <button type="button" className={`btn ${!hi ? 'btn-primary' : ''}`} aria-pressed={!hi} onClick={() => setHi(false)}>Off</button>
          </div>
          <HBarChart title={`Levelised cost of hydrogen (LCOH) by component, heat integration ${hi ? 'on' : 'off'}`} source={src} data={data} catKey="scenario" stacked xLabel="USD per kg H2" height={400}
            description="Stacked cost components of the levelised cost of hydrogen for grey, blue and green ammonia price scenarios."
            series={PARTS.map(([, l, c]) => ({ key: l, label: l, color: c }))} />
          <Reading>{rows.every((r) => Object.entries(r.breakdown_USD_per_kg).sort((a, b) => b[1] - a[1])[0]?.[0] === 'ammonia_feed') ? 'Ammonia feed is the largest component in every scenario, so the ammonia price sets the cost of hydrogen.' : 'Ammonia feed is not the largest component in every scenario; see the chart.'}</Reading>
          <HBarChart title="Resource-adjusted cost (REC), the hydrogen cost without capital charge on the plant" source={src} data={rec} catKey="scenario" xLabel="USD per kg H2" height={300}
            description="REC per scenario" series={[{ key: 'REC (USD/kg H2)', label: 'REC (USD/kg H2)', color: COLORS[0] }]} />
          <DTable caption={`LCOH, REC and returns by ammonia scenario (heat integration ${hi ? 'on' : 'off'})`} rows={rows} keyOf={(r) => r.scenario}
            cols={[
              { h: 'Scenario', cell: (r) => SCEN_LABEL[r.scenario] ?? r.scenario, th: true },
              { h: 'NH3 price (USD/t)', cell: (r) => fmt(r.nh3_price_USD_per_t, 0), right: true },
              { h: 'LCOH (USD/kg)', cell: (r) => fmt(r.lcoh_USD_per_kg, 2), right: true },
              { h: 'REC (USD/kg)', cell: (r) => fmt(r.rec_USD_per_kg, 2), right: true },
              { h: 'NH3 feed (kg/kg H2)', cell: (r) => fmt(r.kg_nh3_feed_per_kg_h2, 2), right: true },
              { h: 'NPV at NE Asia SMR price (MUSD)', cell: (r) => fmt(r.npv_USD / 1e6, 1), right: true },
              { h: 'IRR', cell: (r) => (r.irr === null ? 'none' : `${fmt(r.irr * 100, 0)} %`), right: true },
              { h: 'Payback (yr)', cell: (r) => (r.payback_yr === null ? 'none' : fmt(r.payback_yr, 1)), right: true },
              { h: 'Source', cell: () => <SrcTag s={d.provenance?.source_type} /> },
            ]} />
          <FileNote prov={d.provenance} file="results/research/singapore/scenario_results.json" />
        </>
      )
    }}</AsyncView>
  )
}

function Tornado() {
  const t = useRJson<{ basis: string; lcoh_base_USD_per_kg: number; bars: { label: string; low_input: number; high_input: number; lcoh_at_low_input: number; lcoh_at_high_input: number; swing: number }[]; note?: string } & Prov>('singapore', 'tornado.json')
  return (
    <AsyncView a={t} what="the tornado data">{(d) => {
      const bars = [...d.bars].sort((a, b) => b.swing - a.swing)
      const data = bars.map((b) => ({ parameter: b.label, 'At low input': b.lcoh_at_low_input - d.lcoh_base_USD_per_kg, 'At high input': b.lcoh_at_high_input - d.lcoh_base_USD_per_kg }))
      return (
        <>
          <HBarChart title={`Tornado: change in LCOH from the base ${fmt(d.lcoh_base_USD_per_kg, 2)} USD/kg`} source={srcOf(d.provenance?.source_type) ?? 'python_model'} data={data} catKey="parameter" xLabel="Change in LCOH (USD per kg H2)" height={Math.max(360, bars.length * 48 + 100)}
            description="Change in the levelised cost of hydrogen when each input moves to the low and high end of its range, sorted by swing."
            series={[{ key: 'At low input', label: 'Parameter at low end of range', color: COLORS[0] }, { key: 'At high input', label: 'Parameter at high end of range', color: COLORS[1] }]} />
          <Reading>Basis: {d.basis}. The input ranges are written in each label. {d.note ?? ''}</Reading>
          <FileNote prov={d.provenance} file="results/research/singapore/tornado.json" />
        </>
      )
    }}</AsyncView>
  )
}

function BreakEven() {
  const b = useRJson<{ results: Record<string, Record<string, { h2_price_USD_per_kg: number; breakeven_nh3_USD_per_t: number | null; source: string }>>; nh3_scenarios_USD_per_t: Record<string, number> } & Prov>('singapore', 'breakeven_ammonia_price.json')
  const bm = useRJson<{ comparisons: Record<string, unknown>[] } & Prov>('singapore', 'benchmarks.json')
  return (
    <>
      <AsyncView a={b} what="the break-even ammonia prices">{(d) => {
        const on = d.results.heat_integration_on ?? {}, off = d.results.heat_integration_off ?? {}
        const keys = Object.keys(on)
        return (
          <>
            <DTable caption="Ammonia price at which LCOH equals each hydrogen price benchmark" rows={keys} keyOf={(k) => k}
              cols={[
                { h: 'Hydrogen benchmark', cell: (k) => <>{k.replace(/_/g, ' ')}<div className="muted small">{on[k].source}</div></>, th: true },
                { h: 'Benchmark (USD/kg)', cell: (k) => fmt(on[k].h2_price_USD_per_kg, 2), right: true },
                { h: 'Break-even NH3 price, HI on (USD/t)', cell: (k) => (on[k].breakeven_nh3_USD_per_t === null ? 'none' : fmt(on[k].breakeven_nh3_USD_per_t, 0)), right: true },
                { h: 'Break-even NH3 price, HI off (USD/t)', cell: (k) => (off[k]?.breakeven_nh3_USD_per_t == null ? 'none' : fmt(off[k].breakeven_nh3_USD_per_t, 0)), right: true },
                { h: 'Source type', cell: () => <><SrcTag s="python" /> <SrcTag s="literature" /></> },
              ]} />
            <p className="muted small">Ammonia price scenarios used: {Object.entries(d.nh3_scenarios_USD_per_t).map(([k, v]) => `${SCEN_LABEL[k] ?? k} ${fmt(v, 0)} USD/t`).join('; ')}. Benchmark prices are published market or report values (literature); the break-even ammonia price is calculated by the Python model. Where the break-even is below the scenario price, that scenario does not reach the benchmark.</p>
            <FileNote prov={d.provenance} file="results/research/singapore/breakeven_ammonia_price.json" />
          </>
        )
      }}</AsyncView>
      <AsyncView a={bm} what="the literature benchmarks">{(d) => (
        <>
          <h3>Comparison with the published REC</h3>
          {d.comparisons.map((c) => (
            <div key={String(c.item)} className="prose-p">
              <strong>{String(c.item)}.</strong>
              <ul className="hyp-list">
                {Object.entries(c).filter(([k]) => k !== 'item').map(([k, v]) => (
                  <li key={k}>{k.replace(/_/g, ' ')}: {show(v)} {k.startsWith('amcrax') ? <SrcTag s="python" /> : k.startsWith('literature') ? <SrcTag s="literature" /> : null}</li>
                ))}
              </ul>
            </div>
          ))}
        </>
      )}</AsyncView>
    </>
  )
}

function Maps() {
  const cap = useRRows<Row>('singapore', 'heatmap_nh3_price_x_capacity.csv')
  const tax = useRRows<Row>('singapore', 'heatmap_nh3_price_x_carbon_tax_nh3_heat.csv')
  const gas = useRRows<Row>('singapore', 'heatmap_nh3_price_x_carbon_tax_gas_heat_hypothetical.csv')
  const cvc = useRRows<Row>('singapore', 'cost_vs_capacity.csv')
  const mc = useRJson<{ n_samples: number; seed: number; distributions: Record<string, string>; results: Record<string, Record<string, number>> } & Prov>('singapore', 'monte_carlo.json')
  const sr = useRJson<Prov>('singapore', 'scenario_results.json')
  const prov = sr.phase === 'ready' ? sr.data.provenance : undefined
  const grid = (rows: Row[], rowKey: string) => {
    const cols = rows.length ? Object.keys(rows[0]).filter((k) => /^nh3_\d/.test(k)) : []
    const prices = cols.filter((_, i) => i % 2 === 0 || i === cols.length - 1)
    return {
      rowKeys: rows.map((r) => fmt(num(r[rowKey]), num(r[rowKey]) !== null && (num(r[rowKey]) as number) < 10 ? 1 : 0)),
      colKeys: prices.map((c) => c.replace('nh3_', '')),
      value: (r: string | number, c: string | number) => { const row = rows.find((x) => fmt(num(x[rowKey]), (num(x[rowKey]) as number) < 10 ? 1 : 0) === String(r)); return row ? num(row[`nh3_${c}`]) : null },
    }
  }
  return (
    <>
      <AsyncView a={cap} what="the price against capacity heatmap">{({ rows }) => { const g = grid(rows, 'nh3_feed_kmol_h'); return (
        <HeatGrid title="LCOH against ammonia price and plant capacity" rowLabel="NH3 feed (kmol/h)" colLabel="NH3 price (USD/t)" rowKeys={g.rowKeys} colKeys={g.colKeys} value={g.value} digits={2} source={prov?.source_type} unit="USD per kg H2"
          ariaDescription="Table of LCOH for ammonia feed capacity (rows) and ammonia price (columns)" />
      ) }}</AsyncView>
      <AsyncView a={tax} what="the carbon tax heatmap">{({ rows }) => { const g = grid(rows, 'carbon_tax_SGD_per_t'); return (
        <><HeatGrid title="LCOH against ammonia price and carbon tax, ammonia-fired heat" rowLabel="Carbon tax (SGD/t CO2e)" colLabel="NH3 price (USD/t)" rowKeys={g.rowKeys} colKeys={g.colKeys} value={g.value} digits={2} source={prov?.source_type} unit="USD per kg H2"
          ariaDescription="Table of LCOH for carbon tax (rows) and ammonia price (columns) when the cracker is heated by ammonia" />
        {rows.length > 1 && rows.every((r) => Object.keys(r).filter((k) => /^nh3_\d/.test(k)).every((k) => r[k] === rows[0][k])) ? <Reading>Every row is identical: with ammonia-fired heat the plant has no direct CO2 emission to tax, so the carbon tax does not change the cost in this model.</Reading> : null}</>
      ) }}</AsyncView>
      <AsyncView a={gas} what="the hypothetical gas-heat heatmap">{({ rows }) => { const g = grid(rows, 'carbon_tax_SGD_per_t'); return (
        <>
          <HeatGrid title="Hypothetical: LCOH against ammonia price and carbon tax if the heat came from natural gas" rowLabel="Carbon tax (SGD/t CO2e)" colLabel="NH3 price (USD/t)" rowKeys={g.rowKeys} colKeys={g.colKeys} value={g.value} digits={2} source={prov?.source_type} unit="USD per kg H2"
            ariaDescription="Table of LCOH for carbon tax and ammonia price under a hypothetical gas-fired heat case" />
          <Reading>This grid is a hypothetical comparison only, to show how a carbon tax would act if the heat were fossil; it is not a modelled plant design.</Reading>
        </>
      ) }}</AsyncView>
      <AsyncView a={cvc} what="the cost against capacity data">{({ rows }) => (
        <>
          <XYChart title="LCOH and REC against plant capacity at the grey ammonia price" height={320} description="LCOH and REC against hydrogen output in tonnes per day"
            data={pivotXY('h2_t_per_day', [{ key: 'lcoh', rows, y: 'lcoh' }, { key: 'rec', rows, y: 'rec' }])} xKey="h2_t_per_day" xLabel="Hydrogen output (t/day)" yLabel="USD per kg H2" yDomain={[0, 'auto']}
            series={[{ key: 'lcoh', label: 'LCOH', color: COLORS[0], kind: 'line', source: srcOf(prov?.source_type) ?? 'python_model' }, { key: 'rec', label: 'REC', color: COLORS[1], kind: 'line', source: srcOf(prov?.source_type) ?? 'python_model' }]} />
          <Reading>Capacity changes the capital and fixed-cost share only. The ammonia feed cost per kg of hydrogen does not scale with plant size.</Reading>
        </>
      )}</AsyncView>
      <AsyncView a={mc} what="the Monte Carlo results">{(d) => {
        const rows = Object.entries(d.results)
        const hi = Math.max(...rows.map(([, v]) => v.lcoh_p95))
        return (
          <>
            <h3>Uncertainty: Monte Carlo on the economic inputs</h3>
            <DTable caption={`LCOH and REC percentiles from ${fmt(d.n_samples, 0)} Monte Carlo samples (seed ${d.seed})`} rows={rows} keyOf={([k]) => k}
              cols={[
                { h: 'Scenario', cell: ([k]) => SCEN_LABEL[k] ?? k, th: true },
                { h: 'LCOH P5 (USD/kg)', cell: ([, v]) => fmt(v.lcoh_p5, 2), right: true },
                { h: 'LCOH P50', cell: ([, v]) => fmt(v.lcoh_p50, 2), right: true },
                { h: 'LCOH P95', cell: ([, v]) => fmt(v.lcoh_p95, 2), right: true },
                { h: 'P5 to P95 range', cell: ([, v]) => <span className="hyp-range" aria-hidden="true"><i style={{ left: `${(v.lcoh_p5 / hi) * 100}%`, width: `${((v.lcoh_p95 - v.lcoh_p5) / hi) * 100}%` }} /></span> },
                { h: 'REC P5 to P95 (USD/kg)', cell: ([, v]) => `${fmt(v.rec_p5, 2)} to ${fmt(v.rec_p95, 2)}`, right: true },
                { h: 'Source', cell: () => <SrcTag s={d.provenance?.source_type} /> },
              ]} />
            <p className="muted small">Sampled inputs: {Object.entries(d.distributions).map(([k, v]) => `${k.replace(/_/g, ' ')} ${v}`).join('; ')}.</p>
            <FileNote prov={d.provenance} file="results/research/singapore/monte_carlo.json" />
          </>
        )
      }}</AsyncView>
    </>
  )
}

export function EconomicsView() {
  const ass = useRJson<Assumption[]>('singapore', 'assumptions.json')
  return (
    <>
      <Section id="scenarios" title="LCOH and REC by ammonia scenario" alt
        intro="Levelised cost of hydrogen (LCOH) and the resource-adjusted cost (REC) for a cracker fed with grey, blue and green ammonia at published price scenarios, from the independent Python economics model run on the stored Aspen Plus V15 baseline.">
        <Scenarios />
      </Section>
      <Section id="tornado" title="Sensitivity: tornado"><Tornado /></Section>
      <Section id="breakeven" title="Break-even ammonia price" alt><BreakEven /></Section>
      <Section id="maps" title="Price, capacity, carbon tax and uncertainty"><Maps /></Section>
      <Section id="assumptions" title="Assumptions behind these figures" alt>
        <AsyncView a={ass} what="the assumptions register">{(a) => <AssumptionsTable rows={a} caption="Assumptions register of the Singapore techno-economics" />}</AsyncView>
      </Section>
    </>
  )
}
