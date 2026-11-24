import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fmt } from '../../data/format'
import { AsyncView } from '../../features/common/Notice'
import { XYChart, type XYSeries } from '../../features/common/XYChart'
import { platformPath } from '../routes'
import { refLink } from '../cite'
import { HBarChart } from '../charts'
import { useJson, useMatrix, useRefs, useRows, useValidationSummary } from '../data'
import { mergeSeries } from '../results'
import { Callout, ExtLink, PageHero, Reading, Section } from '../ui'

const FAMILY: Record<string, string> = {
  THERMO: 'Stoichiometry and thermochemistry', EQ: 'Equilibrium: Aspen RGibbs vs Python', FS: 'Flowsheet, every quantity: Aspen vs Python',
  'FS-PRIMARY': 'Flowsheet, primary quantities: Aspen vs Python', FEEDSEC: 'Feed-section analysis (property models)', 'BAL-ASPEN': 'Aspen mass and energy balances', 'BAL-PY': 'Python mass and energy balances',
  SENS: 'Aspen sweep consistency', STEMP: 'Native Aspen sensitivity vs COM sweep', 'FEED-PROP': 'Feed-rate proportionality', PHYS: 'Independent physics checks', LIT: 'Literature benchmarks',
  KIN: 'Kinetics', OPT: 'Optimisation re-solved in Aspen', ECON: 'Economics arithmetic', ENV: 'Carbon-intensity arithmetic', PYTEST: 'Python test suite',
}

const PHYS_LABEL: Record<string, string> = {
  'PHYS-FLAME': 'Burner flame temperature against Cantera (complete combustion)',
  'PHYS-FLAME-DISSOC': 'Effect of dissociation on the flame temperature (Cantera equilibrium)',
  'PHYS-FLUEHX': 'Flue-gas cooler duty against Cantera enthalpies',
  'PHYS-PUMP': 'Pump power against a hand calculation',
  'PHYS-FEHE-UA': 'Exchanger UA against Q / LMTD',
}
const STATUS_PILL: Record<string, string> = { pass: 'pill-ok', fail: 'pill-error', informational: 'pill-info', not_run: 'pill-warn' }

const PHYS_FMT: Record<string, { value: (v: number) => string; tol?: (v: number) => string }> = {
  'PHYS-FLAME': { value: (v) => `${fmt(v, 2)} K largest difference`, tol: (v) => `${fmt(v, 1)} K` },
  'PHYS-FLAME-DISSOC': { value: (v) => `${fmt(v, 2)} K at the baseline (dissociation lowers the temperature)` },
  'PHYS-FLUEHX': { value: (v) => `${fmt(v * 100, 3)} % largest relative difference`, tol: (v) => `${fmt(v * 100, 2)} %` },
  'PHYS-PUMP': { value: (v) => `${fmt(v * 100, 2)} % largest relative difference`, tol: (v) => `${fmt(v * 100, 1)} %` },
  'PHYS-FEHE-UA': { value: (v) => `${v.toExponential(1)} largest relative difference`, tol: (v) => `${fmt(v * 100, 2)} %` },
}

function PhysicsChecks() {
  const mx = useMatrix()
  const rows = mx.items.filter((x) => x.id.startsWith('PHYS-'))
  if (rows.length === 0) return null
  return (
    <>
      <h3 id="physics">Independent physics checks</h3>
      <p className="prose-p">These compare stored Aspen results with calculations that use no Aspen code or databank. Balance closures of about 1e-9 elsewhere in the matrix show that extraction and bookkeeping are consistent; they are not physics checks.</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Independent physics checks">
        <table className="data simple">
          <caption>Independent physics checks of the Aspen flowsheet results</caption>
          <thead><tr><th scope="col">Check</th><th scope="col">Result over the stored cases</th><th scope="col" className="r">Tolerance</th><th scope="col">Status</th></tr></thead>
          <tbody>{rows.map((x) => (
            <tr key={x.id}>
              <th scope="row">{PHYS_LABEL[x.id] ?? x.id}<div className="muted small"><code>{x.id}</code></div></th>
              <td>{x.value != null && PHYS_FMT[x.id] ? PHYS_FMT[x.id].value(x.value) : (x.actual_result ?? '').split(' = ')[1]?.split(' (')[0] ?? 'n/a'}</td>
              <td className="r">{x.tolerance == null ? 'n/a' : PHYS_FMT[x.id]?.tol ? PHYS_FMT[x.id].tol!(x.tolerance) : fmt(x.tolerance, 4)}</td>
              <td><span className={`pill ${STATUS_PILL[x.status] ?? 'pill-neutral'}`}>{x.status}</span></td>
            </tr>))}
          </tbody>
        </table>
      </div>
    </>
  )
}

function FailureCards({ causes }: { causes: { cause: string; description: string; n_items: number; items: string[] }[] }) {
  const mx = useMatrix()
  const feed = mx.byId.get('FEEDSEC-ANALYSIS')?.value
  const kn = mx.byId.get('KIN-NI-PRED'), kr = mx.byId.get('KIN-RU-PRED')
  const kmax = kn?.value != null && kr?.value != null ? Math.max(kn.value, kr.value) : null
  return (
    <div className="grid-2s">
      {causes.map((c) => (
        <article key={c.cause} className="card tile">
          <h4>{c.n_items} failing checks: {c.cause === 'feed_section_enthalpy' ? 'flowsheet cross-check' : c.cause === 'kinetics_figure_predictions' ? 'kinetics reproduction' : c.cause}</h4>
          {c.cause === 'feed_section_enthalpy' ? (
            <>
              <p>The two models use different property models in the feed section. Aspen Plus uses PENG-ROB for the liquid, the vaporisation and the ammonia-water dew point; the Python model uses a reference equation of state for ammonia and an ideal-liquid dew point.
                {feed != null ? <> At identical states the Aspen PENG-ROB vaporiser duty is {fmt(feed * 100, 1)} % above the reference equation of state.</> : null} No reference ammonia-water mixture model was available to arbitrate the dew point.</p>
              <p>The items measure this model-form difference, which acts in both directions. They are not evidence that the Python model is the weaker one, and the primary quantities (conversion, cracked-gas composition, reactor duty) agree in all cases.</p>
            </>
          ) : c.cause === 'kinetics_figure_predictions' ? (
            <p>The microkinetic model of Takahashi and Fujitani reproduces the published conversion curves at diluted NH<sub>3</sub> and with H<sub>2</sub> co-feed only to within about {kmax != null ? fmt(kmax, 2) : 'a larger deviation than the tolerance'} in absolute conversion, against a tolerance of {kn?.tolerance != null ? fmt(kn.tolerance, 2) : 'the stated limit'}. The pure-NH<sub>3</sub> temperature series agree. The catalyst mass was not reported, so the bed was calibrated at one anchor point per catalyst, and the figure readings are approximate.</p>
          ) : <p>{c.description}</p>}
          <p className="muted small">Checks: {c.items.slice(0, 3).join(', ')}{c.items.length > 3 ? `, and ${c.items.length - 3} more` : ''}.</p>
        </article>
      ))}
    </div>
  )
}

function ValidationSummary() {
  const vs = useValidationSummary()
  return (
    <AsyncView a={vs} what="Validation summary">{(v) => {
      const fam = Object.entries(v.file_summary?.by_family ?? {})
      const rows = fam.map(([k, x]) => ({ key: k, name: FAMILY[k] ?? k, n: x.n_items, pass: x.pass, informational: x.informational, fail: x.fail, not_run: x.not_run }))
      const total = v.file_summary?.n_items ?? v.count
      const notRun = v.file_summary ? Object.values(v.file_summary.by_family).reduce((a, x) => a + x.not_run, 0) : 0
      return (
        <>
          <div className="val-counts" role="list" aria-label="Validation matrix totals by status">
            <span role="listitem" className="pill pill-neutral">{total} checks</span>
            <span role="listitem" className="pill pill-ok"><span aria-hidden="true">{'✓'}</span> {v.by_status.pass ?? 0} pass</span>
            <span role="listitem" className="pill pill-error"><span aria-hidden="true">{'✗'}</span> {v.by_status.fail ?? 0} fail</span>
            <span role="listitem" className="pill pill-info">i {v.by_status.informational ?? 0} informational</span>
            <span role="listitem" className="pill pill-warn"><span aria-hidden="true">{'⚠'}</span> {notRun} not run</span>
          </div>
          <HBarChart title="Validation checks by family" source={null} data={rows} catKey="name" stacked xLabel="Number of checks"
            series={[{ key: 'pass', label: 'Pass', color: 'var(--ok)' }, { key: 'informational', label: 'Informational', color: 'var(--info)' }, { key: 'fail', label: 'Fail', color: 'var(--error)' }, { key: 'not_run', label: 'Not run', color: 'var(--warn)' }]}
            description={`Number of validation checks by family, split into pass, informational, fail and not run, ${total} checks in total.`} height={Math.max(360, rows.length * 34 + 110)} />
          <Reading>{(() => { const nf = rows.filter((r) => r.fail > 0).length; return nf === 0 ? 'No family has a failing check.' : `Failures sit in ${nf} of ${rows.length} families, shown in red; the other families have no failing check.` })()}</Reading>
          <div className="table-scroll val-table" tabIndex={0} role="region" aria-label="Validation checks by family and status">
            <table className="data simple">
              <caption>Counts by family and status</caption>
              <thead><tr><th scope="col">Family</th><th scope="col" className="r">Checks</th><th scope="col" className="r">Pass</th><th scope="col" className="r">Fail</th><th scope="col" className="r">Informational</th><th scope="col" className="r">Not run</th></tr></thead>
              <tbody>{rows.map((r) => (
                <tr key={r.key}><th scope="row">{r.name}<div className="muted small"><code>{r.key}</code></div></th><td className="r">{r.n}</td><td className="r">{r.pass}</td><td className="r">{r.fail > 0 ? <strong>{r.fail}</strong> : r.fail}</td><td className="r">{r.informational}</td><td className="r">{r.not_run}</td></tr>))}
              </tbody>
              <tfoot><tr><th scope="row">All families</th><td className="r">{total}</td><td className="r">{v.by_status.pass ?? 0}</td><td className="r">{v.by_status.fail ?? 0}</td><td className="r">{v.by_status.informational ?? 0}</td><td className="r">{notRun}</td></tr></tfoot>
            </table>
          </div>
          <h3 id="failures">The failures, in plain words</h3>
          <FailureCards causes={v.file_summary?.failure_root_causes ?? []} />
          <PhysicsChecks />
        </>
      )
    }}</AsyncView>
  )
}

interface PyRow { T_C: number; P_bar: number; eos: string; nh3_conversion: number }
interface AsRow { T_C: number; P_bar: number; property_method: string; nh3_conversion: number }
interface Where { T_C: number; P_bar: number; value: number }
interface Disc {
  max_abs_dX_ideal_vs_ideal_pp: Where; max_abs_dX_pr_vs_pr_pp: Where; max_abs_dX_aspenPR_vs_pythonIdeal_pp: Where
  mean_abs_dX_ideal_vs_ideal_pp: number; mean_abs_dX_pr_vs_pr_pp: number; n_points: number
}
function Parity() {
  const py = useRows<PyRow>('validation', 'equilibrium_python_grid')
  const as = useRows<AsRow>('validation', 'equilibrium_aspen_grid')
  const disc = useJson<Disc>('/api/data/validation/equilibrium_discrepancy_summary')
  const [P, setP] = useState(20)
  const pressures = useMemo(() => (py.phase === 'ready' ? [...new Set(py.data.rows.map((r) => r.P_bar))].sort((a, b) => a - b) : [1, 5, 10, 20, 30, 40]), [py])
  const data = useMemo(() => {
    if (py.phase !== 'ready' || as.phase !== 'ready') return []
    const pts = (rows: { T_C: number; P_bar: number; nh3_conversion: number }[], sel: (r: never) => boolean) => rows.filter((r) => r.P_bar === P && sel(r as never)).map((r) => ({ x: r.T_C, y: r.nh3_conversion * 100 }))
    return mergeSeries('T', [
      { key: 'pyI', points: pts(py.data.rows, (r: PyRow) => r.eos === 'ideal') },
      { key: 'pyPR', points: pts(py.data.rows, (r: PyRow) => r.eos === 'pr') },
      { key: 'asI', points: pts(as.data.rows, (r: AsRow) => r.property_method === 'IDEAL') },
      { key: 'asPR', points: pts(as.data.rows, (r: AsRow) => r.property_method === 'PENG-ROB') },
    ])
  }, [py, as, P])
  const series: XYSeries[] = [
    { key: 'pyI', label: 'Python, ideal gas', color: '#38bdf8', kind: 'line', source: 'python_model' },
    { key: 'pyPR', label: 'Python, Peng-Robinson', color: '#a5b4fc', kind: 'line', source: 'python_model', dashed: true },
    { key: 'asI', label: 'Aspen RGibbs, IDEAL', color: '#ff7a3d', kind: 'marker', source: 'aspen_plus_v15' },
    { key: 'asPR', label: 'Aspen RGibbs, PENG-ROB', color: '#4ade80', kind: 'marker', source: 'aspen_plus_v15' },
  ]
  return (
    <>
      <div className="preset-row" role="group" aria-label="Pressure of the parity chart">
        <span className="muted">Pressure:</span>
        {pressures.map((p) => <button key={p} type="button" className="chip" aria-pressed={p === P} onClick={() => setP(p)}>{p} bar</button>)}
      </div>
      <AsyncView a={py} what="Python equilibrium grid">{() => (
        <AsyncView a={as} what="Aspen equilibrium grid">{() => (
          <XYChart title={`Equilibrium conversion at ${P} bar: Python models and Aspen Plus RGibbs`} data={data} xKey="T" xLabel={'Temperature [°C]'} yLabel="NH3 conversion [%]" series={series} yDomain={[0, 100]} xDomain={[250, 900]}
            description={`Stored equilibrium conversion of pure ammonia at ${P} bar from the independent Python model (ideal gas and Peng-Robinson) and from Aspen Plus RGibbs with the IDEAL and PENG-ROB property methods; the two programs agree within a small fraction of a percentage point at equal property methods.`} />
        )}</AsyncView>
      )}</AsyncView>
      <AsyncView a={disc} what="Equilibrium discrepancy summary">{(d) => (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Agreement between the Python models and Aspen Plus RGibbs">
          <table className="data simple">
            <caption>Difference in conversion, Aspen minus Python, over the {d.n_points}-point grid (percentage points)</caption>
            <thead><tr><th scope="col">Comparison</th><th scope="col" className="r">Mean absolute</th><th scope="col" className="r">Largest absolute</th><th scope="col">Where</th></tr></thead>
            <tbody>
              <tr><th scope="row">Ideal gas, both programs</th><td className="r">{fmt(d.mean_abs_dX_ideal_vs_ideal_pp, 3)}</td><td className="r">{fmt(Math.abs(d.max_abs_dX_ideal_vs_ideal_pp.value), 3)}</td><td>{d.max_abs_dX_ideal_vs_ideal_pp.T_C} {'°C'}, {d.max_abs_dX_ideal_vs_ideal_pp.P_bar} bar</td></tr>
              <tr><th scope="row">Peng-Robinson, both programs</th><td className="r">{fmt(d.mean_abs_dX_pr_vs_pr_pp, 3)}</td><td className="r">{fmt(Math.abs(d.max_abs_dX_pr_vs_pr_pp.value), 3)}</td><td>{d.max_abs_dX_pr_vs_pr_pp.T_C} {'°C'}, {d.max_abs_dX_pr_vs_pr_pp.P_bar} bar</td></tr>
              <tr><th scope="row">Aspen Peng-Robinson against Python ideal gas</th><td className="r">n/a</td><td className="r">{fmt(Math.abs(d.max_abs_dX_aspenPR_vs_pythonIdeal_pp.value), 2)}</td><td>{d.max_abs_dX_aspenPR_vs_pythonIdeal_pp.T_C} {'°C'}, {d.max_abs_dX_aspenPR_vs_pythonIdeal_pp.P_bar} bar</td></tr>
            </tbody>
          </table>
          <p className="muted small table-note">The last row is the real-gas effect itself: it is largest at low temperature and high pressure and is small at the baseline.</p>
        </div>
      )}</AsyncView>
    </>
  )
}

function References() {
  const refs = useRefs()
  return (
    <AsyncView a={refs} what="Reference list">{(rs) => (
      <ol className="refs">
        {rs.map((r) => {
          const link = refLink(r.doi, r.url)
          return (
            <li key={r.citekey} id={`ref-${r.citekey}`}>
              <span className="ref-text">{r.apa7.replace(/\s?https?:\/\/\S+$/, '')}</span>{' '}
              {link ? <ExtLink href={link}>{link.replace(/^https?:\/\//, '')}</ExtLink> : <span className="muted">no DOI</span>}
              {r.doi_verified ? null : <span className="muted small"> (DOI not verified)</span>}
            </li>
          )
        })}
      </ol>
    )}</AsyncView>
  )
}

export default function Research() {
  return (
    <>
      <PageHero title="What has been checked, and what has not"
        lead="A validation matrix compares Aspen Plus with independent Python models, with literature values and with internal consistency checks. Failures are reported as they are, with their causes." />
      <Section id="matrix" title="Validation matrix" intro="Counts are read from the matrix produced by the validation build script: by status, by family and by cause of failure.">
        <ValidationSummary />
        <p className="muted small">The full matrix, with method, reference, tolerance and limitation for every item, is in the <Link to="/docs">downloads</Link> and on the <Link to={platformPath('/validation')}>platform's Validation page</Link>.</p>
      </Section>
      <Section id="parity" alt title="Equilibrium parity with Aspen Plus" intro="Two independently written programs and one reaction: how far apart do they land when both use the same property model?">
        <Parity />
        <Callout kind="note" title="What this proves.">That the RGibbs block is set up with the right species, reaction and thermodynamic data. It does not validate the process, which has no plant data to be validated against. The remaining difference between the two Peng-Robinson implementations is not explained; a sensitivity study indicates that binary interaction parameters are an unlikely cause.</Callout>
      </Section>
      <Section id="notvalidated" title="What is not validated">
        <ul className="plain-list">
          <li><strong>Hydrogen separation.</strong> The PSA is a reduced-order component splitter with an assumed recovery; the palladium-membrane model is a literature-based Sieverts calculation. Neither is a designed unit.</li>
          <li><strong>Costs.</strong> Levelised cost is an order-of-magnitude, assumption-based estimate; its comparison with published values is informational only.</li>
          <li><strong>Efficiency metrics.</strong> LHV efficiency and the net fuel heat deficit are first-law upper bounds, and the burner flame temperature is the complete-combustion value.</li>
          <li><strong>Carbon accounting.</strong> Simplified cradle-to-gate accounting with stated factors, not a life-cycle assessment.</li>
          <li><strong>Kinetics at pressure.</strong> Rate laws were fitted at 1 atm and are extrapolated to 20 bar; reproduction of published conversion curves fails in two checks.</li>
          <li><strong>Plant behaviour.</strong> No plant or pilot data were available; steady state only, no dynamics or control.</li>
        </ul>
      </Section>
      <Section id="references" alt title="References" intro="APA 7th edition. Every in-text citation on this site links here; DOIs resolve at doi.org.">
        <References />
        <p className="muted small">Literature values are used as inputs or benchmarks, always cited, and never presented as AmCraX results.</p>
      </Section>
    </>
  )
}
