import { useState } from 'react'
import { fmt } from '../../data/format'
import { StatusPill } from '../../components/ui'
import { AsyncView } from '../../features/common/Notice'
import { XYChart } from '../../features/common/XYChart'
import { HBarChart } from '../charts'
import { Callout, Reading, Section } from '../ui'
import { AssumptionsTable, COLORS, DTable, FileNote, SrcTag, useRJson, useRRows, type Assumption, type Prov, type Row } from './parts'
import { groupBy, isoCheck, num, pivotXY, srcOf, truthy } from './shape'

const END_USES: { id: string; label: string }[] = [
  { id: 'industrial_99.9', label: 'Industrial hydrogen (99.9 %)' }, { id: 'turbine_blend', label: 'Gas-turbine blend' }, { id: 'fuel_cell_grade_D', label: 'Fuel-cell hydrogen (ISO 14687 grade D)' },
]
const CASES: Record<string, string> = { '20bar_baseline': '20 bar baseline', '10bar': '10 bar', '30bar': '30 bar' }
const PRICE: Record<string, string> = { nh3_price_grey: 'Grey NH3', nh3_price_blue: 'Blue NH3', nh3_price_green_2030: 'Green NH3, 2030', nh3_price_green_current: 'Green NH3, current' }

interface Study extends Prov {
  iso_14687: { source: string; grades: Record<string, { name: string; index_min_pct: number; total_non_h2_max_ppm: number; limits_ppm: Record<string, number> }> }
  summary: Record<string, Record<string, { ranking_usd_per_kg_usable_h2: { config: string; usd_per_kg: number; conditional_on: string }[] }>>
  not_modelled: string[]
  config_labels?: Record<string, string>
}

const Check = ({ v, limit }: { v: unknown; limit: unknown }) => {
  const c = isoCheck(v, limit)
  const n = num(v)
  return <span className={c === 'fail' ? 'hyp-fail' : undefined}>{n === null ? 'n/a' : fmt(n, n < 1 ? 3 : n < 100 ? 2 : 0)}{c === 'pass' ? ' ✓' : c === 'fail' ? ' ✗' : ''}</span>
}

function Configs({ study }: { study: Study }) {
  const cfg = useRRows<Row>('purification', 'purification_configurations.csv')
  const [cs, setCs] = useState('20bar_baseline')
  const [eu, setEu] = useState('industrial_99.9')
  const lim = study.iso_14687.grades.D?.limits_ppm ?? {}
  const label = (id: string) => study.config_labels?.[id] ?? id
  return (
    <AsyncView a={cfg} what="the purification configurations">{({ rows }) => {
      const sub = rows.filter((r) => r.case === cs && r.end_use === eu)
      const data = sub.map((r) => ({ config: String(r.config), 'Cost per kg usable H2': num(r.usd_per_kg_usable_h2), Recovery: (num(r.h2_recovery) ?? 0) * 100 }))
      return (
        <>
          <div className="hyp-controls" role="group" aria-label="Operating pressure case">
            <span className="muted">Cracker pressure case:</span>
            {Object.entries(CASES).map(([k, l]) => <button key={k} type="button" className={`btn ${k === cs ? 'btn-primary' : ''}`} aria-pressed={k === cs} onClick={() => setCs(k)}>{l}</button>)}
          </div>
          <div className="hyp-controls" role="group" aria-label="End use">
            <span className="muted">End use:</span>
            {END_USES.map((e) => <button key={e.id} type="button" className={`btn ${e.id === eu ? 'btn-primary' : ''}`} aria-pressed={e.id === eu} onClick={() => setEu(e.id)}>{e.label}</button>)}
          </div>
          <HBarChart title={`Cost per kg usable hydrogen for ${END_USES.find((e) => e.id === eu)?.label.toLowerCase()}, ${CASES[cs]}`} source={srcOf(study.provenance?.source_type) ?? 'python_model'} data={data} catKey="config" xLabel="USD per kg usable H2" height={Math.max(300, sub.length * 36 + 90)}
            description="Cost per kg of hydrogen that meets the end-use specification for each purification configuration; configurations that do not meet the specification have no bar."
            series={[{ key: 'Cost per kg usable H2', label: 'Cost per kg usable H2', color: COLORS[0] }]} />
          <Reading>Configurations without a bar do not meet the end-use specification within the modelled species, so they have no usable-hydrogen cost. Membrane costs assume the infinite H2/N2 selectivity of the base model. The only sourced selectivity is an ideal, single-gas value for a new membrane; it is given with the required value under Membrane selectivity.</Reading>
          <DTable caption={`Purification configurations: recovery, purity, contaminants against ISO 14687 grade D limits and cost, ${CASES[cs]}, end use ${eu}`} rows={sub} keyOf={(r, i) => `${r.config}${i}`}
            cols={[
              { h: 'Configuration', cell: (r) => <><code>{String(r.config)}</code><div className="muted small">{label(String(r.config))}</div></>, th: true },
              { h: 'H2 recovery', cell: (r) => `${fmt((num(r.h2_recovery) ?? 0) * 100, 1)} %`, right: true },
              { h: 'H2 purity (mol %)', cell: (r) => fmt((num(r.purity_h2) ?? 0) * 100, 3), right: true },
              { h: `N2 ppm (limit ${fmt(lim.N2 ?? null, 0)})`, cell: (r) => <Check v={r.N2_ppm} limit={lim.N2} />, right: true },
              { h: `NH3 ppm (limit ${fmt(lim.NH3 ?? null, 1)})`, cell: (r) => <Check v={r.NH3_ppm} limit={lim.NH3} />, right: true },
              { h: `H2O ppm (limit ${fmt(lim.H2O ?? null, 0)})`, cell: (r) => <Check v={r.H2O_ppm} limit={lim.H2O} />, right: true },
              { h: 'Meets grade D (modelled species)', cell: (r) => <StatusPill kind={truthy(r.meets_gradeD_in_scope) ? 'ok' : 'neutral'}>{truthy(r.meets_gradeD_in_scope) ? 'yes' : 'no'}</StatusPill> },
              { h: 'Meets this end use', cell: (r) => <StatusPill kind={truthy(r.meets_enduse_spec) ? 'ok' : 'neutral'}>{truthy(r.meets_enduse_spec) ? 'yes' : 'no'}</StatusPill> },
              { h: 'USD/kg usable H2', cell: (r) => (num(r.usd_per_kg_usable_h2) === null ? 'n/a' : fmt(num(r.usd_per_kg_usable_h2), 2)), right: true },
              { h: 'Source', cell: () => <SrcTag s={study.provenance?.source_type} /> },
            ]} />
          <p className="muted small">ISO 14687:2019 grade D limits (umol/mol) from {study.iso_14687.source.split(';')[0]}. A tick or cross marks the modelled contaminant against the limit; purity is computed from the Aspen Plus V15 cracked-gas stream and the separation models, with PSA recoveries that are assumptions, not model results. Data file <code>results/research/purification/purification_configurations.csv</code>.</p>
        </>
      )
    }}</AsyncView>
  )
}

function Ranking({ study }: { study: Study }) {
  const label = (id: string) => study.config_labels?.[id] ?? id
  const s = study.summary['20bar_baseline'] ?? {}
  return (
    <>
      <h3>Ranking by cost per kg usable hydrogen (20 bar baseline)</h3>
      <div className="grid-3">
        {END_USES.map((e) => (
          <article key={e.id} className="card tile">
            <h4>{e.label}</h4>
            <ol className="hyp-list">
              {(s[e.id]?.ranking_usd_per_kg_usable_h2 ?? []).slice(0, 4).map((r) => (
                <li key={r.config}><code>{r.config}</code>: {fmt(r.usd_per_kg, 2)} USD/kg <span className="muted small">{label(r.config)}</span>{r.conditional_on ? <div className="small hyp-cond">{r.conditional_on}</div> : null}</li>
              ))}
            </ol>
          </article>
        ))}
      </div>
    </>
  )
}

function Curves() {
  const rc = useRRows<Row>('purification', 'recovery_vs_cost.csv')
  const pr = useRRows<Row>('purification', 'psa_recovery_vs_purity.csv')
  return (
    <>
      <AsyncView a={pr} what="the PSA recovery against purity relation">{({ rows }) => (
        <>
          <XYChart title="PSA recovery against product purity" height={320} description="Hydrogen recovery of a PSA unit against product purity from the mass-balance relation and from the published anchor"
            data={pivotXY('purity', [{ key: 'mb', rows, y: 'recovery_mass_balance_relation' }, { key: 'anchor', rows, y: 'recovery_hansen_anchor' }], { mb: 100, anchor: 100 }).map((r) => ({ ...r, purity: (r.purity as number) * 100 }))}
            xKey="purity" xLabel="H2 purity (mol %)" yLabel="H2 recovery (%)" xDomain={['auto', 'auto']}
            series={[{ key: 'mb', label: 'Mass-balance relation (optimistic)', color: COLORS[0], kind: 'line', source: 'python_model' }, { key: 'anchor', label: 'Anchored on a published low-recovery point', color: COLORS[1], kind: 'line', dashed: true, source: 'python_model' }]} />
          <Reading>Higher purity costs recovery. Only two published PSA recovery and purity points are available, so the slope between them is a model relation, not a measured curve; the two lines bracket what the data can support.</Reading>
        </>
      )}</AsyncView>
      <AsyncView a={rc} what="the recovery against cost data">{({ rows }) => {
        const g = groupBy(rows, 'config')
        const ps = [...g.entries()].map(([k, rs], i) => ({ key: `s${i}`, name: k, rows: rs }))
        return (
          <>
            <XYChart title="Cost per kg usable hydrogen against hydrogen recovery, fuel-cell purity" height={340} description="Cost per kg usable hydrogen against recovery for PSA plus TSA and Pd-Ag membrane configurations at fuel-cell purity"
              data={pivotXY('recovery', ps.map((p) => ({ key: p.key, rows: p.rows, y: 'usd_per_kg' })), Object.fromEntries(ps.map((p) => [p.key, 1]))).map((r) => ({ ...r, recovery: (r.recovery as number) * 100 }))}
              xKey="recovery" xLabel="H2 recovery (%)" yLabel="USD per kg usable H2"
              series={ps.map((p, i) => ({ key: p.key, label: p.name, color: COLORS[i % COLORS.length], kind: 'line' as const, source: 'python_model' as const }))} />
            <Reading>Lower recovery raises the cost per kg of hydrogen delivered, because the same cracker, ammonia feed and heat serve less product. This is the trade-off between purity requirement and recovery loss.</Reading>
          </>
        )
      }}</AsyncView>
    </>
  )
}

function Prices({ study }: { study: Study }) {
  const sp = useRRows<Row>('purification', 'singapore_price_scenario.csv')
  const [eu, setEu] = useState('industrial_99.9')
  return (
    <AsyncView a={sp} what="the Singapore price scenarios for purification">{({ rows }) => {
      const sub = rows.filter((r) => r.end_use === eu)
      const cfgs = [...new Set(sub.map((r) => String(r.config)))]
      const cases = Object.keys(PRICE).filter((k) => sub.some((r) => r.nh3_price_case === k))
      const data = cfgs.map((c) => ({ config: c, ...Object.fromEntries(cases.map((k) => [PRICE[k], num(sub.find((r) => r.config === c && r.nh3_price_case === k)?.usd_per_kg_usable_h2)])) }))
      return (
        <>
          <div className="hyp-controls" role="group" aria-label="End use">
            <span className="muted">End use:</span>
            {END_USES.map((e) => <button key={e.id} type="button" className={`btn ${e.id === eu ? 'btn-primary' : ''}`} aria-pressed={e.id === eu} onClick={() => setEu(e.id)}>{e.label}</button>)}
          </div>
          <HBarChart title="Cost per kg usable hydrogen by ammonia price scenario" source={srcOf(study.provenance?.source_type) ?? 'python_model'} data={data} catKey="config" xLabel="USD per kg usable H2" height={Math.max(420, cfgs.length * cases.length * 15 + 110)}
            description="Cost per kg usable hydrogen for each purification configuration under grey, blue and green ammonia price scenarios; missing bars mean the configuration does not meet the end-use specification."
            series={cases.map((k, i) => ({ key: PRICE[k], label: PRICE[k], color: COLORS[i] }))} />
          <p className="muted small">Singapore ammonia prices and electricity price as in the techno-economics page. Data file <code>results/research/purification/singapore_price_scenario.csv</code>.</p>
        </>
      )
    }}</AsyncView>
  )
}

export function PurificationView() {
  const study = useRJson<Study>('purification', 'purification_study.json')
  const ass = useRJson<Assumption[]>('purification', 'assumptions.json')
  return (
    <>
      <Section id="configs" title="PSA against membrane: recovery, purity, contaminants and cost" alt
        intro="Pressure swing adsorption (PSA, with a temperature swing adsorption dryer) and Pd-Ag membranes applied to the Aspen Plus V15 cracked-gas stream. Every product is checked against the ISO 14687 limits for the species the model tracks.">
        <AsyncView a={study} what="the purification study">{(s) => (
          <>
            <Configs study={s} />
            <Callout kind="warn" title="Not evaluated.">The model tracks NH3, N2, H2O and H2 only. These ISO 14687 items are not evaluated: {s.not_modelled.join(', ')}. A product that passes every modelled limit is therefore not claimed to be fuel-cell grade.</Callout>
            <Ranking study={s} />
          </>
        )}</AsyncView>
      </Section>
      <Section id="tradeoff" title="Purity against recovery and cost"><Curves /></Section>
      <Section id="singapore" title="Cost per kg usable hydrogen under Singapore ammonia prices" alt>
        <AsyncView a={study} what="the purification study">{(s) => <Prices study={s} />}</AsyncView>
        <AsyncView a={ass} what="the purification assumptions">{(a) => <AssumptionsTable rows={a} caption="Assumptions register of the purification study" />}</AsyncView>
        <AsyncView a={study} what="the purification provenance">{(s) => <FileNote prov={s.provenance} file="results/research/purification/purification_study.json" />}</AsyncView>
      </Section>
    </>
  )
}
