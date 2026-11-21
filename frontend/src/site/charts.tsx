import { useEffect, useState, type ReactNode } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DataSource } from '../api/types'
import { SourceBadge } from '../components/ui'

export function useIsNarrow(max = 640): boolean {
  const q = `(max-width:${max}px)`
  const [n, setN] = useState(() => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(q).matches : false))
  useEffect(() => {
    const m = window.matchMedia(q)
    const on = () => setN(m.matches)
    m.addEventListener('change', on)
    on()
    return () => m.removeEventListener('change', on)
  }, [q])
  return n
}

const axis = { stroke: 'var(--muted)', tick: { fill: 'var(--muted)', fontSize: 12 } }
const tip = { contentStyle: { background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)' }, itemStyle: { color: 'var(--text)' }, labelStyle: { color: 'var(--text)' } }

export interface HBarSeries { key: string; label: string; color: string }

/** Horizontal (stacked) bar chart with category labels on the left; units in the x-axis title; provenance badge in the caption. */
export function HBarChart(p: {
  title: string; description: string; source: DataSource | null; data: Record<string, string | number | null>[]
  catKey: string; series: HBarSeries[]; xLabel: string; stacked?: boolean; height?: number; refLines?: { x: number; label: string }[]; digits?: number; children?: ReactNode
}) {
  const narrow = useIsNarrow()
  const mid = useIsNarrow(900)
  const h = p.height ?? Math.max(220, 46 * p.data.length + 90)
  return (
    <figure className="card chart-card" aria-label={p.title}>
      <figcaption><span>{p.title}</span>{p.source ? <SourceBadge source={p.source} /> : null}</figcaption>
      <div className="chart-box" style={{ height: h }} role="img" aria-label={p.description}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={p.data} layout="vertical" margin={{ top: 6, right: 20, bottom: p.series.length > 1 ? 44 : 26, left: 4 }} barCategoryGap="22%">
            <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} horizontal={false} />
            <XAxis type="number" {...axis} label={{ value: p.xLabel, position: 'insideBottom', offset: p.series.length > 1 ? -4 : -14, fill: 'var(--muted)' }} />
            <YAxis type="category" dataKey={p.catKey} width={narrow ? 118 : mid ? 205 : 275} {...axis} tick={{ fill: 'var(--text-2)', fontSize: narrow ? 11 : 12.5 }} interval={0} />
            <Tooltip {...tip} formatter={(v) => (typeof v === 'number' ? Number(v.toPrecision(4)) : String(v ?? 'n/a'))} cursor={{ fill: 'var(--text)', fillOpacity: 0.05 }} />
            {(p.refLines ?? []).map((r) => (
              <ReferenceLine key={r.label} x={r.x} stroke="var(--warn)" strokeDasharray="5 4" label={{ value: r.label, fill: 'var(--warn)', fontSize: 11, position: 'insideTopRight' }} />
            ))}
            {p.series.length > 1 ? <Legend verticalAlign="bottom" height={26} wrapperStyle={{ paddingTop: 6, fontSize: 12 }} /> : null}
            {p.series.map((s) => (
              <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} stackId={p.stacked ? 'a' : undefined} isAnimationActive={false} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="sr-only">{p.description}</p>
      {p.children}
    </figure>
  )
}

/** Plain chart card around any Recharts chart (used where XYChart does not fit). */
export function ChartFrame({ title, source, description, height = 300, children }: { title: string; source: DataSource | null; description: string; height?: number; children: ReactNode }) {
  return (
    <figure className="card chart-card" aria-label={title}>
      <figcaption><span>{title}</span><SourceBadge source={source} /></figcaption>
      <div className="chart-box" style={{ height }} role="img" aria-label={description}>{children}</div>
      <p className="sr-only">{description}</p>
    </figure>
  )
}
