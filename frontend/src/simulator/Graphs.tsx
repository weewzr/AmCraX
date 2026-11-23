import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { sweeps, type SimData, type SimInputs, type SourceLabel } from '../sim'
import { splitExtrapolation, toSimInputs, type CaseResult, type SimState } from './model'
import { SimBadge } from './Outputs'

type CostVariable = 'T_C' | 'P_bar' | 'W_kg' | 'psa_h2_recovery' | 'nh3_price_USD_per_t' | 'feed_total_kmol_h'

const axis = { stroke: 'var(--muted)', tick: { fill: 'var(--muted)', fontSize: 12 } }
const tip = { contentStyle: { background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)', fontSize: 12 }, itemStyle: { color: 'var(--text)' }, labelStyle: { color: 'var(--text)' } }
const fmt = (v: unknown) => (typeof v === 'number' ? Number(v.toPrecision(4)) : String(v ?? 'n/a'))
const COLORS = ['var(--primary)', 'var(--accent)', 'var(--c-nh3)', 'var(--c-h2)', 'var(--c-n2)', 'var(--c-o2)']
const A_COLOR = 'var(--muted)'

/** Recompute a sweep a short time after the last change (sweeps run 20-60 simulations; controls stay responsive). */
function useSweep<T>(key: string, fn: () => T, delay = 160): T | null {
  const [v, setV] = useState<{ key: string; val: T } | null>(null)
  useEffect(() => {
    const t = window.setTimeout(() => setV({ key, val: fn() }), v === null ? 0 : delay)
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return v ? v.val : null
}

const worstOf = (pts: { source: SourceLabel }[]): SourceLabel | null => {
  const s = new Set(pts.map((p) => p.source))
  if (!s.size) return null
  for (const k of ['extrapolation', 'interpolation', 'browser-model', 'assumption', 'aspen'] as SourceLabel[]) if (s.has(k)) return k
  return null
}

function ChartCard({ n, id, title, sources, desc, note, limit, controls, children, height = 280 }: { n: number; id: string; title: string; sources: (SourceLabel | null)[]; desc: string
  note: ReactNode; limit: ReactNode; controls?: ReactNode; children: ReactNode; height?: number }) {
  const uniq = [...new Set(sources.filter(Boolean))] as SourceLabel[]
  return (
    <figure className="card chart-card sim-chart" id={id} aria-labelledby={`${id}-t`} data-graph={n}>
      <figcaption>
        <span id={`${id}-t`}><span className="sim-gnum">{n}</span> {title}</span>
        <span className="sim-gbadges">{uniq.map((s) => <SimBadge key={s} s={s} />)}</span>
      </figcaption>
      {controls ? <div className="sim-gctl">{controls}</div> : null}
      <div className="chart-box" style={{ height }} role="img" aria-label={desc}>{children}</div>
      <p className="sim-gnote"><strong>Source.</strong> {note} <strong>Limitation.</strong> {limit}</p>
    </figure>
  )
}

const kineticBase = (s: SimState): SimInputs => toSimInputs({ ...s, reactor: s.reactor === 'equilibrium' ? 'isothermal' : s.reactor }, 2)
const caseKey = (s: SimState | null | undefined) => (s ? JSON.stringify({ ...s, preset: null }) : 'none')

const COST_VARS: { id: CostVariable; label: string; unit: string; values: number[] }[] = [
  { id: 'T_C', label: 'Reactor temperature', unit: 'degC', values: [400, 425, 450, 475, 500, 525, 550, 575, 600, 625, 650, 675, 700, 725, 750, 775, 800] },
  { id: 'P_bar', label: 'Reactor pressure', unit: 'bar', values: [3, 5, 7.5, 10, 12.5, 15, 20, 25, 30, 35, 40, 45, 50] },
  { id: 'W_kg', label: 'Catalyst mass', unit: 'kg', values: [10, 20, 50, 100, 150, 200, 300, 500, 750, 1000] },
  { id: 'psa_h2_recovery', label: 'Hydrogen recovery', unit: '-', values: [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99] },
  { id: 'nh3_price_USD_per_t', label: 'Ammonia price', unit: 'USD/t', values: [100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500] },
  { id: 'feed_total_kmol_h', label: 'Ammonia feed flow', unit: 'kmol/h', values: [10, 25, 50, 100, 150, 200, 300, 400, 500] },
]

export default function Graphs({ d, b, a }: { d: SimData; b: CaseResult; a: CaseResult | null }) {
  const s = b.state
  const ids = d.model.kinetics.law_ids
  const short = (id: string) => d.model.kinetics.laws[id]?.label.replace(/\s*\(.*\)\s*$/, '') ?? id
  const [rateIds, setRateIds] = useState<string[]>(ids)
  const [costVar, setCostVar] = useState<CostVariable>('T_C')
  const [cur, setCur] = useState<'SGD' | 'USD'>('SGD')
  const eq = s.reactor === 'equilibrium'
  const mem = s.purification === 'membrane'
  const kB = caseKey(b.state), kA = caseKey(a?.state)

  // 1. conversion vs temperature
  const g1 = useSweep(`g1|${kB}|${kA}`, () => ({
    b: sweeps.conversionVsTemperature(d, kineticBase(s), 300, 800, 26),
    a: a ? sweeps.conversionVsTemperature(d, kineticBase(a.state), 300, 800, 26).kinetic : null,
  }), 120)
  // 2. rate vs temperature
  const g2 = useSweep(`g2|${s.P_bar}|${rateIds.join()}`, () => sweeps.rateVsTemperature(d, rateIds, s.P_bar, 0.1, 300, 800, 51), 120)
  // 5. hydrogen vs heat input
  const g5 = useSweep(`g5|${kB}|${kA}`, () => ({ b: sweeps.h2VsHeatInput(d, kineticBase(s), 2500, 21), a: a ? sweeps.h2VsHeatInput(d, kineticBase(a.state), 2500, 21) : null }), 220)
  // 6. cost by catalyst and against a variable
  const cv = COST_VARS.find((c) => c.id === costVar)!
  const g6 = useSweep(`g6|${kB}|${costVar}`, () => {
    const base = toSimInputs(s, 2)
    return {
      line: sweeps.costVsVariable(d, base, costVar, cv.values, [s.catalyst_id]).series[s.catalyst_id],
      bars: sweeps.costVsVariable(d, base, 'T_C', [s.T_C], ids).series,
    }
  }, 260)
  // 8. carbon by route
  const g8 = useSweep(`g8|${kB}|${kA}`, () => ({
    b: sweeps.carbonByRoute(d, toSimInputs(s, 2), s.carbon_price_SGD_per_t),
    a: a ? sweeps.carbonByRoute(d, toSimInputs(a.state, 2), a.state.carbon_price_SGD_per_t) : null,
  }), 200)

  const prof = useMemo(() => sweeps.axialProfiles(b.out), [b])
  const profA = useMemo(() => (a ? sweeps.axialProfiles(a.out) : null), [a])
  const eb = useMemo(() => sweeps.energyBalance(b.out), [b])
  const ebA = useMemo(() => (a ? sweeps.energyBalance(a.out) : null), [a])

  const memNote = mem ? <span className="sim-gwarn">Membrane selected: not modelled in the browser, so this graph shows the PSA basis. </span> : null
  const eqNote = eq ? <span className="sim-gwarn">Equilibrium reactor selected: the kinetic curves use the selected catalyst for reference. </span> : null
  const xT = { type: 'number' as const, dataKey: 'x', domain: [300, 800] as [number, number], ...axis }

  // ---------- chart 1 data
  const c1 = g1 ? splitExtrapolation(g1.b.kinetic) : null
  // ---------- chart 2 data
  const c2 = g2 ? Object.fromEntries(Object.entries(g2.series).map(([id, pts]) => [id, splitExtrapolation(pts.map((p) => ({ ...p, y: p.y !== null && p.y > 0 ? p.y : null })))])) : null
  // ---------- chart 3/4 data
  const c3 = splitExtrapolation(prof.conversion_vs_length)
  const c4 = splitExtrapolation(prof.temperature_vs_length)
  const yH2 = b.out.process?.h2_product_kg_h.value ?? null

  const energyData = (eb ?? []).map((r) => ({ label: r.label.replace(/ \(.*\)$/, ''), B: Number.isFinite(r.value) ? r.value : null, A: ebA?.find((x) => x.key === r.key)?.value ?? null }))
  const carbonData = g8 ? g8.b.map((r, i) => ({
    route: r.route, CI: r.ci_kgCO2e_per_kgH2, cost: s.carbon_mode === 'hypothetical' ? r.hypothetical_cost_SGD_per_kg : r.actual_cost_SGD_per_kg,
    CI_A: g8.a ? g8.a[i].ci_kgCO2e_per_kgH2 : null,
  })) : []
  const lineY = (p: { y: number | null; y_SGD: number | null }) => (cur === 'SGD' ? p.y_SGD : p.y)

  return (
    <section className="sim-graphs" aria-labelledby="sim-graphs-h">
      <h2 id="sim-graphs-h" className="sim-h2">Eight graphs of the current case{a ? ' (case A overlaid in grey)' : ''}</h2>
      <p className="sim-graphs-lead">Solid lines: inside the fitted range of the rate law or a stored grid. Dashed lines: extrapolation. Large dot: the current operating point.</p>
      <div className="sim-graph-grid">
        <ChartCard n={1} id="g-conv-T" title="NH3 conversion against temperature" sources={['browser-model', ...(g1 ? [worstOf(g1.b.equilibrium_aspen), worstOf(g1.b.kinetic)] : [])]}
          desc={`Equilibrium and kinetic NH3 conversion from 300 to 800 degC at ${s.P_bar} bar`}
          note={<>{eqNote}Equilibrium: ideal gas (browser) and Aspen RGibbs Peng-Robinson grid (dots, pure NH3). Kinetic: plug-flow outlet, {short(s.catalyst_id)}, {s.W_kg} kg, {s.P_bar} bar.</>}
          limit="The kinetic curve is extrapolated wherever the temperature or pressure leaves the fitted range of the rate law.">
          {g1 && c1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 8, right: 16, bottom: 30, left: 4 }}>
                <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
                <XAxis {...xT} label={{ value: 'Reactor temperature (degC)', position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
                <YAxis {...axis} domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}`} label={{ value: 'Conversion (%)', angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
                <Tooltip {...tip} formatter={fmt} labelFormatter={(v) => `${v} degC`} />
                <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 12 }} />
                <Line data={g1.b.equilibrium_browser} dataKey="y" name="Equilibrium, ideal gas" stroke="var(--c-n2)" dot={false} isAnimationActive={false} strokeWidth={2} />
                <Line data={g1.b.equilibrium_aspen} dataKey="y" name="Equilibrium, Aspen grid" stroke="var(--src-aspen)" strokeWidth={0} dot={{ r: 3 }} isAnimationActive={false} />
                <Line data={c1.fit} dataKey="y" name="Kinetic (fitted range)" stroke="var(--accent)" dot={false} strokeWidth={2.4} isAnimationActive={false} connectNulls={false} />
                <Line data={c1.ext} dataKey="y" name="Kinetic (extrapolation)" stroke="var(--accent)" strokeDasharray="6 4" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls={false} />
                {g1.a ? <Line data={g1.a} dataKey="y" name="Case A kinetic" stroke={A_COLOR} strokeDasharray="2 3" dot={false} isAnimationActive={false} /> : null}
                <ReferenceDot x={s.T_C} y={b.out.reactor.conversion.value} r={6} fill="var(--accent)" stroke="var(--bg)" ifOverflow="extendDomain" />
                {a ? <ReferenceDot x={a.state.T_C} y={a.out.reactor.conversion.value} r={5} fill={A_COLOR} stroke="var(--bg)" /> : null}
              </LineChart>
            </ResponsiveContainer>
          ) : <Pending />}
        </ChartCard>

        <ChartCard n={2} id="g-rate-T" title="Reaction rate against temperature" sources={c2 ? ['browser-model', 'extrapolation'] : []}
          desc={`Rate of NH3 decomposition for the selected catalysts at ${s.P_bar} bar and 10 % conversion`}
          note={<>Rate laws of the selected catalysts at {s.P_bar} bar, gas at 10 % conversion of the baseline feed, ideal gas. Logarithmic axis.</>}
          limit="Most laws were fitted at 1 atm: at higher pressure every point is an extrapolation (dashed)."
          controls={<div className="sim-chips" role="group" aria-label="Catalysts shown">{ids.map((id) => (
            <button key={id} type="button" className="chip" aria-pressed={rateIds.includes(id)} onClick={() => setRateIds((r) => (r.includes(id) ? (r.length > 1 ? r.filter((x) => x !== id) : r) : [...r, id]))}>{short(id)}</button>
          ))}</div>}>
          {c2 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 8, right: 16, bottom: 30, left: 8 }}>
                <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
                <XAxis {...xT} label={{ value: 'Temperature (degC)', position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
                <YAxis {...axis} scale="log" domain={['auto', 'auto']} allowDataOverflow tickFormatter={(v: number) => v.toExponential(0)} width={56}
                  label={{ value: 'mol/(kg s)', angle: -90, position: 'insideLeft', offset: -2, fill: 'var(--muted)' }} />
                <Tooltip {...tip} formatter={fmt} labelFormatter={(v) => `${v} degC`} />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: 11.5 }} />
                {Object.entries(c2).flatMap(([id, sp]) => {
                  const col = COLORS[ids.indexOf(id) % COLORS.length]
                  return [
                    <Line key={`${id}-f`} data={sp.fit} dataKey="y" name={short(id)} stroke={col} dot={false} strokeWidth={2.2} isAnimationActive={false} connectNulls={false} />,
                    <Line key={`${id}-e`} data={sp.ext} dataKey="y" name={`${short(id)} (extrap.)`} legendType="none" stroke={col} strokeDasharray="6 4" dot={false} strokeWidth={1.6} isAnimationActive={false} connectNulls={false} />,
                  ]
                })}
                <ReferenceLine x={s.T_C} stroke="var(--accent)" strokeDasharray="3 3" label={{ value: 'current T', fill: 'var(--accent)', fontSize: 11, position: 'insideTopRight' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <Pending />}
        </ChartCard>

        <ChartCard n={3} id="g-conv-z" title="Conversion along the reactor" sources={[worstOf(prof.conversion_vs_length), prof.aspen ? 'aspen' : null]}
          desc="NH3 conversion against axial position in the catalyst bed"
          note={<>{eqNote}Browser plug-flow profile, {short(s.catalyst_id)}, {s.W_kg} kg in 50 tubes. {prof.aspen ? `Stored Aspen RPlug profile overlaid (case ${b.out.reactor.aspen?.case_id}).` : 'No stored Aspen case matches these inputs, so no Aspen profile is overlaid.'}</>}
          limit="One-dimensional plug flow, no radial gradients or catalyst deactivation.">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart margin={{ top: 8, right: 16, bottom: 30, left: 4 }}>
              <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
              <XAxis type="number" dataKey="x" {...axis} domain={[0, 'dataMax']} tickFormatter={(v: number) => Number(v.toPrecision(2)).toString()} label={{ value: 'Bed length (m)', position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
              <YAxis {...axis} domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}`} label={{ value: 'Conversion (%)', angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
              <Tooltip {...tip} formatter={fmt} labelFormatter={(v) => `${Number(v).toFixed(3)} m`} />
              <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 12 }} />
              <Line data={c3.fit} dataKey="y" name="Browser model" stroke="var(--accent)" dot={false} strokeWidth={2.4} isAnimationActive={false} connectNulls={false} />
              <Line data={c3.ext} dataKey="y" name="Browser model (extrapolation)" stroke="var(--accent)" strokeDasharray="6 4" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls={false} />
              {prof.aspen ? <Line data={prof.aspen.conversion_vs_length} dataKey="y" name="Aspen RPlug" stroke="var(--src-aspen)" dot={{ r: 2 }} strokeWidth={1.4} isAnimationActive={false} /> : null}
              {profA ? <Line data={profA.conversion_vs_length} dataKey="y" name="Case A" stroke={A_COLOR} strokeDasharray="2 3" dot={false} isAnimationActive={false} /> : null}
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard n={4} id="g-T-z" title="Temperature along the reactor" sources={[worstOf(prof.temperature_vs_length), prof.aspen ? 'aspen' : null]}
          desc="Gas temperature against axial position in the catalyst bed"
          note={<>{eqNote}Browser plug-flow profile ({s.reactor === 'equilibrium' ? 'isothermal' : s.reactor}). {prof.aspen ? 'Stored Aspen RPlug profile overlaid.' : 'No matching stored Aspen profile.'}</>}
          limit="Isothermal mode holds the set temperature by definition; the furnace and tube wall are not modelled.">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart margin={{ top: 8, right: 16, bottom: 30, left: 4 }}>
              <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
              <XAxis type="number" dataKey="x" {...axis} domain={[0, 'dataMax']} tickFormatter={(v: number) => Number(v.toPrecision(2)).toString()} label={{ value: 'Bed length (m)', position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
              <YAxis {...axis} domain={['auto', 'auto']} label={{ value: 'T (degC)', angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
              <Tooltip {...tip} formatter={fmt} labelFormatter={(v) => `${Number(v).toFixed(3)} m`} />
              <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 12 }} />
              <Line data={c4.fit} dataKey="y" name="Browser model" stroke="var(--c-heat)" dot={false} strokeWidth={2.4} isAnimationActive={false} connectNulls={false} />
              <Line data={c4.ext} dataKey="y" name="Browser model (extrapolation)" stroke="var(--c-heat)" strokeDasharray="6 4" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls={false} />
              {prof.aspen ? <Line data={prof.aspen.temperature_vs_length} dataKey="y" name="Aspen RPlug" stroke="var(--src-aspen)" dot={{ r: 2 }} strokeWidth={1.4} isAnimationActive={false} /> : null}
              {profA ? <Line data={profA.temperature_vs_length} dataKey="y" name="Case A" stroke={A_COLOR} strokeDasharray="2 3" dot={false} isAnimationActive={false} /> : null}
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard n={5} id="g-h2-Q" title="Hydrogen production against heat input" sources={g5 ? [worstOf(g5.b)] : []}
          desc="Hydrogen product rate against the heat supplied to the reactor"
          note={<>{memNote}Specified-duty plug flow (browser-only mode), {short(s.catalyst_id)}, {s.W_kg} kg, inlet {s.T_C} degC, {s.P_bar} bar, heat spread evenly over the catalyst; PSA recovery {s.psa_h2_recovery}.</>}
          limit="The duty mode has no Aspen counterpart; downstream duties assume an outlet at the inlet temperature.">
          {g5 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 8, right: 16, bottom: 30, left: 4 }}>
                <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
                <XAxis type="number" dataKey="x" {...axis} domain={[0, 2500]} label={{ value: 'Heat input to the reactor (kW)', position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
                <YAxis {...axis} domain={[0, 'auto']} label={{ value: 'H2 (kg/h)', angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
                <Tooltip {...tip} formatter={fmt} labelFormatter={(v) => `${v} kW`} />
                <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 12 }} />
                <Line data={splitExtrapolation(g5.b).fit} dataKey="y" name="Browser model" stroke="var(--c-h2)" dot={false} strokeWidth={2.4} isAnimationActive={false} connectNulls={false} />
                <Line data={splitExtrapolation(g5.b).ext} dataKey="y" name="Extrapolation" stroke="var(--c-h2)" strokeDasharray="6 4" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls={false} />
                {g5.a ? <Line data={g5.a} dataKey="y" name="Case A" stroke={A_COLOR} strokeDasharray="2 3" dot={false} isAnimationActive={false} /> : null}
                {yH2 !== null && !mem ? <ReferenceDot x={Math.min(2500, Math.max(0, b.out.reactor.duty_kW.value))} y={yH2} r={6} fill="var(--accent)" stroke="var(--bg)" /> : null}
              </LineChart>
            </ResponsiveContainer>
          ) : <Pending />}
        </ChartCard>

        <ChartCard n={6} id="g-cost" title={`Hydrogen production cost (${cur} per kg)`} sources={g6 ? [worstOf(g6.line)] : []}
          desc="Levelised hydrogen cost by catalyst and against a selected variable"
          note={<>{memNote}AmCraX Singapore cost model, pre-unification Phase 1 equipment CAPEX, ammonia {s.nh3_price_USD_per_t ?? `${s.nh3_route} scenario`}{s.nh3_price_USD_per_t ? ' USD/t' : ''}; SGD at {d.model.fx.SGD_per_USD} SGD/USD. Ni-Ru catalysts priced as Ru (assumption).</>}
          limit="Not the unified reference CAPEX; no IRR; points outside the process grid are omitted."
          controls={<>
            <label className="sim-gsel">Variable <select value={costVar} onChange={(e) => setCostVar(e.target.value as CostVariable)}>{COST_VARS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}</select></label>
            <span className="sim-chips" role="group" aria-label="Currency">{(['SGD', 'USD'] as const).map((c) => <button key={c} type="button" className="chip" aria-pressed={cur === c} onClick={() => setCur(c)}>{c}</button>)}</span>
          </>} height={300}>
          {g6 ? (
            <div className="sim-split">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart margin={{ top: 8, right: 12, bottom: 30, left: 4 }}>
                  <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} />
                  <XAxis type="number" dataKey="x" {...axis} domain={['dataMin', 'dataMax']} label={{ value: `${cv.label} (${cv.unit})`, position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
                  <YAxis {...axis} domain={['auto', 'auto']} label={{ value: `LCOH (${cur}/kg)`, angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
                  <Tooltip {...tip} formatter={fmt} />
                  <Line data={splitExtrapolation(g6.line.map((p) => ({ x: p.x, y: lineY(p), source: p.source }))).fit} dataKey="y" name={short(s.catalyst_id)} stroke="var(--primary)" dot={{ r: 2 }} strokeWidth={2.2} isAnimationActive={false} connectNulls={false} />
                  <Line data={splitExtrapolation(g6.line.map((p) => ({ x: p.x, y: lineY(p), source: p.source }))).ext} dataKey="y" name="extrapolation" stroke="var(--primary)" strokeDasharray="6 4" dot={false} strokeWidth={1.8} isAnimationActive={false} connectNulls={false} />
                  {b.out.economics ? <ReferenceDot x={(s[costVar] as number | null) ?? (costVar === 'nh3_price_USD_per_t' ? d.model.economics.nh3_price_scenarios_USD_per_t[{ grey: 'grey', blue: 'blue', green: 'green_current' }[s.nh3_route]] : 0)}
                    y={cur === 'SGD' ? b.out.economics.lcoh_SGD_per_kg : b.out.economics.lcoh_USD_per_kg} r={6} fill="var(--accent)" stroke="var(--bg)" ifOverflow="extendDomain" /> : null}
                </LineChart>
              </ResponsiveContainer>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ids.map((id) => ({ cat: short(id), v: g6.bars[id][0] ? (cur === 'SGD' ? g6.bars[id][0].y_SGD : g6.bars[id][0].y) : null }))} layout="vertical" margin={{ top: 8, right: 12, bottom: 30, left: 4 }}>
                  <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} horizontal={false} />
                  <XAxis type="number" {...axis} label={{ value: `Current case (${cur}/kg)`, position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
                  <YAxis type="category" dataKey="cat" width={112} {...axis} tick={{ fill: 'var(--text-2)', fontSize: 11 }} interval={0} />
                  <Tooltip {...tip} formatter={fmt} />
                  <Bar dataKey="v" name="LCOH" fill="var(--primary)" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <Pending />}
        </ChartCard>

        <ChartCard n={7} id="g-energy" title="Energy balance" sources={eb ? [...new Set(eb.map((r) => r.source))] : [null]}
          desc="External heating, recovered heat, reactor duty, preheat and other duties of the current case"
          note={<>{memNote}Reduced Python flowsheet: reactor, hydrogen, tail gas and burner computed in the browser; pump, vaporiser, preheater, exchanger and cooler interpolated from the Python grid.{eb ? '' : ' Outside the process grid: not modelled.'}</>}
          limit="First-law balance; flue heat credited regardless of its temperature level; FEHE approach, stack temperature and excess air fixed." height={300}>
          {eb ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={energyData} layout="vertical" margin={{ top: 8, right: 16, bottom: 30, left: 4 }}>
                <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} horizontal={false} />
                <XAxis type="number" {...axis} label={{ value: 'Heat flow (kW)', position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
                <YAxis type="category" dataKey="label" width={150} {...axis} tick={{ fill: 'var(--text-2)', fontSize: 11 }} interval={0} />
                <Tooltip {...tip} formatter={fmt} />
                {a ? <Legend verticalAlign="top" height={22} wrapperStyle={{ fontSize: 12 }} /> : null}
                {a ? <Bar dataKey="A" name="Case A" fill={A_COLOR} isAnimationActive={false} /> : null}
                <Bar dataKey="B" name={a ? 'Case B' : 'Current case'} fill="var(--c-heat)" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="sim-nm-block">not modelled: outside the stored process grid (400-800 degC, 3-50 bar)</p>}
        </ChartCard>

        <ChartCard n={8} id="g-carbon" title={`Carbon intensity and carbon cost by ammonia route${s.carbon_mode === 'hypothetical' ? ' (HYPOTHETICAL price)' : ''}`}
          sources={g8 ? [g8.b[0]?.source ?? null, ...(s.carbon_mode === 'hypothetical' ? ['assumption' as SourceLabel] : [])] : []}
          desc="Life-cycle carbon intensity and carbon cost for grey, blue and green ammonia"
          note={<>{memNote}Life-cycle carbon intensity (upstream ammonia, shipping, electricity, external heat). Carbon cost: {s.carbon_mode === 'hypothetical'
            ? <><strong>HYPOTHETICAL</strong> {s.carbon_price_SGD_per_t} SGD/tCO2e times the life-cycle intensity, not Singapore law.</>
            : 'actual Singapore carbon tax on direct facility emissions above the threshold (zero with ammonia self-firing).'}</>}
          limit="Route emission factors are literature values with wide ranges; the actual boundary excludes upstream emissions." height={300}>
          {g8 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={carbonData} margin={{ top: 8, right: 8, bottom: 30, left: 4 }}>
                <CartesianGrid stroke="var(--text)" strokeOpacity={0.08} vertical={false} />
                <XAxis dataKey="route" {...axis} label={{ value: 'Ammonia route', position: 'insideBottom', offset: -16, fill: 'var(--muted)' }} />
                <YAxis yAxisId="ci" {...axis} label={{ value: 'kg CO2e/kg H2', angle: -90, position: 'insideLeft', fill: 'var(--muted)' }} />
                <YAxis yAxisId="cost" orientation="right" {...axis} label={{ value: 'SGD/kg H2', angle: 90, position: 'insideRight', fill: 'var(--muted)' }} />
                <Tooltip {...tip} formatter={fmt} />
                <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 12 }} />
                {g8.a ? <Bar yAxisId="ci" dataKey="CI_A" name="Carbon intensity, case A" fill={A_COLOR} isAnimationActive={false} /> : null}
                <Bar yAxisId="ci" dataKey="CI" name="Carbon intensity" fill="var(--c-n2)" isAnimationActive={false} />
                <Bar yAxisId="cost" dataKey="cost" name={s.carbon_mode === 'hypothetical' ? 'Carbon cost (HYPOTHETICAL)' : 'Carbon cost (actual tax)'} fill="var(--c-o2)" isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : <Pending />}
        </ChartCard>
      </div>
    </section>
  )
}

function Pending() {
  return <p className="sim-pending" role="status">Calculating</p>
}
