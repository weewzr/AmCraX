import { useMemo, useState } from 'react'
import type { DataRow } from '../../api/sensitivity'
import type { DataSource } from '../../api/types'
import { SourceBadge } from '../../components/ui'
import { fmt } from '../../data/format'
import { axisLabel, buildGrid, heatFraction, INPUT_KEYS, numericColumns, varyingInputs } from './shape'

const Z_PREF = ['nh3_conversion', 'h2_product_kg_h', 'total_external_heating_kW', 'specific_heat_demand_kWh_per_kgH2', 'lhv_efficiency']

/** Two-variable study (e.g. tp_map) as a grid of value labels; colour = value, non-converged cells hatched. */
export function HeatMap({ rows, columns, source }: { rows: DataRow[]; columns: string[]; source: DataSource }) {
  const vary = useMemo(() => varyingInputs(columns, rows), [columns, rows])
  const zs = useMemo(() => numericColumns(columns, rows).filter((c) => !INPUT_KEYS.includes(c)), [columns, rows])
  const [z, setZ] = useState<string>(() => Z_PREF.find((k) => zs.includes(k)) ?? zs[0] ?? '')
  const xKey = vary.includes('reactor_temperature_C') ? 'reactor_temperature_C' : vary[0]
  const yKey = vary.includes('reactor_pressure_bar') ? 'reactor_pressure_bar' : vary.find((k) => k !== xKey) ?? vary[0]
  const g = useMemo(() => (xKey && yKey && z ? buildGrid(rows, columns, xKey, yKey, z) : null), [rows, columns, xKey, yKey, z])
  if (!g || !xKey || !yKey) return null
  const nc = [...g.cell.values()].filter((c) => !c.converged).length
  const d = /conversion|yield|efficiency|purity/.test(z) ? 4 : 1
  return (
    <div className="card">
      <div className="section-h"><h2>Heat map: {axisLabel(z)} <SourceBadge source={source} /></h2>
        <label className="field">KPI<select value={z} onChange={(e) => setZ(e.target.value)}>{zs.map((k) => <option key={k} value={k}>{axisLabel(k)}</option>)}</select></label>
      </div>
      <p className="muted">Columns: {axisLabel(xKey)}; rows: {axisLabel(yKey)}. Every cell is one simulation run{nc ? `; ${nc} non-converged cell(s) are hatched and excluded from the colour scale` : ''}. Missing cells were not run.</p>
      <div className="heat-grid" style={{ gridTemplateColumns: `90px repeat(${g.xs.length}, minmax(64px, 1fr))` }} role="table" aria-label={`Heat map of ${z}`}>
        <div className="heat-head" role="columnheader">{yKey.replace('reactor_', '')} \ {xKey.replace('reactor_', '')}</div>
        {g.xs.map((x) => <div key={x} className="heat-head" role="columnheader">{x}</div>)}
        {[...g.ys].reverse().map((y) => (
          <div key={y} style={{ display: 'contents' }} role="row">
            <div className="heat-head" role="rowheader">{y}</div>
            {g.xs.map((x) => {
              const c = g.cell.get(`${x}|${y}`)
              if (!c) return <div key={x} className="heat-cell nc" role="cell" title="not run">-</div>
              if (!c.converged || c.v === null) return <div key={x} className="heat-cell nc" role="cell" title={c.converged ? 'value n/a' : 'not converged'}>{c.converged ? 'n/a' : 'n/c'}</div>
              const f = heatFraction(c.v, g.min, g.max)
              return <div key={x} className="heat-cell" role="cell" title={`${axisLabel(xKey)} ${x}, ${axisLabel(yKey)} ${y}: ${c.v}`}
                style={{ background: `color-mix(in srgb, var(--primary) ${Math.round(8 + f * 52)}%, var(--surface-2))` }}>{fmt(c.v, d)}</div>
            })}
          </div>
        ))}
      </div>
      <div className="heat-legend" style={{ marginTop: 8 }}>{fmt(g.min, d)}<i aria-hidden="true" />{fmt(g.max, d)} {axisLabel(z)}</div>
    </div>
  )
}
