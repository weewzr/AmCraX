/**
 * Phase 2 sections of the research pages. Every number is read from a stored result file mirrored into the snapshot
 * (scripts/export_snapshot.py, PHASE2_FILES); nothing numeric is typed here. Mode B of the carbon-pricing control is a
 * linear interpolation of the stored Python sweep (results/research/carbon_pricing/price_sweep.csv, step 5 SGD/tCO2e).
 */
import { useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { staticAssetUrl } from '../../api/client'
import { fmt } from '../../data/format'
import { AsyncView } from '../../features/common/Notice'
import { Callout, Reading, Section } from '../ui'
import { DTable, FileNote, useRJson, useRRows, type Prov, type Row } from './parts'
import { interpRows, nearestRow, normVerdict, num, show, verdictKind } from './shape'

type O = Record<string, unknown>
/** Value at a dotted path ("a.b.c"); keys may contain dots when given as an array. */
export function at(o: unknown, path: string | string[]): unknown {
  const parts = Array.isArray(path) ? path : path.split('.')
  let v: unknown = o
  for (const k of parts) { if (v === null || typeof v !== 'object') return undefined; v = (v as O)[k] }
  return v
}
const n = (o: unknown, path: string | string[]) => num(at(o, path))
const f = (v: unknown, d = 2) => (num(v) === null ? 'n/a' : fmt(num(v) as number, d))
const pct = (v: unknown, d = 1) => (num(v) === null ? 'n/a' : `${fmt((num(v) as number) * 100, d)} %`)
const mUSD = (v: unknown, d = 2) => (num(v) === null ? 'n/a' : fmt((num(v) as number) / 1e6, d))
const label = (k: string) => k.replace(/_/g, ' ')

export const ROUTE_LABEL: Record<string, string> = { grey: 'Grey NH3', blue: 'Blue NH3', green_current: 'Green NH3 (current price)', green_2030: 'Green NH3 (2030 price)', green_2050: 'Green NH3 (2050 price)' }
const ROUTES = ['grey', 'blue', 'green_current', 'green_2030', 'green_2050']

/* ------------------------------------------------------------------ verdict chip */
export function VerdictChip({ v, small = false }: { v: unknown; small?: boolean }) {
  const k = verdictKind(v)
  const text = normVerdict(v) || 'NO VERDICT'
  const icon = k === 'ok' ? '✓' : k === 'error' ? '✗' : k === 'partial' ? '◐' : k === 'mixed' ? '±' : k === 'warn' ? '?' : '–'
  return <span className={`pill verdict-chip verdict-${k}${small ? ' verdict-small' : ''}`} data-verdict={text}><span aria-hidden="true">{icon}</span> {text}</span>
}

/* ------------------------------------------------------------------ generic row evidence (row_evidence blocks of the result files) */
function Numbers({ v }: { v: unknown }) {
  if (v === null || v === undefined) return null
  if (typeof v !== 'object' || Array.isArray(v)) return <>{show(v)}</>
  return (
    <ul className="hyp-list">
      {Object.entries(v as O).map(([k, x]) => <li key={k}><code>{k}</code>: {x !== null && typeof x === 'object' && !Array.isArray(x) ? <Numbers v={x} /> : show(x)}</li>)}
    </ul>
  )
}
export function RowEvidence({ id, ev, file }: { id: string; ev: unknown; file: string }) {
  if (!ev || typeof ev !== 'object') return null
  const e = ev as O
  return (
    <details className="hyp-details" id={`ev-${id}`}>
      <summary><strong>{id}</strong> evidence from <code>{file}</code> (stored numbers only; the verdict is set by the coded rule of the evidence matrix)</summary>
      <div className="hyp-row-body">
        {show(e.reason) ? <p><strong>Reason.</strong> {show(e.reason)}</p> : null}
        {show(e.envelope) ? <p><strong>Envelope.</strong> {show(e.envelope)}</p> : null}
        {e.threshold ? <div><strong>Threshold.</strong> <Numbers v={e.threshold} /></div> : null}
        {show(e.uncertainty) ? <p><strong>Uncertainty.</strong> {show(e.uncertainty)}</p> : null}
        {e.assumptions ? <div><strong>Assumptions.</strong> <Numbers v={e.assumptions} /></div> : null}
        {e.numbers ? <div><strong>Numbers (as stored).</strong> <Numbers v={e.numbers} /></div> : null}
      </div>
    </details>
  )
}

/** A stored research figure (copied to research-figures/ by the snapshot export). */
export function Fig({ file, alt, caption }: { file: string; alt: string; caption?: ReactNode }) {
  const src = staticAssetUrl(`/research-figures/${file}`)
  return (
    <figure className="card p2-fig">
      <a href={src} target="_blank" rel="noopener noreferrer"><img src={src} alt={alt} loading="lazy" /></a>
      <figcaption className="muted small">{caption ?? alt} <code>results/figures/research/{file}</code></figcaption>
    </figure>
  )
}

function Kpi({ label: l, value, unit, note }: { label: string; value: string; unit?: string; note?: ReactNode }) {
  return (
    <div className="card tile p2-kpi">
      <span className="muted small">{l}</span>
      <strong className="p2-kpi-v">{value}{unit ? <span className="unit"> {unit}</span> : null}</strong>
      {note ? <span className="muted small">{note}</span> : null}
    </div>
  )
}

/* ================================================================== Singapore economics (H2) */
const PARTS: [string, string][] = [['ammonia_feed', 'Ammonia feed'], ['capex', 'Capital charge'], ['fixed_opex', 'Fixed opex'], ['heat_fuel', 'Heat fuel'], ['catalyst', 'Catalyst'], ['electricity', 'Electricity'], ['cooling_water', 'Cooling water'], ['carbon_tax', 'Carbon tax']]

export function useBaseline() { return useRJson<O & Prov>('reference_scenario', 'baseline.json') }

/** Fuel-efficiency envelope of the frozen baseline (baseline.json key fuel_efficiency_sensitivity): the reference counts the
 *  supplementary NH3 fuel at 100 % of its lower heating value (optimistic). Every number is read from the file. */
export function FuelEnvelope({ b, compact = false }: { b: O; compact?: boolean }) {
  const fe = b.fuel_efficiency_sensitivity as O | undefined
  const cases = (Array.isArray(fe?.cases) ? fe!.cases : []) as O[]
  if (!cases.length) return null
  const eff = (c: O) => { const x = (num(c.fuel_efficiency) ?? 0) * 100; return pct(c.fuel_efficiency, Math.abs(x - Math.round(x)) > 1e-6 ? 2 : 0) }
  if (compact) {
    return (
      <span data-testid="fuel-envelope-note">The reference value counts the supplementary ammonia fuel at 100 % of its lower heating value (optimistic); with the fuel delivered at {cases.slice(1).map((c) => `${eff(c)} it is ${f(c.lcoh_USD_per_kg, 3)}`).join(' and at ')} USD/kg.</span>
    )
  }
  return (
    <div data-testid="fuel-envelope">
      <DTable caption="Fuel-efficiency envelope of the baseline (supplementary NH3 fuel heat delivered; grey NH3, heat integration on)" rows={cases} keyOf={(_, i) => String(i)}
        cols={[
          { h: 'Fuel heat delivered', cell: (c) => <><strong>{eff(c)}</strong><div className="muted small">{num(c.fuel_efficiency) === 1 && !/optimistic/i.test(show(c.label)) ? 'reference (optimistic): ' : ''}{show(c.label)}</div></>, th: true },
          { h: 'LCOH (USD/kg)', cell: (c) => f(c.lcoh_USD_per_kg, 3), right: true },
          { h: 'LCOH (SGD/kg)', cell: (c) => f(c.lcoh_SGD_per_kg, 3), right: true },
          { h: 'NPV (MUSD)', cell: (c) => mUSD(c.npv_USD, 2), right: true },
          { h: 'Break-even NH3 (USD/t)', cell: (c) => f(c.breakeven_nh3_USD_per_t_vs_marker, 1), right: true },
          { h: 'Heat-integration gross saving (USD/kg)', cell: (c) => f(c.heat_integration_gross_saving_USD_per_kg, 3), right: true },
        ]} />
      <p className="muted small">{show(fe?.description)}</p>
    </div>
  )
}

export function UnifiedBaseline() {
  const b = useBaseline()
  const fd = useRJson<O & Prov>('carbon_pricing', 'feed_dominance.json')
  const audit = useRJson<O>('reference_scenario', 'capex_audit.json')
  return (
    <AsyncView a={b} what="the unified baseline (results/research/reference_scenario/baseline.json)">{(d) => {
      const share = fd.phase === 'ready' ? (fd.data.share_of_lcoh as O) : null
      const sup = (d.superseded_bases ?? {}) as Record<string, O>
      const range = audit.phase === 'ready' ? (audit.data.independent_range_USD as unknown[]) : null
      return (
        <>
          <div className="p2-kpis" data-testid="baseline-kpis">
            <Kpi label="Baseline LCOH" value={f(d.lcoh_USD_per_kg, 3)} unit="USD/kg H2" note={<><span data-testid="baseline-sgd">{f(d.lcoh_SGD_per_kg, 3)} SGD/kg</span>{d.fuel_efficiency_sensitivity ? '; fuel at 100 % of LHV (optimistic reference; envelope below)' : ''}</>} />
            <Kpi label="REC (cost excluding feed)" value={f(d.rec_USD_per_kg, 3)} unit="USD/kg H2" note={`${f(d.rec_SGD_per_kg, 3)} SGD/kg`} />
            <Kpi label="CAPEX (total capital investment)" value={mUSD(d.capex_total_USD, 3)} unit="MUSD" note={`${mUSD(d.capex_total_SGD, 2)} MSGD; method ${show(d.capex_method)}`} />
            <Kpi label="NPV" value={mUSD(d.npv_USD, 2)} unit="MUSD" note={`${mUSD(d.npv_SGD, 2)} MSGD; ${show(d.npv_basis)}`} />
            <Kpi label="LCOH, heat integration off" value={f(at(d, 'heat_integration_off.lcoh_USD_per_kg'), 3)} unit="USD/kg H2" note={`${f(at(d, 'heat_integration_off.lcoh_SGD_per_kg'), 3)} SGD/kg`} />
            <Kpi label="Exchange rate" value={f(d.fx_SGD_per_USD, 6)} unit="SGD per USD" note={`ECB reference rate of ${show(d.fx_date)}; the only rate used for conversion`} />
          </div>
          <p className="prose-p">{show(d.description)}</p>
          <FuelEnvelope b={d} />
          <DTable caption="Unified baseline LCOH by component (grey NH3, heat integration on)" rows={PARTS} keyOf={([k]) => k}
            cols={[
              { h: 'Component', cell: ([, l]) => l, th: true },
              { h: 'USD/kg H2', cell: ([k]) => f(at(d, ['breakdown_USD_per_kg', k]), 3), right: true },
              { h: 'SGD/kg H2', cell: ([k]) => f(at(d, ['breakdown_SGD_per_kg', k]), 3), right: true },
              { h: 'Share of LCOH', cell: ([k]) => (share ? pct(share[k]) : 'n/a'), right: true },
              { h: 'USD per year', cell: ([k]) => f(at(d, ['annual_USD_per_yr', k]), 0), right: true },
            ]} />
          <p className="muted small">CAPEX basis: {show(d.capex_basis)}. Cost basis: {show(d.price_year)}.
            {range && range.length === 2 ? <> The independent published CAPEX range normalised to this plant is {mUSD(range[0], 2)} to {mUSD(range[1], 2)} MUSD (comparison with published literature, <code>capex_audit.json</code>); the reference CAPEX of {mUSD(d.capex_total_USD, 2)} MUSD is {(num(d.capex_total_USD) ?? 0) > (num(range[1]) ?? Infinity) ? 'above it, so the reference sits at the conservative (costly) end' : 'inside it'}.</> : null}</p>
          {Array.isArray(d.boundary_notes) ? <ul className="hyp-list">{(d.boundary_notes as unknown[]).map((x, i) => <li key={i}>{show(x)}</li>)}</ul> : null}
          <Callout kind="warn" title="Two earlier baselines are superseded for research outputs.">
            <span data-testid="superseded-note">
              {Object.entries(sup).map(([k, v], i) => <span key={k}>{i > 0 ? ' ' : ''}{label(k)}: {f(v.lcoh_USD_per_kg, 3)} USD/kg (CAPEX {mUSD(v.capex_total_USD, 2)} MUSD; {show(v.basis)}).</span>)}
              {' '}These numbers are history, not the baseline. Pages that still show them label them as legacy core results.
            </span>
          </Callout>
          <FileNote prov={d.provenance as Prov['provenance']} file="results/research/reference_scenario/baseline.json" />
        </>
      )
    }}</AsyncView>
  )
}

interface SobolIdx { S1?: number; ST?: number; ST_ci?: number[] }
export function FeedDominance() {
  const fd = useRJson<O & Prov>('carbon_pricing', 'feed_dominance.json')
  const sob = useRJson<O>('uq', 'gsa_sobol.json')
  return (
    <AsyncView a={fd} what="the feed-dominance result (carbon_pricing/feed_dominance.json)">{(d) => {
      const idx = sob.phase === 'ready' ? (at(sob.data, ['cases', 'grey|heat_integration_on', 'outputs', 'lcoh_USD_per_kg', 'indices']) as Record<string, SobolIdx> | undefined) : undefined
      const ranked = idx ? Object.entries(idx).sort((a, b) => (b[1].ST ?? 0) - (a[1].ST ?? 0)) : []
      const be = (d.breakeven_nh3_USD_per_t ?? {}) as O
      const bm = (d.breakeven_benchmarks_USD_per_kg ?? {}) as O
      const byCapex = (d.breakeven_vs_ne_asia_smr_by_capex_multiplier ?? {}) as O
      const capexRows = Array.isArray(at(d, 'thresholds.capex_multiple')) ? (at(d, 'thresholds.capex_multiple') as O[]) : []
      const grey = n(d, 'sourced_comparison.nh3_price_scenarios_USD_per_t.grey.value')
      const beSmr = num(be.ne_asia_smr_production_cost)
      const pBelow = n(d, 'monte_carlo.P_lcoh_below_ne_asia_smr_3p06')
      return (
        <>
          <div className="p2-kpis">
            <Kpi label="Feed share of LCOH" value={pct(d.feed_share)} note={`feed plus heat fuel ${pct(d.feed_plus_fuel_share)}`} />
            <Kpi label="Total-effect index of the NH3 price" value={idx ? f(idx.nh3_price_USD_per_t?.ST, 3) : 'n/a'} note={idx?.nh3_price_USD_per_t?.ST_ci ? `95 % interval ${f(idx.nh3_price_USD_per_t.ST_ci[0], 3)} to ${f(idx.nh3_price_USD_per_t.ST_ci[1], 3)} (Sobol, Jansen estimator)` : undefined} />
            <Kpi label="Break-even NH3 price against the NE Asia SMR price" value={f(beSmr, 0)} unit="USD/t" note={`benchmark ${f(bm.ne_asia_smr_production_cost, 2)} USD/kg H2`} />
            <Kpi label="NH3 price at which feed falls to half of LCOH" value={f(at(d, 'thresholds.nh3_price_feed_share_50pct_USD_per_t'), 0)} unit="USD/t" />
          </div>
          {grey !== null && beSmr !== null ? (
            <Callout kind="warn" title="Adverse finding.">
              <span data-testid="adverse-h2">Grey ammonia at {f(grey, 0)} USD/t is {grey > beSmr ? 'not' : ''} cheap enough to reach the NE Asia SMR price: the break-even ammonia price is {f(beSmr, 0)} USD/t. In the Monte Carlo run ({show(at(d, 'monte_carlo.n'))} samples) the probability that LCOH is below {f(bm.ne_asia_smr_production_cost, 2)} USD/kg is {pct(pBelow)}. Only one hydrogen benchmark is used for this statement.</span>
            </Callout>
          ) : null}
          <DTable caption="Break-even ammonia price against each hydrogen price benchmark" rows={Object.keys(be)} keyOf={(k) => k}
            cols={[
              { h: 'Benchmark', cell: (k) => label(k), th: true },
              { h: 'Hydrogen price (USD/kg)', cell: (k) => f(bm[k], 2), right: true },
              { h: 'Break-even NH3 (USD/t)', cell: (k) => f(be[k], 0), right: true },
            ]} />
          <DTable caption="Break-even ammonia price against the NE Asia SMR price, by CAPEX multiplier" rows={Object.keys(byCapex)} keyOf={(k) => k}
            cols={[
              { h: 'CAPEX multiplier', cell: (k) => k.replace('capex_multiplier_', ''), th: true },
              { h: 'Break-even NH3 (USD/t)', cell: (k) => f(byCapex[k], 0), right: true },
            ]} />
          {capexRows.length ? (
            <DTable caption="CAPEX multiple at which capital costs overtake the feed, by ammonia price" rows={capexRows} keyOf={(_, i) => String(i)}
              cols={Object.keys(capexRows[0]).map((k, i) => ({ h: label(k), cell: (r: O) => f(r[k], 2), right: i > 0, th: i === 0 }))} />
          ) : null}
          {ranked.length ? (
            <DTable caption="Sobol indices of LCOH (grey NH3, heat integration on), sorted by total effect" rows={ranked} keyOf={([k]) => k}
              cols={[
                { h: 'Input', cell: ([k]) => label(k), th: true },
                { h: 'First order S1', cell: ([, v]) => f(v.S1, 3), right: true },
                { h: 'Total effect ST', cell: ([, v]) => f(v.ST, 3), right: true },
                { h: 'ST 95 % interval', cell: ([, v]) => (v.ST_ci ? `${f(v.ST_ci[0], 3)} to ${f(v.ST_ci[1], 3)}` : 'n/a'), right: true },
              ]} />
          ) : null}
          {sob.phase === 'ready' ? <p className="muted small">{show(sob.data.label)} Method: {show(sob.data.method)}</p> : null}
          <p className="muted small">Monte Carlo: {show(at(d, 'monte_carlo.nh3_price'))}; P(feed is the largest item) {pct(at(d, 'monte_carlo.P_feed_largest_item'))}; feed share P5, P50, P95 {show(at(d, 'monte_carlo.feed_share_p5_p50_p95'))}.</p>
          <Fig file="uq_gsa_sobol.png" alt="Sobol first-order and total-effect indices of LCOH" />
          <FileNote prov={d.provenance as Prov['provenance']} file="results/research/carbon_pricing/feed_dominance.json and results/research/uq/gsa_sobol.json" />
        </>
      )
    }}</AsyncView>
  )
}

/* ---- carbon pricing control */
interface Case extends O { route: string; mode: string; ci_level?: string; carbon_price_SGD_per_tCO2e: number }
export type CarbonMode = 'actual_sg' | 'hypothetical_lca'

/** Mode B values for one route at a user price: LCOH low/central/high from the sweep; NPV and break-even from the stored cases. */
export function modeBRoute(sweep: Row[], cases: Case[], route: string, price: number) {
  const cen = interpRows(sweep, 'price_SGD_per_tCO2e', `lcoh_${route}_central_USD_per_kg`, price)
  const lo = interpRows(sweep, 'price_SGD_per_tCO2e', `lcoh_${route}_low_USD_per_kg`, price)
  const hi = interpRows(sweep, 'price_SGD_per_tCO2e', `lcoh_${route}_high_USD_per_kg`, price)
  const cs = cases.filter((c) => c.route === route && c.mode === 'hypothetical_lca' && (c.ci_level ?? 'central') === 'central') as Row[]
  return {
    lcoh: cen, lcohLow: lo, lcohHigh: hi,
    npv: interpRows(cs, 'carbon_price_SGD_per_tCO2e', 'npv_at_carbon_adjusted_benchmark_USD', price),
    breakeven: interpRows(cs, 'carbon_price_SGD_per_tCO2e', 'breakeven_nh3_vs_carbon_adjusted_benchmark_USD_per_t', price),
  }
}

export function CarbonPricing() {
  const ss = useRJson<O>('carbon_pricing', 'site_summary.json')
  const sw = useRRows<Row>('carbon_pricing', 'price_sweep.csv')
  const sc = useRJson<O & Prov>('carbon_pricing', 'scenarios.json')
  const [mode, setMode] = useState<CarbonMode>('actual_sg')
  const [price, setPrice] = useState(45)
  return (
    <AsyncView a={ss} what="the carbon-pricing summary (carbon_pricing/site_summary.json)">{(s) => (
      <AsyncView a={sw} what="the stored carbon-price sweep (carbon_pricing/price_sweep.csv)">{(sweep) => (
        <AsyncView a={sc} what="the carbon-pricing cases (carbon_pricing/scenarios.json)">{(scen) => (
          <CarbonBody s={s} sweep={sweep.rows} scen={scen} mode={mode} setMode={setMode} price={price} setPrice={setPrice} />
        )}</AsyncView>
      )}</AsyncView>
    )}</AsyncView>
  )
}

function CarbonBody({ s, sweep, scen, mode, setMode, price, setPrice }: { s: O; sweep: Row[]; scen: O & Prov; mode: CarbonMode; setMode: (m: CarbonMode) => void; price: number; setPrice: (p: number) => void }) {
  const fx = n(s, 'fx_SGD_per_USD')
  const max = n(s, 'sweep_max_SGD') ?? 500
  const step = n(s, 'sweep_step_SGD')
  const cases = (Array.isArray(scen.cases) ? scen.cases : []) as Case[]
  const routes = (s.routes ?? {}) as Record<string, O>
  const modeA = cases.filter((c) => c.mode === 'actual_sg')
  const rows = useMemo(() => ROUTES.filter((r) => routes[r]).map((r) => {
    const ci = routes[r].ci_kgCO2e_per_kgH2 as O | undefined
    if (mode === 'actual_sg') {
      const c = modeA.find((x) => x.route === r) as O | undefined
      return { route: r, lcoh: num(c?.lcoh_USD_per_kg) ?? num(routes[r].lcoh_USD_per_kg), lcohLow: null, lcohHigh: null, carbon: num(c?.carbon_cost_USD_per_kg), npv: num(c?.npv_USD), breakeven: num(c?.breakeven_nh3_USD_per_t), ci }
    }
    const b = modeBRoute(sweep, cases, r, price)
    const g = interpRows(sweep, 'price_SGD_per_tCO2e', `lcoh_${r}_central_USD_per_kg`, 0)
    return { route: r, ...b, carbon: b.lcoh !== null && g !== null ? b.lcoh - g : null, ci }
  }), [mode, price, sweep, cases, routes, modeA])
  const ranked = [...rows].filter((r) => r.lcoh !== null).sort((a, b) => (a.lcoh as number) - (b.lcoh as number))
  const near = mode === 'hypothetical_lca' ? nearestRow(sweep, 'price_SGD_per_tCO2e', price) : null
  const bench = mode === 'hypothetical_lca' ? interpRows(sweep, 'price_SGD_per_tCO2e', 'benchmark_smr_carbon_adjusted_USD_per_kg', price) : null
  const th = (s.thresholds_SGD_per_tCO2e ?? {}) as Record<string, O>
  const pol = (s.policy ?? {}) as O
  const labels = (s.labels ?? {}) as O
  const consequence = at(scen, 'mode_a_actual_boundary.consequence')
  return (
    <div className="p2-carbon" data-testid="carbon-control" data-mode={mode}>
      <div className="hyp-controls" role="group" aria-label="Carbon pricing mode">
        <span className="muted">Carbon pricing:</span>
        <button type="button" className={`btn ${mode === 'actual_sg' ? 'btn-primary' : ''}`} aria-pressed={mode === 'actual_sg'} data-testid="mode-a" onClick={() => setMode('actual_sg')}>Mode A: actual Singapore boundary</button>
        <button type="button" className={`btn ${mode === 'hypothetical_lca' ? 'btn-primary' : ''}`} aria-pressed={mode === 'hypothetical_lca'} data-testid="mode-b" onClick={() => setMode('hypothetical_lca')}>Mode B: hypothetical life-cycle carbon price (not Singapore law)</button>
      </div>
      {mode === 'actual_sg' ? (
        <Callout title="Mode A, actual Singapore boundary (default).">
          <span data-testid="mode-a-text">{show(labels.actual_sg)}. Legislated rate {f(pol.rate_SGD_2026_onward, 0)} SGD/tCO2e for 2026 and any later year; {Array.isArray(pol.aim_2030_not_law) ? (pol.aim_2030_not_law as unknown[]).map((x) => f(x, 0)).join(' to ') : show(pol.aim_2030_not_law)} SGD/tCO2e by 2030 is a stated aim, not law. Threshold {f(pol.threshold_tCO2e, 0)} tCO2e per year; N2O GWP {f(pol.n2o_gwp, 0)}. Carbon tax on the reference plant: {f(at(s, 'mode_a.carbon_tax_USD_per_kg'), 2)} USD/kg H2; upstream emissions of imported ammonia taxed: {at(s, 'mode_a.upstream_taxed') ? 'yes' : 'no'}. {show(consequence)}</span>
        </Callout>
      ) : (
        <Callout kind="warn" title="Mode B is hypothetical. It is not Singapore law.">
          <span data-testid="mode-b-text">{show(labels.hypothetical_lca)}. The values below are a linear interpolation of stored Python results (price sweep at {f(step, 0)} SGD/tCO2e steps, <code>price_sweep.csv</code>; NPV and break-even between the stored cases of <code>scenarios.json</code>); they are not a new calculation.</span>
          <div className="p2-slider">
            <label htmlFor="carbon-price">Hypothetical life-cycle carbon price: <strong data-testid="carbon-price-value">{fmt(price, 0)}</strong> SGD/tCO2e</label>
            <input id="carbon-price" type="range" min={0} max={max} step={1} value={price} onChange={(e) => setPrice(Number(e.target.value))} data-testid="carbon-price" />
            <input type="number" min={0} max={max} step={1} value={price} aria-label="Hypothetical carbon price in SGD per tonne CO2e" onChange={(e) => { const v = Number(e.target.value); if (Number.isFinite(v)) setPrice(Math.min(max, Math.max(0, v))) }} className="hyp-select p2-num" />
          </div>
        </Callout>
      )}
      <DTable caption={mode === 'actual_sg' ? 'Cost by ammonia route, actual Singapore boundary' : `Cost by ammonia route at a hypothetical ${fmt(price, 0)} SGD/tCO2e (interpolated from stored Python results; not Singapore law)`} rows={rows} keyOf={(r) => r.route}
        cols={[
          { h: 'Route', cell: (r) => ROUTE_LABEL[r.route] ?? r.route, th: true },
          { h: 'NH3 price (USD/t)', cell: (r) => f(routes[r.route]?.nh3_USD_per_t, 0), right: true },
          { h: 'LCOH (USD/kg)', cell: (r) => <span data-testid={`lcoh-${r.route}`}>{f(r.lcoh, 3)}</span>, right: true },
          { h: 'LCOH range from CI range', cell: (r) => (r.lcohLow !== null && r.lcohHigh !== null ? `${f(r.lcohLow, 3)} to ${f(r.lcohHigh, 3)}` : 'none (no price on CI)'), right: true },
          { h: 'LCOH (SGD/kg)', cell: (r) => (r.lcoh !== null && fx !== null ? f(r.lcoh * fx, 3) : 'n/a'), right: true },
          { h: 'Carbon cost (USD/kg)', cell: (r) => f(r.carbon, 3), right: true },
          { h: 'Break-even NH3 (USD/t)', cell: (r) => f(r.breakeven, 0), right: true },
          { h: 'NPV (MUSD)', cell: (r) => mUSD(r.npv, 2), right: true },
          { h: 'Carbon intensity (kgCO2e/kg H2; green: including embedded emissions)', cell: (r) => (r.ci ? `${f(r.ci.central, 2)} (${f(r.ci.low, 2)} to ${f(r.ci.high, 2)})` : 'n/a'), right: true },
        ]} />
      <GreenCiNote />
      <p className="prose-p" data-testid="carbon-ranking">Ranking by central LCOH, cheapest first: {ranked.map((r) => ROUTE_LABEL[r.route] ?? r.route).join(', ')}.
        {near ? <> Stored cheapest route at the nearest sweep point ({f(near.price_SGD_per_tCO2e, 0)} SGD/tCO2e): {ROUTE_LABEL[String(near.cheapest_central)] ?? show(near.cheapest_central)}.</> : null}
        {bench !== null ? <> SMR benchmark adjusted for the same hypothetical price: {f(bench, 3)} USD/kg.</> : null}</p>
      <p className="muted small">The green 2030 and 2050 routes use projected ammonia prices; setting them against current grey and blue prices mixes time bases. NPV and break-even are against the carbon-adjusted NE Asia SMR benchmark.</p>
      <DTable caption="Hypothetical carbon price at which one route overtakes another (SGD/tCO2e; range from the carbon-intensity ranges; not Singapore law)" rows={Object.keys(th)} keyOf={(k) => k}
        cols={[
          { h: 'Crossover', cell: (k) => k.replace(/_over_/, ' overtakes ').replace(/_/g, ' '), th: true },
          { h: 'Central', cell: (k) => <span data-testid={`th-${k}`}>{f(th[k].central, 1)}</span>, right: true },
          { h: 'Low', cell: (k) => f(th[k].low, 1), right: true },
          { h: 'High', cell: (k) => f(th[k].high, 1), right: true },
        ]} />
      <p className="muted small">{show(s.note)}</p>
      <FileNote prov={scen.provenance as Prov['provenance']} file="results/research/carbon_pricing/ (site_summary.json, price_sweep.csv, scenarios.json, thresholds.json)" />
    </div>
  )
}

export function EconomicsPhase2() {
  return (
    <>
      <Section id="baseline" title="Unified baseline (Phase 2 reference scenario)" intro="One techno-economic basis for every Phase 2 research output: the stored Aspen Plus V15 baseline costed by the Python economics model on the reference scenario.">
        <UnifiedBaseline />
      </Section>
      <Section id="feed" title="Feed dominance and break-even ammonia price (H2)" alt>
        <FeedDominance />
      </Section>
      <Section id="carbon" title="Carbon pricing: actual Singapore boundary and a hypothetical life-cycle price">
        <CarbonPricing />
      </Section>
      <p className="wrap muted small">The sections below hold the Singapore study tables (scenarios, tornado, maps and Monte Carlo) from <code>results/research/singapore/</code>; each states its basis. The unified baseline above is the reference for research outputs. Carbon intensity by route is in the <Link to="/hypotheses/end-use#lca">Environmental Analysis</Link> section.</p>
    </>
  )
}

/* ================================================================== Catalysts (H3) */
interface Law extends O { catalyst: string; catalyst_id?: string; class: string; fitted_range_basis?: string; class_evidence?: string }

function useValidity() { return useRJson<O & { laws?: Law[]; counts?: O } & Prov>('kinetics', 'validity_classification.json') }

export function CatalystPhase2() {
  const pr = useRJson<O & Prov>('catalyst_economics', 'catalyst_prices_sgd.json')
  const vc = useValidity()
  const ce = useRJson<O & Prov>('catalyst_economics', 'catalyst_economics.json')
  const cost = useRRows<Row>('catalyst_economics', 'catalyst_cost_table.csv')
  const be = useRRows<Row>('catalyst_economics', 'catalyst_breakeven.csv')
  const xo = useRRows<Row>('catalyst_economics', 'catalyst_crossover.csv')
  const hx = useRJson<O & Prov>('heat_exchanger', 'heat_exchanger_study.json')
  const [priceCase, setPriceCase] = useState('central')
  const [life, setLife] = useState<number | null>(null)
  const [basis, setBasis] = useState<string | null>(null)
  const classOf = (id: unknown, name: unknown): string => {
    const laws = vc.phase === 'ready' && Array.isArray(vc.data.laws) ? vc.data.laws : []
    const l = laws.find((x) => (id && x.catalyst_id === id) || x.catalyst === name)
    return l ? label(l.class) : 'not classified'
  }
  return (
    <>
      <Section id="validity" title="Kinetic validity of each rate law" intro="Every catalyst has exactly one class at the AmCraX conditions. The class is printed beside every catalyst on this page.">
        <AsyncView a={vc} what="the kinetic validity classification (kinetics/validity_classification.json)">{(d) => (
          <>
            <Callout kind="warn" title="Kinetic validity."><span data-testid="validity-statement">{show(d.statement)}</span></Callout>
            <div className="p2-kpis">
              {Object.entries(d.counts ?? {}).map(([k, v]) => <Kpi key={k} label={label(k)} value={f(v, 0)} unit="laws or catalysts" />)}
            </div>
            <DTable caption="Validity class per catalyst" rows={Array.isArray(d.laws) ? d.laws : []} keyOf={(l, i) => `${l.catalyst}${i}`}
              cols={[
                { h: 'Catalyst', cell: (l) => l.catalyst, th: true },
                { h: 'Class', cell: (l) => <strong>{label(l.class)}</strong> },
                { h: 'Fitted range', cell: (l) => <span className="small">{show(l.fitted_range_basis)}</span> },
                { h: 'Why', cell: (l) => <span className="small">{show(l.class_evidence)}</span> },
              ]} />
            <FileNote prov={d.provenance as Prov['provenance']} file="results/research/kinetics/validity_classification.json" />
          </>
        )}</AsyncView>
      </Section>
      <Section id="prices" title="Catalyst prices in SGD and USD" alt intro="Derived from metal content plus a non-metal part. No supplier quotation exists for any ammonia-cracking catalyst.">
        <AsyncView a={pr} what="the catalyst prices (catalyst_economics/catalyst_prices_sgd.json)">{(d) => {
          const cats = (Array.isArray(d.catalysts) ? d.catalysts : []) as O[]
          const tea = (Array.isArray(d.published_TEA_prices) ? d.published_TEA_prices : []) as O[]
          return (
            <>
              <p className="prose-p"><strong>Derived from metal content, no supplier quotation exists.</strong> {show(d.evidence_grade_note)} Conversion at {f(d.fx_SGD_per_USD, 6)} SGD/USD. {show(d.fx_note)}</p>
              <DTable caption="Derived catalyst prices per kg of catalyst (low, central, high)" rows={cats} keyOf={(c, i) => `${show(c.catalyst)}${i}`}
                cols={[
                  { h: 'Catalyst', cell: (c) => <>{show(c.catalyst)}<div className="muted small">{show(c.loading_basis)}</div></>, th: true },
                  { h: 'Kinetic validity', cell: (c) => (c.modelled === false ? <strong>unmodelled, no performance figures</strong> : classOf(c.catalyst_id, c.catalyst)) },
                  { h: 'Low USD (SGD)', cell: (c) => `${f(at(c, 'low.USD_per_kg'), 0)} (${f(at(c, 'low.SGD_per_kg'), 0)})`, right: true },
                  { h: 'Central USD (SGD)', cell: (c) => `${f(at(c, 'central.USD_per_kg'), 0)} (${f(at(c, 'central.SGD_per_kg'), 0)})`, right: true },
                  { h: 'High USD (SGD)', cell: (c) => `${f(at(c, 'high.USD_per_kg'), 0)} (${f(at(c, 'high.SGD_per_kg'), 0)})`, right: true },
                  { h: 'Evidence grade', cell: (c) => <span className="small">{show(c.grade)}; {show(c.quoted_or_derived)}</span> },
                  { h: 'Published TEA case (labelled historical)', cell: (c) => (num(c.published_TEA_case_USD_per_kg) !== null ? <span className="small">{f(c.published_TEA_case_USD_per_kg, 0)} USD ({f(c.published_TEA_case_SGD_per_kg, 0)} SGD): {show(c.published_TEA_case_label)}</span> : 'none') },
                ]} />
              <details className="hyp-details"><summary>Published TEA prices: historical case only, not current prices ({tea.length} entries)</summary>
                <DTable caption="Published techno-economic analysis prices (historical case)" rows={tea} keyOf={(t, i) => `${show(t.id)}${i}`}
                  cols={[
                    { h: 'Material', cell: (t) => show(t.material), th: true },
                    { h: 'Price', cell: (t) => `${show(t.price_value)} ${show(t.currency)}`, right: true },
                    { h: 'USD/kg (SGD/kg)', cell: (t) => `${f(t.USD_per_kg, 1)} (${f(t.SGD_per_kg, 1)})`, right: true },
                    { h: 'Date', cell: (t) => show(t.price_date) },
                    { h: 'Publication', cell: (t) => <span className="small">{show(t.publication)}</span> },
                    { h: 'Grade and label', cell: (t) => <span className="small">{show(t.grade)}; {show(t.label)}</span> },
                  ]} />
              </details>
              <FileNote prov={d.provenance as Prov['provenance']} file="results/research/catalyst_economics/catalyst_prices_sgd.json" />
            </>
          )
        }}</AsyncView>
      </Section>
      <Section id="catalyst-cost" title="Catalyst cost per kg of hydrogen and annual expenditure">
        <AsyncView a={cost} what="the catalyst cost table (catalyst_economics/catalyst_cost_table.csv)">{({ rows }) => {
          const lifes = [...new Set(rows.map((r) => num(r.lifetime_yr)).filter((x): x is number => x !== null))].sort((a, b) => a - b)
          const cases = [...new Set(rows.map((r) => String(r.price_case)))]
          const L = life ?? (lifes.includes(2) ? 2 : lifes[0])
          const shown = rows.filter((r) => String(r.price_case) === priceCase && num(r.lifetime_yr) === L)
          return (
            <>
              <div className="hyp-controls">
                <label className="muted" htmlFor="cat-price">Price case</label>
                <select id="cat-price" className="hyp-select" value={priceCase} onChange={(e) => setPriceCase(e.target.value)}>{cases.map((c) => <option key={c} value={c}>{c}</option>)}</select>
                <label className="muted" htmlFor="cat-life">Catalyst lifetime (yr)</label>
                <select id="cat-life" className="hyp-select" value={L} onChange={(e) => setLife(Number(e.target.value))}>{lifes.map((x) => <option key={x} value={x}>{x}</option>)}</select>
              </div>
              <DTable caption={`Cost-optimal design per catalyst, ${priceCase} price, lifetime ${L} yr`} rows={shown} keyOf={(r, i) => `${show(r.catalyst_id)}${i}`}
                cols={[
                  { h: 'Catalyst', cell: (r) => show(r.catalyst), th: true },
                  { h: 'Kinetic validity', cell: (r) => classOf(r.catalyst_id, r.catalyst) },
                  { h: 'Price USD/kg (SGD/kg)', cell: (r) => `${f(r.price_USD_per_kg, 0)} (${f(r.price_SGD_per_kg, 0)})`, right: true },
                  { h: 'Optimal T (degC)', cell: (r) => f(r.costopt_T_C, 0), right: true },
                  { h: 'Charge (kg)', cell: (r) => f(r.costopt_W_kg, 1), right: true },
                  { h: 'Catalyst USD/kg H2 (SGD)', cell: (r) => `${f(r.costopt_catalyst_USD_per_kg_H2, 4)} (${f(r.costopt_catalyst_SGD_per_kg_H2, 4)})`, right: true },
                  { h: 'Annual catalyst SGD/yr', cell: (r) => f(r.costopt_annual_catalyst_SGD_per_yr, 0), right: true },
                  { h: 'LCOH USD/kg (SGD)', cell: (r) => `${f(r.costopt_lcoh_USD_per_kg, 3)} (${f(r.costopt_lcoh_SGD_per_kg, 3)})`, right: true },
                  { h: 'Label', cell: (r) => <span className="small">{show(r.price_label)}; {show(r.result_label)}</span> },
                ]} />
              <Fig file="catalyst_econ_cost_per_kg.png" alt="Catalyst cost per kg of hydrogen by catalyst and price case" />
            </>
          )
        }}</AsyncView>
      </Section>
      <Section id="breakeven-price" title="Break-even catalyst price and lifetime" alt>
        <AsyncView a={be} what="the break-even table (catalyst_economics/catalyst_breakeven.csv)">{({ rows }) => {
          const shown = rows.filter((r) => String(r.mode) === 'reference')
          return (
            <>
              <DTable caption="Price at which each low-temperature catalyst matches the Ni/MgO reference (reference mode)" rows={shown} keyOf={(r, i) => `${show(r.catalyst_id)}${i}`}
                cols={[
                  { h: 'Catalyst', cell: (r) => show(r.catalyst), th: true },
                  { h: 'Kinetic validity', cell: (r) => classOf(r.catalyst_id, r.catalyst) },
                  { h: 'Central price (USD/kg)', cell: (r) => f(r.central_price_USD_per_kg, 0), right: true },
                  { h: 'Metal floor (USD/kg)', cell: (r) => f(r.floor_price_USD_per_kg, 0), right: true },
                  { h: 'Published TEA (historical)', cell: (r) => f(r.published_TEA_price_USD_per_kg, 0), right: true },
                  { h: 'Break-even, re-optimised USD/kg (SGD)', cell: (r) => `${f(r.breakeven_price_reoptimised_USD_per_kg, 0)} (${f(r.breakeven_price_reoptimised_SGD_per_kg, 0)})`, right: true },
                  { h: 'Break-even lifetime (yr)', cell: (r) => f(r.breakeven_lifetime_reoptimised_yr, 1), right: true },
                  { h: 'Label', cell: (r) => <span className="small">{show(r.result_label)}</span> },
                ]} />
              <Reading>Where the break-even price is below the central derived price, the low-temperature catalyst does not pay at equal conversion. This finding goes against the essay.</Reading>
              <Fig file="catalyst_econ_breakeven.png" alt="Break-even catalyst price against the derived price range" />
            </>
          )
        }}</AsyncView>
      </Section>
      <Section id="crossover" title="Crossover table">
        <AsyncView a={xo} what="the crossover table (catalyst_economics/catalyst_crossover.csv)">{({ rows }) => {
          const bases = [...new Set(rows.map((r) => String(r.basis)))]
          const B = basis ?? bases[0]
          const shown = rows.filter((r) => String(r.basis) === B)
          const yn = (v: unknown) => (v === true || v === 'True' ? 'yes' : v === false || v === 'False' ? 'no' : show(v))
          return (
            <>
              <div className="hyp-controls"><label className="muted" htmlFor="xo-basis">Design basis</label>
                <select id="xo-basis" className="hyp-select" value={B} onChange={(e) => setBasis(e.target.value)}>{bases.map((b) => <option key={b} value={b}>{label(b)}</option>)}</select></div>
              <DTable caption={`Is the low-temperature catalyst cheaper than the reference? (${label(B)})`} rows={shown} keyOf={(r, i) => `${show(r.catalyst)}${i}`}
                cols={[
                  { h: 'Catalyst', cell: (r) => show(r.catalyst), th: true },
                  { h: 'Kinetic validity', cell: (r) => classOf(undefined, r.catalyst) },
                  { h: 'Lifetime (yr)', cell: (r) => f(r.lifetime_yr, 0), right: true },
                  { h: 'T low / ref (degC)', cell: (r) => `${f(r.low_T_C, 0)} / ${f(r.ref_T_C, 0)}`, right: true },
                  { h: 'Break-even price USD/kg (SGD)', cell: (r) => (num(r.breakeven_price_USD_per_kg) === null ? 'none' : `${f(r.breakeven_price_USD_per_kg, 0)} (${f(r.breakeven_price_SGD_per_kg, 0)})`), right: true },
                  { h: 'Cheaper at low / central / high price', cell: (r) => `${yn(r.low_cheaper_at_low)} / ${yn(r.low_cheaper_at_central)} / ${yn(r.low_cheaper_at_high)}` },
                  { h: 'At published TEA price', cell: (r) => yn(r.low_cheaper_at_published_TEA) },
                  { h: 'Label', cell: (r) => <span className="small">{show(r.result_label)}</span> },
                ]} />
            </>
          )
        }}</AsyncView>
      </Section>
      <Section id="exchanger" title="Heat exchanger sizing and the net benefit of heat integration" alt>
        <AsyncView a={hx} what="the heat exchanger study (heat_exchanger/heat_exchanger_study.json)">{(d) => {
          const bl = (d.baseline ?? {}) as O
          const sz = (bl.sizing_turton ?? {}) as Record<string, O>
          const ev = at(d, ['row_evidence', 'H3-d']) as O | undefined
          const net = (at(ev, 'numbers.baseline_net_USD_per_kg') ?? {}) as O
          const cost = (at(ev, 'numbers.baseline_exchanger_cost_USD_per_kg') ?? {}) as O
          return (
            <>
              <div className="p2-kpis">
                <Kpi label="Gross fuel saving of heat integration" value={f(bl.saving_USD_per_kg, 3)} unit="USD/kg H2" note={`${f(bl.saving_SGD_per_kg, 3)} SGD/kg; LCOH ${f(bl.lcoh_hi_USD_per_kg, 3)} with, ${f(bl.lcoh_no_hi_USD_per_kg, 3)} without`} />
                <Kpi label="Net benefit after exchanger cost" value={`${f(net.low, 3)} to ${f(net.high, 3)}`} unit="USD/kg H2" note={`central ${f(net.central, 3)}`} />
                <Kpi label="Break-even overall U" value={f(at(ev, 'numbers.baseline_breakeven_U_W_m2K'), 1)} unit="W/(m2 K)" note="no sourced U at 20 bar" />
                <Kpi label="FEHE duty" value={f(at(bl, 'fehe.duty_kW'), 0)} unit="kW" />
              </div>
              <DTable caption="Feed-effluent exchanger sizing (Turton 2018 module costing) for three U cases" rows={Object.keys(sz)} keyOf={(k) => k}
                cols={[
                  { h: 'U case', cell: (k) => k, th: true },
                  { h: 'U (W/m2 K)', cell: (k) => f(sz[k].U_W_m2K, 1), right: true },
                  { h: 'Area (m2)', cell: (k) => f(sz[k].area_m2, 0), right: true },
                  { h: 'Arrangement', cell: (k) => show(sz[k].arrangement) },
                  { h: 'TCI-equivalent USD (SGD)', cell: (k) => `${mUSD(sz[k].tci_equivalent_USD, 2)} M (${mUSD(sz[k].tci_equivalent_SGD, 2)} M)`, right: true },
                  { h: 'Exchanger cost (USD/kg H2)', cell: (k) => f(cost[k], 3), right: true },
                  { h: 'Net benefit (USD/kg H2)', cell: (k) => f(net[k], 3), right: true },
                ]} />
              <Fig file="heat_exchanger_net_benefit.png" alt="Net benefit of heat integration after exchanger cost" />
              <RowEvidence id="H3-d" ev={ev} file="heat_exchanger/heat_exchanger_study.json" />
            </>
          )
        }}</AsyncView>
      </Section>
      <Section id="equal-conversion" title="Equal-conversion correction of the Phase 1 figure">
        <AsyncView a={ce} what="the catalyst economics findings (catalyst_economics/catalyst_economics.json)">{(d) => {
          const a = at(d, ['row_evidence', 'H3-a']) as O | undefined
          return (
            <>
              <Callout kind="warn" title="Phase 1 energy saving withdrawn.">
                <span data-testid="equal-conversion">{show(at(a, 'envelope'))}</span>
              </Callout>
              <RowEvidence id="H3-a" ev={a} file="catalyst_economics/catalyst_economics.json" />
              <RowEvidence id="H3-c" ev={at(d, ['row_evidence', 'H3-c'])} file="catalyst_economics/catalyst_economics.json" />
              <RowEvidence id="H3-b" ev={at(d, ['row_evidence', 'H3-b'])} file="catalyst_economics/catalyst_economics.json" />
              <p className="muted small">Python against Aspen resolution: largest absolute LCOH difference {f(at(d, 'resolution.max_abs_python_minus_aspen_lcoh_USD_per_kg'), 4)} USD/kg. {show(at(d, 'resolution.rule'))}</p>
              <FileNote prov={d.provenance as Prov['provenance']} file="results/research/catalyst_economics/catalyst_economics.json" />
            </>
          )
        }}</AsyncView>
      </Section>
    </>
  )
}

/* ================================================================== Purification (H4) */
export function PurificationPhase2() {
  const pc = useRJson<O & Prov>('purification', 'phase2_comparison.json')
  const tab = useRRows<Row>('purification', 'phase2_comparison.csv')
  return (
    <Section id="phase2" title="PSA against Pd-Ag membrane, per specification (Phase 2)" intro="One table per hydrogen specification, on the unified basis. Low, central and high are the sourced or assumed recovery and cost cases; readiness level beside each configuration.">
      <AsyncView a={tab} what="the Phase 2 comparison table (purification/phase2_comparison.csv)">{({ rows }) => {
        const specs = [...new Set(rows.map((r) => String(r.spec)))]
        return (
          <>
            {specs.map((s) => (
              <DTable key={s} caption={`Specification ${label(s)}`} rows={rows.filter((r) => String(r.spec) === s)} keyOf={(r, i) => `${show(r.config)}${i}`}
                cols={[
                  { h: 'Configuration', cell: (r) => label(String(r.config)), th: true },
                  { h: 'H2 purity', cell: (r) => f(r.purity, 5), right: true },
                  { h: 'N2 (ppm)', cell: (r) => f(r.n2_ppm, 0), right: true },
                  { h: 'H2 recovery', cell: (r) => f(r.recovery, 3), right: true },
                  { h: 'Fixed capital, excluding membrane modules (MUSD)', cell: (r) => mUSD(r.capital_USD, 2), right: true },
                  { h: 'Membrane modules, purchase cost (MUSD)', cell: (r) => (r.membrane_module_cost_USD === undefined ? 'not in file' : mUSD(r.membrane_module_cost_USD, 2)), right: true },
                  { h: 'LCOH USD/kg (SGD)', cell: (r) => `${f(r.lcoh_usd, 3)} (${f(r.lcoh_sgd, 3)})`, right: true },
                  { h: 'Readiness (TRL)', cell: (r) => <span className="small">{show(r.trl)}</span> },
                ]} />
            ))}
            <AsyncView a={pc} what="the column notes (purification/phase2_comparison.json)">{(d) => (
              show(at(d, 'csv_column_notes.capital_USD')) ? <p className="muted small" data-testid="capital-note">{show(at(d, 'csv_column_notes.capital_USD'))} {show(at(d, 'csv_column_notes.membrane_module_cost_USD'))}</p> : null
            )}</AsyncView>
          </>
        )
      }}</AsyncView>
      <AsyncView a={pc} what="the Phase 2 purification comparison (purification/phase2_comparison.json)">{(d) => {
        const h4d = at(d, ['row_evidence', 'H4-d']) as O | undefined
        const sens = (at(d, 'psa_recovery_sensitivity.points') ?? {}) as Record<string, Record<string, O>>
        return (
          <>
            <Callout kind="warn" title="The ranking is not robust.">
              <span data-testid="h4-parity">{show(at(h4d, 'envelope'))}. Threshold: {show(at(h4d, 'threshold'))}.</span>
            </Callout>
            {Object.entries(sens).map(([spec, pts]) => (
              <DTable key={spec} caption={`PSA recovery sensitivity, ${label(spec)}`} rows={Object.entries(pts)} keyOf={([k]) => k}
                cols={[
                  { h: 'Case', cell: ([k, v]) => <>{label(k)}<div className="muted small">{show(v.label)}</div></>, th: true },
                  { h: 'Recovery', cell: ([, v]) => f(v.recovery, 3), right: true },
                  { h: 'LCOH (USD/kg)', cell: ([, v]) => f(v.lcoh_usd, 3), right: true },
                  { h: 'LCOH (SGD/kg)', cell: ([, v]) => f(v.lcoh_sgd, 3), right: true },
                  { h: 'Change against 0.85 (USD/kg)', cell: ([, v]) => f(v.delta_vs_0_85_usd ?? v['delta_vs_0.85_usd'], 3), right: true },
                ]} />
            ))}
            <h3>Membrane selectivity</h3>
            <p className="prose-p" data-testid="selectivity">{show(at(d, 'selectivity_statement.phase2'))}</p>
            <p className="prose-p muted small">Phase 1 statement, kept for the record: {show(at(d, 'selectivity_statement.phase1'))}.</p>
            <p className="prose-p" data-testid="nus-wording">Zhang Sui and Zhao Dan are membrane scientists at NUS. None of their verified publications covers cracked-ammonia purification. Nothing quantitative from their work is used in AmCraX, and no specific result is attributed to them.</p>
            <RowEvidence id="H4-d" ev={h4d} file="purification/phase2_comparison.json" />
            <RowEvidence id="H4-b" ev={at(d, ['row_evidence', 'H4-b'])} file="purification/phase2_comparison.json" />
            <RowEvidence id="H4-e" ev={at(d, ['row_evidence', 'H4-e'])} file="purification/phase2_comparison.json" />
            <div className="grid-2s">
              <Fig file="purification_phase2_comparison.png" alt="PSA against Pd-Ag membrane by specification" />
              <Fig file="purification_phase2_psa_recovery.png" alt="LCOH against PSA recovery" />
            </div>
            <FileNote prov={d.provenance as Prov['provenance']} file="results/research/purification/phase2_comparison.json" />
          </>
        )
      }}</AsyncView>
    </Section>
  )
}

/* ================================================================== End use (H1) */
/** H1 thresholds with the cracker-heat fuel counted at 100 %, the flowsheet tail-gas ratio and 85 % (turbine_threshold.json key
 *  cracker_heat_fuel_efficiency_sensitivity); every value read from the file. */
function H1FuelSensitivity({ s }: { s: unknown }) {
  const cases = (Array.isArray(at(s, 'cases')) ? at(s, 'cases') : []) as O[]
  if (!cases.length) return null
  const eff = (c: O) => { const x = (num(c.heat_fuel_efficiency) ?? 0) * 100; return pct(c.heat_fuel_efficiency, Math.abs(x - Math.round(x)) > 1e-6 ? 2 : 0) }
  return (
    <div data-testid="h1-fuel-envelope" style={{ marginTop: 20 }}>
      <DTable caption="Turbine-efficiency thresholds (pp, reference basis) with the extra NH3 for cracker heat delivered at less than 100 % of its LHV" rows={cases} keyOf={(_, i) => String(i)}
        cols={[
          { h: 'Cracker-heat fuel delivered', cell: (c) => <>{eff(c)}{num(c.heat_fuel_efficiency) === 1 ? <div className="muted small">reference (optimistic)</div> : null}</>, th: true },
          { h: 'Fired cracking: threshold (pp)', cell: (c) => f(at(c, 'full_fired.threshold_delta_fuel_pp_vs_direct_turbine'), 2), right: true },
          { h: 'Fired cracking: LCOE (USD/MWh)', cell: (c) => f(at(c, 'full_fired.LCOE_USD_per_MWh'), 1), right: true },
          { h: 'Cracking plus PSA: threshold (pp)', cell: (c) => f(at(c, 'full_purified.threshold_delta_fuel_pp_vs_direct_turbine'), 2), right: true },
          { h: 'Cracking plus PSA: LCOE (USD/MWh)', cell: (c) => f(at(c, 'full_purified.LCOE_USD_per_MWh'), 1), right: true },
        ]} />
      <p className="muted small">{show(at(s, 'description'))}</p>
    </div>
  )
}

const PATHS: [string, string][] = [['full_fired', 'Fired cracking, H2/N2 fuel'], ['full_purified', 'Cracking plus PSA, purified H2'], ['full_exhaust', 'Exhaust-heated cracking']]
export function EndUsePhase2() {
  const tt = useRJson<O & Prov>('enduse', 'turbine_threshold.json')
  const tc = useRRows<Row>('enduse', 'turbine_threshold.csv')
  const sc = useRJson<O>('carbon_pricing', 'scenarios.json')
  return (
    <Section id="h1" title="Direct ammonia against cracking for power (H1, unified basis)">
      <AsyncView a={tt} what="the turbine threshold study (enduse/turbine_threshold.json)">{(d) => {
        const nu = (at(d, 'statement_of_result.new_unified') ?? {}) as Record<string, O>
        const old = (at(d, 'statement_of_result.old_pre_unification') ?? {}) as O
        const fired = num(at(nu, 'full_fired.direct_cheaper_pct_of_cracking_1_minus_d_over_c'))
        const pur = num(at(nu, 'full_purified.direct_cheaper_pct_of_cracking_1_minus_d_over_c'))
        const exh = num(at(nu, 'full_exhaust.direct_cheaper_pct_of_cracking_1_minus_d_over_c'))
        const sv = (d.sourced_values ?? {}) as Record<string, O>
        const rng = (v: unknown) => (Array.isArray(v) && v.length === 2 ? `${f(v[0], 1)} to ${f(v[1], 1)}` : show(v))
        const sourced: Record<string, string> = {
          full_fired: `none sourced; orientation bracket ${rng(at(sv, 'fired_H2N2_fuel_delta_pp.indirect_bracket'))} pp (not like-for-like)`,
          full_purified: `upper bound ${f(at(sv, 'purified_H2_fuel_delta_pp.netl_absolute'), 1)} pp (NETL, steam-diluted H2); no lower-side source`,
          full_exhaust: `${rng(at(sv, 'exhaust_heated_system_delta_pp.supported_range'))} pp (cycle simulations)`,
        }
        const rows = tc.phase === 'ready' ? tc.data.rows : []
        return (
          <>
            <p className="prose-p p2-required" data-testid="h1-wording">Under the modelled operating conditions, direct ammonia combustion produces electricity at a lower cost than the standalone cracking pathways, with a calculated cost advantage of approximately {fired !== null ? fmt(fired, 0) : 'n/a'} to {pur !== null ? fmt(pur, 0) : 'n/a'} % ({f(old.fired_pct, 0)} to {f(old.purified_pct, 0)} % on the earlier cost basis). This comparison assumes that the hydrogen-rich turbine operates at the same 49.64 % efficiency as the direct-ammonia turbine. The actual economic advantage depends on fuel-specific turbine performance.</p>
            <DTable caption="Turbine-efficiency gain each cracking pathway needs to match direct ammonia, against the sourced ranges" rows={PATHS} keyOf={([k]) => k}
              cols={[
                { h: 'Pathway', cell: ([, l]) => l, th: true },
                { h: 'LCOE (USD/MWh)', cell: ([k]) => f(at(nu, [k, 'LCOE']), 1), right: true },
                { h: 'Direct cheaper by', cell: ([k]) => `${f(at(nu, [k, 'direct_cheaper_pct_of_cracking_1_minus_d_over_c']), 1)} %`, right: true },
                { h: 'Threshold, reference basis (pp)', cell: ([k]) => { const r = rows.find((x) => x.pathway === k && x.basis === 'reference'); return <span data-testid={`thr-${k}`}>{f(r?.threshold_delta_pp, 2)}</span> }, right: true },
                { h: 'Range over bases (pp)', cell: ([k]) => { const v = rows.filter((x) => x.pathway === k).map((x) => num(x.threshold_delta_pp)).filter((x): x is number => x !== null); return v.length ? `${fmt(Math.min(...v), 2)} to ${fmt(Math.max(...v), 2)} (${v.length} bases)` : 'n/a' }, right: true },
                { h: 'Sourced efficiency gain', cell: ([k]) => <span className="small">{sourced[k]}</span> },
              ]} />
            <H1FuelSensitivity s={d.cracker_heat_fuel_efficiency_sensitivity} />
            {exh !== null && exh < 0 ? <Callout kind="warn" title="Against the essay."><span data-testid="exhaust-finding">On the reference basis exhaust-heated full cracking ({f(at(nu, 'full_exhaust.LCOE'), 1)} USD/MWh) is {fmt(-exh, 1)} % cheaper than direct ammonia. The outcome flips with the CAPEX, price and operating-hours bases (see the range above and the row evidence).</span></Callout> : null}
            <p className="prose-p">{show(at(d, 'statement_of_result.text'))}</p>
            <div className="grid-2s">
              <Fig file="enduse_turbine_threshold.png" alt="Turbine-efficiency threshold of each cracking pathway" />
              <Fig file="enduse_sensitivity_efficiency.png" alt="LCOE sensitivity to turbine efficiency" />
              <Fig file="enduse_sensitivity_price_cf.png" alt="LCOE sensitivity to ammonia price and capacity factor" />
              <Fig file="enduse_sensitivity_capital.png" alt="LCOE sensitivity to capital cost" />
              <Fig file="enduse_twoway_map.png" alt="Two-way map of turbine efficiency against cracker capital cost" />
            </div>
            {['H1-a', 'H1-b', 'H1-c', 'H1-d'].map((id) => <RowEvidence key={id} id={id} ev={at(d, ['row_evidence', id])} file="enduse/turbine_threshold.json" />)}
            {sc.phase === 'ready' ? (
              <>
                <h3>N2O treatment</h3>
                <p className="prose-p" data-testid="n2o">{show(at(sc.data, 'mode_a_actual_boundary.n2o_treatment'))} To reach the 25,000 tCO2e threshold from N2O alone, the flue gas would need about {f(at(sc.data, 'mode_a_actual_boundary.n2o_threshold_test.n2o_ppmv_needed_in_flue'), 0)} ppmv N2O ({pct(at(sc.data, 'mode_a_actual_boundary.n2o_threshold_test.fraction_of_fuel_N_to_N2O_needed'))} of the fuel nitrogen). {show(at(sc.data, 'mode_a_actual_boundary.n2o_at_ahmad_0p15_ppmv_note'))}</p>
              </>
            ) : null}
            <FileNote prov={d.provenance as Prov['provenance']} file="results/research/enduse/turbine_threshold.json and turbine_threshold.csv" />
          </>
        )
      }}</AsyncView>
    </Section>
  )
}

/** The two green-ammonia carbon intensities, each with its boundary (carbon_intensity.json routes green and green_lee). */
export function GreenCiNote() {
  const ci = useRJson<O>('carbon_pricing', 'carbon_intensity.json')
  if (ci.phase !== 'ready') return null
  const g = at(ci.data, ['routes', 'green', 'ci_kgCO2e_per_kgH2', 'central']), z = at(ci.data, ['routes', 'green_lee', 'ci_kgCO2e_per_kgH2', 'central'])
  if (num(g) === null || num(z) === null) return null
  return (
    <p className="muted small" data-testid="green-ci-note">Green ammonia has two carbon intensities here, on two boundaries: {f(g, 2)} kgCO2e/kg H2 including the embedded emissions of the renewable assets (the value used for the green routes in the cost and carbon-price tables), and {f(z, 2)} kgCO2e/kg H2 on the boundary that counts renewable electricity as zero (Lee et al.; what remains is shipping, electricity and external heat).</p>
  )
}

/** Carbon intensity of hydrogen by ammonia route with ranges (Environmental Analysis). */
export function CarbonIntensityTable() {
  const ci = useRJson<O & Prov>('carbon_pricing', 'carbon_intensity.json')
  return (
    <AsyncView a={ci} what="the carbon intensity by route (carbon_pricing/carbon_intensity.json)">{(d) => {
      const routes = (d.routes ?? {}) as Record<string, O>
      const comp = (d.comparators_kgCO2e_per_kgH2 ?? {}) as O
      return (
        <>
          <p className="prose-p">{show(d.statement)}</p>
          <DTable caption="Carbon intensity of hydrogen by ammonia route (kgCO2e per kg H2, cradle to PSA outlet)" rows={Object.keys(routes)} keyOf={(k) => k}
            cols={[
              { h: 'Route', cell: (k) => show(routes[k].label), th: true },
              { h: 'Central', cell: (k) => f(at(routes[k], 'ci_kgCO2e_per_kgH2.central'), 2), right: true },
              { h: 'Low to high', cell: (k) => `${f(at(routes[k], 'ci_kgCO2e_per_kgH2.low'), 2)} to ${f(at(routes[k], 'ci_kgCO2e_per_kgH2.high'), 2)}`, right: true },
              { h: 'At 2000 km / 12000 km', cell: (k) => `${f(at(routes[k], ['ci_at_distance_kgCO2e_per_kgH2', '2000_km']), 2)} / ${f(at(routes[k], ['ci_at_distance_kgCO2e_per_kgH2', '12000_km']), 2)}`, right: true },
              { h: 'Gate factor (kgCO2e/kg NH3)', cell: (k) => `${f(at(routes[k], 'gate_ef_kgCO2e_per_kgNH3.central'), 2)} (${f(at(routes[k], 'gate_ef_kgCO2e_per_kgNH3.low'), 2)} to ${f(at(routes[k], 'gate_ef_kgCO2e_per_kgNH3.high'), 2)})`, right: true },
            ]} />
          <GreenCiNote />
          <p className="muted small">Comparators: {Object.entries(comp).map(([k, v]) => `${label(k)} ${show(v)}`).join('; ')} kgCO2e/kg H2.</p>
          <FileNote prov={d.provenance as Prov['provenance']} file="results/research/carbon_pricing/carbon_intensity.json" />
        </>
      )
    }}</AsyncView>
  )
}

/* ================================================================== Validation by evidence kind */
interface KindBlock { total: number; by_status: Record<string, number>; failures: O[] }
const KIND_TITLE: Record<string, string> = {
  numerical_verification: '1. Numerical verification',
  python_vs_aspen: '2. Python against Aspen comparison',
  literature_comparison: '3. Comparison with published literature',
  experimental_validation: '4. Independent experimental validation',
}
export function ValidationByKind() {
  const v = useRJson<{ kinds: Record<string, KindBlock>; evidence_kinds: string[]; statement: string; areas: Record<string, O>; source: string }>('validation', 'by_kind')
  const fehe = useRJson<O & Prov>('heat_exchanger', 'fehe_duty_diagnosis.json')
  return (
    <Section id="by-kind" title="Checks by evidence kind" intro="The four kinds of evidence are kept apart. A pass count is never a validation percentage.">
      <AsyncView a={v} what="the validation counts by evidence kind (validation/by_kind)">{(d) => (
        <>
          <Callout kind="warn" title="No independent experimental validation."><span data-testid="no-experimental">{d.statement}</span></Callout>
          <div className="p2-kinds">
            {d.evidence_kinds.map((k) => {
              const b = d.kinds[k] ?? { total: 0, by_status: {}, failures: [] }
              return (
                <article key={k} className="card p2-kind" data-testid={`kind-${k}`}>
                  <h3>{KIND_TITLE[k] ?? label(k)}</h3>
                  <p><strong>{b.total}</strong> {b.total === 1 ? 'item' : 'items'}: {Object.entries(b.by_status).map(([s, c]) => `${c} ${label(s)}`).join(', ') || 'none'}.</p>
                  {k === 'experimental_validation' ? <p className="small">AmCraX has none. Any item here records that no experimental data exist.</p> : null}
                  {b.failures.length ? (
                    <details className="hyp-details"><summary>{b.failures.length} failing checks with their causes</summary>
                      <ul className="hyp-list">{b.failures.map((x, i) => <li key={i}><code>{show(x.area)}/{show(x.id)}</code>: {show(x.description)} Observed {show(x.observed)}{show(x.expected) ? `, expected ${show(x.expected)}` : ''}, tolerance {show(x.tolerance)}{show(x.unit) ? ` (${show(x.unit)})` : ''}. <span className="muted">{show(x.cause) ? `Cause: ${show(x.cause)}` : `No cause is stored with this item${show(x.method) ? `; method: ${show(x.method)}` : ''}.`}</span></li>)}</ul>
                    </details>
                  ) : null}
                </article>
              )
            })}
          </div>
          {d.kinds.not_labelled ? <p className="muted small">{d.kinds.not_labelled.total} items carry no evidence kind in their file (areas: {Object.entries(d.areas).filter(([, a]) => (a.by_kind as O | undefined)?.not_labelled).map(([k]) => k).join(', ')}); they are not assigned one here.</p> : null}
          <p className="muted small">Source: {d.source}.</p>
        </>
      )}</AsyncView>
      <AsyncView a={fehe} what="the FEHE duty diagnosis (heat_exchanger/fehe_duty_diagnosis.json)">{(d) => {
        const rows = (Array.isArray(d.rows) ? d.rows : []) as O[]
        const WANT = ['case', 'T_reactor_C', 'aspen_duty_kW', 'python_duty_kW', 'difference_kW', 'rel_difference', 'state_effect_kW', 'property_effect_kW', 'python_PR_basis_minus_aspen_kW', 'rel_if_state_matched']
        const cols = rows.length ? WANT.filter((k) => k in rows[0]) : []
        return rows.length ? (
          <>
            <h3>Quantified cause of the FEHE duty failures</h3>
            <DTable caption="FEHE duty: Aspen against Python, with the quantified parts of the difference" rows={rows} keyOf={(_, i) => String(i)}
              cols={cols.map((k, i) => ({ h: label(k), cell: (r: O) => (typeof r[k] === 'number' ? f(r[k], 2) : show(r[k])), right: i > 0, th: i === 0 }))} />
            <p className="muted small">State effect: the dew-point state of the cold inlet stream; property effect: the NH3 residual enthalpy basis. With both parts removed (Python on the Peng-Robinson basis at the Aspen states) the difference is the last column but one. The failing checks keep their tolerance; the diagnosis explains the difference, it does not relabel the failure.</p>
            <FileNote prov={d.provenance as Prov['provenance']} file="results/research/heat_exchanger/fehe_duty_diagnosis.json" />
          </>
        ) : null
      }}</AsyncView>
    </Section>
  )
}

/* ================================================================== legacy banner for the older pages */
export function LegacyBanner() {
  const b = useBaseline()
  if (b.phase !== 'ready') return null
  return (
    <div className="wrap p2-legacy" data-testid="legacy-banner">
      <Callout kind="warn" title="Legacy core result.">
        Cost figures on this page (for example the stored core LCOH of {f(at(b.data, 'superseded_bases.legacy_v1_correlation.lcoh_USD_per_kg'), 2)} USD/kg and its electricity price) are the legacy core result, superseded for research outputs by the unified baseline of {f(b.data.lcoh_USD_per_kg, 3)} USD/kg ({f(b.data.lcoh_SGD_per_kg, 3)} SGD/kg). <FuelEnvelope b={b.data} compact /> <Link to="/hypotheses/economics#baseline">See the unified baseline</Link>.
      </Callout>
    </div>
  )
}

/* ================================================================== findings that changed (supersession) */
export function WhatChanged() {
  const s = useRJson<{ rows: O[]; description?: string; n_rows?: number }>('reference_scenario', 'supersession.json')
  return (
    <AsyncView a={s} what="the supersession table (reference_scenario/supersession.json)">{(d) => (
      <details className="hyp-details" id="what-changed">
        <summary>What changed from the 23 November 2026 release: {d.rows.length} stored numbers, old against new</summary>
        <p className="muted small" style={{ padding: '0 16px' }}>{show(d.description)}</p>
        <DTable caption="Numbers superseded by the unified reference scenario" rows={d.rows} keyOf={(_, i) => String(i)}
          cols={[
            { h: 'Quantity', cell: (r) => show(r.quantity), th: true },
            { h: 'Old', cell: (r) => show(r.old_value), right: true },
            { h: 'New', cell: (r) => show(r.new_value), right: true },
            { h: 'Unit', cell: (r) => show(r.unit) },
            { h: 'Reason', cell: (r) => <span className="small">{show(r.reason)}</span> },
            { h: 'File', cell: (r) => <code className="small">{show(r.file)}</code> },
          ]} />
      </details>
    )}</AsyncView>
  )
}
