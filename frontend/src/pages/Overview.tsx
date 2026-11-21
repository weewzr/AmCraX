import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getJson } from '../api/client'
import type { DataSource } from '../api/types'
import { useData } from '../data/DataContext'
import { KpiTile, SourceBadge, StatusPill, Value } from '../components/ui'
import { fmt } from '../data/format'
import { platformPath } from '../site/routes'

interface EconFile { lcoh_USD_per_kg?: number | null; source?: DataSource; input_source?: string }
interface EnvRow { nh3_route: string; heating_option: string; heating_label: string; total_kgCO2e_per_kgH2: number | null }
interface EnvFile { comparison?: { source?: DataSource; rows?: EnvRow[]; method?: string } }
interface ValSummary { n_items?: number; pass?: number; fail?: number; not_run?: number; informational?: number }

type Remote<T> = { state: 'loading' } | { state: 'ok'; v: T } | { state: 'na'; why: string }

function useRemote<T>(url: string | null): Remote<T> {
  const [r, setR] = useState<Remote<T>>({ state: 'loading' })
  useEffect(() => {
    if (!url) { setR({ state: 'na', why: 'no active case' }); return }
    let live = true
    setR({ state: 'loading' })
    getJson<T>(url).then((v) => { if (live) setR({ state: 'ok', v }) }).catch((e: unknown) => { if (live) setR({ state: 'na', why: e instanceof Error ? e.message : String(e) }) })
    return () => { live = false }
  }, [url])
  return r
}

const LINKS: [string, string, string][] = [
  [platformPath('/pfd'), 'Process Flow Diagram', 'interactive flowsheet with stream and equipment data'],
  [platformPath('/simulation'), 'Simulation', 'cases, inputs and balances'],
  [platformPath('/reactor'), 'Reactor Analysis', 'equilibrium and kinetic PFR'],
  [platformPath('/heat'), 'Heat Integration', 'pinch analysis, FEHE, tail-gas heat'],
  [platformPath('/sensitivity'), 'Sensitivity Analysis', 'Aspen parameter sweeps'],
  [platformPath('/optimisation'), 'Optimisation', 'single-objective and Pareto'],
  [platformPath('/economics'), 'Techno-Economics', 'levelised cost of hydrogen'],
  [platformPath('/environment'), 'Environment', 'carbon intensity scenarios'],
  [platformPath('/validation'), 'Validation', 'Aspen vs Python vs literature'],
  [platformPath('/reports'), 'Reports', 'report, deck and figures'],
]

export default function Overview() {
  const { phase, mode, active, error, skipped, cases, manifest, caseLabel } = useData()
  const k = active?.kpis
  const src = active?.source ?? null
  const id = active?.case_id ?? null
  const econ = useRemote<EconFile>(mode === 'DEMO' || !id ? null : `/api/data/analysis/economics_${id}`)
  const env = useRemote<EnvFile>(mode === 'DEMO' || !id ? null : `/api/data/analysis/environmental_${id}`)
  const val = useRemote<{ summary?: ValSummary; generated_utc?: string }>(mode === 'DEMO' ? null : '/api/validation')

  const envRows = env.state === 'ok' ? (env.v.comparison?.rows ?? []) : []
  const ciRow = envRows.find((r) => r.nh3_route === 'green' && r.heating_option === 'self_firing')
  const ciVals = envRows.map((r) => r.total_kgCO2e_per_kgH2).filter((x): x is number => x !== null)
  const ciSrc: DataSource | null = env.state === 'ok' ? (env.v.comparison?.source ?? 'python_model') : null
  const lcohSrc: DataSource | null = econ.state === 'ok' ? (econ.v.source ?? 'python_model') : null
  const naWhy = (r: Remote<unknown>) => (r.state === 'na' ? `not available for this case (${r.why})` : undefined)

  return (
    <section className="page">
      <h1>Overview</h1>
      <p className="lead">
        AmCraX models ammonia cracking to hydrogen: liquid NH3 is pumped, vaporised, preheated and cracked over a catalyst
        (2 NH3 {'\u21C4'} N2 + 3 H2), cooled, and purified in a pressure-swing adsorption (PSA) unit; the PSA tail gas is burned for heat recovery.
        Flowsheet results come from Aspen Plus V15 and an independent Python model; every number carries its provenance.
      </p>
      {phase === 'loading' && <div className="card">Loading data...</div>}
      {phase === 'error' && <div className="card error-card" role="alert"><StatusPill kind="error">Data load failed</StatusPill> {error}</div>}
      {phase === 'ready' && !active && (
        <div className="card" role="status">
          No simulation case is available in {mode} mode. {skipped.length ? `Unreadable cases: ${skipped.join(', ')}.` : 'No case files were found.'}
        </div>
      )}
      {active && (
        <>
          <div className="result-head card">
            <strong>Case {active.case_id}</strong>
            <span className="muted">{caseLabel(active.case_id) !== active.case_id ? caseLabel(active.case_id) : ''}</span>
            <SourceBadge source={src} />
            {active.status.converged ? <StatusPill kind="ok">Converged</StatusPill> : <StatusPill kind="error">Not converged</StatusPill>}
            {active.status.has_errors && <StatusPill kind="error">Errors</StatusPill>}
            {active.status.has_warnings && <StatusPill kind="warn">Warnings</StatusPill>}
            <span>Mass closure residual: {active.balances.mass_closure_rel === null ? 'n/a' : fmt(active.balances.mass_closure_rel, 6)}</span>
            <span>Energy closure residual: {active.balances.energy_closure_rel === null ? 'n/a' : fmt(active.balances.energy_closure_rel, 6)}</span>
          </div>
          <div className="kpi-grid kpi-4">
            <KpiTile label="NH3 conversion" v={k?.nh3_conversion === null || k === undefined ? null : k.nh3_conversion * 100} unit="%" digits={2} source={src} />
            <KpiTile label="H2 product" v={k?.h2_product_kg_h} unit="kg/h" source={src} />
            <KpiTile label="H2 purity" v={k?.h2_purity_mole_frac === null || k === undefined ? null : k.h2_purity_mole_frac * 100} unit="mol %" digits={3} source={src} />
            <KpiTile label="External heating demand" v={k?.total_external_heating_kW} unit="kW" source={src} hint="VAPORIZR + HEATER + CRACKER duties" />
            <KpiTile label="Specific heat demand" v={k?.specific_heat_demand_kWh_per_kgH2} unit="kWh/kg H2" digits={2} source={src} />
            <KpiTile label="LHV efficiency" v={k?.lhv_efficiency === null || k === undefined ? null : k.lhv_efficiency * 100} unit="%" digits={1} source={src} />
            <KpiTile label="LCOH (assumption-based)" v={econ.state === 'ok' ? (econ.v.lcoh_USD_per_kg ?? null) : null} unit="USD/kg H2" digits={2} source={lcohSrc}
              hint={naWhy(econ) ?? 'Levelised cost of hydrogen from analysis/economics_<case>.json; depends on cost assumptions listed on the Techno-Economics page'} />
            <KpiTile label="Carbon intensity, green NH3 + self-firing" v={ciRow?.total_kgCO2e_per_kgH2 ?? null} unit="kg CO2e/kg H2" digits={2} source={ciSrc}
              hint={naWhy(env) ?? (ciVals.length ? `Range over all NH3 routes and heating options: ${fmt(Math.min(...ciVals), 2)} to ${fmt(Math.max(...ciVals), 2)} kg CO2e/kg H2. Simplified accounting, not an LCA.` : 'no scenario rows')} />
          </div>
          {(econ.state === 'na' || env.state === 'na') && (
            <p className="muted" role="note">LCOH / carbon intensity are only computed for cases with an analysis file (baseline and baseline_no_hi); n/a elsewhere. LCOH and carbon intensity are model/assumption-based, not Aspen results.</p>
          )}

          <div className="grid-2">
            <div className="card">
              <h2>Process summary</h2>
              <table className="plain-kv">
                <tbody>
                  <tr><th>Feed</th><td><Value v={active.inputs.feed_total_kmol_h} unit="kmol/h" source={src} showSource={false} /> liquid NH3, H2O <Value v={active.inputs.feed_h2o_mole_frac * 100} unit="mol %" digits={2} source={src} showSource={false} /></td></tr>
                  <tr><th>Reactor</th><td><Value v={active.inputs.reactor_temperature_C} unit={'\u00B0C'} digits={0} source={src} showSource={false} />, <Value v={active.inputs.reactor_pressure_bar} unit="bar" digits={1} source={src} showSource={false} /> (isothermal Gibbs reactor)</td></tr>
                  <tr><th>Heat integration</th><td>{active.inputs.heat_integration ? <>feed/effluent exchanger on, hot-end approach <Value v={active.inputs.fehe_hot_end_approach_K} unit="K" digits={0} source={src} showSource={false} /></> : 'off (FEHE removed)'}</td></tr>
                  <tr><th>Purification</th><td>reduced-order PSA, H2 recovery <Value v={active.inputs.psa_h2_recovery} digits={2} source={src} showSource={false} />, feed <Value v={active.inputs.psa_feed_temperature_C} unit={'\u00B0C'} digits={0} source={src} showSource={false} /></td></tr>
                  <tr><th>Tail gas</th><td>burned with <Value v={active.inputs.burner_excess_air * 100} unit="% excess air" digits={0} source={src} showSource={false} />, stack <Value v={active.inputs.stack_temperature_C} unit={'\u00B0C'} digits={0} source={src} showSource={false} /></td></tr>
                  <tr><th>Property method</th><td>{active.inputs.property_method}</td></tr>
                </tbody>
              </table>
              <p className="muted">Case source: <SourceBadge source={src} /> {active.model_file ? `model file ${active.model_file.split(/[\\/]/).pop()}` : ''}</p>
            </div>
            <div className="card">
              <h2>Validation summary</h2>
              {val.state === 'loading' && <p>Loading...</p>}
              {val.state === 'na' && <p className="muted">Validation matrix not available ({val.why}).</p>}
              {val.state === 'ok' && (
                <>
                  <div className="val-counts">
                    <StatusPill kind="ok">{val.v.summary?.pass ?? 'n/a'} pass</StatusPill>
                    <StatusPill kind="error">{val.v.summary?.fail ?? 'n/a'} fail</StatusPill>
                    <StatusPill kind="warn">{val.v.summary?.not_run ?? 'n/a'} not run</StatusPill>
                    <StatusPill kind="info">{val.v.summary?.informational ?? 'n/a'} informational</StatusPill>
                  </div>
                  <p className="muted">{val.v.summary?.n_items ?? 'n/a'} checks in total. Failures are reported, not hidden; details and discrepancies are on the <Link to={platformPath('/validation')}>Validation</Link> page.</p>
                </>
              )}
            </div>
          </div>
        </>
      )}

      <div className="card">
        <h2>Data modes</h2>
        <ul>
          <li><strong>LIVE</strong> - the FastAPI backend answers; results are read from its results store and actions (simulations, sweeps) are enabled.</li>
          <li><strong>SNAPSHOT</strong> - the API is down but a results export exists bundled with the site (real stored results; read-only pages work, actions are disabled; export time shown in the banner).</li>
          <li><strong>DEMO</strong> - neither is available; a small bundled fixture is shown under a permanent banner. Demonstration values are not results.</li>
        </ul>
        <p className="muted">
          Currently: <strong>{mode ?? '...'}</strong>, {cases.length} case(s) loaded{mode === 'SNAPSHOT' && manifest?.exported_utc ? `, exported ${manifest.exported_utc}` : ''}. Modes are never mixed.
        </p>
      </div>
      <div className="card">
        <h2>Sections</h2>
        <ul className="quick-links">
          {LINKS.map(([to, label, d]) => (<li key={to}><Link to={to}>{label}</Link> <span className="muted">- {d}</span></li>))}
        </ul>
      </div>
    </section>
  )
}


