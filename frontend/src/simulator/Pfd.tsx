import { memo, useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import type { SimData } from '../sim'
import { formatValue, type CaseResult } from './model'
import { SimBadge } from './Outputs'
import {
  BED, BED_PATH, labelValue, particleCount, pathD, pointAt, polyLength, SPECIES_COLOR, speciesOf, STREAM_NAMES, STREAM_ORDER, STREAMS, streamViews,
  UNITS, unitViews, VIEW, type Fact, type P, type StreamGeom, type StreamView,
} from './pfdData'

const SPEED = 55 // px per second along every stream (density, not speed, carries the flow)

interface Props {
  c: CaseResult
  d: SimData
  playing: boolean
  selected: string | null
  onSelect: (id: string) => void
  /** print flow (kmol/h) on the streams and duty (kW) under the heat units */
  showValues?: boolean
  /** ids kept at full strength (guided tour); null or empty: nothing dimmed */
  focus?: string[] | null
}

function activeStreams(hi: boolean): StreamGeom[] {
  return STREAMS.filter((s) => (hi ? !s.bypassOnly : !s.hiOnly))
}

/** Keyboard order: units, then streams (arrow keys, Home, End). */
export const ITEM_ORDER = [...UNITS.map((u) => u.id), ...STREAM_ORDER]

/** Where the duty value of a unit is printed (x, y, anchor) under "Show values". */
const UNIT_VAL: Record<string, [number, number, 'middle' | 'start']> = {
  PUMP: [150, 427, 'middle'], VAPORIZR: [254, 427, 'middle'], FEHE: [430, 427, 'middle'], HEATER: [562, 427, 'middle'],
  CRACKER: [762, 280, 'start'], BURNER: [762, 436, 'start'], COOLER: [915, 135, 'middle'], FLUEHX: [902, 317, 'middle'],
}

/** Content of the diagram tooltip of a unit or a stream: the same facts as its panel. */
export function tooltipModel(id: string, units: ReturnType<typeof unitViews>, streams: Record<string, StreamView>): { title: string; sub: string; facts: Fact[] } | null {
  const u = units[id]
  if (u) return { title: u.title, sub: u.bypassed ? 'Bypassed: heat recovery is off.' : u.notModelled ? 'Not modelled in the browser.' : '', facts: u.facts }
  const s = streams[id]
  const n = STREAM_NAMES[id]
  if (!s || !n) return null
  return { title: `Stream ${id}: ${n.name}`, sub: `From ${n.from} to ${n.to}.`, facts: s.facts }
}

/** Engineering-style process flow diagram with flow particles (steady-state solution, not a transient simulation). */
export const Pfd = memo(function Pfd({ c, d, playing, selected, onSelect, showValues = false, focus = null }: Props) {
  const hi = c.state.heat_integration
  const mem = c.state.purification === 'membrane'
  const kin = c.state.reactor !== 'equilibrium'
  const views = useMemo(() => streamViews(c, d), [c, d])
  const uviews = useMemo(() => unitViews(c, d), [c, d])
  const geoms = useMemo(() => activeStreams(hi), [hi])
  const maxFlow = Math.max(...geoms.map((g) => views[g.id]?.flow ?? 0))
  const prof = c.out.reactor.pfr.profiles
  const Xout = c.out.reactor.conversion.value
  const dim = (id: string) => (focus && focus.length && !focus.includes(id) ? ' is-dim' : '')

  // particles: positions are written by the animation loop through refs (no React re-render per frame)
  const parts = useMemo(() => {
    const list: { key: string; stream: string; pts: P[]; len: number; off: number; color: string; bed?: boolean }[] = []
    for (const g of geoms) {
      const v: StreamView | undefined = views[g.id]
      if (!v) continue
      const len = polyLength(g.pts)
      const n = particleCount(len, v.flow, maxFlow)
      for (let i = 0; i < n; i++) list.push({ key: `${g.id}-${g.pts[0].join()}-${i}`, stream: g.id, pts: g.pts, len, off: (i / n) * len, color: SPECIES_COLOR[speciesOf(i, v.mix)] })
    }
    const blen = polyLength(BED_PATH)
    const nb = particleCount(blen, views.S4.flow, maxFlow, 14)
    for (let i = 0; i < nb; i++) list.push({ key: `bed-${i}`, stream: 'CRACKER', pts: BED_PATH, len: blen, off: (i / nb) * blen, color: SPECIES_COLOR.NH3, bed: true })
    return list
  }, [geoms, views, maxFlow])

  const refs = useRef<(SVGCircleElement | null)[]>([])
  const profRef = useRef({ X: prof.conversion, kin, Xout })
  profRef.current = { X: kin ? prof.conversion : prof.conversion.map((_, i, a) => (i / Math.max(1, a.length - 1)) * Xout), kin, Xout }

  useEffect(() => {
    if (!playing) return
    let raf = 0
    let t0 = performance.now()
    let acc = 0
    const step = (now: number) => {
      acc += Math.min(0.05, (now - t0) / 1000)
      t0 = now
      const X = profRef.current.X
      for (let i = 0; i < parts.length; i++) {
        const el = refs.current[i]
        if (!el) continue
        const p = parts[i]
        const s = (p.off + acc * SPEED * (p.bed ? 0.45 : 1)) % p.len
        const [x, y] = pointAt(p.pts, s)
        el.setAttribute('cx', x.toFixed(1))
        el.setAttribute('cy', y.toFixed(1))
        if (p.bed) {
          // colour follows the computed conversion profile: an NH3 particle turns into H2 / N2 with probability X(z)
          const xloc = X[Math.min(X.length - 1, Math.round((s / p.len) * (X.length - 1)))] ?? 0
          const u = ((i * 0.6180339887) % 1)
          el.setAttribute('fill', u < xloc ? (u < xloc * 0.75 ? SPECIES_COLOR.H2 : SPECIES_COLOR.N2) : SPECIES_COLOR.NH3)
        }
      }
      raf = requestAnimationFrame(step)
    }
    const start = () => { t0 = performance.now(); raf = requestAnimationFrame(step) }
    const onVis = () => { cancelAnimationFrame(raf); if (!document.hidden) start() }
    document.addEventListener('visibilitychange', onVis)
    if (!document.hidden) start()
    return () => { cancelAnimationFrame(raf); document.removeEventListener('visibilitychange', onVis) }
  }, [playing, parts])

  // ---------------------------------------------------------------- tooltip (hover, focus, pin)
  const wrap = useRef<HTMLDivElement>(null)
  const tipRef = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<{ id: string; pinned: boolean } | null>(null)
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const elOf = (id: string) => wrap.current?.querySelector<SVGGElement>(`[data-unit="${id}"], [data-stream="${id}"]`) ?? null
  const show = (id: string) => setTip((t) => (t && t.pinned && t.id !== id ? t : { id, pinned: t?.id === id ? t.pinned : false }))
  const hide = (id: string) => window.setTimeout(() => {
    if (tipRef.current && tipRef.current.contains(document.activeElement)) return
    setTip((t) => (t && t.id === id && !t.pinned ? null : t))
  }, 0)
  const closeTip = (back = true) => { const id = tip?.id; setTip(null); if (back && id) elOf(id)?.focus() }
  useLayoutEffect(() => {
    if (!tip || !wrap.current || !tipRef.current) { setPos(null); return }
    const el = elOf(tip.id)
    if (!el) { setPos(null); return }
    const wr = wrap.current.getBoundingClientRect()
    const er = el.getBoundingClientRect()
    const box = wrap.current.parentElement
    // the card stays inside the diagram box: at most the box height (it scrolls inside), clamped to the visible part of the box
    const maxH = Math.max(120, wr.height - 8)
    tipRef.current.style.maxHeight = `${maxH}px`
    const tw = tipRef.current.offsetWidth, th = Math.min(maxH, tipRef.current.offsetHeight)
    const left0 = box ? box.scrollLeft + 6 : 6
    const right0 = box ? box.scrollLeft + box.clientWidth - tw - 6 : wr.width - tw - 6
    const x = Math.max(left0, Math.min(right0, er.left - wr.left + er.width / 2 - tw / 2))
    let y = er.bottom - wr.top + 8
    if (y + th > wr.height - 4) y = er.top - wr.top - th - 8
    y = Math.max(4, Math.min(wr.height - th - 4, y))
    setPos({ x, y })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tip, c])
  const tm = tip ? tooltipModel(tip.id, uviews, views) : null

  const keyNav = (id: string) => (e: KeyboardEvent<SVGGElement>) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(id); return }
    if (e.key === 'Escape' && tip) { e.preventDefault(); closeTip(); return }
    if (e.key === 'p' || e.key === 'P') { e.preventDefault(); setTip({ id, pinned: !(tip?.id === id && tip.pinned) }); return }
    const present = ITEM_ORDER.filter((x) => elOf(x))
    const i = present.indexOf(id)
    if (i < 0) return
    let j = -1
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') j = (i + 1) % present.length
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') j = (i - 1 + present.length) % present.length
    if (e.key === 'Home') j = 0
    if (e.key === 'End') j = present.length - 1
    if (j >= 0) { e.preventDefault(); elOf(present[j])?.focus() }
  }
  const hover = (id: string) => ({ onMouseEnter: () => show(id), onMouseLeave: () => hide(id), onFocus: () => show(id), onBlur: () => hide(id) })
  /** a click selects; a click on the item that is already selected pins (or unpins) its card */
  const click = (id: string) => () => { if (selected === id) setTip({ id, pinned: !(tip?.id === id && tip.pinned) }); onSelect(id) }
  const unitProps = (id: string, label: string) => ({
    'data-unit': id, role: 'button', tabIndex: 0, 'aria-pressed': selected === id, 'aria-label': label, 'aria-describedby': tip?.id === id ? 'sim-tip' : undefined,
    className: `sim-unit ${selected === id ? 'is-selected' : ''}${dim(id)}`, onClick: click(id), onKeyDown: keyNav(id), ...hover(id),
  })
  const U = (id: string, label: string, children: ReactNode, extra = '') => {
    const p = unitProps(id, label)
    const lv = showValues ? labelValue(uviews[id]?.facts, 'kW') : null
    const at = UNIT_VAL[id]
    return (
      <g {...p} className={`${p.className} ${extra}`}>
        {children}
        {lv && at ? <text x={at[0]} y={at[1]} textAnchor={at[2]} className="sim-val">{lv.text} <tspan className="sim-mark">{lv.mark}</tspan></text> : null}
      </g>
    )
  }

  // bed colour gradient from the computed profile (equilibrium mode: the outlet value only)
  const stops = kin ? prof.conversion.filter((_, i, a) => i % Math.max(1, Math.floor(a.length / 12)) === 0 || i === a.length - 1) : [0, Xout]
  const mixCol = (x: number) => `color-mix(in srgb, var(--c-h2) ${(Math.max(0, Math.min(1, x)) * 100).toFixed(0)}%, var(--c-nh3))`

  return (
    <div className="sim-pfd-wrap" ref={wrap}>
      <svg className={`sim-pfd ${playing ? 'is-playing' : 'is-paused'}${focus && focus.length ? ' is-touring' : ''}`} viewBox={`0 0 ${VIEW.w} ${VIEW.h}`} role="group"
        aria-label="Process flow diagram of the ammonia cracker. Select a unit or a stream for its values. Arrow keys, Home and End move between items; P pins the tooltip, Escape closes it.">
        <defs>
          <marker id="sim-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--text-2)" /></marker>
          <linearGradient id="sim-steel" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="var(--surface-2)" /><stop offset="0.5" stopColor="var(--surface)" /><stop offset="1" stopColor="var(--surface-2)" />
          </linearGradient>
          <linearGradient id="sim-steel-h" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor="var(--surface-2)" /><stop offset="0.5" stopColor="var(--surface)" /><stop offset="1" stopColor="var(--surface-2)" />
          </linearGradient>
          <linearGradient id="sim-bed" x1="0" x2="0" y1="1" y2="0">
            {stops.map((x, i) => <stop key={i} offset={stops.length > 1 ? i / (stops.length - 1) : 0} style={{ stopColor: mixCol(x) }} />)}
          </linearGradient>
          <radialGradient id="sim-glow" cx="0.5" cy="0.85" r="0.75"><stop offset="0" stopColor="var(--c-heat)" stopOpacity="0.28" /><stop offset="1" stopColor="var(--c-heat)" stopOpacity="0" /></radialGradient>
        </defs>

        {/* legend (upper left; on a phone an HTML legend above the diagram replaces it) */}
        <g className="sim-legend" aria-hidden="true" transform="translate(16 18)">
          {(['NH3', 'H2', 'N2', 'H2O', 'O2'] as const).map((k, i) => (
            <g key={k} transform={`translate(${i * 66} 0)`}><circle cx="6" cy="6" r="5.5" fill={SPECIES_COLOR[k]} /><text x="16" y="11">{k}</text></g>
          ))}
          <text x="0" y="34" className="sim-legend-note">Dot colour: species. Dot density: molar flow.</text>
          <text x="0" y="54" className="sim-legend-note">Dashed: bypass, bypassed or not modelled.</text>
          {showValues ? <>
            <text x="0" y="74" className="sim-legend-note">Values: streams kmol/h, units kW. Source:</text>
            <text x="0" y="94" className="sim-legend-note">A Aspen, G Aspen grid, B browser model,</text>
            <text x="0" y="114" className="sim-legend-note">E extrapolation, S assumed.</text>
          </> : null}
        </g>

        {/* furnace box and glow */}
        <g aria-hidden="true">
          <rect x="650" y="118" width="190" height="302" rx="6" className="sim-furnace" />
          <rect x="650" y="118" width="190" height="302" rx="6" fill="url(#sim-glow)" className={playing ? 'sim-glow-anim' : ''} />
          <text x="660" y="137" className="sim-tag">FURNACE</text>
        </g>

        {/* streams (lines and hit areas; the tags are drawn after the particles) */}
        {geoms.map((g) => {
          const nm = STREAM_NAMES[g.id]
          const sel = selected === g.id
          return (
            <g key={`${g.id}-${g.pts[0].join()}`} data-stream={g.id} role="button" tabIndex={0} aria-pressed={sel} aria-describedby={tip?.id === g.id ? 'sim-tip' : undefined}
              aria-label={`Stream ${g.id}, ${nm.name}, from ${nm.from} to ${nm.to}`} className={`sim-stream st-${g.id} ${sel ? 'is-selected' : ''} ${g.bypassOnly ? 'is-bypass' : ''}${dim(g.id)}`}
              onClick={click(g.id)} onKeyDown={keyNav(g.id)} {...hover(g.id)}>
              <path d={pathD(g.pts)} className="sim-hit" />
              <path d={pathD(g.pts)} className="sim-line" markerEnd="url(#sim-arrow)" />
              {!playing ? <path d={pathD(g.pts)} className="sim-dash" /> : null}
            </g>
          )
        })}

        {/* units */}
        {U('TANK', 'Liquid ammonia storage, FEED', <>
          <rect x="18" y="330" width="74" height="60" rx="26" fill="url(#sim-steel)" className="sim-shell" />
          <line x1="30" y1="372" x2="80" y2="372" className="sim-liquid" />
          <text x="55" y="410" textAnchor="middle" className="sim-label">NH3 storage</text>
          <text x="55" y="425" textAnchor="middle" className="sim-tag">liquid</text>
        </>)}
        {U('PUMP', 'Feed pump, PUMP', <>
          <circle cx="150" cy="360" r="17" fill="url(#sim-steel)" className="sim-shell" />
          <path d="M142 350 L162 360 L142 370 Z" className="sim-sym" />
          <text x="150" y="398" textAnchor="middle" className="sim-label">Feed pump</text>
          <text x="150" y="412" textAnchor="middle" className="sim-tag">PUMP</text>
        </>)}
        {U('VAPORIZR', 'Vaporiser, VAPORIZR', <>
          <rect x="214" y="342" width="80" height="36" rx="18" fill="url(#sim-steel)" className="sim-shell" />
          <path d="M226 360 l8 -9 l8 18 l8 -18 l8 18 l8 -18 l8 18 l8 -9" className="sim-coil" />
          <text x="254" y="398" textAnchor="middle" className="sim-label">Vaporiser</text>
          <text x="254" y="412" textAnchor="middle" className="sim-tag">VAPORIZR</text>
        </>)}
        {U('FEHE', hi ? 'Feed-effluent heat exchanger, FEHE' : 'Feed-effluent heat exchanger, FEHE, bypassed because heat recovery is off', <>
          <rect x="384" y="340" width="92" height="40" rx="20" fill="url(#sim-steel)" className="sim-shell" />
          <path d="M396 352 H466 M396 360 H466 M396 368 H466" className="sim-tubes" />
          <line x1="400" y1="340" x2="400" y2="334" className="sim-nozzle" /><line x1="460" y1="340" x2="460" y2="334" className="sim-nozzle" />
          <text x="430" y="398" textAnchor="middle" className="sim-label">Feed-effluent exchanger</text>
          <text x="430" y="412" textAnchor="middle" className="sim-tag">{hi ? 'FEHE' : 'FEHE BYPASSED'}</text>
        </>, hi ? '' : 'is-bypassed')}
        {U('HEATER', 'Preheater, HEATER', <>
          <rect x="530" y="340" width="64" height="40" rx="4" fill="url(#sim-steel-h)" className="sim-shell" />
          <path d="M540 372 q6 -14 12 0 q6 -14 12 0 q6 -14 12 0 q6 -14 12 0" className="sim-flame-line" />
          <text x="562" y="398" textAnchor="middle" className="sim-label">Preheater</text>
          <text x="562" y="412" textAnchor="middle" className="sim-tag">HEATER</text>
        </>)}
        {U('CRACKER', 'Cracking reactor, packed bed, CRACKER', <>
          <rect x="704" y="150" width="52" height="192" rx="24" fill="url(#sim-steel-h)" className="sim-shell" />
          <rect x={BED.x} y={BED.y} width={BED.w} height={BED.h} rx="3" fill="url(#sim-bed)" className="sim-bed" />
          <path d={`M${BED.x} ${BED.y} H${BED.x + BED.w} M${BED.x} ${BED.y + BED.h} H${BED.x + BED.w}`} className="sim-bedgrid" />
          <text x="764" y="170" className="sim-tag">X outlet</text>
          <text x="764" y="186" className="sim-xlabel">{Number.isFinite(Xout) ? `${(Xout * 100).toFixed(1)} %` : 'n/a'}</text>
          <text x="764" y="314" className="sim-tag">X inlet</text>
          <text x="764" y="330" className="sim-xlabel">0 %</text>
          <text x="764" y="248" className="sim-label sim-label-l">Reactor</text>
          <text x="764" y="263" className="sim-tag">CRACKER</text>
        </>)}
        {U('BURNER', 'Furnace burner, BURNER', <>
          <path d="M716 414 C 712 398 724 394 722 382 C 730 390 734 386 733 376 C 744 388 748 402 742 414 Z" className={`sim-flame ${playing ? 'is-live' : ''}`} />
          <rect x="704" y="414" width="52" height="6" className="sim-shell" />
          <text x="764" y="396" className="sim-label sim-label-l">Burner</text>
          <text x="764" y="411" className="sim-tag">BURNER</text>
        </>)}
        {U('COOLER', 'Cracked-gas cooler, COOLER', <>
          <rect x="880" y="52" width="70" height="36" rx="18" fill="url(#sim-steel)" className="sim-shell" />
          <path d="M892 70 l7 -8 l7 16 l7 -16 l7 16 l7 -16 l7 16 l4 -8" className="sim-coil sim-coil-cold" />
          <text x="915" y="106" textAnchor="middle" className="sim-label">Cooler</text>
          <text x="915" y="121" textAnchor="middle" className="sim-tag">COOLER</text>
        </>)}
        {U('PSA', mem ? 'Hydrogen purification, Pd-Ag membrane, not modelled in the browser' : 'Hydrogen purification, pressure-swing adsorption, PSA', mem ? <>
          <rect x="1000" y="108" width="60" height="104" rx="6" fill="url(#sim-steel-h)" className="sim-shell" />
          <line x1="1030" y1="114" x2="1030" y2="206" className="sim-membrane" />
          <text x="1068" y="186" className="sim-label sim-label-l">Membrane</text>
          <text x="1068" y="201" className="sim-tag">not modelled</text>
        </> : <>
          <rect x="1002" y="108" width="24" height="104" rx="11" fill="url(#sim-steel-h)" className="sim-shell" />
          <rect x="1034" y="108" width="24" height="104" rx="11" fill="url(#sim-steel-h)" className="sim-shell" />
          <path d="M1007 128 H1021 M1007 148 H1021 M1007 168 H1021 M1007 188 H1021 M1039 128 H1053 M1039 148 H1053 M1039 168 H1053 M1039 188 H1053" className="sim-bedgrid" />
          <text x="1068" y="186" className="sim-label sim-label-l">PSA</text>
          <text x="1068" y="201" className="sim-tag">PSA</text>
        </>, mem ? 'is-notmodelled' : '')}
        {U('FLUEHX', 'Flue-gas heat recovery, FLUEHX', <>
          <rect x="870" y="232" width="64" height="36" rx="18" fill="url(#sim-steel)" className="sim-shell" />
          <path d="M880 250 l7 -8 l7 16 l7 -16 l7 16 l7 -16 l7 16 l4 -8" className="sim-coil" />
          <rect x="975" y="190" width="16" height="96" rx="2" fill="url(#sim-steel-h)" className="sim-shell" />
          <text x="902" y="288" textAnchor="middle" className="sim-label">Flue-gas cooler</text>
          <text x="902" y="302" textAnchor="middle" className="sim-tag">FLUEHX, stack</text>
        </>)}

        {/* end labels */}
        <g aria-hidden="true" className="sim-ends">
          <text x="1168" y="122" textAnchor="end" className="sim-label sim-h2">H2 product</text>
          <text x="969" y="170" textAnchor="end" className="sim-tag">flue gas out</text>
          <text x="596" y="448" textAnchor="end" className="sim-tag">air</text>
        </g>

        {/* particles (only while playing) */}
        {playing ? (
          <g className="sim-particles" aria-hidden="true">
            {parts.map((p, i) => {
              const [x, y] = pointAt(p.pts, p.off)
              return <circle key={p.key} ref={(el) => { refs.current[i] = el }} className="pfd-particle" cx={x} cy={y} r={p.bed ? 3 : 3.4} fill={p.color} />
            })}
          </g>
        ) : null}

        {/* stream tags and values, above the particles so that the dots never cross them */}
        <g className="sim-tags" aria-hidden="true">
          {geoms.map((g) => {
            const lv = showValues && g.val ? labelValue(views[g.id]?.facts, 'kmol/h') : null
            const w = g.id.length * 7.6 + 16
            return (
              <g key={`t-${g.id}-${g.pts[0].join()}`} className={`sim-stag ${selected === g.id ? 'is-selected' : ''}${dim(g.id)}`}>
                <g transform={`translate(${g.tag[0]} ${g.tag[1]})`}>
                  <rect x={-w / 2} y="-9" width={w} height="18" rx="9" />
                  <text textAnchor="middle" y="4.5">{g.id}</text>
                </g>
                {lv && g.val ? <text x={g.val[0]} y={g.val[1]} textAnchor="middle" className="sim-val">{lv.text} <tspan className="sim-mark">{lv.mark}</tspan></text> : null}
              </g>
            )
          })}
        </g>
      </svg>
      {tip && tm ? (
        <div ref={tipRef} id="sim-tip" className={`sim-tip ${tip.pinned ? 'is-pinned' : ''}`} role="tooltip" style={pos ? { left: pos.x, top: pos.y } : { visibility: 'hidden', left: 0, top: 0 }}
          onKeyDown={(e) => { if (e.key === 'Escape') { e.preventDefault(); closeTip() } }}>
          <div className="sim-tip-head">
            <strong>{tm.title}</strong>
            {tip.pinned ? (
              <span className="sim-tip-btns">
                <button type="button" className="sim-tip-btn" onClick={() => setTip({ id: tip.id, pinned: false })}>Unpin</button>
                <button type="button" className="sim-tip-btn" aria-label="Close tooltip" onClick={() => closeTip()}>Close</button>
              </span>
            ) : null}
          </div>
          {tm.sub ? <p className="sim-tip-sub">{tm.sub}</p> : null}
          {tm.facts.length ? (
            <dl className="sim-tip-facts">
              {tm.facts.map((f, i) => (
                <div key={`${f.label}-${i}`}>
                  <dt>{f.label}</dt>
                  <dd>{f.value === null || !Number.isFinite(f.value) ? <span className="sim-nm">not modelled</span> : <span className="sim-num">{formatValue({ value: f.value, kind: f.frac ? 'frac' : 'num', unit: f.unit })}</span>} <SimBadge s={f.value === null ? null : f.source} short /></dd>
                </div>
              ))}
            </dl>
          ) : <p className="sim-tip-sub">No computed values for this item.</p>}
          <p className="sim-tip-hint">{tip.pinned ? 'Pinned. Escape or Close closes it.' : 'Click selects; click again or press P to pin this card.'}</p>
        </div>
      ) : null}
    </div>
  )
})
