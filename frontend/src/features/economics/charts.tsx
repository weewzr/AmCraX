import type { ReactNode } from 'react'
import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import type { DataSource } from '../../api/types'
import { SourceBadge } from '../../components/ui'

export const axisProps = { stroke: 'var(--muted)', tick: { fill: 'var(--muted)', fontSize: 12 } }
export const tipStyle = { background: 'var(--surface-2)', border: '1px solid var(--border)' }
export const grid = <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
export const SERIES_COLORS = ['var(--primary)', 'var(--accent)', 'var(--c-nh3)', 'var(--c-h2)', 'var(--c-n2)', 'var(--warn)', 'var(--c-heat)']
const num = (v: unknown) => (typeof v === 'number' ? Number(v.toPrecision(4)) : String(v ?? 'n/a'))

/** Card with title, provenance badge(s) and a text alternative. */
export function ChartFrame(p: { title: string; description: string; sources: (DataSource | null)[]; height?: number; note?: ReactNode; children: React.ReactElement }) {
  return (
    <figure className="card chart-card" aria-label={p.title}>
      <figcaption><span>{p.title}</span><span>{p.sources.map((s, i) => <SourceBadge key={i} source={s} />)}</span></figcaption>
      <div className="chart-box" style={p.height ? { height: p.height } : undefined} role="img" aria-label={p.description}>
        <ResponsiveContainer width="100%" height="100%">{p.children}</ResponsiveContainer>
      </div>
      <p className="sr-only">{p.description}</p>
      {p.note ? <p className="muted" style={{ margin: '6px 0 0', fontSize: 12 }}>{p.note}</p> : null}
    </figure>
  )
}

export interface BarSeries { key: string; label: string; color?: string }

/** Bars with optional stacking, optional horizontal reference lines (labelled as references by the caller). */
export function BarsChart(p: {
  data: Record<string, number | string | null>[]; xKey: string; series: BarSeries[]; stacked?: boolean; xLabel: string; yLabel: string
  refs?: { y: number; label: string }[]; height?: number
}) {
  return (
    <ComposedChart data={p.data} margin={{ top: 12, right: 24, bottom: 26, left: 8 }}>
      {grid}
      <XAxis dataKey={p.xKey} {...axisProps} label={{ value: p.xLabel, position: 'insideBottom', offset: -14, fill: 'var(--muted)' }} />
      <YAxis {...axisProps} label={{ value: p.yLabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
      <Tooltip contentStyle={tipStyle} formatter={(v) => num(v)} />
      <Legend verticalAlign="top" height={30} />
      {(p.refs ?? []).map((r, i) => <ReferenceLine key={r.label} y={r.y} stroke="var(--warn)" strokeDasharray="5 4" label={{ value: r.label, fill: 'var(--warn)', fontSize: 11, position: i % 2 ? 'insideBottomLeft' : 'insideTopLeft' }} />)}
      {p.series.map((s, i) => <Bar key={s.key} dataKey={s.key} name={s.label} stackId={p.stacked ? 's' : undefined} fill={s.color ?? SERIES_COLORS[i % SERIES_COLORS.length]} isAnimationActive={false} />)}
    </ComposedChart>
  )
}

/** Tornado: horizontal floating bars between the LCOH at the low and high end of each parameter. */
export function TornadoChart({ rows, base }: { rows: { parameter: string; low: number; high: number }[]; base: number }) {
  const data = rows.map((r) => ({ parameter: r.parameter, floor: r.low, span: r.high - r.low, low: r.low, high: r.high }))
  return (
    <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, bottom: 26, left: 130 }}>
      {grid}
      <XAxis type="number" domain={['auto', 'auto']} {...axisProps} label={{ value: 'LCOH [USD/kg H2]', position: 'insideBottom', offset: -14, fill: 'var(--muted)' }} />
      <YAxis type="category" dataKey="parameter" width={125} {...axisProps} />
      <Tooltip contentStyle={tipStyle} formatter={(_v, _n, item) => { const d = (item as { payload?: { low: number; high: number } }).payload; return d ? `${num(d.low)} .. ${num(d.high)} USD/kg` : '' }} />
      <ReferenceLine x={base} stroke="var(--text)" strokeDasharray="4 3" label={{ value: 'base', fill: 'var(--muted)', fontSize: 11, position: 'top' }} />
      <Bar dataKey="floor" stackId="t" fill="transparent" isAnimationActive={false} legendType="none" />
      <Bar dataKey="span" stackId="t" name="LCOH range" fill="var(--primary)" isAnimationActive={false} />
    </BarChart>
  )
}

export interface MarkerPoint { x: number; y: number; label: string }
/** Line chart with an optional breakeven marker and a separately labelled set of literature markers. */
export function PriceCurveChart(p: {
  data: { x: number; y: number }[]; lineLabel: string; xLabel: string; yLabel: string
  breakeven?: { x: number; y: number } | null; literature?: MarkerPoint[]; target?: number
}) {
  const be = p.breakeven ? [p.breakeven] : []
  return (
    <ComposedChart margin={{ top: 12, right: 24, bottom: 26, left: 8 }}>
      {grid}
      <XAxis type="number" dataKey="x" name={p.xLabel} domain={['auto', 'auto']} {...axisProps} label={{ value: p.xLabel, position: 'insideBottom', offset: -14, fill: 'var(--muted)' }} />
      <YAxis type="number" dataKey="y" name={p.yLabel} domain={['auto', 'auto']} {...axisProps} label={{ value: p.yLabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
      <ZAxis range={[70, 70]} />
      <Tooltip contentStyle={tipStyle} formatter={(v) => num(v)} />
      <Legend verticalAlign="top" height={30} />
      {p.target !== undefined ? <ReferenceLine y={p.target} stroke="var(--muted)" strokeDasharray="4 4" label={{ value: `target ${p.target}`, fill: 'var(--muted)', fontSize: 11, position: 'insideTopLeft' }} /> : null}
      <Line data={p.data} dataKey="y" name={p.lineLabel} stroke="var(--primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
      {be.length ? <Scatter data={be} dataKey="y" name="Break-even" fill="var(--ok)" shape="diamond" isAnimationActive={false} /> : null}
      {p.literature?.length ? <Scatter data={p.literature} dataKey="y" name="Published literature (not AmCraX)" fill="var(--src-literature)" shape="triangle" isAnimationActive={false} /> : null}
    </ComposedChart>
  )
}