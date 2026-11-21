import '../features/common/features.css'
import { useData } from '../data/DataContext'
import { ModeGate } from '../features/common/Notice'
import { ActiveReactor } from '../features/reactor/ActiveReactor'
import { EquilibriumExplorer } from '../features/reactor/EquilibriumExplorer'
import { KineticsSection } from '../features/reactor/KineticsSection'
import { EquilibriumCalculator } from '../site/EquilibriumCalculator'

export default function ReactorPage() {
  const { mode, active, phase } = useData()
  const live = mode === 'LIVE'
  const readable = mode === 'LIVE' || mode === 'SNAPSHOT'
  return (
    <section className="page">
      <h1>Reactor Analysis</h1>
      <p className="lead">Thermodynamic equilibrium of 2 NH3 = N2 + 3 H2 from the independent Python model, overlaid with the Aspen Plus RGibbs results, the cracker of the active case, and the literature-based kinetic plug-flow model.</p>
      <ModeGate what="The equilibrium point calculator, arbitrary pressure / EOS grids and new plug-flow runs" />
      <h2>Equilibrium calculator (runs in your browser)</h2>
      <p className="muted">Closed-form ideal-gas equilibrium of pure NH3, calculated in this page at any temperature and pressure, with the stored Aspen RGibbs points. Works in every data mode, including the published static site.</p>
      <EquilibriumCalculator compact />
      <h2>Equilibrium explorer</h2>
      <EquilibriumExplorer live={live} readable={readable} />
      <h2>Reactor of the active case</h2>
      {phase === 'ready' ? <ActiveReactor active={active} /> : <p className="muted">Loading case ...</p>}
      <h2>Kinetics (reduced-order, literature rate laws)</h2>
      <p className="muted">Plug-flow results below are model-based and only valid inside each catalyst's stated validity range; they are not Aspen results and imply no catalyst design.</p>
      <KineticsSection live={live} readable={readable} />
    </section>
  )
}

