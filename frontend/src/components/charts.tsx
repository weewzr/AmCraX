import type { ReactNode } from 'react'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { DataSource } from '../api/types'
import { SourceBadge } from './ui'

export interface Series { key: string; label: string; color?: string }
const PALETTE = ['var(--primary)', 'var(--accent)', 'var(--c-nh3)', 'var(--c-h2)', 'var(--c-n2)', 'var(--warn)']

interface CardProps {
  title: string
  source: DataSource | null
  /** text alternative describing what the chart shows */
  description: string
  xLabel: string
  yLabel: string
  children?: ReactNode
}

function Card({ title, source, description, children }: CardProps) {
  return (
    <figure className="card chart-card" aria-label={title}>
      <figcaption><span>{title}</span><SourceBadge source={source} /></figcaption>
      <div className="chart-box" role="img" aria-label={description}>
        <ResponsiveContainer width="100%" height="100%">{children as React.ReactElement}</ResponsiveContainer>
      </div>
      <p className="sr-only">{description}</p>
    </figure>
  )
}

const axisProps = { stroke: 'var(--muted)', tick: { fill: 'var(--muted)', fontSize: 12 } }
const grid = <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />

export function LineChartCard(p: CardProps & { data: Record<string, number | null>[]; xKey: string; series: Series[] }) {
  return (
    <Card {...p}>
      <LineChart data={p.data} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        {grid}
        <XAxis dataKey={p.xKey} {...axisProps} height={46} label={{ value: p.xLabel, position: 'insideBottom', offset: 0, fill: 'var(--muted)' }} />
        <YAxis {...axisProps} label={{ value: p.yLabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
        <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }} />
        <Legend verticalAlign="bottom" height={30} wrapperStyle={{ paddingTop: 8 }} />
        {p.series.map((s, i) => (
          <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color ?? PALETTE[i % PALETTE.length]} strokeWidth={2} dot={false} connectNulls={false} />
        ))}
      </LineChart>
    </Card>
  )
}

export function BarChartCard(p: CardProps & { data: Record<string, number | string | null>[]; xKey: string; series: Series[] }) {
  return (
    <Card {...p}>
      <BarChart data={p.data} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        {grid}
        <XAxis dataKey={p.xKey} {...axisProps} height={46} label={{ value: p.xLabel, position: 'insideBottom', offset: 0, fill: 'var(--muted)' }} />
        <YAxis {...axisProps} label={{ value: p.yLabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
        <Tooltip contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }} />
        <Legend verticalAlign="bottom" height={30} wrapperStyle={{ paddingTop: 8 }} />
        {p.series.map((s, i) => (
          <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color ?? PALETTE[i % PALETTE.length]} />
        ))}
      </BarChart>
    </Card>
  )
}

export function ScatterChartCard(p: CardProps & { data: Record<string, number | null>[]; xKey: string; yKey: string; name: string }) {
  return (
    <Card {...p}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        {grid}
        <XAxis type="number" dataKey={p.xKey} name={p.xLabel} {...axisProps} height={46} label={{ value: p.xLabel, position: 'insideBottom', offset: 0, fill: 'var(--muted)' }} />
        <YAxis type="number" dataKey={p.yKey} name={p.yLabel} {...axisProps} label={{ value: p.yLabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }} />
        <Legend verticalAlign="bottom" height={30} wrapperStyle={{ paddingTop: 8 }} />
        <Scatter name={p.name} data={p.data} fill="var(--primary)" />
      </ScatterChart>
    </Card>
  )
}
