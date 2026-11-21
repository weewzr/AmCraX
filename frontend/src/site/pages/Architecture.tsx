import { Link } from 'react-router-dom'
import { GITHUB_URL } from '../../api/url'
import { SourceBadge } from '../../components/ui'
import { platformPath } from '../routes'
import { ArchitectureDiagram } from '../ArchitectureDiagram'
import { Callout, ExtLink, PageHero, Section } from '../ui'

export default function Architecture() {
  return (
    <>
      <PageHero
        eyebrow="Section 6 - Software architecture"
        title="How the pieces fit together"
        lead="Aspen Plus does the rigorous flowsheet calculation. Python drives it, cross-checks it and stores the results. A web app reads the stored results, locally through an API or, on this site, from a static copy."
      />
      <Section id="diagram" title="Architecture" intro="The path of one number: from the Aspen Plus solver, through the results store, to a chart in your browser.">
        <ArchitectureDiagram />
      </Section>

      <Section id="layers" alt title="The layers">
        <div className="grid-3">
          <article className="card tile"><h3>Aspen Plus V15 and COM automation</h3><p>A generated input file defines the flowsheet. The <code>amcrax.aspen</code> package starts Aspen through COM, changes inputs, runs the engine synchronously and extracts every stream and block into a typed result.</p></article>
          <article className="card tile"><h3>Independent Python models</h3><p>Thermochemistry and equilibrium (NASA-7), a Python mirror of the flowsheet, pinch analysis, kinetics and plug-flow reactor, economics, carbon accounting, separation and optimisation. They run without Aspen.</p></article>
          <article className="card tile"><h3>Results store</h3><p>JSON per case and CSV per study under <code>results/</code>. Every value carries a provenance label, so the interface can show which model produced it.</p></article>
          <article className="card tile"><h3>FastAPI back end</h3><p>Serves cases, datasets and figures, runs the Python engine on demand and queues Aspen jobs in an isolated worker process. It never starts Aspen unless asked to.</p></article>
          <article className="card tile"><h3>React dashboard</h3><p>React, TypeScript, React Flow for the process flow diagram and Recharts for charts. Eleven pages; plain CSS, no UI kit.</p></article>
          <article className="card tile"><h3>Static export</h3><p>A script copies results, figures and screenshots into a committed snapshot. The same app, built with a different base path, reads it with no server at all.</p></article>
        </div>
      </Section>

      <Section id="modes" title="Two execution modes" intro="The header of every page says which one is active, and the two are never mixed.">
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Comparison of the public static site and the local platform">
          <table className="data simple">
            <thead><tr><th scope="col">&nbsp;</th><th scope="col">Public static site (this website)</th><th scope="col">Local platform</th></tr></thead>
            <tbody>
              <tr><th scope="row">Data source</th><td>Committed snapshot of stored results, mode <strong>SNAPSHOT</strong></td><td>FastAPI results store, mode <strong>LIVE</strong> (snapshot or demo data if the API is down)</td></tr>
              <tr><th scope="row">Aspen Plus runs</th><td>None. Results were computed offline on a licensed machine.</td><td>New cases, sweeps and optimisation with a licensed Aspen Plus V15; the Python engine without one.</td></tr>
              <tr><th scope="row">Live calculation</th><td>The ideal-gas equilibrium calculator, in your browser, labelled as such</td><td>Python engine, sweeps, kinetic plug-flow runs, parametric economics and carbon queries</td></tr>
              <tr><th scope="row">Server</th><td>None; static files on GitHub Pages</td><td>Uvicorn (FastAPI) plus the Vite dev server or a static build</td></tr>
              <tr><th scope="row">Updated by</th><td>Re-exporting the snapshot and pushing</td><td>Running the studies and saving to the results store</td></tr>
            </tbody>
          </table>
        </div>
        <p className="prose-p">
          The platform's pages are under <Link to={platformPath('/')}>/platform</Link>. On this site every request goes to files bundled with the page, none to an API; the build mode that guarantees it sets the base path and switches the API off at build time.
        </p>
      </Section>

      <Section id="provenance" alt title="Provenance labels" intro="Every number in the app and on this site is tagged with the model that produced it.">
        <dl className="prov-list">
          <div><dt><SourceBadge source="aspen_plus_v15" /></dt><dd>Stored result of an Aspen Plus V15 run (flowsheet, sweeps, RGibbs grid, optimisation re-verification).</dd></div>
          <div><dt><SourceBadge source="python_model" /></dt><dd>Result of the independent Python models, often computed from an Aspen result (economics, carbon intensity, optimisation, kinetics).</dd></div>
          <div><dt><SourceBadge source="literature" /></dt><dd>A value from a cited publication, used as an input or a benchmark and never presented as an AmCraX result.</dd></div>
          <div><dt><SourceBadge source="assumption" /></dt><dd>An engineering assumption of the project, such as the PSA recovery of the baseline.</dd></div>
          <div><dt><span className="badge badge-browser">in your browser</span></dt><dd>Calculated in this page by JavaScript (the equilibrium calculator). Not an Aspen result.</dd></div>
        </dl>
        <Callout kind="note" title="Source code.">All of it is in the <ExtLink href={GITHUB_URL}>GitHub repository</ExtLink>: <code>backend/amcrax</code> (Python), <code>frontend</code> (this app), <code>aspen</code> (models and automation scripts) and <code>results</code>.</Callout>
      </Section>
    </>
  )
}
