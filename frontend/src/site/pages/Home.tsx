import { Link } from 'react-router-dom'
import type { DataSource } from '../../api/types'
import { GITHUB_URL, IS_PAGES, withBase } from '../../api/url'
import { SourceBadge } from '../../components/ui'
import { fmt } from '../../data/format'
import { useData } from '../../data/DataContext'
import { EquilibriumCalculatorLazy } from '../EquilibriumCalculatorLazy'
import { countAspenRuns, exportDate, useJson, useValidationSummary, type DatasetIndexItem } from '../data'
import { REPORT_PDF, downloadUrl } from '../downloads'
import { NAV_GROUPS, platformPath, SITE_ROUTES } from '../routes'
import { Callout, ExtLink, Section } from '../ui'

const CARDS: { to: string; title: string; text: string }[] = [
  { to: '/why', title: 'Why ammonia cracking', text: 'Hydrogen is hard to move; ammonia carries 17.8 wt% of it. What the cracking reaction costs in heat, and why purification matters.' },
  { to: '/pfd', title: 'Process flow diagram', text: 'The flowsheet as an interactive diagram: click equipment or a stream for duties, conditions and composition.' },
  { to: '/methodology', title: 'Methodology', text: 'The Aspen Plus V15 model, how Python drives it through COM, the independent equilibrium and kinetic models, and every assumption.' },
  { to: '/results', title: 'Engineering results', text: 'Conversion and duties versus temperature, the temperature-pressure map, heat integration, optimisation, cost and carbon intensity.' },
  { to: '/architecture', title: 'Software architecture', text: 'How Aspen Plus, Python, FastAPI, React and the static export fit together, and the two ways to run the platform.' },
  { to: '/research', title: 'Research and validation', text: 'The validation matrix reported as it is, failures with their root causes, equilibrium parity with Aspen Plus and the reference list.' },
  { to: '/docs', title: 'Documentation and downloads', text: 'Technical report, pitch deck, validation documents and the repository documentation.' },
  { to: '/about', title: 'About and limits', text: 'Where the project comes from, who it builds on, and an explicit list of what AmCraX does not claim.' },
]

function Fact({ label, value, unit, source, note }: { label: string; value: string; unit: string; source: DataSource | null; note: string }) {
  return (
    <div className="fact">
      <p className="fact-label">{label}</p>
      <p className="fact-value"><span className="num">{value}</span> <span className="unit">{unit}</span></p>
      <p className="fact-note">{note}</p>
      <SourceBadge source={source} />
    </div>
  )
}

export default function Home() {
  const { cases, phase, mode, manifest } = useData()
  const base = cases.find((c) => c.case_id === 'baseline') ?? null
  const vs = useValidationSummary()
  const sensIndex = useJson<{ items: DatasetIndexItem[] }>('/api/data/sensitivity')
  const valIndex = useJson<{ items: DatasetIndexItem[] }>('/api/data/validation')
  const eqPoints = valIndex.phase === 'ready' ? (valIndex.data.items.find((d) => d.name === 'equilibrium_aspen_grid')?.rows ?? 0) : null
  const runs = sensIndex.phase === 'ready' && eqPoints !== null ? countAspenRuns(cases, sensIndex.data.items, eqPoints) : null
  const k = base?.kpis
  const na = 'n/a'
  const loading = phase === 'loading'
  const d = exportDate(manifest?.exported_utc)
  return (
    <>
      <section className="hero" aria-labelledby="hero-h">
        <div className="wrap hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Ammonia cracking simulation and optimisation platform</p>
            <h1 id="hero-h">Ammonia cracking, from the Aspen Plus flowsheet to an interactive dashboard.</h1>
            <p className="lead">
              AmCraX simulates a complete plant that turns liquid ammonia into hydrogen. A rigorous Aspen Plus V15 flowsheet, independent Python models and a
              React dashboard sit on the same stored results, and every number on screen carries the name of the model that produced it.
            </p>
            <div className="btn-row">
              <Link to={platformPath('/pfd')} className="btn btn-primary btn-lg">Open the platform</Link>
              <ExtLink href={GITHUB_URL} className="btn btn-lg">GitHub</ExtLink>
              {IS_PAGES
                ? <a href={downloadUrl(REPORT_PDF.file)} className="btn btn-lg" download>Technical report (PDF)</a>
                : <Link to="/docs" className="btn btn-lg">Technical report (PDF)</Link>}
            </div>
            <p className="hero-note muted">
              This website shows published results{d ? ` (exported ${d})` : ''} and runs no Aspen Plus. Live Aspen runs need the local platform.
            </p>
          </div>
          <figure className="hero-figure">
            <Link to={platformPath('/pfd')} aria-label="Open the interactive process flow diagram">
              <img src={withBase('/img/pfd_baseline.png')} width="1340" height="710" alt="Screenshot of the AmCraX interactive process flow diagram for the baseline case: feed pump, vaporiser, feed/effluent exchanger, trim heater, cracker, cooler, PSA and tail-gas burner with coloured streams." />
            </Link>
            <figcaption className="muted">Genuine screenshot of the platform's process flow diagram (baseline case{base ? `, ${base.inputs.reactor_temperature_C} \u00B0C, ${base.inputs.reactor_pressure_bar} bar` : ''}). The diagram is interactive: <Link to="/pfd">try it</Link>.</figcaption>
          </figure>
        </div>
      </section>

      <section className="facts-band" aria-labelledby="facts-h">
        <div className="wrap">
          <h2 id="facts-h" className="sr-only">Baseline case at a glance</h2>
          <div className="facts" role="list">
            <div role="listitem"><Fact label="NH3 conversion" value={k?.nh3_conversion != null ? fmt(k.nh3_conversion * 100, 2) : loading ? '...' : na} unit="%" source={base?.source ?? null} note={`${base ? `Baseline: ${base.inputs.reactor_temperature_C} \u00B0C, ${base.inputs.reactor_pressure_bar} bar, ` : ''}equilibrium (RGibbs) reactor`} /></div>
            <div role="listitem"><Fact label="H2 product" value={k?.h2_product_kg_h != null ? fmt(k.h2_product_kg_h, 1) : loading ? '...' : na} unit="kg/h" source={base?.source ?? null} note={`From ${base ? fmt(base.inputs.feed_total_kmol_h, 0) : na} kmol/h liquid ammonia, ${k?.h2_purity_mole_frac != null ? fmt(k.h2_purity_mole_frac * 100, 3) : na} mol% H2 (set by the assumed PSA split)`} /></div>
            <div role="listitem"><Fact label="LHV efficiency" value={k?.lhv_efficiency != null ? fmt(k.lhv_efficiency * 100, 1) : loading ? '...' : na} unit="%" source={base?.source ?? null} note="First-law upper bound: product H2 LHV over ammonia LHV, with feed/effluent heat recovery" /></div>
            <div role="listitem"><Fact label="Aspen Plus runs behind this site" value={runs ? fmt(runs.total, 0) : loading ? '...' : na} unit="runs" source={runs ? 'aspen_plus_v15' : null} note={runs ? `${runs.aspenCases} flowsheet cases, ${runs.sensitivityRuns} sensitivity runs, ${runs.equilibriumPoints} equilibrium points` : 'Count of stored Aspen cases, sweeps and equilibrium points'} /></div>
          </div>
          {mode === 'DEMO' ? <Callout kind="warn" title="Demonstration data.">No results snapshot is available, so the figures above are placeholders.</Callout> : null}
        </div>
      </section>

      <Section id="what" title="What AmCraX is" intro="Four layers that share one flowsheet definition, so a design change is one input value and cannot drift between the models.">
        <div className="grid-4">
          <article className="card tile"><h3>Aspen Plus V15 flowsheet</h3><p>Pump, vaporiser, feed/effluent exchanger, trim heater, an RGibbs cracker, cooler, a reduced-order hydrogen separator and a tail-gas burner, with Peng-Robinson properties.</p></article>
          <article className="card tile"><h3>Independent Python models</h3><p>Thermochemistry and equilibrium, a Python mirror of the flowsheet, pinch analysis, kinetics, economics, carbon intensity and optimisation: an independent cross-check of the main Aspen results.</p></article>
          <article className="card tile"><h3>FastAPI back end</h3><p>Runs cases, queues Aspen jobs in an isolated worker and serves results with a provenance label: Aspen Plus V15, Python model, literature or assumption.</p></article>
          <article className="card tile"><h3>React dashboard</h3><p>Eleven pages around an interactive React Flow diagram. The published site is the same app reading a stored snapshot.</p></article>
        </div>
      </Section>

      <Section id="try" alt title="Try the equilibrium: calculated in your browser" intro="Move the sliders. The curve is calculated here, live, for an ideal gas; the markers are Aspen Plus RGibbs results that were computed offline and stored.">
        <EquilibriumCalculatorLazy />
      </Section>

      <Section id="explore" title="Explore the project" intro={`${SITE_ROUTES.length} pages in ${NAV_GROUPS.length} groups. The top navigation reaches all of them; Ctrl + K searches them.`}>
        <ul className="card-grid" aria-label="Sections of the website">
          {CARDS.map((c) => (
            <li key={c.to}>
              <Link to={c.to} className="card link-card">
                <span className="link-card-num">{SITE_ROUTES.find((r) => r.path === c.to)?.section ?? ''}</span>
                <h3>{c.title}</h3>
                <p>{c.text}</p>
                <span className="link-card-go" aria-hidden="true">Read more</span>
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="modes" alt title="Two ways to run it" intro="The same app serves a public site and a local engineering platform; the header always says which one you are looking at.">
        <div className="grid-2s">
          <article className="card tile">
            <h3>Public static site (you are here)</h3>
            <p>Hosted on GitHub Pages. No server, no database, no Aspen Plus. Every page reads the committed snapshot of stored results and says so in the header. The equilibrium calculator is the only live calculation and is labelled as such.</p>
          </article>
          <article className="card tile">
            <h3>Local platform</h3>
            <p>Clone the repository, start the FastAPI back end and the dashboard. With a licensed Aspen Plus V15 installation the platform can also run new Aspen cases, sweeps and optimisations; without it, it runs the independent Python models.</p>
            <p><ExtLink href={`${GITHUB_URL}#readme`}>Setup instructions on GitHub</ExtLink></p>
          </article>
        </div>
      </Section>

      <Section id="limits" title="Read this before quoting a number">
        <Callout kind="warn" title="Preliminary engineering results.">
          The cracker is an equilibrium reactor; the hydrogen separator is a reduced-order splitter with an assumed recovery; costs are order-of-magnitude; carbon accounting is simplified;
          the baseline product is not fuel-cell grade. The complete list is on the <Link to="/about#limits">About page</Link>, and the validation record, including {vs.phase === 'ready' ? vs.data.by_status.fail : 'the'} failed checks, is on the <Link to="/research">Research page</Link>.
        </Callout>
      </Section>
    </>
  )
}
