import { useId } from 'react'

interface Box { id: string; x: number; y: number; w: number; h: number; title: string; lines: string[]; tone: 'aspen' | 'python' | 'store' | 'web' | 'pub' }
type Pt = [number, number]
interface Edge { pts: Pt[]; dashed?: boolean; both?: boolean; label?: { x: number; y: number; text: string; anchor?: 'start' | 'middle' | 'end' } }

/** Original architecture diagram, drawn twice from the same content: a wide layout (>= 760 px) and a tall one for phones. */
const WIDE: { w: number; h: number; boxes: Box[]; edges: Edge[]; frames: { x: number; y: number; w: number; h: number; label: string }[] } = {
  w: 1000, h: 580,
  frames: [
    { x: 8, y: 8, w: 984, h: 340, label: 'LOCAL ENGINEERING PLATFORM (needs a licensed Aspen Plus V15 for new Aspen runs)' },
    { x: 208, y: 398, w: 784, h: 174, label: 'PUBLIC STATIC SITE (GitHub Pages, no server, no Aspen Plus)' },
  ],
  boxes: [
    { id: 'aspen', x: 28, y: 50, w: 190, h: 100, title: 'Aspen Plus V15', lines: ['rigorous flowsheet', 'RGibbs, PENG-ROB'], tone: 'aspen' },
    { id: 'auto', x: 280, y: 50, w: 220, h: 100, title: 'amcrax.aspen', lines: ['Python COM automation:', 'input generator, session,', 'extraction, worker'], tone: 'python' },
    { id: 'store', x: 560, y: 50, w: 190, h: 100, title: 'Results store', lines: ['results/ JSON + CSV', 'each value tagged with', 'its source'], tone: 'store' },
    { id: 'api', x: 810, y: 50, w: 170, h: 100, title: 'FastAPI', lines: ['read results, queue', 'Aspen / Python runs'], tone: 'python' },
    { id: 'models', x: 280, y: 220, w: 220, h: 100, title: 'Independent models', lines: ['thermodynamics, process', 'mirror, pinch, kinetics,', 'economics, carbon, optimisation'], tone: 'python' },
    { id: 'dash', x: 810, y: 220, w: 170, h: 100, title: 'React dashboard', lines: ['React Flow, Recharts', 'mode: LIVE'], tone: 'web' },
    { id: 'export', x: 228, y: 440, w: 210, h: 100, title: 'export_snapshot.py', lines: ['copies results, figures', 'and screenshots'], tone: 'pub' },
    { id: 'snap', x: 500, y: 440, w: 210, h: 100, title: 'snapshot + downloads', lines: ['committed static mirror,', 'report and deck files'], tone: 'store' },
    { id: 'pages', x: 780, y: 440, w: 200, h: 100, title: 'Static website', lines: ['same React app,', 'base /AmCraX/, SNAPSHOT'], tone: 'web' },
  ],
  edges: [
    { pts: [[218, 100], [280, 100]], both: true, label: { x: 249, y: 88, text: 'COM', anchor: 'middle' } },
    { pts: [[500, 100], [560, 100]] },
    { pts: [[750, 100], [810, 100]], label: { x: 780, y: 88, text: 'reads', anchor: 'middle' } },
    { pts: [[895, 150], [895, 220]], both: true, label: { x: 905, y: 190, text: 'HTTP /api', anchor: 'start' } },
    { pts: [[500, 270], [600, 270], [600, 150]] },
    { pts: [[390, 150], [390, 220]], dashed: true, both: true, label: { x: 400, y: 190, text: 'cross-check', anchor: 'start' } },
    { pts: [[690, 150], [690, 380], [333, 380], [333, 440]], label: { x: 520, y: 372, text: 'static export', anchor: 'middle' } },
    { pts: [[438, 490], [500, 490]] },
    { pts: [[710, 490], [780, 490]], label: { x: 745, y: 512, text: 'deploy', anchor: 'middle' } },
    { pts: [[895, 320], [895, 440]], dashed: true, label: { x: 885, y: 385, text: 'same build, two data modes', anchor: 'end' } },
  ],
}

const TALL: typeof WIDE = {
  w: 360, h: 1010,
  frames: [
    { x: 4, y: 4, w: 352, h: 540, label: 'LOCAL ENGINEERING PLATFORM' },
    { x: 4, y: 580, w: 352, h: 420, label: 'PUBLIC STATIC SITE (no server, no Aspen)' },
  ],
  boxes: [
    { id: 'aspen', x: 24, y: 36, w: 312, h: 70, title: 'Aspen Plus V15', lines: ['rigorous flowsheet, RGibbs, PENG-ROB'], tone: 'aspen' },
    { id: 'auto', x: 24, y: 136, w: 312, h: 84, title: 'amcrax.aspen', lines: ['Python COM automation: input generator,', 'session, extraction, worker'], tone: 'python' },
    { id: 'store', x: 24, y: 250, w: 150, h: 100, title: 'Results store', lines: ['results/ JSON + CSV,', 'values tagged with', 'their source'], tone: 'store' },
    { id: 'models', x: 190, y: 250, w: 146, h: 100, title: 'Python models', lines: ['thermodynamics,', 'process mirror, pinch,', 'kinetics, economics'], tone: 'python' },
    { id: 'api', x: 24, y: 380, w: 312, h: 64, title: 'FastAPI', lines: ['reads results, queues Aspen / Python runs'], tone: 'python' },
    { id: 'dash', x: 24, y: 474, w: 312, h: 54, title: 'React dashboard (mode: LIVE)', lines: [], tone: 'web' },
    { id: 'export', x: 24, y: 612, w: 312, h: 64, title: 'export_snapshot.py', lines: ['copies results, figures, screenshots'], tone: 'pub' },
    { id: 'snap', x: 24, y: 710, w: 312, h: 64, title: 'public/snapshot + downloads', lines: ['committed static mirror, report and deck'], tone: 'store' },
    { id: 'pages', x: 24, y: 808, w: 312, h: 84, title: 'Static website', lines: ['same React app, base /AmCraX/,', 'mode: SNAPSHOT'], tone: 'web' },
  ],
  edges: [
    { pts: [[180, 106], [180, 136]], both: true, label: { x: 190, y: 126, text: 'COM', anchor: 'start' } },
    { pts: [[99, 220], [99, 250]] },
    { pts: [[190, 300], [174, 300]] },
    { pts: [[263, 220], [263, 250]], dashed: true, both: true, label: { x: 273, y: 240, text: 'check', anchor: 'start' } },
    { pts: [[99, 350], [99, 380]], label: { x: 109, y: 370, text: 'reads', anchor: 'start' } },
    { pts: [[180, 444], [180, 474]], both: true, label: { x: 190, y: 464, text: 'HTTP /api', anchor: 'start' } },
    { pts: [[24, 300], [12, 300], [12, 644], [24, 644]], label: undefined },
    { pts: [[180, 676], [180, 710]] },
    { pts: [[180, 774], [180, 808]], label: { x: 190, y: 796, text: 'deploy', anchor: 'start' } },
    { pts: [[336, 501], [348, 501], [348, 850], [336, 850]], dashed: true },
  ],
}

function Diagram({ d, cls, titleId, descId }: { d: typeof WIDE; cls: string; titleId: string; descId: string }) {
  const mk = `${cls}-arrow`
  return (
    <svg className={`arch-svg ${cls}`} viewBox={`0 0 ${d.w} ${d.h}`} role="img" aria-labelledby={`${titleId} ${descId}`} xmlns="http://www.w3.org/2000/svg">
      <title id={titleId}>AmCraX software architecture</title>
      <desc id={descId}>
        Aspen Plus V15 is driven through COM by the Python automation package, which writes results to a results store. Independent Python models write to the same store and cross-check the Aspen results. A FastAPI back end serves the store to the React dashboard in the local platform. A static export copies the results into a committed snapshot, which the same React app, built for GitHub Pages, reads without any server.
      </desc>
      <defs>
        <marker id={mk} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" className="arch-head" /></marker>
      </defs>
      {d.frames.map((f) => (
        <g key={f.label}>
          <rect x={f.x} y={f.y} width={f.w} height={f.h} rx="14" className="arch-frame" />
          <text x={f.x + 16} y={f.y + 22} className="arch-frame-label">{f.label}</text>
        </g>
      ))}
      {d.edges.map((e, i) => (
        <g key={i}>
          <polyline points={e.pts.map((p) => p.join(',')).join(' ')} className={`arch-edge ${e.dashed ? 'dashed' : ''}`} markerEnd={`url(#${mk})`} markerStart={e.both ? `url(#${mk})` : undefined} fill="none" />
          {e.label ? <text x={e.label.x} y={e.label.y} textAnchor={e.label.anchor ?? 'middle'} className="arch-edge-label">{e.label.text}</text> : null}
        </g>
      ))}
      {d.boxes.map((b) => (
        <g key={b.id} className={`arch-box tone-${b.tone}`}>
          <rect x={b.x} y={b.y} width={b.w} height={b.h} rx="10" />
          <text x={b.x + 14} y={b.y + 26} className="arch-title">{b.title}</text>
          {b.lines.map((l, i) => <text key={i} x={b.x + 14} y={b.y + 48 + i * 18} className="arch-line">{l}</text>)}
        </g>
      ))}
    </svg>
  )
}

export function ArchitectureDiagram() {
  const uid = useId().replace(/:/g, '')
  return (
    <figure className="arch-figure">
      <div className="only-wide"><Diagram d={WIDE} cls="wide" titleId={`${uid}-t1`} descId={`${uid}-d1`} /></div>
      <div className="only-narrow"><Diagram d={TALL} cls="tall" titleId={`${uid}-t2`} descId={`${uid}-d2`} /></div>
      <figcaption className="muted">
        Original diagram. Solid arrows: data flow. Dashed: consistency check and build relation. Aspen Plus runs happen offline on a licensed machine;
        the published site only reads their stored results.
      </figcaption>
    </figure>
  )
}
