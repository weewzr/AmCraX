import type { BlockResult, DataSource, FlowsheetBlock, FlowsheetStream, StreamResult } from '../api/types'
import { SourceBadge, StatusPill, Value } from '../components/ui'
import { NA } from '../data/format'

export type Selection = { kind: 'block'; id: string } | { kind: 'stream'; id: string } | null

interface Common { source: DataSource | null; converged: boolean | null; onClose: () => void }

function Header({ title, subtitle, source, converged, onClose }: Common & { title: string; subtitle: string }) {
  return (
    <div className="panel-head">
      <div>
        <div className="panel-title">{title}</div>
        <div className="muted">{subtitle}</div>
      </div>
      <button type="button" className="btn btn-sm" onClick={onClose} aria-label="Close panel (Esc)">Close</button>
      <div className="panel-badges">
        <SourceBadge source={source} />
        {converged === null ? <StatusPill kind="neutral">No result</StatusPill> : converged ? <StatusPill kind="ok">Converged</StatusPill> : <StatusPill kind="error">Not converged</StatusPill>}
      </div>
    </div>
  )
}

export function BlockPanel(p: Common & { block: FlowsheetBlock; result: BlockResult | null }) {
  const { block, result, source } = p
  return (
    <aside className="panel" aria-label={`Equipment ${block.id}`}>
      <Header {...p} title={`${block.id} - ${block.name}`} subtitle={`Aspen block type: ${block.aspen_type}`} />
      {block.pfd.symbol === 'psa' && <p><span className="pchip pchip-ro">reduced-order model</span> <span className="muted">material balance with specified recovery, not a designed PSA</span></p>}
      <p className="role">{block.role}</p>
      <table className="pfd-kv">
        <tbody>
          <tr><th>Aspen block type</th><td>{block.aspen_type}{result && result.block_type && result.block_type !== block.aspen_type ? ` (result reports ${result.block_type})` : ''}</td></tr>
          <tr><th>Section</th><td>{block.section}</td></tr>
          <tr><th>Block status</th><td>{typeof result?.details?.aspen_status === 'string' ? result.details.aspen_status : NA}</td></tr>
          <tr><th>Duty (+ = heat added)</th><td><Value v={result?.duty_kW} unit="kW" source={source} /></td></tr>
          <tr><th>Shaft power</th><td><Value v={result?.power_kW} unit="kW" source={source} /></td></tr>
          <tr><th>Outlet temperature</th><td><Value v={result?.outlet_temperature_C} unit={'\u00B0C'} source={source} /></td></tr>
          <tr><th>Outlet pressure</th><td><Value v={result?.outlet_pressure_bar} unit="bar" source={source} /></td></tr>
        </tbody>
      </table>
      <h3>Details</h3>
      {result && Object.keys(result.details).length ? (
        <table className="pfd-kv">
          <tbody>
            {Object.entries(result.details).map(([k, v]) => (
              <tr key={k}><th>{k}</th><td>{typeof v === 'number' ? <Value v={v} source={source} /> : v === null ? NA : v}</td></tr>
            ))}
          </tbody>
        </table>
      ) : <p className="muted">No additional block details in this result.</p>}
    </aside>
  )
}

export function StreamPanel(p: Common & { stream: FlowsheetStream; result: StreamResult | null; destLabel: string | null }) {
  const { stream, result: r, source } = p
  const comps = r ? Array.from(new Set([...Object.keys(r.mole_frac), ...Object.keys(r.mass_frac), ...Object.keys(r.component_mole_flow_kmol_h)])) : []
  return (
    <aside className="panel" aria-label={`Stream ${stream.id}`}>
      <Header {...p} title={`${stream.id} - ${stream.name}`} subtitle={`${stream.from ?? 'feed boundary'} \u2192 ${p.destLabel ?? 'product boundary'}`} />
      <table className="pfd-kv">
        <tbody>
          <tr><th>Temperature</th><td><Value v={r?.temperature_C} unit={'\u00B0C'} source={source} /></td></tr>
          <tr><th>Pressure</th><td><Value v={r?.pressure_bar} unit="bar" source={source} /></td></tr>
          <tr><th>Vapour fraction</th><td><Value v={r?.vapor_fraction} source={source} digits={3} /></td></tr>
          <tr><th>Phase</th><td>{r?.phase ?? NA}</td></tr>
          <tr><th>Molar flow</th><td><Value v={r?.mole_flow_kmol_h} unit="kmol/h" source={source} /></td></tr>
          <tr><th>Mass flow</th><td><Value v={r?.mass_flow_kg_h} unit="kg/h" source={source} /></td></tr>
          <tr><th>Enthalpy flow</th><td><Value v={r?.enthalpy_flow_kW} unit="kW" source={source} /></td></tr>
        </tbody>
      </table>
      <h3>Composition</h3>
      {comps.length ? (
        <>
          <div className="compbar" role="img" aria-label={'Mole fraction bar: ' + comps.map((c) => `${c} ${((r?.mole_frac[c] ?? 0) * 100).toFixed(1)}%`).join(', ')}>
            {comps.map((c) => (<span key={c} className={`seg seg-${c}`} style={{ width: `${(r?.mole_frac[c] ?? 0) * 100}%` }} title={c} />))}
          </div>
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Composition table">
            <table className="data">
              <thead><tr><th>Comp.</th><th className="r">y [mol/mol]</th><th className="r">w [kg/kg]</th><th className="r">n [kmol/h]</th></tr></thead>
              <tbody>
                {comps.map((c) => (
                  <tr key={c}>
                    <td><span className={`dot seg-${c}`} aria-hidden="true" /> {c}</td>
                    <td className="r"><Value v={r?.mole_frac[c]} digits={4} source={source} showSource={false} /></td>
                    <td className="r"><Value v={r?.mass_frac[c]} digits={4} source={source} showSource={false} /></td>
                    <td className="r"><Value v={r?.component_mole_flow_kmol_h[c]} digits={2} source={source} showSource={false} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : <p className="muted">No composition available for this stream (n/a).</p>}
    </aside>
  )
}

