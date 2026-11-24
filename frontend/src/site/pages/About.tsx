import { Link } from 'react-router-dom'
import { GITHUB_URL, PORTFOLIO_PROJECT_URL, PORTFOLIO_URL } from '../../api/url'
import { Value } from '../../components/ui'
import { useData } from '../../data/DataContext'
import { useValidationSummary } from '../data'
import { Callout, Cite, ExtLink, PageHero, Section } from '../ui'

const SOFTWARE: [string, string, string][] = [
  ['Aspen Plus V15', 'https://www.aspentech.com/en/products/engineering/aspen-plus', 'rigorous flowsheet simulation, driven through its COM interface'],
  ['Cantera', 'https://cantera.org/', 'source of the GRI-Mech 3.0 NASA-7 thermochemical data'],
  ['CoolProp', 'http://www.coolprop.org/', 'reference equation of state for liquid ammonia in the Python model'],
  ['SciPy and NumPy', 'https://scipy.org/', 'root finding, optimisation (differential evolution, SLSQP) and numerics'],
  ['FastAPI and Pydantic', 'https://fastapi.tiangolo.com/', 'the API and the typed result schemas'],
  ['React and TypeScript', 'https://react.dev/', 'the web application'],
  ['React Flow (xyflow)', 'https://reactflow.dev/', 'the interactive process flow diagram'],
  ['Recharts', 'https://recharts.org/', 'the charts'],
  ['Vite and Vitest', 'https://vite.dev/', 'build tooling and unit tests'],
]

export default function About() {
  const { cases } = useData()
  const i = cases.find((c) => c.case_id === 'baseline')
  const k = i?.kpis
  const vs = useValidationSummary()
  const nFail = vs.phase === 'ready' ? vs.data.by_status.fail : null
  const rc = vs.phase === 'ready' ? (vs.data.file_summary?.failure_root_causes ?? []) : []
  const nFs = rc.find((c) => c.cause === 'feed_section_enthalpy')?.n_items ?? null
  const nKin = rc.find((c) => c.cause === 'kinetics_figure_predictions')?.n_items ?? null
  const nAll = vs.phase === 'ready' ? (vs.data.file_summary?.n_items ?? vs.data.count) : null
  return (
    <>
      <PageHero title="About AmCraX"
        lead="An independent project that turns a literature question, what does it cost to get hydrogen back out of ammonia, into a simulation platform whose every number can be traced." />
      <Section id="motivation" title="Motivation">
        <div className="prose">
          <p>
            AmCraX grew out of a hydrogen-energy course essay on ammonia cracking. The essay asked how much of the carrier's energy is spent releasing the hydrogen; answering it properly needed a flowsheet, a heat balance, an independent check and an honest account of where the models stop.
            The result is a platform rather than a calculation: an Aspen Plus V15 model driven from Python, independent Python models alongside it, and a web interface that shows which model every number comes from.
          </p>
          <p>
            More about the author's projects: <ExtLink href={PORTFOLIO_PROJECT_URL}>the AmCraX page</ExtLink> on the <ExtLink href={PORTFOLIO_URL}>portfolio</ExtLink>. The source code is on <ExtLink href={GITHUB_URL}>GitHub</ExtLink>.
          </p>
        </div>
      </Section>

      <Section id="limits" alt title="What AmCraX does not claim" intro="The platform is a preliminary engineering study. These limits apply to every number on this site.">
        <ul className="limit-list">
          <li><strong>The reactor is an equilibrium reactor.</strong> The RGibbs cracker shows the thermodynamic limit, not a reactor design. Kinetic plug-flow results exist only in the Python model, are extrapolated beyond their fitted pressure and never enter the Aspen flowsheet.</li>
          <li><strong>The hydrogen separator is a reduced-order splitter.</strong> Its recovery of <Value v={i?.inputs.psa_h2_recovery} digits={2} source="assumption" showSource={false} /> and its nitrogen slip are assumptions, so the product purity is set by them and is not predicted. The recovery is an assumption above the published PSA range of 0.71 to 0.81 (<Cite k={['hansen2024hysys', 'cho2026nickel', 'kum2026heatintegrated', 'mehr2026highcapacity']} />). No bed, cycle or adsorbent is designed.</li>
          <li><strong>Costs are preliminary.</strong> The levelised cost of hydrogen is an order-of-magnitude estimate from a plant-level capital correlation that does not see exchanger area, PSA size or catalyst volume. It leaves out NOx treatment, NH<sub>3</sub> polishing, compression and installed-cost factors, and mixes cost years. Ammonia is priced on the NH<sub>3</sub> actually contained in the feed and fuel.</li>
          <li><strong>Efficiency numbers are upper bounds.</strong> LHV efficiency and the net fuel heat deficit are first-law metrics that count external heat one to one against fuel LHV and credit flue-gas heat below the reactor temperature. The burner flame temperature is the complete-combustion value, without dissociation.</li>
          <li><strong>Optimisation is on the Python model.</strong> The objectives largely do not conflict in this model, and the optimum sits on bounds of the decision variables because the cost model does not see equipment size. The optimum points were re-solved in Aspen Plus, not searched with it.</li>
          <li><strong>Carbon accounting is simplified.</strong> It is a cradle-to-gate bookkeeping with stated factors, not a life-cycle assessment.</li>
          <li><strong>Steady state only.</strong> No start-up, turndown, dynamics, control or catalyst deactivation. AmCraX is not a digital twin of any plant.</li>
          <li><strong>The baseline product is not fuel-cell grade.</strong> Its purity, set by the assumed PSA split, is <Value v={k?.h2_purity_mole_frac == null ? null : k.h2_purity_mole_frac * 100} unit="mol% H2" digits={3} source={i?.source} showSource={false} />, above the 300 ppm nitrogen limit for vehicles in ISO 14687 <Cite k="iso2019hydrogen" />, and NH<sub>3</sub> polishing to 0.1 ppm is not modelled.</li>
          <li><strong>Validation is partial.</strong> {nAll !== null && nFail !== null && nFs !== null && nKin !== null ? <>{nFail} of {nAll} checks in the validation matrix fail. {nFs} of them are flowsheet cross-checks between Aspen Plus and the Python model, which use different property models in the feed section; they measure that model-form difference in both directions and are not evidence that either model is the weaker one. The other {nKin} are kinetics reproductions. </> : null}Like-for-like equilibrium, the primary flowsheet quantities and several independent physics checks agree. All of it is on the <Link to="/research">research page</Link>. There is no plant data.</li>
          <li><strong>This website runs no Aspen Plus.</strong> It displays stored results. Only the equilibrium calculator computes anything in your browser, and it is labelled.</li>
        </ul>
        <Callout kind="warn" title="Do not design a plant with this.">Use the platform to understand trends and trade-offs, not to size equipment or to quote costs.</Callout>
      </Section>

      <Section id="ack" title="Acknowledgements">
        <div className="two-col">
          <div className="prose">
            <h3>Research</h3>
            <p>The models stand on published work: the process-simulation and techno-economic studies, catalyst reviews and kinetic papers listed in the <Link to={{ pathname: '/research', hash: '#references' }}>reference list</Link>. Every parameter taken from a paper is cited to its page in the technical report.</p>
          </div>
          <div>
            <h3>Software</h3>
            <ul className="plain-list">
              {SOFTWARE.map(([name, url, what]) => <li key={name}><ExtLink href={url}>{name}</ExtLink> <span className="muted">- {what}</span></li>)}
            </ul>
          </div>
        </div>
      </Section>

      <Section id="licence" alt title="Licence">
        <p className="prose-p">AmCraX is released under the <ExtLink href={`${GITHUB_URL}/blob/main/LICENSE`}>MIT licence</ExtLink>. Third-party software and data keep their own licences; Aspen Plus is commercial software and is not distributed with AmCraX. Aspen Plus is a trademark of Aspen Technology, Inc.</p>
      </Section>
    </>
  )
}
