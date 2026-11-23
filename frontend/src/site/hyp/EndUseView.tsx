import { useState } from 'react'
import { fmt } from '../../data/format'
import { AsyncView } from '../../features/common/Notice'
import { XYChart } from '../../features/common/XYChart'
import { HBarChart } from '../charts'
import { Callout, Reading, Section } from '../ui'
import { AssumptionsTable, COLORS, DTable, FileNote, SrcTag, useRJson, useRRows, type Assumption, type Prov, type Row } from './parts'
import { groupBy, num, pivotXY, srcOf } from './shape'

const PRICES: [string, string][] = [['grey_450', 'Grey NH3, 450 USD/t'], ['blue_487', 'Blue NH3, 487 USD/t'], ['green_2030_709', 'Green NH3 2030, 709 USD/t'], ['green_current_1000', 'Green NH3 now, 1000 USD/t']]
const ROUTES: [string, string][] = [['green', 'Green NH3'], ['blue', 'Blue NH3'], ['grey', 'Grey NH3']]

interface EndUse extends Prov {
  halim_claim_check: { halim_statement: string; computed: Row[] }
  hydrogen_summary: Record<string, unknown>
  limitations: string[]
  nox_note?: string
}
interface Lca extends Prov {
  method: string; system_boundary: string; limitations: string[]
  alternatives: { ccgt_ng_kgCO2e_per_MWh: { central: number; source_type: string }; grid_average_kgCO2e_per_MWh: { central: number; source_type: string }; smr_h2_unabated_kgCO2e_per_kgH2: { central: number; range?: number[]; source_type: string }; smr_h2_ccs_kgCO2e_per_kgH2: { central: number; range?: number[]; source_type: string } }
}

function Power({ eu }: { eu: EndUse | null }) {
  const pw = useRRows<Row>('enduse', 'pathway_table_power.csv')
  const lca = useRJson<Lca>('lca', 'lca_results.json')
  const [price, setPrice] = useState('grey_450')
  return (
    <AsyncView a={pw} what="the power pathway table">{({ rows }) => {
      const key = `cost_USD_per_MWh_at_${price}`
      const costRows = [...rows].sort((a, b) => (num(a[key]) ?? 0) - (num(b[key]) ?? 0))
      const alt = lca.phase === 'ready' ? lca.data.alternatives : null
      const refs = alt ? [{ x: alt.ccgt_ng_kgCO2e_per_MWh.central, label: `Natural-gas CCGT ${fmt(alt.ccgt_ng_kgCO2e_per_MWh.central, 0)}` }, { x: alt.grid_average_kgCO2e_per_MWh.central, label: `Grid average ${fmt(alt.grid_average_kgCO2e_per_MWh.central, 0)}` }] : []
      return (
        <>
          <div className="hyp-controls" role="group" aria-label="Ammonia price scenario">
            <span className="muted">Ammonia price:</span>
            {PRICES.map(([k, l]) => <button key={k} type="button" className={`btn ${k === price ? 'btn-primary' : ''}`} aria-pressed={k === price} onClick={() => setPrice(k)}>{l}</button>)}
          </div>
          <HBarChart title="Cost of electricity per MWh by power pathway" source="python_model" data={costRows.map((r) => ({ pathway: String(r.pathway), 'USD per MWh': num(r[key]) }))} catKey="pathway" xLabel="USD per MWh net electricity" height={Math.max(420, rows.length * 38 + 90)}
            description="Levelised cost of electricity for direct ammonia combustion and cracking-based power pathways at the selected ammonia price."
            series={[{ key: 'USD per MWh', label: 'USD per MWh', color: COLORS[0] }]} />
          <Reading>Efficiency values are calibrated to published plant data (literature) and cost is computed by the Python economics model; each pathway's basis is listed in the table below. Compare the direct-combustion pathway (c1) with the cracking pathways at the same price.</Reading>
          <HBarChart title="Life-cycle carbon intensity of power by pathway and ammonia route" source="python_model" data={rows.map((r) => ({ pathway: String(r.pathway), 'Green NH3': num(r.CI_green_kgCO2e_per_MWh), 'Blue NH3': num(r.CI_blue_kgCO2e_per_MWh), 'Grey NH3': num(r.CI_grey_kgCO2e_per_MWh) }))} catKey="pathway" xLabel="kg CO2e per MWh net electricity" height={Math.max(520, rows.length * 62 + 110)} refLines={refs}
            description="Carbon intensity of electricity per pathway for green, blue and grey ammonia routes, with natural-gas CCGT and the Singapore grid average as reference lines."
            series={[{ key: 'Green NH3', label: 'Green NH3', color: COLORS[2] }, { key: 'Blue NH3', label: 'Blue NH3', color: COLORS[0] }, { key: 'Grey NH3', label: 'Grey NH3', color: COLORS[1] }]} />
          <Reading>Reference lines: natural-gas CCGT and the Singapore grid average{alt ? ` (${alt.ccgt_ng_kgCO2e_per_MWh.source_type}; ${alt.grid_average_kgCO2e_per_MWh.source_type})` : ''}. Ammonia routes below the lines cut emissions against them; routes above do not.</Reading>
          <DTable caption="Power pathways: efficiency, cost at each ammonia price and carbon intensity" rows={rows} keyOf={(r) => String(r.id)}
            cols={[
              { h: 'Pathway', cell: (r) => String(r.pathway), th: true },
              { h: 'Efficiency (NH3 LHV to power)', cell: (r) => `${fmt((num(r.efficiency_NH3_LHV_to_electricity) ?? 0) * 100, 1)} %`, right: true },
              ...PRICES.map(([k, l]) => ({ h: `${l.split(',')[0]} (USD/MWh)`, cell: (r: Row) => fmt(num(r[`cost_USD_per_MWh_at_${k}`]), 0), right: true })),
              ...ROUTES.map(([k, l]) => ({ h: `CI ${l} (kg CO2e/MWh)`, cell: (r: Row) => fmt(num(r[`CI_${k}_kgCO2e_per_MWh`]), 0), right: true })),
              { h: 'Basis', cell: (r: Row) => <span className="small">{String(r.source_labels ?? '')}</span> },
            ]} />
          <FileNote prov={eu?.provenance} file="results/research/enduse/pathway_table_power.csv" />
        </>
      )
    }}</AsyncView>
  )
}

function Claim({ eu }: { eu: EndUse }) {
  const sw = useRRows<Row>('enduse', 'price_sweep.csv')
  const rows = eu.halim_claim_check.computed
  return (
    <>
      <p className="prose-p">Statement tested: {eu.halim_claim_check.halim_statement}</p>
      <DTable caption="Direct ammonia combustion against cracking-based power: cost per MWh" rows={rows} keyOf={(r, i) => `${r.basis}${r.cracking_pathway}${i}`}
        cols={[
          { h: 'Basis', cell: (r) => String(r.basis), th: true },
          { h: 'Cracking pathway', cell: (r) => String(r.cracking_pathway).replace(/_/g, ' ') },
          { h: 'LCOE direct (USD/MWh)', cell: (r) => fmt(num(r.LCOE_direct), 0), right: true },
          { h: 'LCOE cracking (USD/MWh)', cell: (r) => fmt(num(r.LCOE_cracking), 0), right: true },
          { h: 'Direct cheaper than cracking by (%)', cell: (r) => fmt(num(r['direct_cheaper_by_pct_of_cracking(1-d/c)']), 1), right: true },
          { h: 'Source', cell: () => <><SrcTag s="python" /> <SrcTag s="literature" /></> },
        ]} />
      <p className="muted small">A negative percentage means direct combustion is dearer than that cracking pathway on this basis. Direct combustion is cheaper than {rows.filter((r) => (num(r['direct_cheaper_by_pct_of_cracking(1-d/c)']) ?? 0) > 0).length} of the {rows.length} cracking variants listed.</p>
      <p className="muted small"><strong>Read this with its main assumption.</strong> The fired and purified cracking pathways use the same turbine efficiency on hydrogen-rich fuel as the direct ammonia case (an assumption, listed in the end-use assumptions below), so a cracker can only add fuel use and capital. The direction of the comparison for those pathways therefore follows from that assumption; only the size of the gap is computed. The exhaust-heated pathways rest on a literature efficiency gain, not on a simulation.</p>
      <AsyncView a={sw} what="the price sweep">{({ rows: s }) => {
        const keys = Object.keys(s[0] ?? {}).filter((k) => k !== 'NH3_price_USD_t')
        return (
          <XYChart title="Cost per MWh against ammonia price" height={340} description="LCOE per power pathway against ammonia price" data={pivotXY('NH3_price_USD_t', keys.map((k) => ({ key: k, rows: s, y: k })))} xKey="NH3_price_USD_t" xLabel="Ammonia price (USD/t)" yLabel="USD per MWh"
            series={keys.map((k, i) => ({ key: k, label: k.replace(/_/g, ' '), color: COLORS[i % COLORS.length], kind: 'line' as const, source: 'python_model' as const }))} />
        )
      }}</AsyncView>
    </>
  )
}

function Hydrogen() {
  const h = useRRows<Row>('enduse', 'pathway_table_hydrogen.csv')
  return (
    <AsyncView a={h} what="the hydrogen pathway table">{({ rows }) => (
      <>
        <HBarChart title="Cost per kg usable hydrogen by end use and ammonia price" source="python_model" data={rows.map((r) => ({ pathway: String(r.pathway), ...Object.fromEntries(PRICES.map(([k, l]) => [l, num(r[`cost_USD_per_kg_at_${k}`])])) }))} catKey="pathway" xLabel="USD per kg H2" height={Math.max(380, rows.length * 4 * 18 + 110)}
          description="Cost per kg hydrogen at the stated purity and pressure for the hydrogen end uses at four ammonia prices."
          series={PRICES.map(([, l], i) => ({ key: l, label: l, color: COLORS[i] }))} />
        <DTable caption="Hydrogen pathways: efficiency, ammonia use, cost and carbon intensity" rows={rows} keyOf={(r) => String(r.id)}
          cols={[
            { h: 'Pathway', cell: (r) => <>{String(r.pathway)}<div className="muted small">{String(r.purity_note ?? '')}</div></>, th: true },
            { h: 'NH3 (kg/kg H2)', cell: (r) => fmt(num(r.NH3_kg_per_kg_H2), 2), right: true },
            { h: 'Grey NH3 (USD/kg)', cell: (r) => fmt(num(r.cost_USD_per_kg_at_grey_450), 2), right: true },
            { h: 'Blue NH3 (USD/kg)', cell: (r) => fmt(num(r.cost_USD_per_kg_at_blue_487), 2), right: true },
            { h: 'Green 2030 (USD/kg)', cell: (r) => fmt(num(r.cost_USD_per_kg_at_green_2030_709), 2), right: true },
            { h: 'CI green (kg CO2e/kg H2)', cell: (r) => fmt(num(r.CI_green_kgCO2e_per_kgH2), 1), right: true },
            { h: 'CI blue', cell: (r) => fmt(num(r.CI_blue_kgCO2e_per_kgH2), 1), right: true },
            { h: 'CI grey', cell: (r) => fmt(num(r.CI_grey_kgCO2e_per_kgH2), 1), right: true },
            { h: 'Basis', cell: (r) => <span className="small">{String(r.source_labels ?? '')}</span> },
          ]} />
        <FileNote file="results/research/enduse/pathway_table_hydrogen.csv" />
      </>
    )}</AsyncView>
  )
}

function Lcas() {
  const lr = useRRows<Row>('lca', 'lca_routes.csv')
  const ld = useRRows<Row>('lca', 'lca_distance.csv')
  const lca = useRJson<Lca>('lca', 'lca_results.json')
  return (
    <>
      <AsyncView a={lr} what="the life-cycle routes">{({ rows }) => {
        const alt = lca.phase === 'ready' ? lca.data.alternatives : null
        const refs = alt ? [{ x: alt.smr_h2_unabated_kgCO2e_per_kgH2.central, label: `SMR unabated ${fmt(alt.smr_h2_unabated_kgCO2e_per_kgH2.central, 1)}` }, { x: alt.smr_h2_ccs_kgCO2e_per_kgH2.central, label: `SMR with CCS ${fmt(alt.smr_h2_ccs_kgCO2e_per_kgH2.central, 1)}` }] : []
        return (
          <>
            <HBarChart title="Life-cycle carbon intensity of cracked hydrogen by ammonia route, 5000 km shipping" source="python_model" data={rows.map((r) => ({ route: String(r.label), 'kg CO2e per kg H2': num(r.H2_kgCO2e_per_kg) }))} catKey="route" xLabel="kg CO2e per kg H2" height={360} refLines={refs}
              description="Carbon intensity of industrial hydrogen made by cracking ammonia from each production route, with steam methane reforming without and with carbon capture as reference lines."
              series={[{ key: 'kg CO2e per kg H2', label: 'kg CO2e per kg H2', color: COLORS[0] }]} />
            <Reading>Reference lines are the Singapore-relevant alternatives, steam methane reforming without and with capture ({alt ? `${alt.smr_h2_unabated_kgCO2e_per_kgH2.source_type}; ${alt.smr_h2_ccs_kgCO2e_per_kgH2.source_type}` : 'literature'}). A route to the right of a line is worse than that alternative.</Reading>
            <DTable caption="Ammonia routes: emission factor at the production gate, with range, and delivered intensity" rows={rows} keyOf={(r) => String(r.route)}
              cols={[
                { h: 'Route', cell: (r) => String(r.label), th: true },
                { h: 'Gate (kg CO2e/kg NH3)', cell: (r) => fmt(num(r.gate_kgCO2e_per_kgNH3), 2), right: true },
                { h: 'Range', cell: (r) => `${fmt(num(r.range_low), 2)} to ${fmt(num(r.range_high), 2)}`, right: true },
                { h: 'Delivered, 5000 km', cell: (r) => fmt(num(r.delivered_5000km), 2), right: true },
                { h: 'H2 (kg CO2e/kg)', cell: (r) => fmt(num(r.H2_kgCO2e_per_kg), 1), right: true },
                { h: 'Direct NH3 CCGT (kg CO2e/MWh)', cell: (r) => fmt(num(r.direct_NH3_CCGT_kgCO2e_per_MWh), 0), right: true },
                { h: 'Cracked H2 CCGT (kg CO2e/MWh)', cell: (r) => fmt(num(r.cracked_purified_H2_CCGT_kgCO2e_per_MWh), 0), right: true },
                { h: 'Gate factor source', cell: (r) => <SrcTag s={r.source_type} /> },
              ]} />
            <FileNote file="results/research/lca/lca_routes.csv" />
          </>
        )
      }}</AsyncView>
      <AsyncView a={ld} what="the shipping distance scenarios">{({ rows }) => {
        const g = groupBy(rows, 'route')
        const ps = [...g.entries()].map(([k, rs], i) => ({ key: `r${i}`, name: k, rows: rs }))
        return (
          <XYChart title="Carbon intensity of cracked hydrogen against shipping distance" height={320} description="Hydrogen carbon intensity per ammonia route against ship distance"
            data={pivotXY('distance_km', ps.map((p) => ({ key: p.key, rows: p.rows, y: 'H2_kgCO2e_per_kg' })))} xKey="distance_km" xLabel="Shipping distance (km, scenario values)" yLabel="kg CO2e per kg H2"
            series={ps.map((p, i) => ({ key: p.key, label: `${p.name} NH3`, color: COLORS[i], kind: 'line' as const, source: srcOf('python') ?? 'python_model' }))} />
        )
      }}</AsyncView>
    </>
  )
}

export function EndUseView() {
  const eu = useRJson<EndUse>('enduse', 'enduse_results.json')
  const lca = useRJson<Lca>('lca', 'lca_results.json')
  const a1 = useRJson<Assumption[]>('enduse', 'assumptions.json')
  const a2 = useRJson<Assumption[]>('lca', 'assumptions.json')
  return (
    <>
      <Section id="power" title="Power pathways: cost per MWh and kg CO2e per MWh" alt
        intro="Direct ammonia combustion and cracking-based variants compared on the same plant basis. Cost per MWh is calculated by the Python economics model; efficiencies are calibrated to published plant data.">
        <Power eu={eu.phase === 'ready' ? eu.data : null} />
      </Section>
      <Section id="claim" title="Direct combustion against cracking-based power">
        <AsyncView a={eu} what="the end-use results">{(d) => <Claim eu={d} />}</AsyncView>
      </Section>
      <Section id="hydrogen" title="Cost per kg usable hydrogen by end use" alt><Hydrogen /></Section>
      <Section id="lca" title="Life-cycle carbon intensity by ammonia route against Singapore alternatives"
        intro="Global warming potential over 100 years, from the ammonia production gate to the cracker product, with shipping from an assumed distance.">
        <Lcas />
        <AsyncView a={lca} what="the life-cycle method">{(d) => (
          <Callout title="Method and limits.">{d.method} {d.system_boundary} Limitations: {d.limitations.join(' ')}</Callout>
        )}</AsyncView>
      </Section>
      <Section id="assumptions" title="Assumptions behind these figures" alt>
        <AsyncView a={a1} what="the end-use assumptions">{(a) => <AssumptionsTable rows={a} caption="Assumptions register of the end-use comparison" />}</AsyncView>
        <AsyncView a={a2} what="the life-cycle assumptions">{(a) => <AssumptionsTable rows={a} caption="Assumptions register of the life-cycle assessment" />}</AsyncView>
        <AsyncView a={eu} what="the end-use limitations">{(d) => <Callout title="End-use limitations.">{d.limitations.join(' ')}{d.nox_note ? ` ${d.nox_note}` : ''}</Callout>}</AsyncView>
      </Section>
    </>
  )
}
