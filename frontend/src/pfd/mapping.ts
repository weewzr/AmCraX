import type { Edge, Node } from '@xyflow/react'
import type { BlockResult, Flowsheet, FlowsheetBlock, FlowsheetStream, SimulationResult, StreamResult } from '../api/types'

export const NODE_W = 140
export const NODE_H = 116
export const HEAD_H = 32
/** symbol scale: symbols are drawn in a 120 x 72 box and rendered at 140 x 84 */
export const SYM_K = 7 / 6
/** y of the process line inside a node box (head strip + symbol line at y = 36). */
export const CY = HEAD_H + 36 * SYM_K
export const TERM_W = 96
export const TERM_H = 44
const FEHE_HOT_DY = 18 * SYM_K
const LANE_PAD_X = 34
const LANE_PAD_TOP = 28
const LANE_PAD_BOTTOM = 34

export type ColorBy = 'component' | 'temperature'
/** T, P, F = molar flow (kmol/h), M = mass flow (kg/h), X = main composition (two largest mole fractions) */
export interface Overlays { T: boolean; P: boolean; F: boolean; M?: boolean; X?: boolean }
export interface PfdOptions {
  colorBy: ColorBy
  overlays: Overlays
  animate: boolean
  heatIntegration: boolean
}
export interface Pt { x: number; y: number }

export type EquipData = {
  block: FlowsheetBlock
  result: BlockResult | null
  resultSource: SimulationResult['source'] | null
  converged: boolean | null
}
export type TerminalData = { label: string; streamId: string; direction: 'in' | 'out' }
export type LaneData = { label: string; w: number; h: number }
export type LabelHint = { seg: number; t: number; side: 'above' | 'below' | 'left' | 'right' }
export type StreamEdgeData = {
  label?: LabelHint
  points: Pt[]
  stream: FlowsheetStream
  result: StreamResult | null
  color: string
  width: number
  animate: boolean
  overlays: Overlays
  source: SimulationResult['source'] | null
}
export type EquipNode = Node<EquipData, 'equipment'>
export type TerminalNode = Node<TerminalData, 'terminal'>
export type LaneNode = Node<LaneData, 'lane'>
export type PfdNode = EquipNode | TerminalNode | LaneNode
export type StreamEdge = Edge<StreamEdgeData, 'stream'>

export const COMPONENT_COLOR: Record<string, string> = {
  NH3: 'var(--c-nh3)', H2: 'var(--c-h2)', N2: 'var(--c-n2)', H2O: 'var(--c-h2o)', O2: 'var(--c-o2)',
}

/** Whether a flowsheet block / stream exists for the chosen heat-integration setting. */
export function blockVisible(b: FlowsheetBlock, heatIntegration: boolean): boolean {
  return !(b.optional && b.id === 'FEHE' && !heatIntegration)
}
export function streamVisible(s: FlowsheetStream, heatIntegration: boolean): boolean {
  return !(s.requires === 'FEHE' && !heatIntegration)
}
/** Destination block of a stream after FEHE removal (to_if_no_fehe from flowsheet.json). */
export function streamDest(s: FlowsheetStream, heatIntegration: boolean): string | null {
  return !heatIntegration && s.to_if_no_fehe ? s.to_if_no_fehe : s.to
}

export function dominantComponent(r: StreamResult | null): string | null {
  if (!r) return null
  const e = Object.entries(r.mole_frac)
  if (!e.length) return null
  return e.reduce((a, b) => (b[1] > a[1] ? b : a))[0]
}

/** Linear blend between the cold and hot theme colours; returns a CSS color-mix() expression. */
export function temperatureColor(T: number | null, lo: number, hi: number): string {
  if (T === null || !(hi > lo)) return 'var(--muted)'
  const t = Math.min(1, Math.max(0, (T - lo) / (hi - lo)))
  return `color-mix(in srgb, var(--c-heat) ${Math.round(t * 100)}%, var(--c-cold))`
}

/** Stroke width in px from mass flow, scaled gently (sqrt) between 2.5 and 7. */
export function strokeWidth(mass: number | null, maxMass: number): number {
  if (mass === null || !(maxMass > 0)) return 3
  return 2.5 + 4.5 * Math.sqrt(Math.max(0, Math.min(1, mass / maxMass)))
}

interface Layout { pos: Record<string, Pt>; terminals: Record<string, { x: number; y: number }> }

/**
 * Frontend layout table keyed by block id (px, node box NODE_W x NODE_H): a compact three-row arrangement that
 * fills a landscape canvas. Positions in config/flowsheet.json ("pfd") are only the fallback for unknown blocks.
 */
export const PFD_LAYOUT: Record<string, Pt> = {
  PUMP: { x: 0, y: 0 }, VAPORIZR: { x: 225, y: 0 }, FEHE: { x: 450, y: 0 }, HEATER: { x: 675, y: 0 }, CRACKER: { x: 900, y: 0 },
  COOLER: { x: 450, y: 280 }, PSA: { x: 675, y: 280 },
  BURNER: { x: 675, y: 510 }, FLUEHX: { x: 900, y: 510 },
}
/** where the overlay label of the awkward streams sits (segment index, fraction along it, side) */
const LABEL_HINTS: Record<string, LabelHint> = {
  S5: { seg: 1, t: 0.5, side: 'right' }, TAILGAS: { seg: 2, t: 0.5, side: 'left' }, AIR: { seg: 0, t: 0.5, side: 'right' },
}
const TERM_GAP = 90
const Y_RETURN = 190 // y of the horizontal S5 return line between row 1 and row 2
const AIR_X = 100 // x offset (in the burner node) where the air stream enters from below

function buildLayout(fs: Flowsheet, hi: boolean): Layout {
  const pos: Record<string, Pt> = {}
  for (const b of fs.blocks) if (blockVisible(b, hi)) pos[b.id] = PFD_LAYOUT[b.id] ?? { x: b.pfd.x, y: b.pfd.y }
  const terminals: Record<string, Pt> = {}
  for (const s of fs.streams) {
    if (!streamVisible(s, hi)) continue
    if (s.from === null && s.to && pos[s.to]) {
      const t = pos[s.to]
      terminals[s.id] =
        s.id === 'AIR' ? { x: t.x + AIR_X - TERM_W / 2, y: t.y + NODE_H + 64 } : { x: t.x - TERM_GAP - TERM_W, y: t.y + CY - TERM_H / 2 }
    }
    if (s.to === null && s.from && pos[s.from]) {
      const f = pos[s.from]
      terminals[s.id] = { x: f.x + NODE_W + TERM_GAP, y: f.y + CY - TERM_H / 2 }
    }
  }
  return { pos, terminals }
}

/** Absolute polyline of one stream (waypoints, orthogonal). Exported for tests. */
export function routeStream(s: FlowsheetStream, lay: Layout, hi: boolean): Pt[] | null {
  const P = lay.pos
  const dest = streamDest(s, hi)
  const T = lay.terminals[s.id]
  const outOf = (id: string, dy = 0): Pt => ({ x: P[id].x + NODE_W, y: P[id].y + CY + dy })
  const inTo = (id: string, dy = 0): Pt => ({ x: P[id].x, y: P[id].y + CY + dy })
  if (s.from === null) {
    if (!dest || !P[dest] || !T) return null
    if (s.id === 'AIR') return [{ x: T.x + TERM_W / 2, y: T.y }, { x: P[dest].x + AIR_X, y: P[dest].y + HEAD_H + 68 }]
    return [{ x: T.x + TERM_W, y: T.y + TERM_H / 2 }, inTo(dest)]
  }
  if (!P[s.from]) return null
  if (dest === null) {
    if (!T) return null
    return [outOf(s.from), { x: T.x, y: T.y + TERM_H / 2 }]
  }
  if (!P[dest]) return null
  const hiFehe = hi && P.FEHE
  switch (s.id) {
    case 'S5': {
      // CRACKER outlet -> right -> down to the return line -> left -> FEHE hot inlet (right face) or COOLER (left face).
      const a = outOf(s.from)
      const x1 = a.x + 20
      if (hiFehe) {
        const b = outOf('FEHE', FEHE_HOT_DY)
        const xv = (b.x + P.HEATER.x) / 2
        return [a, { x: x1, y: a.y }, { x: x1, y: Y_RETURN }, { x: xv, y: Y_RETURN }, { x: xv, y: b.y }, b]
      }
      const b = inTo(dest)
      const xv = b.x - 22
      return [a, { x: x1, y: a.y }, { x: x1, y: Y_RETURN }, { x: xv, y: Y_RETURN }, { x: xv, y: b.y }, b]
    }
    case 'S6': {
      const a = inTo('FEHE', FEHE_HOT_DY)
      const b = inTo(dest)
      const xv = b.x - 22
      return [a, { x: xv, y: a.y }, { x: xv, y: b.y }, b]
    }
    case 'TAILGAS': {
      // PSA bottom (right-hand vessel) -> down -> left -> BURNER left face
      const a: Pt = { x: P[s.from].x + 92, y: P[s.from].y + HEAD_H + 72 * SYM_K - 8 }
      const b = inTo(dest)
      const yh = 456
      const xv = b.x - 55
      return [a, { x: a.x, y: yh }, { x: xv, y: yh }, { x: xv, y: b.y }, b]
    }
    default: {
      const a = outOf(s.from)
      const b = inTo(dest)
      if (Math.abs(a.y - b.y) < 0.5) return [a, b]
      const xm = (a.x + b.x) / 2
      return [a, { x: xm, y: a.y }, { x: xm, y: b.y }, b]
    }
  }
}
function streamColor(r: StreamResult | null, opts: PfdOptions, lo: number, hi: number): string {
  if (opts.colorBy === 'temperature') return temperatureColor(r?.temperature_C ?? null, lo, hi)
  const c = dominantComponent(r)
  return c ? (COMPONENT_COLOR[c] ?? 'var(--muted)') : 'var(--muted)'
}

export function flowsheetToGraph(fs: Flowsheet, result: SimulationResult | null, opts: PfdOptions): { nodes: PfdNode[]; edges: StreamEdge[] } {
  const hi = opts.heatIntegration
  const lay = buildLayout(fs, hi)
  const nodes: PfdNode[] = []
  const edges: StreamEdge[] = []

  // section lanes (bounding box of the visible blocks of each section)
  for (const sec of fs.sections) {
    const bs = fs.blocks.filter((b) => b.section === sec.id && lay.pos[b.id])
    if (!bs.length) continue
    const x0 = Math.min(...bs.map((b) => lay.pos[b.id].x)) - LANE_PAD_X
    const x1 = Math.max(...bs.map((b) => lay.pos[b.id].x + NODE_W)) + LANE_PAD_X
    const y0 = Math.min(...bs.map((b) => lay.pos[b.id].y)) - LANE_PAD_TOP
    const y1 = Math.max(...bs.map((b) => lay.pos[b.id].y + NODE_H)) + LANE_PAD_BOTTOM
    nodes.push({
      id: `lane:${sec.id}`, type: 'lane', position: { x: x0, y: y0 }, data: { label: sec.label, w: x1 - x0, h: y1 - y0 },
      draggable: false, selectable: false, focusable: false, zIndex: -1, style: { width: x1 - x0, height: y1 - y0 },
    })
  }
  for (const b of fs.blocks) {
    if (!lay.pos[b.id]) continue
    nodes.push({
      id: b.id, type: 'equipment', position: lay.pos[b.id], draggable: false,
      data: { block: b, result: result?.blocks[b.id] ?? null, resultSource: result?.source ?? null, converged: result ? result.status.converged : null },
    })
  }
  const temps = result ? Object.values(result.streams).map((s) => s.temperature_C).filter((t): t is number => t !== null) : []
  const lo = temps.length ? Math.min(...temps) : 0
  const hiT = temps.length ? Math.max(...temps) : 1
  const maxMass = result ? Math.max(0, ...Object.values(result.streams).map((s) => s.mass_flow_kg_h ?? 0)) : 0

  for (const s of fs.streams) {
    if (!streamVisible(s, hi)) continue
    const pts = routeStream(s, lay, hi)
    if (!pts) continue
    const tpos = lay.terminals[s.id]
    if (tpos) {
      nodes.push({
        id: `T:${s.id}`, type: 'terminal', position: tpos, draggable: false, selectable: false, focusable: false,
        data: { label: s.name, streamId: s.id, direction: s.from === null ? 'in' : 'out' },
      })
    }
    const dest = streamDest(s, hi)
    const src = s.from ?? `T:${s.id}`
    const tgt = dest ?? `T:${s.id}`
    const r = result?.streams[s.id] ?? null
    edges.push({
      id: s.id, type: 'stream', source: src, target: tgt, focusable: true, ariaLabel: `Stream ${s.id}: ${s.name}`,
      data: {
        label: LABEL_HINTS[s.id], points: pts, stream: s, result: r, color: streamColor(r, opts, lo, hiT), width: strokeWidth(r?.mass_flow_kg_h ?? null, maxMass),
        animate: opts.animate, overlays: opts.overlays, source: result?.source ?? null,
      },
    })
  }
  return { nodes, edges }
}

/** Longest segment of a polyline: returns midpoint and orientation. */
export function labelAnchor(pts: Pt[]): { x: number; y: number; horizontal: boolean } {
  let best = 0
  let len = -1
  for (let i = 0; i < pts.length - 1; i++) {
    const l = Math.abs(pts[i + 1].x - pts[i].x) + Math.abs(pts[i + 1].y - pts[i].y)
    if (l > len) { len = l; best = i }
  }
  const a = pts[best]
  const b = pts[best + 1]
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, horizontal: Math.abs(b.y - a.y) < Math.abs(b.x - a.x) }
}

/** SVG path with rounded corners through waypoints. */
export function roundedPath(pts: Pt[], r = 10): string {
  if (pts.length < 2) return ''
  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 1; i < pts.length - 1; i++) {
    const p0 = pts[i - 1], p1 = pts[i], p2 = pts[i + 1]
    const l1 = Math.hypot(p1.x - p0.x, p1.y - p0.y)
    const l2 = Math.hypot(p2.x - p1.x, p2.y - p1.y)
    const rr = Math.min(r, l1 / 2, l2 / 2)
    const a = { x: p1.x - ((p1.x - p0.x) / l1) * rr, y: p1.y - ((p1.y - p0.y) / l1) * rr }
    const b = { x: p1.x + ((p2.x - p1.x) / l2) * rr, y: p1.y + ((p2.y - p1.y) / l2) * rr }
    d += ` L ${a.x} ${a.y} Q ${p1.x} ${p1.y} ${b.x} ${b.y}`
  }
  const last = pts[pts.length - 1]
  return d + ` L ${last.x} ${last.y}`
}








