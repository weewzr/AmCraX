import { useCallback, useEffect, useMemo, useState } from 'react'
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from '@xyflow/react'
import { useData } from '../data/DataContext'
import { SourceBadge, StatusPill, Value } from '../components/ui'
import { fmt, NA } from '../data/format'
import { COMPONENT_COLOR, flowsheetToGraph, streamDest, type ColorBy, type Overlays, type PfdNode, type StreamEdge } from '../pfd/mapping'
import { EquipmentNodeView, LaneNodeView, StreamEdgeView, TerminalNodeView } from '../pfd/nodes'
import { BlockPanel, StreamPanel, type Selection } from '../pfd/panels'

const nodeTypes = { equipment: EquipmentNodeView, terminal: TerminalNodeView, lane: LaneNodeView }
const edgeTypes = { stream: StreamEdgeView }

/**
 * The interactive diagram with its toolbar, legend and equipment / stream lists. Used by the platform page and, read-only on the public site,
 * with a fixed case (`caseId`) so that it never changes the platform's active-case selection.
 */
export function PfdExplorer({ caseId, compact = false }: { caseId?: string; compact?: boolean }) {
  const { flowsheet, active: ctxActive, cases, phase, mode, error } = useData()
  const active = caseId ? (cases.find((c) => c.case_id === caseId) ?? null) : ctxActive
  const [colorBy, setColorBy] = useState<ColorBy>('component')
  const [overlays, setOverlays] = useState<Overlays>({ T: false, P: false, F: false, M: false, X: false })
  const [animate, setAnimate] = useState(false)
  const [sel, setSel] = useState<Selection>(null)
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(null)

  const hi = active ? active.inputs.heat_integration : true
  const graph = useMemo(
    () => (flowsheet ? flowsheetToGraph(flowsheet, active, { colorBy, overlays, animate, heatIntegration: hi }) : null),
    [flowsheet, active, colorBy, overlays, animate, hi],
  )
  const nodes = useMemo(() => graph?.nodes.map((n) => ({ ...n, selected: sel?.kind === 'block' && sel.id === n.id })) ?? [], [graph, sel])
  const edges = useMemo(() => graph?.edges.map((e) => ({ ...e, selected: sel?.kind === 'stream' && sel.id === e.id })) ?? [], [graph, sel])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { setSel(null); setHover(null) } }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  // a selection that no longer exists (e.g. FEHE after switching to a no-heat-integration case) is dropped
  useEffect(() => {
    if (!graph || !sel) return
    const exists = sel.kind === 'block' ? graph.nodes.some((n) => n.id === sel.id && n.type === 'equipment') : graph.edges.some((e) => e.id === sel.id)
    if (!exists) setSel(null)
  }, [graph, sel])

  const onNodeClick = useCallback((_: unknown, n: Node) => { if (n.type === 'equipment') setSel({ kind: 'block', id: n.id }) }, [])
  const onEdgeClick = useCallback((_: unknown, e: Edge) => setSel({ kind: 'stream', id: e.id }), [])

  if (phase === 'loading') return <div className="card" role="status">Loading flowsheet...</div>
  if (!flowsheet || !graph) return <div className="card error-card" role="alert"><StatusPill kind="error">Flowsheet unavailable</StatusPill> {error ?? 'No flowsheet topology could be loaded.'}</div>

  const src = active?.source ?? null
  const equip = graph.nodes.filter((n): n is Extract<PfdNode, { type: 'equipment' }> => n.type === 'equipment')
  const streamEdges = graph.edges as StreamEdge[]
  const selBlock = sel?.kind === 'block' ? equip.find((n) => n.id === sel.id) : undefined
  const selStream = sel?.kind === 'stream' ? streamEdges.find((e) => e.id === sel.id) : undefined
  const hoverEdge = hover ? streamEdges.find((e) => e.id === hover.id) : undefined
  const common = { source: src, converged: active ? active.status.converged : null, onClose: () => setSel(null) }
  const toggle = (k: keyof Overlays) => setOverlays((o) => ({ ...o, [k]: !o[k] }))
  const xs = graph.nodes.filter((n) => n.type === 'equipment').map((n) => n.position.x)
  const midX = (Math.min(...xs) + Math.max(...xs)) / 2
  const selX = selBlock ? selBlock.position.x : selStream ? (selStream.data?.points ?? []).reduce((a, p) => a + p.x, 0) / Math.max(1, selStream.data?.points.length ?? 1) : 0
  const sideCls = selX > midX ? 'left' : 'right'
  /** keyboard: Enter / Space on a focused node or edge opens its panel (Esc closes, handled globally) */
  const onCanvasKey = (ev: React.KeyboardEvent) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return
    const el = (ev.target as HTMLElement).closest('.react-flow__node, .react-flow__edge') as HTMLElement | null
    const id = el?.getAttribute('data-id')
    if (!el || !id) return
    ev.preventDefault()
    if (el.classList.contains('react-flow__node')) { if (equip.some((n) => n.id === id)) setSel({ kind: 'block', id }) }
    else setSel({ kind: 'stream', id })
  }

  return (
    <div className={`pfd-page ${compact ? 'pfd-compact' : ''}`}>
      <div className="card result-head">
        {active ? (
          <>
            <strong>Case {active.case_id}</strong>
            <SourceBadge source={src} />
            {active.status.converged ? <StatusPill kind="ok">Converged</StatusPill> : <StatusPill kind="error">Not converged</StatusPill>}
            {active.status.has_errors && <StatusPill kind="error">Errors</StatusPill>}
            {active.status.has_warnings && <StatusPill kind="warn">Warnings</StatusPill>}
            <span>Heat integration: <strong>{hi ? 'on (FEHE present)' : 'off (FEHE, S3, S6 removed)'}</strong></span>
            <span>Mass closure: {fmt(active.balances.mass_closure_rel, 6)}</span>
            <span>Energy closure: {fmt(active.balances.energy_closure_rel, 6)}</span>
            {active.status.messages.length > 0 && (
              <details className="messages"><summary>{active.status.messages.length} message(s)</summary><ul>{active.status.messages.map((m, i) => (<li key={i}>{m}</li>))}</ul></details>
            )}
          </>
        ) : <span role="status">No simulation case loaded in {mode} mode - topology only, all values n/a.</span>}
      </div>

      <div className="toolbar card" role="group" aria-label="Diagram options">
        <fieldset>
          <legend>Stream colour</legend>
          <label><input type="radio" name="cb" checked={colorBy === 'component'} onChange={() => setColorBy('component')} /> Dominant component</label>
          <label><input type="radio" name="cb" checked={colorBy === 'temperature'} onChange={() => setColorBy('temperature')} /> Temperature</label>
        </fieldset>
        <fieldset>
          <legend>Stream labels</legend>
          <label><input type="checkbox" checked={overlays.T} onChange={() => toggle('T')} /> T</label>
          <label><input type="checkbox" checked={overlays.P} onChange={() => toggle('P')} /> P</label>
          <label><input type="checkbox" checked={overlays.F} onChange={() => toggle('F')} /> Molar flow</label>
          <label><input type="checkbox" checked={!!overlays.M} onChange={() => toggle('M')} /> Mass flow</label>
          <label><input type="checkbox" checked={!!overlays.X} onChange={() => toggle('X')} /> Main composition</label>
        </fieldset>
        <label className="anim"><input type="checkbox" checked={animate} onChange={() => setAnimate((a) => !a)} /> Animate flow</label>
      </div>

      <p className="muted pfd-touch-hint">The whole diagram is shown. Pinch or use the + / - buttons to zoom, drag to pan, tap equipment or a stream (or pick it from the lists below) for details.</p>

      <div className="pfd-layout">
        <div className="pfd-canvas" onKeyDown={onCanvasKey} role="region" aria-label="Interactive process flow diagram. Equipment and stream lists below mirror it.">
          <ReactFlow
            key={`${active?.case_id ?? 'none'}-${hi}`}
            nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
            onNodeClick={onNodeClick} onEdgeClick={onEdgeClick} onPaneClick={() => setSel(null)}
            onEdgeMouseEnter={(ev, e) => setHover({ id: e.id, x: ev.clientX, y: ev.clientY })}
            onEdgeMouseMove={(ev, e) => setHover({ id: e.id, x: ev.clientX, y: ev.clientY })}
            onEdgeMouseLeave={() => setHover(null)}
            nodesDraggable={false} nodesConnectable={false} elementsSelectable
            fitView fitViewOptions={{ padding: 0.03, maxZoom: 1.5, minZoom: 0.15 }} minZoom={0.15} maxZoom={2.5} proOptions={{ hideAttribution: true }} autoPanOnNodeFocus={false}
          >
            <Background gap={24} />
            <Controls showInteractive={false} />
            <MiniMap position="bottom-left" style={{ width: 170, height: 105, marginLeft: 56 }} pannable zoomable nodeStrokeWidth={2} nodeColor={(n) => (n.type === 'equipment' ? '#38bdf8' : 'transparent')} maskColor="rgba(0,0,0,0.35)" />
          </ReactFlow>
          {hover && hoverEdge && (
            <div className="edge-tip" style={{ left: hover.x + 14, top: hover.y + 14 }} role="tooltip">
              <strong>{hoverEdge.id}</strong> {hoverEdge.data?.stream.name}
              <div>T <Value v={hoverEdge.data?.result?.temperature_C} unit={'\u00B0C'} source={src} showSource={false} /> | P <Value v={hoverEdge.data?.result?.pressure_bar} unit="bar" source={src} showSource={false} /></div>
              <div>Flow <Value v={hoverEdge.data?.result?.mole_flow_kmol_h} unit="kmol/h" source={src} showSource={false} /></div>
              <div>{Object.entries(hoverEdge.data?.result?.mole_frac ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([c, y]) => `${c} ${fmt(y, 3)}`).join(', ') || `composition ${NA}`}</div>
            </div>
          )}
          <div className="pfd-src" title="Provenance of every value drawn on the diagram">
            Values: <SourceBadge source={src} />
            {active && <span className="muted">case {active.case_id}</span>}
            {active ? (active.status.converged ? <StatusPill kind="ok">Converged</StatusPill> : <StatusPill kind="error">Not converged</StatusPill>) : <StatusPill kind="neutral">No result</StatusPill>}
          </div>
          {sel && (
            <div className={`pfd-side ${sideCls}`}>
              {selBlock && <BlockPanel {...common} block={selBlock.data.block} result={selBlock.data.result} />}
              {selStream && (
                <StreamPanel {...common} stream={selStream.data!.stream} result={selStream.data!.result} destLabel={streamDest(selStream.data!.stream, hi)} />
              )}
            </div>
          )}
        </div>
        <div className="legend" aria-label="Legend">
          {colorBy === 'component' ? (
            <>
              {['NH3', 'H2', 'N2', 'H2O', 'O2'].map((c) => (<span key={c}><i style={{ background: COMPONENT_COLOR[c] }} />{c}-rich</span>))}
              <span className="muted">(dominant mole fraction; line width ~ sqrt(mass flow))</span>
            </>
          ) : (
            <span><i className="grad" /> cold {'→'} hot (min-max of this case)</span>
          )}
          <span>Dashed boxes: process sections</span>
          <span>Q = duty (+ heat added), W = shaft power</span>
          <span className="muted">Click equipment or a stream for details; Tab + Enter works too; Esc closes. Panel opens on the side away from the selection.</span>
        </div>
      </div>
      {!sel && <p className="muted pfd-hint">Select equipment or a stream to see role, duty, outlet conditions and composition. Equipment and stream lists below are keyboard accessible.</p>}
      <div className="card lists">
        <div>
          <h2>Equipment</h2>
          <ul>{equip.map((n) => (<li key={n.id}><button type="button" className="linkbtn" aria-pressed={sel?.kind === 'block' && sel.id === n.id} onClick={() => setSel({ kind: 'block', id: n.id })}>{n.id} - {n.data.block.name}</button></li>))}</ul>
        </div>
        <div>
          <h2>Streams</h2>
          <ul>{streamEdges.map((e) => (<li key={e.id}><button type="button" className="linkbtn" aria-pressed={sel?.kind === 'stream' && sel.id === e.id} onClick={() => setSel({ kind: 'stream', id: e.id })}>{e.id} - {e.data?.stream.name}</button></li>))}</ul>
        </div>
      </div>
    </div>
  )
}

export default function PfdPage() {
  return (
    <section className="page pfd-page-wrap">
      <h1>Process Flow Diagram</h1>
      <PfdExplorer />
    </section>
  )
}





