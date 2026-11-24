import { Link } from 'react-router-dom'
import { assetUrl, fetchShots } from '../../api/reports'
import { Value } from '../../components/ui'
import { useData } from '../../data/DataContext'
import { AsyncView } from '../../features/common/Notice'
import { useAsync } from '../../features/common/useAsync'
import { fmt } from '../../data/format'
import { useMatrix, useResultsReady } from '../data'
import { EquilibriumCalculatorLazy } from '../EquilibriumCalculatorLazy'
import { Callout, Cite, PageHero, Section } from '../ui'

function BlockTable() {
  const { flowsheet } = useData()
  if (!flowsheet) return <p className="muted">Flowsheet definition not available.</p>
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Aspen Plus blocks of the flowsheet">
      <table className="data simple blocks">
        <caption>Blocks of the Aspen Plus flowsheet (read from the flowsheet definition shared by Aspen, Python and the diagram)</caption>
        <thead><tr><th scope="col">Block</th><th scope="col">Aspen type</th><th scope="col">Role in the process</th></tr></thead>
        <tbody>
          {flowsheet.blocks.map((b) => (
            <tr key={b.id}>
              <th scope="row"><code>{b.id}</code><div className="muted small">{b.name}{b.optional ? ' (optional)' : ''}</div></th>
              <td><code>{b.aspen_type}</code></td>
              <td>{b.role}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Assumptions() {
  const { cases } = useData()
  const mx = useMatrix()
  const b = cases.find((c) => c.case_id === 'baseline')
  if (!b) return <p className="muted">Baseline case not available.</p>
  const i = b.inputs
  const dis = mx.byId.get('PHYS-FLAME-DISSOC')?.value ?? null
  const rows: { item: string; value: React.ReactNode; origin: React.ReactNode }[] = [
    { item: 'Feed', value: <><Value v={i.feed_total_kmol_h} unit="kmol/h" digits={0} source="assumption" showSource={false} />, <Value v={(1 - i.feed_h2o_mole_frac) * 100} unit="mol% NH3" digits={1} source="assumption" showSource={false} />, saturated liquid at 1.013 bar</>, origin: <>Engineering assumption: atmospheric refrigerated storage; a liquid NH3 inlet near -33 °C is also the boundary used by <Cite k="mehr2026highcapacity" />. Water stands for the impurity of commercial ammonia.</> },
    { item: 'Reactor', value: <>RGibbs, isothermal, <Value v={i.reactor_temperature_C} unit={'°C'} digits={0} source="assumption" showSource={false} />, <Value v={i.reactor_pressure_bar} unit="bar" digits={0} source="assumption" showSource={false} /></>, origin: <>Engineering assumption, within the 17.5 to 21 bar of <Cite k="mehr2026highcapacity" /> and at the 20 bar of <Cite k="richard2024technoeconomic" />; <Cite k="cho2026nickel" /> compare cracker pressures from 1.2 to 30 bar.</> },
    { item: 'Feed/effluent exchanger', value: <>{i.heat_integration ? <>cold outlet = reactor T minus <Value v={i.fehe_hot_end_approach_K} unit="K" digits={0} source="assumption" showSource={false} /></> : 'off'}</>, origin: 'Engineering assumption (hot-end approach).' },
    { item: 'PSA hydrogen recovery', value: <Value v={i.psa_h2_recovery} digits={2} source="assumption" showSource={false} />, origin: <>Engineering assumption above the published range of 0.71 to 0.81 (0.71 <Cite k="hansen2024hysys" />, as reported there for Cha et al.; 0.756 <Cite k="cho2026nickel" />; 0.80 <Cite k="kum2026heatintegrated" />; about 0.81 <Cite k="mehr2026highcapacity" />). The PSA is a reduced-order component splitter.</> },
    { item: 'PSA N2 slip, feed temperature', value: <><Value v={i.psa_n2_slip} digits={3} source="assumption" showSource={false} /> of the N2 fed, <Value v={i.psa_feed_temperature_C} unit={'°C'} digits={0} source="assumption" showSource={false} /></>, origin: 'Engineering assumption. Together with the recovery this sets the product purity: the purity of the baseline product is a consequence of these inputs, not a prediction of a PSA design.' },
    { item: 'Tail-gas burner', value: <>adiabatic, complete combustion, <Value v={i.burner_excess_air * 100} unit="% excess air" digits={0} source="assumption" showSource={false} />, stack <Value v={i.stack_temperature_C} unit={'°C'} digits={0} source="assumption" showSource={false} /></>, origin: <>Engineering assumption. The flame temperature of the stored results is the complete-combustion value (no dissociation){dis === null ? null : <>; an equilibrium calculation with dissociation gives about {fmt(Math.abs(dis), 1)} K less</>}.</> },
    { item: 'Vaporiser outlet', value: <>dew point + 10 K</>, origin: 'Engineering assumption. The outlet temperature and duty follow from the dew point of the feed, which with 0.2 mol% water depends on the vapour-liquid model; no reference ammonia-water mixture model was available to check it (see the research page).' },
    { item: 'Property method', value: <code>{i.property_method}</code>, origin: <>Peng-Robinson is also the property method of <Cite k={['cho2026nickel', 'mehr2026highcapacity', 'richard2024technoeconomic']} /> (Aspen Plus) and of <Cite k={['hansen2024hysys', 'farokhi2025costoptimization']} /> (Aspen HYSYS); <Cite k="ahmad2025gtcc" /> use the Boston-Mathias variant and <Cite k="chopra2026decentralized" /> Redlich-Kwong-Soave with Boston-Mathias. Hansen et al. found no significant difference from SRK on their base case.</> },
  ]
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Baseline design basis and the origin of each choice">
      <table className="data simple">
        <caption>Baseline design basis (case inputs of the stored Aspen run) and where each choice comes from</caption>
        <thead><tr><th scope="col">Item</th><th scope="col">Baseline value</th><th scope="col">Origin</th></tr></thead>
        <tbody>{rows.map((r) => (<tr key={r.item}><th scope="row">{r.item}</th><td>{r.value}</td><td>{r.origin}</td></tr>))}</tbody>
      </table>
    </div>
  )
}

function Screenshots() {
  const ready = useResultsReady()
  const shots = useAsync((s) => fetchShots(s), [], ready)
  return (
    <AsyncView a={shots} what="Aspen Plus screenshots">{(s) => (
      <>
        <p className="muted">{s.aspen_manifest?.aspen_version}. {s.aspen_manifest?.note}</p>
        <ul className="shot-gallery">
          {s.aspen.filter((x) => x.status === 'captured').map((x) => (
            <li key={x.file}>
              <figure className="card shot-card">
                <a href={assetUrl(x.url)} target="_blank" rel="noopener noreferrer">
                  <img src={assetUrl(x.url)} loading="lazy" width="1600" height="900" alt={`Aspen Plus V15 screenshot, ${x.title}. ${x.what_is_shown ?? ''}`} />
                  <span className="sr-only"> (full size, opens in a new tab)</span>
                </a>
                <figcaption>
                  <strong>{x.title}</strong>
                  <span className="muted small block">{x.navigation_path}</span>
                  <span className="block">{x.what_is_shown}</span>
                  {x.why_it_matters ? <span className="muted small block">Why it matters: {x.why_it_matters}</span> : null}
                </figcaption>
              </figure>
            </li>
          ))}
        </ul>
      </>
    )}</AsyncView>
  )
}

export default function Methodology() {
  const mx = useMatrix()
  const janaf = mx.byId.get('EQ-DH-JANAF') ? Number((mx.byId.get('EQ-DH-JANAF')?.actual_result ?? '').match(/=\s*([0-9.eE+-]+)/)?.[1]) || null : null
  const kt = mx.byId.get('KIN-TABLE2'), kn = mx.byId.get('KIN-NI-PRED'), kr = mx.byId.get('KIN-RU-PRED')
  const kin = kt && kn && kr && kt.value != null && kn.value != null && kr.value != null
    ? <>It reproduces the published rate constants (largest relative deviation {fmt(kt.value * 100, 1)} %) but not the published conversion curves at dilute NH<sub>3</sub> or with H<sub>2</sub> co-feed: the largest absolute deviations in conversion are about {fmt(Math.max(kn.value, kr.value), 2)} against a tolerance of {fmt(kn.tolerance ?? 0.05, 2)}, so two validation checks fail, and the research page says so.</>
    : <>It reproduces published rate constants but not published conversion curves at dilute NH<sub>3</sub> or with H<sub>2</sub> co-feed: two validation checks fail, and the research page says so.</>
  return (
    <>
      <PageHero
        eyebrow="Section 4 - Simulation methodology"
        title="How the simulation is built"
        lead="Three models of the same plant: a rigorous Aspen Plus V15 flowsheet driven from Python, an independent equilibrium model that checks it, and literature kinetics for the question the equilibrium model cannot answer."
      />

      <Section id="aspen" title="The Aspen Plus V15 model" intro="A steady-state flowsheet with Peng-Robinson properties. The exchanger loop is converged by tearing stream S4.">
        <div className="prose">
          <p>
            The model is not edited by hand. A generator writes the Aspen input file (<code>baseline.inp</code>) from a validated case object and the flowsheet definition, and the solved model is saved as a <code>.bkp</code> backup file. The variant without the feed/effluent exchanger comes from the same generator with one switch, so a design change is one input value.
          </p>
          <p>
            All components, the property method and the stream class are global settings: NH<sub>3</sub>, H<sub>2</sub>, N<sub>2</sub>, H<sub>2</sub>O and O<sub>2</sub>, <code>PENG-ROB</code> and one vapour-liquid substream.
            A cubic equation of state covers the refrigerated liquid feed, the pressurised cracking gas and the hot combustion side with one parameter set and supplies the fugacity coefficients for the Gibbs reactor
            {' '}<Cite k="peng1976new" />. Peng-Robinson is also what five published cracker flowsheet studies used <Cite k={['cho2026nickel', 'mehr2026highcapacity', 'richard2024technoeconomic', 'hansen2024hysys', 'farokhi2025costoptimization']} />; two others used Boston-Mathias variants of the cubic equation (see the assumptions table).
          </p>
          <p>
            The cracker is an <strong>RGibbs</strong> block: it minimises the Gibbs energy at fixed temperature and pressure, so it shows the thermodynamic limit, not a reactor design. Aspen detects the loop between the
            feed/effluent exchanger and the temperature link and tears stream S4 with a Wegstein block; the saved model reports it converged with a tear error of zero. Mass and energy balances close to round-off, which shows that extraction and bookkeeping are consistent; it is not a test of the physics.
          </p>
        </div>
        <BlockTable />
      </Section>

      <Section id="automation" alt title="Python COM automation" intro="Every Aspen result on this site was produced by a Python program, not by interactive GUI work.">
        <ol className="steps">
          <li><strong>Generator.</strong> Validates a typed case and writes the complete Aspen input file with explicit units (bar, {'°C'}, kW).</li>
          <li><strong>COM session.</strong> Starts Aspen Plus V15 as an out-of-process COM server, opens the file, reads and writes variable-tree nodes, runs the engine and releases the server.</li>
          <li><strong>Extraction.</strong> Reads every stream and block, run messages and convergence status.</li>
          <li><strong>Typed result.</strong> A schema-checked result carrying <code>source = "aspen_plus_v15"</code>; KPIs and balance closures use the same functions as the Python process model.</li>
          <li><strong>Storage.</strong> JSON per case and CSV per study; model files are referenced by project-relative paths.</li>
          <li><strong>API worker.</strong> A separate process launched by the FastAPI back end for each on-demand run.</li>
        </ol>
        <div className="grid-3">
          <article className="card tile"><h3>Run synchronously</h3><p><code>Engine.Run2()</code> after <code>Reinit</code>. An earlier asynchronous loop returned one stale duty; the validation matrix caught it and the equilibrium grid was regenerated with repeatability checks.</p></article>
          <article className="card tile"><h3>One Aspen at a time</h3><p>A cross-process lock file allows a single Aspen instance, and a second file in the same COM instance fails in V15, so the session restarts the server.</p></article>
          <article className="card tile"><h3>Safe release</h3><p>Dialogs are suppressed, the server is closed and quit, and orphaned processes are cleaned up, so a failed run does not leave Aspen running.</p></article>
        </div>
      </Section>

      <Section id="equilibrium" title="Independent equilibrium model" intro="An independent check of the Aspen reactor, written without Aspen: thermochemistry, closed form, no fitted parameters.">
        <div className="two-col">
          <div className="prose">
            <p>
              Species data are the NASA-7 polynomials of GRI-Mech 3.0 <Cite k="smith_grimech30" /> as shipped with Cantera <Cite k="goodwin2018cantera" />. They give the reaction Gibbs energy and so
              K(T). For a pure ammonia feed and an ideal gas, the element balances and the mass-action law reduce to a closed form:
            </p>
            <div className="eq-block">
              <p className="eq">K(T) = exp( {'−'}{'Δ'}G{'°'}<sub>r</sub>(T) / RT )</p>
              <p className="eq">K = (3{'√'}3 / 4) {'·'} X<sup>2</sup> / (1 {'−'} X<sup>2</sup>) {'·'} P/p{'°'}</p>
              <p className="eq">X<sub>eq</sub> = ( 1 + (3{'√'}3 / 4) {'·'} (P/p{'°'}) / K(T) )<sup>{'−'}1/2</sup></p>
            </div>
            <p>
              With y<sub>NH3</sub> = (1{'−'}X)/(1+X), y<sub>N2</sub> = X/(2(1+X)) and y<sub>H2</sub> = 3X/(2(1+X)). A real-gas variant with Peng-Robinson fugacity coefficients exists in the Python model; the calculator below
              uses the ideal-gas closed form. The same data are checked against NIST-JANAF <Cite k="nist_janaf" />{janaf ? <> (largest difference in reaction enthalpy {fmt(janaf, 3)} kJ/mol)</> : null}.
            </p>
            <p>
              Parity with Aspen Plus is shown on the <Link to="/research#parity">research page</Link>: the table there gives, for each pair of property methods, the mean and the largest difference in conversion between the two programs.
            </p>
          </div>
          <Callout title="Why two models?">
            Agreement between two independently written codes, compared like for like (same property model on both sides) over the whole stored Aspen RGibbs grid, is evidence that the RGibbs block is set up correctly. It does not validate the process against plant data, of which there is none.
          </Callout>
        </div>
        <EquilibriumCalculatorLazy />
      </Section>

      <Section id="kinetics" alt title="Kinetics and plug-flow reactor" intro="Equilibrium says how far cracking can go; kinetics says how much catalyst it takes. This part is Python only, with literature rate laws.">
        <div className="prose">
          <p>
            Two rate-law families are implemented: a reversible Temkin-Pyzhev law fitted to Ru/Al<sub>2</sub>O<sub>3</sub> data valid from 623 to 773 K <Cite k={['kum2026heatintegrated', 'dicarlo2014ammonia']} p="5-7" />, and the microkinetic Ni/MgO and Ru/MgO models of
            {' '}<Cite k="takahashi2016kinetic" p="23-25" />. Every parameter carries its page reference. They are integrated in an isothermal, adiabatic or heated plug-flow reactor with an Ergun pressure drop.
          </p>
          <p>
            The microkinetic model was fitted at 1 atm (Ni 350 to 650 {'°C'}, Ru 300 to 550 {'°C'}), so its use at 20 bar is an extrapolation that is capped at equilibrium.
            {' '}{kin}{' '}
            Kinetic results never enter the Aspen flowsheet, which has no catalyst or reactor volume.
          </p>
        </div>
      </Section>

      <Section id="assumptions" title="Assumptions" intro="Inputs of the baseline case. The values are read from the stored Aspen case; the origin column says what is behind each one.">
        <Assumptions />
        <Callout kind="warn" title="Reading the efficiency numbers.">LHV efficiency and the net fuel heat deficit are first-law, upper-bound metrics: external heat is counted one to one against the fuel LHV (a fired heater with 100 % efficiency) and flue-gas heat below the reactor temperature is credited. The pinch analysis, which respects temperature levels, gives a different heat import, which is reported on the platform's Heat Integration page.</Callout>
        <Callout kind="warn" title="Steady state only.">The flowsheet has no dynamics, start-up, turndown, catalyst deactivation or control; it is not a digital twin.</Callout>
      </Section>

      <Section id="screenshots" alt title="Aspen Plus screenshots" intro="Genuine captures of the Aspen Plus V15 window with the baseline model opened through COM and run before capture, each opened and checked after saving.">
        <Screenshots />
      </Section>
    </>
  )
}
