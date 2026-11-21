import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DataSource } from '../../api/types'
import { SourceBadge } from '../../components/ui'

export interface XYSeries {
  key: string
  label: string
  color: string
  /** 'line' = python/model curve, 'marker' = discrete points (e.g. Aspen RGibbs) */
  kind: 'line' | 'marker'
  /** 'browser' = calculated in the visitor's browser (public site equilibrium calculator), not a stored result */
  source: DataSource | 'browser'
  dashed?: boolean
}
export type XYRow = Record<string, number | null>

const axisProps = { stroke: 'var(--muted)', tick: { fill: 'var(--muted)', fontSize: 12 } }

/** Numeric-x line/marker chart with one provenance badge per series (rendered under the chart). */
export function XYChart(p: {
  title: string; description: string; data: XYRow[]; xKey: string; xLabel: string; yLabel: string; series: XYSeries[]
  yDomain?: [number | 'auto', number | 'auto']; height?: number; hline?: { y: number; label: string }; yLog?: boolean; xDomain?: [number | 'auto', number | 'auto']
}) {
  const sources = p.series.map((s) => ({ s, k: s.key }))
  return (
    <figure className="card chart-card" aria-label={p.title}>
      <figcaption><span>{p.title}</span></figcaption>
      <div className="chart-box" style={p.height ? { height: p.height } : undefined} role="img" aria-label={p.description}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={p.data} margin={{ top: 8, right: 16, bottom: 22, left: 8 }}>
            <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
            <XAxis type="number" dataKey={p.xKey} domain={p.xDomain ?? ['auto', 'auto']} {...axisProps}
              label={{ value: p.xLabel, position: 'insideBottom', offset: -12, fill: 'var(--muted)' }} />
            <YAxis type="number" scale={p.yLog ? 'log' : 'auto'} allowDataOverflow={p.yLog} domain={p.yDomain ?? ['auto', 'auto']} {...axisProps}
              label={{ value: p.yLabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)', style: { textAnchor: 'middle' } }} />
            <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
              formatter={(v) => (typeof v === 'number' ? Number(v.toPrecision(5)) : String(v ?? 'n/a'))} />
            {p.hline ? <ReferenceLine y={p.hline.y} stroke="var(--muted)" strokeDasharray="4 4" label={{ value: p.hline.label, fill: 'var(--muted)', fontSize: 11 }} /> : null}
            {p.series.map((s) => s.kind === 'line' ? (
              <Line key={s.key} dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? '6 4' : undefined}
                dot={false} connectNulls isAnimationActive={false} />
            ) : (
              <Line key={s.key} dataKey={s.key} name={s.label} stroke="none" isAnimationActive={false} connectNulls={false}
                dot={{ r: 4, fill: s.color, stroke: s.color }} activeDot={{ r: 5 }} legendType="diamond" />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="sr-only">{p.description}</p>
      <div className="series-src">
        {sources.map(({ s, k }) => (
          <span key={k} className="series-chip"><i style={{ background: s.color }} aria-hidden="true" />{s.label} {s.source === 'browser' ? <span className="badge badge-browser" title="Calculated by JavaScript in this page">in your browser</span> : <SourceBadge source={s.source} />}</span>
        ))}
      </div>
    </figure>
  )
}
