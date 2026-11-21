import { EdgeLabelRenderer, Handle, Position, type EdgeProps, type NodeProps } from '@xyflow/react'
import { Value } from '../components/ui'
import { EquipmentSymbol } from './symbols'
import {
  labelAnchor, roundedPath, type EquipNode, type LaneNode, type StreamEdge, type TerminalNode,
} from './mapping'

const hidden = { opacity: 0, pointerEvents: 'none' as const, width: 1, height: 1 }

function chip(d: EquipNode['data']): { icon: string; text: string; cls: string; title: string } {
  const st = d.result?.details?.aspen_status
  if (!d.result) return { icon: '\u2013', text: 'no result', cls: 'neutral', title: 'No result for this block' }
  if (d.converged === false) return { icon: '\u2717', text: 'not conv.', cls: 'error', title: 'Run did not converge' }
  if (d.resultSource === 'demo') return { icon: 'i', text: 'demo', cls: 'demo', title: 'Illustrative demonstration data' }
  if (typeof st === 'string' && st !== 'ok') return { icon: '\u26A0', text: st, cls: 'warn', title: `Block status reported by the engine: ${st}` }
  const stTxt = typeof st === 'string' ? `block status: ${st}` : 'no block status reported'
  if (d.resultSource === 'aspen_plus_v15') return { icon: '\u2713', text: 'Aspen', cls: 'ok', title: `Aspen Plus V15 result, ${stTxt}` }
  if (d.resultSource === 'python_model') return { icon: '\u2713', text: 'Python', cls: 'py', title: `Python model result, ${stTxt}` }
  return { icon: '\u2713', text: String(d.resultSource), cls: 'ok', title: stTxt }
}

export function EquipmentNodeView({ data, selected }: NodeProps<EquipNode>) {
  const c = chip(data)
  const r = data.result
  const src = data.resultSource
  const isPsa = data.block.pfd.symbol === 'psa'
  return (
    <div className={`equip sec-${data.block.section}${selected ? ' is-selected' : ''}`} title={`${data.block.id}: ${data.block.name}`}>
      <Handle type="target" position={Position.Left} style={hidden} isConnectable={false} />
      <Handle type="source" position={Position.Right} style={hidden} isConnectable={false} />
      <div className="equip-head">
        <span className="equip-tag">{data.block.id}</span>
        <span className={`pchip pchip-${c.cls}`} title={c.title}><span aria-hidden="true">{c.icon}</span> {c.text}</span>
        <span className="equip-name">{data.block.name}</span>
      </div>
      <EquipmentSymbol symbol={data.block.pfd.symbol} />
      {isPsa && <span className="pchip pchip-ro" title="Component splitter with specified recovery; not a designed PSA">reduced-order</span>}
      {r && (r.duty_kW !== null || r.power_kW !== null) && (
        <span className="equip-badge" title={r.power_kW !== null ? 'Shaft power' : 'Duty (+ = heat added)'}>
          {r.power_kW !== null
            ? <>W <Value v={r.power_kW} unit="kW" digits={2} source={src} showSource={false} /></>
            : <>Q <Value v={r.duty_kW} unit="kW" digits={Math.abs(r.duty_kW ?? 0) < 10 ? 2 : 0} source={src} showSource={false} /></>}
        </span>
      )}
    </div>
  )
}
export function TerminalNodeView({ data }: NodeProps<TerminalNode>) {
  return (
    <div className={`terminal terminal-${data.direction}`}>
      <Handle type="target" position={Position.Left} style={hidden} isConnectable={false} />
      <Handle type="source" position={Position.Right} style={hidden} isConnectable={false} />
      <span className="terminal-tag">{data.streamId}</span>
      <span className="terminal-label">{data.label}</span>
    </div>
  )
}

export function LaneNodeView({ data }: NodeProps<LaneNode>) {
  return <div className="lane" style={{ width: data.w, height: data.h }}><span>{data.label}</span></div>
}

export function StreamEdgeView({ data, selected }: EdgeProps<StreamEdge>) {
  if (!data) return null
  const { points, stream, result, color, width, animate, overlays, source } = data
  const d = roundedPath(points)
  const last = points[points.length - 1]
  const prev = points[points.length - 2]
  const ang = Math.atan2(last.y - prev.y, last.x - prev.x)
  const L = 9 + width
  const W = 5 + width * 0.6
  const bx = last.x - Math.cos(ang) * L
  const by = last.y - Math.sin(ang) * L
  const tri = `${last.x},${last.y} ${bx - Math.sin(ang) * W},${by + Math.cos(ang) * W} ${bx + Math.sin(ang) * W},${by - Math.cos(ang) * W}`
  const top2 = Object.entries(result?.mole_frac ?? {}).filter(([, y]) => y > 0).sort((p, q) => q[1] - p[1]).slice(0, 2)
  const h = data.label
  let a = labelAnchor(points)
  let side: 'above' | 'below' | 'left' | 'right' = a.horizontal ? 'above' : 'left'
  if (h && points[h.seg + 1]) {
    const p0 = points[h.seg], p1 = points[h.seg + 1]
    a = { x: p0.x + (p1.x - p0.x) * h.t, y: p0.y + (p1.y - p0.y) * h.t, horizontal: Math.abs(p1.y - p0.y) < Math.abs(p1.x - p0.x) }
    side = h.side
  }
  const tr = side === 'above' ? `translate(-50%, -100%) translate(${a.x}px, ${a.y - 7}px)`
    : side === 'below' ? `translate(-50%, 0) translate(${a.x}px, ${a.y + 7}px)`
    : side === 'right' ? `translate(0, -50%) translate(${a.x + 10}px, ${a.y}px)`
    : `translate(-100%, -50%) translate(${a.x - 10}px, ${a.y}px)`
  return (
    <g className={`stream${selected ? ' is-selected' : ''}`}>
      {selected && <path d={d} fill="none" stroke="var(--primary)" strokeWidth={width + 9} strokeOpacity={0.45} strokeLinecap="round" strokeLinejoin="round" />}
      <path d={d} fill="none" stroke="var(--bg)" strokeWidth={width + 3} strokeLinecap="round" strokeLinejoin="round" />
      <path className="stream-core" d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap="butt" strokeLinejoin="round" />
      {animate && <path className="flow-anim" d={d} fill="none" stroke="var(--bg)" strokeOpacity={0.55} strokeWidth={Math.max(1.5, width / 3)} strokeDasharray="2 14" />}
      <polygon points={tri} fill={color} stroke="var(--bg)" strokeWidth={1} />
      <path d={d} fill="none" stroke="transparent" strokeWidth={18} style={{ cursor: 'pointer' }} />
      <EdgeLabelRenderer>
        <div className={`edge-label nodrag nopan${selected ? ' is-selected' : ''}`} style={{ transform: tr }}>
          <span className="edge-tag">{stream.id}</span>
          {overlays.T && <span className="edge-line">T <Value v={result?.temperature_C} unit={'\u00B0C'} digits={0} source={source} showSource={false} /></span>}
          {overlays.P && <span className="edge-line">P <Value v={result?.pressure_bar} unit="bar" digits={1} source={source} showSource={false} /></span>}
          {overlays.F && <span className="edge-line">n <Value v={result?.mole_flow_kmol_h} unit="kmol/h" digits={1} source={source} showSource={false} /></span>}
          {overlays.M && <span className="edge-line">m <Value v={result?.mass_flow_kg_h} unit="kg/h" digits={0} source={source} showSource={false} /></span>}
          {overlays.X && (top2.length ? top2.map(([k, y]) => <span key={k} className="edge-line">{k} <Value v={y * 100} unit="%" digits={1} source={source} showSource={false} /></span>) : <span className="edge-line">y n/a</span>)}
        </div>
      </EdgeLabelRenderer>
    </g>
  )
}





