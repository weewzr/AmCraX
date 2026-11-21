import { exportUrl } from '../../api/simulation'
import type { BlockResult, SimulationResult, StreamResult } from '../../api/types'
import { DataTable, type Column } from '../../components/DataTable'
import { KpiTile, SourceBadge, StatusPill, Value } from '../../components/ui'
import { fmt } from '../../data/format'
import { useLive } from '../common/Notice'
import { KPI_DEFS } from './kpis'

const COMPS = ['NH3', 'H2', 'N2', 'H2O', 'O2']

export function Results({ c }: { c: SimulationResult }) {
  const live = useLive()
  const src = c.source
  const s = c.status
  const streams = Object.values(c.streams)
  const blocks = Object.values(c.blocks)
  const sCols: Column<StreamResult>[] = [
    { key: 'id', label: 'Stream' },
    { key: 'temperature_C', label: 'T', unit: 'degC', align: 'right', render: (r) => <Value v={r.temperature_C} digits={1} source={src} showSource={false} />, csv: (r) => String(r.temperature_C ?? '') },
    { key: 'pressure_bar', label: 'P', unit: 'bar', align: 'right', render: (r) => <Value v={r.pressure_bar} digits={2} source={src} showSource={false} />, csv: (r) => String(r.pressure_bar ?? '') },
    { key: 'vapor_fraction', label: 'Vapour fraction', align: 'right', render: (r) => <Value v={r.vapor_fraction} digits={3} source={src} showSource={false} />, csv: (r) => String(r.vapor_fraction ?? '') },
    { key: 'mole_flow_kmol_h', label: 'Mole flow', unit: 'kmol/h', align: 'right', render: (r) => <Value v={r.mole_flow_kmol_h} digits={2} source={src} showSource={false} />, csv: (r) => String(r.mole_flow_kmol_h ?? '') },
    { key: 'mass_flow_kg_h', label: 'Mass flow', unit: 'kg/h', align: 'right', render: (r) => <Value v={r.mass_flow_kg_h} digits={1} source={src} showSource={false} />, csv: (r) => String(r.mass_flow_kg_h ?? '') },
    ...COMPS.map((k): Column<StreamResult> => ({
      key: `y_${k}`, label: `y ${k}`, unit: 'mole frac', align: 'right',
      render: (r) => <Value v={r.mole_frac[k] ?? null} digits={4} source={src} showSource={false} />, csv: (r) => String(r.mole_frac[k] ?? ''),
    })),
  ]
  const bCols: Column<BlockResult>[] = [
    { key: 'id', label: 'Block' }, { key: 'block_type', label: 'Type' },
    { key: 'duty_kW', label: 'Duty', unit: 'kW', align: 'right', render: (r) => <Value v={r.duty_kW} digits={1} source={src} showSource={false} />, csv: (r) => String(r.duty_kW ?? '') },
    { key: 'power_kW', label: 'Power', unit: 'kW', align: 'right', render: (r) => <Value v={r.power_kW} digits={2} source={src} showSource={false} />, csv: (r) => String(r.power_kW ?? '') },
    { key: 'outlet_temperature_C', label: 'Outlet T', unit: 'degC', align: 'right', render: (r) => <Value v={r.outlet_temperature_C} digits={1} source={src} showSource={false} />, csv: (r) => String(r.outlet_temperature_C ?? '') },
    { key: 'outlet_pressure_bar', label: 'Outlet P', unit: 'bar', align: 'right', render: (r) => <Value v={r.outlet_pressure_bar} digits={2} source={src} showSource={false} />, csv: (r) => String(r.outlet_pressure_bar ?? '') },
  ]
  const b = c.balances
  const bal: [string, number | null, string, number][] = [
    ['Mass in', b.mass_in_kg_h, 'kg/h', 2], ['Mass out', b.mass_out_kg_h, 'kg/h', 2], ['Mass closure (relative)', b.mass_closure_rel, '-', 9],
    ['N atoms in', b.n_atoms_in_kmol_h, 'kmol/h', 3], ['N atoms out', b.n_atoms_out_kmol_h, 'kmol/h', 3],
    ['H atoms in', b.h_atoms_in_kmol_h, 'kmol/h', 3], ['H atoms out', b.h_atoms_out_kmol_h, 'kmol/h', 3],
    ['Energy in', b.energy_in_kW, 'kW', 1], ['Energy out', b.energy_out_kW, 'kW', 1], ['Energy closure (relative)', b.energy_closure_rel, '-', 9],
  ]
  return (
    <div className="page-block">
      <div className="card">
        <div className="section-h"><h2>Case <code>{c.case_id}</code> <SourceBadge source={src} /></h2>
          <span className="export-row">
            {(['json', 'csv', 'xlsx'] as const).map((f) => (
              live ? <a key={f} className="btn btn-sm" href={exportUrl(c.case_id, f)} download>Export {f.toUpperCase()}</a>
                : <span key={f} className="btn btn-sm is-disabled" title="Export needs the live API">Export {f.toUpperCase()}</span>))}
          </span>
        </div>
        <p>
          {s.converged ? <StatusPill kind="ok">converged</StatusPill> : <StatusPill kind="error">NOT converged</StatusPill>}{' '}
          {s.has_errors ? <StatusPill kind="error">errors</StatusPill> : null}{' '}
          {s.has_warnings ? <StatusPill kind="warn">warnings</StatusPill> : <StatusPill kind="neutral">no warnings</StatusPill>}{' '}
          <span className="muted">engine time <Value v={s.engine_time_s} unit="s" digits={1} source={src} showSource={false} /> - created {c.created_utc}{c.model_file ? ` - model ${c.model_file}` : ''}</span>
        </p>
        {s.messages.length ? <details open={!s.converged || s.has_errors}><summary>Run messages ({s.messages.length})</summary><ul className="msg-list">{s.messages.map((m, i) => <li key={i}>{m}</li>)}</ul></details>
          : <p className="muted">No engine messages.</p>}
        {c.notes.length ? <details><summary>Notes ({c.notes.length})</summary><ul className="msg-list">{c.notes.map((m, i) => <li key={i}>{m}</li>)}</ul></details> : null}
      </div>
      <div className="kpi-grid">
        {KPI_DEFS.filter((d) => ['nh3_conversion', 'h2_product_kg_h', 'h2_purity_mole_frac', 'h2_yield_overall', 'total_external_heating_kW', 'recovered_heat_kW', 'specific_heat_demand_kWh_per_kgH2', 'lhv_efficiency'].includes(d.key)).map((d) => (
          <KpiTile key={d.key} label={d.label} v={c.kpis[d.key]} unit={d.unit === '-' ? undefined : d.unit} digits={d.digits} source={src} />))}
      </div>
      <details className="card"><summary>All KPIs ({KPI_DEFS.length})</summary>
        <dl className="kv" style={{ marginTop: 8 }}>{KPI_DEFS.map((d) => (<div key={d.key} style={{ display: 'contents' }}><dt>{d.label}</dt><dd><Value v={c.kpis[d.key]} unit={d.unit === '-' ? undefined : d.unit} digits={d.digits} source={src} showSource={false} /></dd></div>))}</dl></details>
      <DataTable columns={sCols} rows={streams} caption={`Streams of ${c.case_id} (${streams.length})`} filename={`streams_${c.case_id}.csv`} />
      <DataTable columns={bCols} rows={blocks} caption={`Blocks of ${c.case_id} (${blocks.length}); duty > 0 = heat added to the process`} filename={`blocks_${c.case_id}.csv`} />
      <div className="card"><h3 style={{ marginTop: 0 }}>Balance closures <SourceBadge source={src} /></h3>
        <dl className="kv">{bal.map(([l, v, u, d]) => (<div key={l} style={{ display: 'contents' }}><dt>{l}</dt><dd>{v === null ? 'n/a' : <>{d >= 9 ? v.toExponential(2) : fmt(v, d)} <span className="unit">{u === '-' ? '' : u}</span></>}</dd></div>))}</dl>
      </div>
    </div>
  )
}
