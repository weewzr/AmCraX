import { useMemo, useState } from 'react'
import { fmt } from '../../data/format'
import { AsyncView } from '../../features/common/Notice'
import { XYChart, type XYSeries } from '../../features/common/XYChart'
import { HBarChart } from '../charts'
import { Reading, Section } from '../ui'
import { AssumptionsTable, COLORS, countBeyond, DTable, FileNote, SrcTag, useRJson, useRRows, type Assumption, type Prov, type Row } from './parts'
import { groupBy, num, pivotXY, splitFitted, srcOf, truthy } from './shape'

const DEG = '°C'
const SRC = (r: Row[]) => r[0]?.source_type

function useNames(): Map<string, string> {
  const be = useRRows<Row>('catalyst_comparison', 'catalyst_breakeven_price.csv')
  return useMemo(() => {
    const m = new Map<string, string>()
    if (be.phase === 'ready') for (const r of be.data.rows) m.set(String(r.catalyst_id), String(r.catalyst))
    return m
  }, [be])
}

/* 1. kinetic against equilibrium conversion */
function Conversion({ names }: { names: Map<string, string> }) {
  const kt = useRRows<Row>('kinetics', 'study_conversion_vs_T.csv')
  const kp = useRRows<Row>('kinetics', 'study_conversion_vs_P.csv')
  const [p, setP] = useState<string>('20')
  const [t, setT] = useState<string>('600')
  return (
    <>
      <AsyncView a={kt} what="the conversion against temperature study">{({ rows }) => {
        const pressures = [...new Set(rows.map((r) => num(r.P_bar)).filter((x): x is number => x !== null))].sort((a, b) => a - b)
        const sel = pressures.find((x) => String(Math.round(x)) === p) ?? pressures[pressures.length - 1]
        const sub = rows.filter((r) => num(r.P_bar) === sel)
        const byCat = groupBy(sub, 'catalyst_id')
        const W = num(sub[0]?.W_cat_kg)
        const series: XYSeries[] = [], ps: { key: string; rows: Row[]; y: string }[] = []
        let i = 0
        for (const [id, rs] of byCat) {
          const { inside, beyond } = splitFitted(rs)
          const nm = names.get(id) ?? id
          const color = COLORS[i++ % COLORS.length]
          if (inside.length) { series.push({ key: id, label: nm, color, kind: 'line', source: srcOf(SRC(rs)) ?? 'python_model' }); ps.push({ key: id, rows: inside, y: 'X_kinetic' }) }
          if (beyond.length) { series.push({ key: `${id}~x`, label: `${nm} (beyond fitted range)`, color, kind: 'line', dashed: true, source: srcOf(SRC(rs)) ?? 'python_model' }); ps.push({ key: `${id}~x`, rows: beyond, y: 'X_kinetic' }) }
        }
        const first = [...byCat.values()][0] ?? []
        series.push({ key: 'eq', label: 'Equilibrium (ideal gas)', color: '#e5e7eb', kind: 'line', dashed: true, source: srcOf(SRC(first)) ?? 'python_model' })
        ps.push({ key: 'eq', rows: first, y: 'X_eq' })
        const scale = Object.fromEntries(ps.map((x) => [x.key, 100]))
        return (
          <>
            <div className="hyp-controls" role="group" aria-label="Pressure">
              <span className="muted">Pressure:</span>
              {pressures.map((x) => <button key={x} type="button" className={`btn ${x === sel ? 'btn-primary' : ''}`} aria-pressed={x === sel} onClick={() => setP(String(Math.round(x)))}>{fmt(x, x < 2 ? 3 : 0)} bar</button>)}
            </div>
            <XYChart title={`NH3 conversion against temperature at ${fmt(sel, sel < 2 ? 3 : 0)} bar, ${fmt(W, 0)} kg catalyst`} height={380}
              description="Kinetic conversion of each catalyst rate law and the equilibrium conversion against temperature. Dashed coloured lines are beyond the fitted range of that rate law."
              data={pivotXY('T_C', ps, scale)} xKey="T_C" xLabel={`Temperature (${DEG})`} yLabel="NH3 conversion (%)" yDomain={[0, 100]} series={series} />
            <Reading>The gap between a catalyst curve and the dashed equilibrium line is the kinetic penalty at this bed size. {countBeyond(sub) > 0 ? <>{countBeyond(sub)} of {sub.length} points are beyond the fitted range of their rate law (dashed coloured segments): at this pressure the curves are extrapolations.</> : 'All points are inside the fitted ranges of the rate laws.'}</Reading>
            <FileNote file="results/research/kinetics/study_conversion_vs_T.csv" />
          </>
        )
      }}</AsyncView>
      <AsyncView a={kp} what="the conversion against pressure study">{({ rows }) => {
        const temps = [...new Set(rows.map((r) => num(r.T_C)).filter((x): x is number => x !== null))].sort((a, b) => a - b)
        const sel = temps.find((x) => String(Math.round(x)) === t) ?? temps[temps.length - 1]
        const sub = rows.filter((r) => num(r.T_C) === sel)
        const byCat = groupBy(sub, 'catalyst_id')
        const series: XYSeries[] = [], ps: { key: string; rows: Row[]; y: string }[] = []
        let i = 0
        for (const [id, rs] of byCat) {
          const { inside, beyond } = splitFitted(rs)
          const nm = names.get(id) ?? id
          const color = COLORS[i++ % COLORS.length]
          if (inside.length) { series.push({ key: id, label: nm, color, kind: 'line', source: srcOf(SRC(rs)) ?? 'python_model' }); ps.push({ key: id, rows: inside, y: 'X_kinetic' }) }
          if (beyond.length) { series.push({ key: `${id}~x`, label: `${nm} (beyond fitted range)`, color, kind: 'line', dashed: true, source: srcOf(SRC(rs)) ?? 'python_model' }); ps.push({ key: `${id}~x`, rows: beyond, y: 'X_kinetic' }) }
        }
        const first = [...byCat.values()][0] ?? []
        series.push({ key: 'eq', label: 'Equilibrium (ideal gas)', color: '#e5e7eb', kind: 'line', dashed: true, source: srcOf(SRC(first)) ?? 'python_model' })
        ps.push({ key: 'eq', rows: first, y: 'X_eq' })
        return (
          <>
            <div className="hyp-controls" role="group" aria-label="Temperature">
              <span className="muted">Temperature:</span>
              {temps.map((x) => <button key={x} type="button" className={`btn ${x === sel ? 'btn-primary' : ''}`} aria-pressed={x === sel} onClick={() => setT(String(Math.round(x)))}>{fmt(x, 0)} {DEG}</button>)}
            </div>
            <XYChart title={`NH3 conversion against pressure at ${fmt(sel, 0)} ${DEG}, ${fmt(num(sub[0]?.W_cat_kg), 0)} kg catalyst`} height={340}
              description="Kinetic conversion of each catalyst rate law and the equilibrium conversion against pressure."
              data={pivotXY('P_bar', ps, Object.fromEntries(ps.map((x) => [x.key, 100])))} xKey="P_bar" xLabel="Pressure (bar)" yLabel="NH3 conversion (%)" yDomain={[0, 100]} series={series} />
            <Reading>Higher pressure lowers the equilibrium conversion (thermodynamics). Dashed coloured segments are beyond the fitted range of that rate law.</Reading>
            <FileNote file="results/research/kinetics/study_conversion_vs_P.csv" />
          </>
        )
      }}</AsyncView>
    </>
  )
}

/* 2. catalyst mass for a target approach to equilibrium */
function MassTargets({ names }: { names: Map<string, string> }) {
  const km = useRRows<Row>('kinetics', 'study_mass_for_fraction_of_equilibrium.csv')
  const am = useRRows<Row>('aspen_kinetic', 'catalyst_mass_targets.csv')
  const [f, setF] = useState('0.95')
  return (
    <>
      <AsyncView a={km} what="the catalyst mass study">{({ rows }) => {
        const fr = [...new Set(rows.map((r) => num(r.fraction_of_equilibrium)).filter((x): x is number => x !== null))].sort()
        const sel = fr.find((x) => String(x) === f) ?? fr[0]
        const sub = rows.filter((r) => num(r.fraction_of_equilibrium) === sel && truthy(r.reachable_within_1e7_kg))
        const byCat = groupBy(sub, 'catalyst_id')
        const series: XYSeries[] = [], ps: { key: string; rows: Row[]; y: string }[] = []
        let i = 0
        for (const [id, rs] of byCat) {
          const { inside, beyond } = splitFitted(rs)
          const nm = names.get(id) ?? id
          const color = COLORS[i++ % COLORS.length]
          if (inside.length) { series.push({ key: id, label: nm, color, kind: 'line', source: srcOf(SRC(rs)) ?? 'python_model' }); ps.push({ key: id, rows: inside, y: 'W_cat_kg' }) }
          if (beyond.length) { series.push({ key: `${id}~x`, label: `${nm} (beyond fitted range)`, color, kind: 'line', dashed: true, source: srcOf(SRC(rs)) ?? 'python_model' }); ps.push({ key: `${id}~x`, rows: beyond, y: 'W_cat_kg' }) }
        }
        return (
          <>
            <div className="hyp-controls" role="group" aria-label="Target approach to equilibrium">
              <span className="muted">Target approach to equilibrium:</span>
              {fr.map((x) => <button key={x} type="button" className={`btn ${x === sel ? 'btn-primary' : ''}`} aria-pressed={x === sel} onClick={() => setF(String(x))}>{fmt(x * 100, 0)} %</button>)}
            </div>
            <XYChart title={`Catalyst mass for ${fmt((sel ?? 0) * 100, 0)} % of the equilibrium conversion at ${fmt(num(sub[0]?.P_bar), 0)} bar`} height={380} yLog
              description="Catalyst mass needed to reach the target fraction of the equilibrium conversion against temperature, for each catalyst rate law, on a logarithmic mass axis."
              data={pivotXY('T_C', ps)} xKey="T_C" xLabel={`Temperature (${DEG})`} yLabel="Catalyst mass (kg, log scale)" series={series} />
            <Reading>Each curve gives the bed mass at which that rate law reaches the target at a given temperature, for the same feed flow in every case. {countBeyond(sub) > 0 ? <>{countBeyond(sub)} of {sub.length} points are beyond the fitted ranges of their rate laws (dashed): these 20 bar masses are extrapolated, not measured.</> : null}</Reading>
            <FileNote file="results/research/kinetics/study_mass_for_fraction_of_equilibrium.csv" />
          </>
        )
      }}</AsyncView>
      <AsyncView a={am} what="the Aspen-checked catalyst masses">{({ rows }) => (
        <>
          <h3>Catalyst mass checked in Aspen Plus V15</h3>
          <p className="prose-p">The Python masses above were re-run in the Aspen RPlug model at the same temperature and pressure. Where the Aspen approach to equilibrium differs from the target, the mass interpolated in Aspen is given.</p>
          <DTable caption="Catalyst mass for a target fraction of equilibrium: Python value and Aspen Plus V15 check" rows={rows} keyOf={(r, i) => `${r.catalyst_id}${r.T_C}${r.fraction_target}${i}`}
            cols={[
              { h: 'Catalyst', cell: (r) => String(r.catalyst), th: true },
              { h: `T (${DEG})`, cell: (r) => fmt(num(r.T_C), 0), right: true },
              { h: 'Target', cell: (r) => `${fmt((num(r.fraction_target) ?? 0) * 100, 0)} %`, right: true },
              { h: 'W Python (kg)', cell: (r) => fmt(num(r.W_python_kg), 1), right: true },
              { h: 'Aspen fraction at W Python', cell: (r) => (num(r.fraction_aspen_at_W_python) === null ? 'n/a' : `${fmt((num(r.fraction_aspen_at_W_python) as number) * 100, 1)} %`), right: true },
              { h: 'W Aspen, interpolated (kg)', cell: (r) => (num(r.W_aspen_interpolated_kg) === null ? 'n/a' : fmt(num(r.W_aspen_interpolated_kg), 1)), right: true },
              { h: 'Fitted range', cell: (r) => (truthy(r.within_fitted_range) ? 'inside' : 'extrapolated') },
              { h: 'Source', cell: (r) => <SrcTag s={r.source_type} /> },
            ]} />
          <FileNote file="results/research/aspen_kinetic/catalyst_mass_targets.csv" />
        </>
      )}</AsyncView>
    </>
  )
}

interface Findings {
  findings: {
    fixed_inventory_100kg_aspen: { fired_duty_HI_kW: Record<string, number>; fired_duty_noHI_kW: Record<string, number>; lcoh_HI_USD_per_kg: Record<string, number>; lcoh_noHI_USD_per_kg: Record<string, number>; source_type?: string; Ru_Al2O3_vs_Ni_fired_duty_reduction_HI?: number; Ru_Al2O3_minus_Ni_lcoh_HI?: number; Ru_Al2O3_minus_Ni_lcoh_noHI?: number }
    ranking_robustness: { n_cases: number; n_same_best_as_base: number; cases_where_a_low_T_catalyst_beats_Ni: string[]; max_abs_best_low_T_minus_Ni_USD_per_kg: number }
  }
  basis?: Record<string, string>
}

/* 3. heat duty and cost, with and without heat integration */
function HeatAndCost({ names }: { names: Map<string, string> }) {
  const cmp = useRJson<Findings & Prov>('catalyst_comparison', 'catalyst_comparison.json')
  const cost = useRRows<Row>('catalyst_comparison', 'catalyst_cost_breakdown_plotdata.csv')
  return (
    <>
      <AsyncView a={cmp} what="the catalyst comparison findings">{(d) => {
        const f = d.findings.fixed_inventory_100kg_aspen
        const cats = Object.keys(f.fired_duty_HI_kW)
        const duty = cats.map((c) => ({ catalyst: c, 'With heat integration': f.fired_duty_HI_kW[c], 'Without heat integration': f.fired_duty_noHI_kW[c] }))
        return (
          <>
            <HBarChart title="Fired heat duty of the cracker section per catalyst, 100 kg bed" source="aspen_plus_v15" data={duty} catKey="catalyst" xLabel="Fired duty (kW)" height={380}
              description="Fired process duty per catalyst with and without heat integration, from Aspen Plus V15 runs at each catalyst's kinetic operating temperature."
              series={[{ key: 'With heat integration', label: 'With heat integration', color: COLORS[0] }, { key: 'Without heat integration', label: 'Without heat integration', color: COLORS[1] }]} />
            <Reading>Heat integration lowers the fired duty by {fmt(Math.min(...cats.map((c) => (1 - f.fired_duty_HI_kW[c] / f.fired_duty_noHI_kW[c]) * 100)), 0)} to {fmt(Math.max(...cats.map((c) => (1 - f.fired_duty_HI_kW[c] / f.fired_duty_noHI_kW[c]) * 100)), 0)} % depending on the catalyst, which is a larger effect than the difference between catalysts. Aspen Plus V15 gives the duties; the 100 kg bed is the same for every catalyst.</Reading>
            <DTable caption="Fired duty and cost per kg H2 per catalyst, with and without heat integration (fixed 100 kg bed, Aspen duties, Python economics)" rows={cats} keyOf={(c) => c}
              cols={[
                { h: 'Catalyst', cell: (c) => c, th: true },
                { h: 'Fired duty with HI (kW)', cell: (c) => fmt(f.fired_duty_HI_kW[c], 0), right: true },
                { h: 'Fired duty without HI (kW)', cell: (c) => fmt(f.fired_duty_noHI_kW[c], 0), right: true },
                { h: 'LCOH with HI (USD/kg)', cell: (c) => fmt(f.lcoh_HI_USD_per_kg[c], 3), right: true },
                { h: 'LCOH without HI (USD/kg)', cell: (c) => fmt(f.lcoh_noHI_USD_per_kg[c], 3), right: true },
                { h: 'Source', cell: () => <><SrcTag s="aspen" /> <SrcTag s="python" /></> },
              ]} />
            <p className="muted small">Duties: Aspen Plus V15 (results/research/aspen_kinetic/ci_*.json); economics: independent Python model on those duties. {d.findings.fixed_inventory_100kg_aspen.source_type ? `File label: ${d.findings.fixed_inventory_100kg_aspen.source_type}.` : ''}</p>
          </>
        )
      }}</AsyncView>
      <AsyncView a={cost} what="the cost breakdown per catalyst">{({ rows }) => {
        const data = rows.map((r) => ({ catalyst: names.get(String(r.catalyst_id)) ?? String(r.catalyst_id), 'Heat fuel': num(r.heat_fuel), Catalyst: num(r.catalyst), Capex: num(r.capex), 'Fixed opex': num(r.fixed_opex) }))
        const feed = rows.map((r) => num(r.ammonia_feed)).filter((x): x is number => x !== null)
        return (
          <>
            <h3>Cost per kg hydrogen at each catalyst's cost-optimal temperature</h3>
            <HBarChart title="LCOH components other than ammonia feed, with heat integration" source={srcOf(SRC(rows)) ?? 'python_model'} data={data} catKey="catalyst" xLabel="USD per kg H2" stacked height={330}
              description="Stacked heat fuel, catalyst, capital and fixed operating cost per kg hydrogen for each catalyst at its cost-optimal temperature."
              series={[{ key: 'Heat fuel', label: 'Heat fuel', color: COLORS[1] }, { key: 'Catalyst', label: 'Catalyst', color: COLORS[0] }, { key: 'Capex', label: 'Capex', color: COLORS[4] }, { key: 'Fixed opex', label: 'Fixed opex', color: COLORS[5] }]} />
            <Reading>Ammonia feed ({feed.length ? `${fmt(Math.min(...feed), 3)} to ${fmt(Math.max(...feed), 3)}` : 'n/a'} USD/kg) is left out because it dominates and is nearly the same for all catalysts. Catalyst cost per kg of hydrogen is at most {fmt(Math.max(...rows.map((r) => num(r.catalyst) ?? 0)), 3)} USD across the catalysts, at the catalyst prices in the assumptions register.</Reading>
            <DTable caption="Cost-optimal design per catalyst (heat integration on)" rows={rows} keyOf={(r) => String(r.catalyst_id)}
              cols={[
                { h: 'Catalyst', cell: (r) => names.get(String(r.catalyst_id)) ?? String(r.catalyst_id), th: true },
                { h: `T optimum (${DEG})`, cell: (r) => fmt(num(r.T_opt_C), 0), right: true },
                { h: 'Catalyst mass (kg)', cell: (r) => fmt(num(r.W_kg), 1), right: true },
                { h: 'Ammonia feed (USD/kg)', cell: (r) => fmt(num(r.ammonia_feed), 3), right: true },
                { h: 'Heat fuel (USD/kg)', cell: (r) => fmt(num(r.heat_fuel), 3), right: true },
                { h: 'Catalyst (USD/kg)', cell: (r) => fmt(num(r.catalyst), 4), right: true },
                { h: 'LCOH (USD/kg)', cell: (r) => fmt(num(r.lcoh), 3), right: true },
                { h: 'Source', cell: (r) => <SrcTag s={r.source_type} /> },
              ]} />
            <FileNote file="results/research/catalyst_comparison/catalyst_cost_breakdown_plotdata.csv" />
          </>
        )
      }}</AsyncView>
    </>
  )
}

/* 4. break-even catalyst price and ranking robustness */
function BreakEven() {
  const be = useRRows<Row>('catalyst_comparison', 'catalyst_breakeven_price.csv')
  const rb = useRJson<{ cases: { case: string; best: string; same_ranking_as_base: boolean; same_best_as_base: boolean; best_low_T_minus_Ni_USD_per_kg: number; spread_USD_per_kg: number; source_type?: string }[] } & Prov>('catalyst_comparison', 'catalyst_ranking_robustness.json')
  const cmp = useRJson<Findings & Prov>('catalyst_comparison', 'catalyst_comparison.json')
  return (
    <>
      <AsyncView a={be} what="the break-even catalyst prices">{({ rows }) => (
        <>
          <DTable caption="Break-even catalyst price against the Ni reference at its cost-optimal temperature" rows={rows} keyOf={(r, i) => `${r.catalyst_id}${r.reference}${i}`}
            cols={[
              { h: 'Catalyst', cell: (r) => String(r.catalyst), th: true },
              { h: 'Reference', cell: (r) => <span className="small">{String(r.reference)}</span> },
              { h: 'Break-even price (USD/kg)', cell: (r) => fmt(num(r.breakeven_price_USD_per_kg), 0), right: true },
              { h: 'Assumed price (USD/kg)', cell: (r) => fmt(num(r.assumed_price_USD_per_kg), 0), right: true },
              { h: 'Break-even / assumed', cell: (r) => fmt(num(r.ratio_breakeven_to_Cho_Ru_price), 2), right: true },
              { h: `T at break-even (${DEG})`, cell: (r) => fmt(num(r.T_opt_at_breakeven_C), 0), right: true },
              { h: 'Source', cell: (r) => <SrcTag s={r.source_type} /> },
            ]} />
          <p className="muted small">Basis: {String(rows[0]?.basis ?? '')}. The price at which the catalyst's cost per kg of hydrogen equals the reference; above it the reference is cheaper. Data file <code>results/research/catalyst_comparison/catalyst_breakeven_price.csv</code>.</p>
        </>
      )}</AsyncView>
      <AsyncView a={rb} what="the ranking robustness cases">{(d) => {
        const rr = (cmp.phase === 'ready' ? cmp.data.findings.ranking_robustness : null)
        const worse = d.cases.filter((c) => !c.same_best_as_base)
        return (
          <>
            <h3>Is the catalyst ranking robust?</h3>
            <p className="prose-p">
              {rr ? <>The best catalyst is the same as in the base case in {rr.n_same_best_as_base} of {rr.n_cases} cases. A low-temperature catalyst has the lowest cost in {rr.cases_where_a_low_T_catalyst_beats_Ni.length} cases (listed below), by at most {fmt(rr.max_abs_best_low_T_minus_Ni_USD_per_kg, 3)} USD per kg H2.</> : <>{d.cases.length} cases were re-optimised.</>}
              {' '}Cost differences between catalysts are small against the cost of ammonia feed, so the ranking changes with small input changes.
            </p>
            {rr ? <p className="small"><strong>Cases in which a low-temperature catalyst beats Ni:</strong> {rr.cases_where_a_low_T_catalyst_beats_Ni.map((c) => <code key={c} className="hyp-code">{c}</code>)}</p> : null}
            <details className="hyp-details"><summary>All {d.cases.length} ranking cases ({worse.length} with a different best catalyst)</summary>
              <DTable caption="Ranking robustness: best catalyst and best low-temperature catalyst minus Ni cost per kg H2" rows={d.cases} keyOf={(c) => c.case}
                cols={[
                  { h: 'Case', cell: (c) => <code>{c.case}</code>, th: true },
                  { h: 'Best catalyst', cell: (c) => c.best },
                  { h: 'Same best as base', cell: (c) => (c.same_best_as_base ? 'yes' : 'no') },
                  { h: 'Best low-T minus Ni (USD/kg)', cell: (c) => fmt(c.best_low_T_minus_Ni_USD_per_kg, 4), right: true },
                  { h: 'Spread (USD/kg)', cell: (c) => fmt(c.spread_USD_per_kg, 4), right: true },
                  { h: 'Source', cell: (c) => <SrcTag s={c.source_type} /> },
                ]} />
            </details>
            <FileNote prov={d.provenance} file="results/research/catalyst_comparison/catalyst_ranking_robustness.json" />
          </>
        )
      }}</AsyncView>
    </>
  )
}

/* 5. comparison with the published Ni and Ru designs */
function ChoComparison() {
  const c = useRJson<{ summary: Row[]; boundary_differences: string[] } & Prov>('catalyst_comparison', 'catalyst_cho_comparison.json')
  return (
    <AsyncView a={c} what="the comparison with the published designs">{(d) => (
      <>
        <DTable caption="Ni and Ru designs on the AmCraX boundaries against the published values" rows={d.summary} keyOf={(r, i) => `${r.psa_recovery}${r.inventory_basis}${i}`}
          cols={[
            { h: 'PSA recovery', cell: (r) => fmt((num(r.psa_recovery) ?? 0) * 100, 0) + ' %', right: true, th: true },
            { h: 'Catalyst inventory basis', cell: (r) => String(r.inventory_basis) },
            { h: 'REC Ni (USD/kg)', cell: (r) => fmt(num(r.rec_Ni), 3), right: true },
            { h: 'REC Ru (USD/kg)', cell: (r) => fmt(num(r.rec_Ru), 3), right: true },
            { h: 'Ru REC lower by (%)', cell: (r) => fmt(num(r.rec_Ru_lower_by_pct), 2), right: true },
            { h: 'Ni needs supplementary NH3', cell: (r) => (truthy(r.Ni_needs_supplementary_fuel) ? 'yes' : 'no') },
            { h: 'Ru needs supplementary NH3', cell: (r) => (truthy(r.Ru_needs_supplementary_fuel) ? 'yes' : 'no') },
            { h: 'Source', cell: () => <SrcTag s="python" /> },
          ]} />
        <p className="muted small">A negative value means the Ru design is dearer than the Ni design on this boundary. Differences in system boundary against the published study:</p>
        <ul className="hyp-list">{d.boundary_differences.map((b, i) => <li key={i}>{b}</li>)}</ul>
        <FileNote prov={d.provenance} file="results/research/catalyst_comparison/catalyst_cho_comparison.json" />
      </>
    )}</AsyncView>
  )
}

export function CatalystView() {
  const names = useNames()
  const ass = useRJson<Assumption[]>('catalyst_comparison', 'assumptions.json')
  return (
    <>
      <Section id="conversion" title="Kinetic against equilibrium conversion" alt
        intro="Each catalyst has a published rate law. The conversion a given bed reaches is limited by kinetics at low temperature and by equilibrium at high temperature and pressure.">
        <Conversion names={names} />
      </Section>
      <Section id="mass" title="Catalyst mass for a target approach to equilibrium"
        intro="How much catalyst each rate law needs to come within a set fraction of the equilibrium conversion, and the same masses checked in Aspen Plus V15.">
        <MassTargets names={names} />
      </Section>
      <Section id="heat" title="Heat duty and cost with and without heat integration" alt
        intro="Fired duty from Aspen Plus V15 runs of the integrated flowsheet at each catalyst's operating temperature; cost from the independent Python economics model on those duties.">
        <HeatAndCost names={names} />
      </Section>
      <Section id="breakeven" title="Break-even catalyst price and ranking robustness">
        <BreakEven />
      </Section>
      <Section id="published" title="Ni and Ru designs against the published study" alt>
        <ChoComparison />
        <AsyncView a={ass} what="the catalyst assumptions">{(a) => <AssumptionsTable rows={a} caption="Assumptions register of the catalyst comparison" />}</AsyncView>
      </Section>
    </>
  )
}
