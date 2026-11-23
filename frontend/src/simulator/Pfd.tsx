import { memo, useEffect, useMemo, useRef, type KeyboardEvent, type ReactNode } from 'react'
import type { SimData } from '../sim'
import type { CaseResult } from './model'
import { BED, BED_PATH, particleCount, pathD, pointAt, polyLength, SPECIES_COLOR, speciesOf, STREAM_NAMES, STREAMS, streamViews, UNITS, VIEW, type P, type StreamGeom, type StreamView } from './pfdData'

const SPEED = 55 // px per second along every stream (density, not speed, carries the flow)

interface Props {
  c: CaseResult
  d: SimData
  playing: boolean
  selected: string | null
  onSelect: (id: string) => void
}

function activeStreams(hi: boolean): StreamGeom[] {
  return STREAMS.filter((s) => (hi ? !s.bypassOnly : !s.hiOnly))
}

const UNIT_ORDER = UNITS.map((u) => u.id)

/** Engineering-style process flow diagram with flow particles (steady-state solution, not a transient simulation). */
export const Pfd = memo(function Pfd({ c, d, playing, selected, onSelect }: Props) {
  const hi = c.state.heat_integration
  const mem = c.state.purification === 'membrane'
  const kin = c.state.reactor !== 'equilibrium'
  const views = useMemo(() => streamViews(c, d), [c, d])
  const geoms = useMemo(() => activeStreams(hi), [hi])
  const maxFlow = Math.max(...geoms.map((g) => views[g.id]?.flow ?? 0))
  const prof = c.out.reactor.pfr.profiles
  const Xout = c.out.reactor.conversion.value

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

  const keyNav = (id: string) => (e: KeyboardEvent<SVGGElement>) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(id); return }
    const i = UNIT_ORDER.indexOf(id)
    if (i < 0) return
    let j = -1
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') j = (i + 1) % UNIT_ORDER.length
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') j = (i - 1 + UNIT_ORDER.length) % UNIT_ORDER.length
    if (j >= 0) { e.preventDefault(); (document.querySelector(`[data-unit="${UNIT_ORDER[j]}"]`) as SVGGElement | null)?.focus() }
  }
  const unitProps = (id: string, label: string) => ({
    'data-unit': id, role: 'button', tabIndex: 0, 'aria-pressed': selected === id, 'aria-label': label,
    className: `sim-unit ${selected === id ? 'is-selected' : ''}`, onClick: () => onSelect(id), onKeyDown: keyNav(id),
  })
  const U = (id: string, label: string, children: ReactNode, extra = '') => {
    const p = unitProps(id, label)
    return <g {...p} className={`${p.className} ${extra}`}>{children}</g>
  }

  // bed colour gradient from the computed profile (equilibrium mode: the outlet value only)
  const stops = kin ? prof.conversion.filter((_, i, a) => i % Math.max(1, Math.floor(a.length / 12)) === 0 || i === a.length - 1) : [0, Xout]
  const mixCol = (x: number) => `color-mix(in srgb, var(--c-h2) ${(Math.max(0, Math.min(1, x)) * 100).toFixed(0)}%, var(--c-nh3))`

  return (
    <svg className={`sim-pfd ${playing ? 'is-playing' : 'is-paused'}`} viewBox={`0 0 ${VIEW.w} ${VIEW.h}`} role="group" aria-label="Process flow diagram of the ammonia cracker. Select a unit or a stream for its values.">
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

      {/* legend */}
      <g className="sim-legend" aria-hidden="true" transform="translate(14 14)">
        {(['NH3', 'H2', 'N2', 'H2O', 'O2'] as const).map((k, i) => (
          <g key={k} transform={`translate(${i * 62} 0)`}><circle cx="6" cy="6" r="5" fill={SPECIES_COLOR[k]} /><text x="15" y="10">{k}</text></g>
        ))}
        <text x="0" y="30" className="sim-legend-note">Dot colour = species; dot density = molar flow</text>
      </g>

      {/* furnace box and glow */}
      <g aria-hidden="true">
        <rect x="650" y="118" width="170" height="302" rx="6" className="sim-furnace" />
        <rect x="650" y="118" width="170" height="302" rx="6" fill="url(#sim-glow)" className={playing ? 'sim-glow-anim' : ''} />
        <text x="660" y="136" className="sim-tag">FURNACE</text>
      </g>

      {/* streams */}
      {geoms.map((g) => {
        const nm = STREAM_NAMES[g.id]
        const sel = selected === g.id
        return (
          <g key={`${g.id}-${g.pts[0].join()}`} data-stream={g.id} role="button" tabIndex={0} aria-pressed={sel}
            aria-label={`Stream ${g.id}, ${nm.name}, from ${nm.from} to ${nm.to}`} className={`sim-stream st-${g.id} ${sel ? 'is-selected' : ''} ${g.bypassOnly ? 'is-bypass' : ''}`}
            onClick={() => onSelect(g.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(g.id) } }}>
            <path d={pathD(g.pts)} className="sim-hit" />
            <path d={pathD(g.pts)} className="sim-line" markerEnd="url(#sim-arrow)" />
            {!playing ? <path d={pathD(g.pts)} className="sim-dash" /> : null}
            <g className="sim-stag" transform={`translate(${g.tag[0]} ${g.tag[1]})`}>
              <rect x={-(g.id.length * 3.6 + 6)} y="-8" width={g.id.length * 7.2 + 12} height="16" rx="8" />
              <text textAnchor="middle" y="4">{g.id}</text>
            </g>
          </g>
        )
      })}

      {/* units */}
      {U('TANK', 'Liquid ammonia storage, FEED', <>
        <rect x="18" y="330" width="74" height="60" rx="26" fill="url(#sim-steel)" className="sim-shell" />
        <line x1="30" y1="372" x2="80" y2="372" className="sim-liquid" />
        <text x="55" y="410" textAnchor="middle" className="sim-label">NH3 storage</text>
        <text x="55" y="424" textAnchor="middle" className="sim-tag">liquid</text>
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
        <text x="764" y="178" className="sim-xlabel">X {Number.isFinite(Xout) ? `${(Xout * 100).toFixed(1)} %` : 'n/a'}</text>
        <text x="764" y="322" className="sim-xlabel">X 0 %</text>
        <text x="764" y="250" className="sim-label sim-label-l">Reactor</text>
        <text x="764" y="264" className="sim-tag">CRACKER</text>
      </>)}
      {U('BURNER', 'Furnace burner, BURNER', <>
        <path d="M716 414 C 712 398 724 394 722 382 C 730 390 734 386 733 376 C 744 388 748 402 742 414 Z" className={`sim-flame ${playing ? 'is-live' : ''}`} />
        <rect x="704" y="414" width="52" height="6" className="sim-shell" />
        <text x="764" y="398" className="sim-label sim-label-l">Burner</text>
        <text x="764" y="411" className="sim-tag">BURNER</text>
      </>)}
      {U('COOLER', 'Cracked-gas cooler, COOLER', <>
        <rect x="880" y="52" width="70" height="36" rx="18" fill="url(#sim-steel)" className="sim-shell" />
        <path d="M892 70 l7 -8 l7 16 l7 -16 l7 16 l7 -16 l7 16 l4 -8" className="sim-coil sim-coil-cold" />
        <text x="915" y="106" textAnchor="middle" className="sim-label">Cooler</text>
        <text x="915" y="120" textAnchor="middle" className="sim-tag">COOLER</text>
      </>)}
      {U('PSA', mem ? 'Hydrogen purification, Pd-Ag membrane, not modelled in the browser' : 'Hydrogen purification, pressure-swing adsorption, PSA', mem ? <>
        <rect x="1000" y="108" width="60" height="104" rx="6" fill="url(#sim-steel-h)" className="sim-shell" />
        <line x1="1030" y1="114" x2="1030" y2="206" className="sim-membrane" />
        <text x="1068" y="186" className="sim-label sim-label-l">Membrane</text>
        <text x="1068" y="199" className="sim-tag">not modelled</text>
      </> : <>
        <rect x="1002" y="108" width="24" height="104" rx="11" fill="url(#sim-steel-h)" className="sim-shell" />
        <rect x="1034" y="108" width="24" height="104" rx="11" fill="url(#sim-steel-h)" className="sim-shell" />
        <path d="M1007 128 H1021 M1007 148 H1021 M1007 168 H1021 M1007 188 H1021 M1039 128 H1053 M1039 148 H1053 M1039 168 H1053 M1039 188 H1053" className="sim-bedgrid" />
        <text x="1068" y="186" className="sim-label sim-label-l">PSA</text>
        <text x="1068" y="199" className="sim-tag">PSA</text>
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
        <text x="983" y="160" textAnchor="middle" className="sim-tag">flue gas</text>
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
    </svg>
  )
})
