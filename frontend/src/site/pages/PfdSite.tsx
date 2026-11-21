import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../../data/DataContext'
import { PfdExplorer } from '../../pages/PfdPage'
import { platformPath } from '../routes'
import { Callout, PageHero, Section } from '../ui'

export default function PfdSite() {
  const { cases } = useData()
  const [hi, setHi] = useState(true)
  const caseId = hi ? 'baseline' : 'baseline_no_hi'
  const hasNoHi = cases.some((c) => c.case_id === 'baseline_no_hi')
  const cur = cases.find((c) => c.case_id === caseId)
  const cond = cur ? `, ${cur.inputs.reactor_temperature_C} \u00B0C, ${cur.inputs.reactor_pressure_bar} bar` : ''
  return (
    <>
      <PageHero
        eyebrow="Section 3 - Interactive process flow diagram"
        title="The flowsheet, as an interactive diagram"
        lead="Click any piece of equipment or any stream. Values come from the stored Aspen Plus V15 run of the baseline case; nothing on this page is recalculated."
      />
      <Section id="diagram" title="Baseline flowsheet" intro="Liquid ammonia is pumped, vaporised, preheated against the hot product, cracked, cooled and purified; the tail gas is burned to recover heat.">
        <div className="pfd-site-controls card">
          <div className="seg" role="group" aria-label="Heat integration">
            <button type="button" aria-pressed={hi} onClick={() => setHi(true)}>With feed/effluent exchanger</button>
            <button type="button" aria-pressed={!hi} onClick={() => setHi(false)} disabled={!hasNoHi}>Without exchanger</button>
          </div>
          <span className="muted">Case <code>{caseId}</code>{cond}, Aspen Plus V15 (pre-computed). Switching shows how the exchanger removes FEHE, S3 and S6 from the diagram.</span>
        </div>
        <PfdExplorer caseId={caseId} compact />
        <p className="pfd-cta">
          <Link to={platformPath('/pfd')} className="btn btn-primary">Open the full platform diagram</Link>
          <span className="muted"> with the case selector, all eleven dashboard pages and, on a local installation, live runs.</span>
        </p>
      </Section>
      <Section id="reading" alt title="How to read the diagram">
        <div className="grid-3">
          <article className="card tile"><h3>Equipment</h3><p>Each box shows the Aspen block tag, its type and its duty. A chip states where the numbers come from. Dashed lanes group the process sections.</p></article>
          <article className="card tile"><h3>Streams</h3><p>Line colour is the dominant component (or temperature); width grows with mass flow. The stream labels switch on temperature, pressure, flows and main composition.</p></article>
          <article className="card tile"><h3>Panels</h3><p>Selecting equipment or a stream opens a side panel with its role, conditions and composition. Esc closes it; the lists below the diagram work with the keyboard.</p></article>
        </div>
        <Callout kind="note" title="Provenance.">Every value is an Aspen Plus V15 result stored in the snapshot. The reactor is an equilibrium (RGibbs) block and the PSA is a reduced-order splitter with an assumed hydrogen recovery.</Callout>
      </Section>
    </>
  )
}
