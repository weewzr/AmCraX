import type { SimulationResult } from '../../api/types'
import { SourceBadge, Value } from '../../components/ui'
import { Notice } from '../common/Notice'

const COMPS = ['NH3', 'H2', 'N2', 'H2O'] as const

/** Cracker of the active case: inlet/outlet composition, conversion, duty. */
export function ActiveReactor({ active }: { active: SimulationResult | null }) {
  if (!active) return <Notice kind="warn" title="No active case.">No simulation result is loaded.</Notice>
  const src = active.source
  const inlet = active.streams.S4 ?? null
  const outlet = active.streams.S5 ?? null
  const blk = active.blocks.CRACKER ?? null
  const k = active.kpis
  return (
    <div className="card">
      <div className="section-h">
        <h3 style={{ margin: 0 }}>Cracker (RGibbs) of case <code>{active.case_id}</code> <SourceBadge source={src} /></h3>
        <span className="muted">Approach: equilibrium reactor (RGibbs) - no catalyst volume implied.</span>
      </div>
      <div className="kpi-grid" style={{ marginTop: 10 }}>
        <div className="kpi card"><div className="kpi-label">NH3 conversion</div><Value v={k.nh3_conversion === null ? null : k.nh3_conversion * 100} unit="%" digits={2} source={src} /></div>
        <div className="kpi card"><div className="kpi-label">Reactor temperature</div><Value v={active.inputs.reactor_temperature_C} unit="degC" source={src} /></div>
        <div className="kpi card"><div className="kpi-label">Reactor pressure</div><Value v={active.inputs.reactor_pressure_bar} unit="bar" source={src} /></div>
        <div className="kpi card"><div className="kpi-label">Reactor duty</div><Value v={blk?.duty_kW ?? k.reactor_duty_kW} unit="kW" digits={1} source={src} /></div>
      </div>
      <div className="table-wrap" style={{ marginTop: 10 }}>
        <div className="table-scroll">
          <table className="data">
            <caption className="sr-only">Cracker inlet (S4) and outlet (S5) composition</caption>
            <thead><tr><th scope="col">Stream</th><th scope="col" className="r">T [degC]</th><th scope="col" className="r">P [bar]</th><th scope="col" className="r">Flow [kmol/h]</th>
              {COMPS.map((c) => <th key={c} scope="col" className="r">y {c} [mol/mol]</th>)}</tr></thead>
            <tbody>
              {([['S4 cracker inlet', inlet], ['S5 cracker outlet', outlet]] as const).map(([label, s]) => (
                <tr key={label}>
                  <td>{label}</td>
                  <td className="r"><Value v={s?.temperature_C} source={src} showSource={false} /></td>
                  <td className="r"><Value v={s?.pressure_bar} source={src} showSource={false} /></td>
                  <td className="r"><Value v={s?.mole_flow_kmol_h} digits={2} source={src} showSource={false} /></td>
                  {COMPS.map((c) => <td key={c} className="r"><Value v={s ? (s.mole_frac[c] ?? 0) : null} digits={4} source={src} showSource={false} /></td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="muted">Values are Aspen Plus results of the active case ({src}); change the case in the header selector.</p>
    </div>
  )
}
