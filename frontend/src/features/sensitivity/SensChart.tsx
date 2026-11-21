import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DataSource } from '../../api/types'
import { SourceBadge } from '../../components/ui'

export interface SensSeries { key: string; label: string; color: string; dots: boolean; dashed?: boolean; source: DataSource }
const axisProps = { stroke: 'var(--muted)', tick: { fill: 'var(--muted)', fontSize: 12 } }

export function SensChart(p: {
  title: string; xLabel: string; yLabel: string; data: Record<string, number | null>[]; series: SensSeries[]
  baseline?: { x: number; y: number | null; label: string } | null
}) {
  const bl = p.baseline
  return (
    <figure className="card chart-card" aria-label={p.title}>
      <figcaption><span>{p.title}</span></figcaption>
      <div className="chart-box" role="img" aria-label={`${p.title}: ${p.yLabel} against ${p.xLabel}`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={p.data} margin={{ top: 8, right: 16, bottom: 22, left: 8 }}>
            <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
            <XAxis type="number" dataKey="x" domain={['auto', 'auto']} {...axisProps} label={{ value: p.xLabel, position: 'insideBottom', offset: -12, fill: 'var(--muted)' }} />
            <YAxis type="number" domain={['auto', 'auto']} {...axisProps} width={64} label={{ value: p.yLabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
            <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }} formatter={(v) => (typeof v === 'number' ? Number(v.toPrecision(6)) : String(v ?? 'n/a'))} />
            {bl ? <ReferenceLine x={bl.x} stroke="var(--muted)" strokeDasharray="4 4" /> : null}
            {p.series.map((s) => (
              <Line key={s.key} dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? '6 4' : undefined}
                dot={s.dots ? { r: 3.5, fill: s.color, stroke: s.color } : false} connectNulls isAnimationActive={false} />
            ))}
            {bl && bl.y !== null ? <ReferenceDot x={bl.x} y={bl.y} r={7} fill="none" stroke="var(--accent)" strokeWidth={2.5} ifOverflow="visible" /> : null}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="series-src">
        {p.series.map((s) => <span key={s.key} className="series-chip"><i style={{ background: s.color }} aria-hidden="true" />{s.label} <SourceBadge source={s.source} /></span>)}
        {bl ? <span className="series-chip"><i style={{ background: 'transparent', border: '2px solid var(--accent)', borderRadius: 999 }} aria-hidden="true" />{bl.label}</span> : null}
      </div>
    </figure>
  )
}
