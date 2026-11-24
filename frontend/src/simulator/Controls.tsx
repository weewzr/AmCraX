import { useId, useState, type ReactNode } from 'react'
import { catalystPrice, type Range, type SimData } from '../sim'
import { fixedValues, REACTOR_MODES, WITHHELD, type Action, type SimState } from './model'

/** Basis chip of a control (C8): which evidence the output rests on over the control's range. Text from the data, not hard-coded numbers. */
export function controlBasis(d: SimData, s: SimState, key: string): string {
  const m = d.model
  const g = m.process.grid
  const kin = s.reactor !== 'equilibrium'
  const v = m.kinetics.laws[s.catalyst_id]?.validity
  const Tfit = v ? `${(v.T_min_K - 273.15).toFixed(0)}-${(v.T_max_K - 273.15).toFixed(0)} degC` : 'not given'
  const Pfit = v ? (v.P_min_bar === v.P_max_bar ? `${v.P_min_bar} bar` : `${v.P_min_bar}-${v.P_max_bar} bar`) : 'not given'
  const Tg = `${g.T_C[0]}-${g.T_C[g.T_C.length - 1]} degC`, Pg = `${g.P_bar[0]}-${g.P_bar[g.P_bar.length - 1]} bar`
  switch (key) {
    case 'T_C': return kin ? `Rate law fitted ${Tfit}; process grid ${Tg}` : `Equilibrium (browser); process grid ${Tg}`
    case 'P_bar': return kin ? `Rate law fitted ${Pfit}; process grid ${Pg}` : `Equilibrium (browser); process grid ${Pg}`
    case 'W_kg': return kin ? 'Browser plug-flow model' : 'Not used (equilibrium)'
    case 'duty_kW': return 'Browser-only mode, no Aspen case'
    case 'feed_total_kmol_h': return 'Process grid per kmol/h of feed'
    case 'psa_h2_recovery': return 'Assumed'
    case 'nh3_price_USD_per_t': return 'Assumed scenario'
    case 'carbon_price_SGD_per_t': return 'Assumed, HYPOTHETICAL'
    default: return 'Assumed'
  }
}

/** Validity class of a rate law from the exported classification (null when absent). */
export function validityClass(d: SimData, id: string): string | null {
  const v = d.model.kinetics.laws[id]?.validity_classification as { class?: string } | null | undefined
  return v && typeof v.class === 'string' ? v.class.replace(/_/g, ' ') : null
}

const decimals = (step: number) => { const s = String(step); const i = s.indexOf('.'); return i < 0 ? 0 : s.length - i - 1 }

/** Slider + number box with unit, valid range and a domain warning (pattern of the NUS-H2 parameters page). */
export function NumberControl(p: { id: string; label: string; unit: string; range: Range; value: number; step?: number; disabled?: boolean
  warn?: string[]; note?: ReactNode; basis?: string; onChange: (v: number) => void }) {
  const uid = useId()
  const step = p.step ?? p.range.step ?? 1
  const [draft, setDraft] = useState<string | null>(null)
  const [err, setErr] = useState('')
  const commit = (raw: string) => {
    const v = Number(raw)
    if (raw.trim() === '' || !Number.isFinite(v)) { setErr(`Enter a number between ${p.range.min} and ${p.range.max} ${p.unit}.`); return }
    if (v < p.range.min || v > p.range.max) { setErr(`${raw} is outside the allowed range ${p.range.min} to ${p.range.max} ${p.unit}; not applied.`); return }
    setErr(''); setDraft(null); p.onChange(v)
  }
  const shown = draft ?? (Number.isInteger(p.value) && decimals(step) === 0 ? String(p.value) : String(Number(p.value.toFixed(Math.max(decimals(step), 2)))))
  return (
    <div className={`sim-ctl ${p.disabled ? 'is-disabled' : ''} ${p.warn && p.warn.length ? 'has-warn' : ''}`} data-ctl={p.id}>
      <div className="sim-ctl-head">
        <label htmlFor={`${uid}-n`}>{p.label}</label>
        <span className="sim-ctl-unit">{p.unit}</span>
      </div>
      {p.basis ? <span className="sim-basis-chip" data-basis={p.id}>Basis: {p.basis}</span> : null}
      <div className="sim-ctl-inputs">
        <input type="range" min={p.range.min} max={p.range.max} step={step} value={p.value} disabled={p.disabled} aria-label={`${p.label} slider`}
          aria-describedby={`${uid}-r`} onChange={(e) => { setErr(''); setDraft(null); p.onChange(Number(e.target.value)) }} />
        <input id={`${uid}-n`} type="number" inputMode="decimal" min={p.range.min} max={p.range.max} step={step} value={shown} disabled={p.disabled}
          aria-describedby={`${uid}-r ${uid}-e`} aria-invalid={err ? true : undefined}
          onChange={(e) => setDraft(e.target.value)} onBlur={(e) => { if (draft !== null) commit(e.target.value) }}
          onKeyDown={(e) => { if (e.key === 'Enter') commit((e.target as HTMLInputElement).value) }} />
      </div>
      <span className="sim-ctl-range" id={`${uid}-r`}>Allowed {p.range.min} to {p.range.max} {p.unit}.{p.note ? <> {p.note}</> : null}</span>
      {err ? <span className="sim-ctl-err" id={`${uid}-e`} role="alert">{err}</span> : <span id={`${uid}-e`} hidden />}
      {p.warn && p.warn.length ? <ul className="sim-ctl-warn">{p.warn.map((w) => <li key={w}><span aria-hidden="true">! </span>{w}</li>)}</ul> : null}
    </div>
  )
}

function Segmented<T extends string>(p: { label: string; value: T; options: { id: T; label: string }[]; onChange: (v: T) => void; name: string }) {
  return (
    <fieldset className="sim-seg">
      <legend>{p.label}</legend>
      <div className="sim-seg-opts">
        {p.options.map((o) => (
          <label key={o.id} className={p.value === o.id ? 'is-on' : ''}>
            <input type="radio" name={p.name} value={o.id} checked={p.value === o.id} onChange={() => p.onChange(o.id)} />{o.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

function Section({ title, children, open = true }: { title: string; children: ReactNode; open?: boolean }) {
  return (
    <details className="sim-sec" open={open}>
      <summary>{title}</summary>
      <div className="sim-sec-body">{children}</div>
    </details>
  )
}

export function Controls({ s, d, ranges, warnings, dispatch, compact }: { s: SimState; d: SimData; ranges: Record<string, Range>; warnings: string[]
  dispatch: (a: Action) => void; compact: boolean }) {
  const set = <K extends keyof SimState>(key: K, value: SimState[K]) => dispatch({ type: 'set', key, value })
  const kin = s.reactor !== 'equilibrium'
  const wT = warnings.filter((w) => /^T = /.test(w) || /process grid|equilibrium grid/.test(w))
  const wP = warnings.filter((w) => /^P = /.test(w))
  const law = d.model.kinetics.laws[s.catalyst_id]
  const catPrice = catalystPrice(d.model, s.catalyst_id, s.catalyst_price_source)
  const routePrice = d.model.economics.nh3_price_scenarios_USD_per_t[{ grey: 'grey', blue: 'blue', green: 'green_current' }[s.nh3_route]]
  return (
    <div className="sim-controls" aria-label="Simulator controls">
      <Section title="Reactor" open>
        <div className="sim-ctl">
          <div className="sim-ctl-head"><label htmlFor="sim-mode">Reactor operating mode</label></div>
          <select id="sim-mode" value={s.reactor} onChange={(e) => set('reactor', e.target.value as SimState['reactor'])}>
            {REACTOR_MODES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
          <span className="sim-ctl-range">{REACTOR_MODES.find((m) => m.id === s.reactor)?.note}.</span>
        </div>
        <div className="sim-ctl">
          <div className="sim-ctl-head"><label htmlFor="sim-cat">Catalyst (rate law)</label></div>
          <select id="sim-cat" value={s.catalyst_id} onChange={(e) => set('catalyst_id', e.target.value)}>
            {d.model.kinetics.law_ids.map((id) => {
              const l = d.model.kinetics.laws[id]
              const vc = validityClass(d, id)
              return <option key={id} value={id}>{l.label}{vc ? ` [${vc}]` : ''}</option>
            })}
          </select>
          <span className="sim-ctl-range">
            Validity class: <strong>{validityClass(d, s.catalyst_id) ?? 'not classified'}</strong>. Fitted {((law?.validity.T_min_K ?? 273.15) - 273.15).toFixed(0)}-{((law?.validity.T_max_K ?? 273.15) - 273.15).toFixed(0)} degC,
            {' '}{law?.validity.P_min_bar === law?.validity.P_max_bar ? `${law?.validity.P_min_bar} bar` : `${law?.validity.P_min_bar}-${law?.validity.P_max_bar} bar`}.
            {kin ? '' : ' Not used by the equilibrium reactor.'}
          </span>
        </div>
        <NumberControl id="T_C" basis={controlBasis(d, s, 'T_C')} label="Reactor temperature" unit="degC" range={ranges.T_C} value={s.T_C} warn={wT} onChange={(v) => set('T_C', v)} note={ranges.T_C.note} />
        <NumberControl id="P_bar" basis={controlBasis(d, s, 'P_bar')} label="Reactor pressure" unit="bar" range={ranges.P_bar} value={s.P_bar} step={0.5} warn={wP} onChange={(v) => set('P_bar', v)} note={ranges.P_bar.note} />
        <NumberControl id="W_kg" basis={controlBasis(d, s, 'W_kg')} label="Catalyst mass" unit="kg" range={ranges.W_kg} value={s.W_kg} step={1} onChange={(v) => set('W_kg', v)} note={kin ? 'Total over 50 tubes.' : 'Not used by the equilibrium reactor.'} />
        <NumberControl id="duty_kW" basis={controlBasis(d, s, 'duty_kW')} label="Additional heat input to the reactor" unit="kW" range={ranges.duty_kW} value={s.duty_kW} step={10} disabled={s.reactor !== 'duty'}
          onChange={(v) => set('duty_kW', v)} note={s.reactor === 'duty' ? 'Spread evenly over the catalyst (browser-only mode).' : 'Used in the "Specified heat duty" mode only.'} />
        <label className="sim-check">
          <input type="checkbox" checked={s.pressure_drop && kin} disabled={!kin} onChange={(e) => set('pressure_drop', e.target.checked)} />
          Bed pressure drop (Ergun){kin ? '' : ': kinetic modes only'}. Off in the stored Aspen cases.
        </label>
      </Section>
      <Section title="Feed and heat recovery" open={!compact}>
        <NumberControl id="feed_total_kmol_h" basis={controlBasis(d, s, 'feed_total_kmol_h')} label="Ammonia feed flow rate" unit="kmol/h" range={ranges.feed_total_kmol_h} value={s.feed_total_kmol_h} step={1}
          onChange={(v) => set('feed_total_kmol_h', v)} note={ranges.feed_total_kmol_h.note} />
        <label className="sim-switch">
          <input type="checkbox" role="switch" checked={s.heat_integration} aria-checked={s.heat_integration} onChange={(e) => set('heat_integration', e.target.checked)} />
          <span>Heat integration (feed-effluent exchanger) {s.heat_integration ? 'on' : 'off: FEHE bypassed'}</span>
        </label>
      </Section>
      <Section title="Purification" open={!compact}>
        <Segmented name="sim-pur" label="Purification technology" value={s.purification} onChange={(v) => set('purification', v)}
          options={[{ id: 'psa', label: 'PSA' }, { id: 'membrane', label: 'Pd-Ag membrane' }]} />
        {s.purification === 'membrane' ? <p className="sim-ctl-warn-p">The membrane is not modelled in the browser: live purification and downstream outputs show "not modelled". A stored Python comparison of PSA and membrane at the reference conditions is shown under Live outputs; it does not respond to the controls.</p> : null}
        <NumberControl id="psa_h2_recovery" basis={controlBasis(d, s, 'psa_h2_recovery')} label="Hydrogen recovery" unit="-" range={ranges.psa_h2_recovery} value={s.psa_h2_recovery} step={0.01} disabled={s.purification !== 'psa'}
          onChange={(v) => set('psa_h2_recovery', v)} note="Assumed input of the reduced-order PSA (fraction)." />
      </Section>
      <Section title="Ammonia and carbon pricing" open={!compact}>
        <Segmented name="sim-route" label="Ammonia route" value={s.nh3_route} onChange={(v) => set('nh3_route', v)}
          options={[{ id: 'grey', label: 'Grey' }, { id: 'blue', label: 'Blue' }, { id: 'green', label: 'Green' }]} />
        <label className="sim-check">
          <input type="checkbox" checked={s.nh3_price_USD_per_t === null} onChange={(e) => set('nh3_price_USD_per_t', e.target.checked ? null : routePrice)} />
          Use the route's price scenario ({routePrice} USD/t)
        </label>
        <NumberControl id="nh3_price_USD_per_t" basis={controlBasis(d, s, 'nh3_price_USD_per_t')} label="Ammonia price" unit="USD/t NH3" range={ranges.nh3_price_USD_per_t} value={s.nh3_price_USD_per_t ?? routePrice} step={5}
          disabled={s.nh3_price_USD_per_t === null} onChange={(v) => set('nh3_price_USD_per_t', v)} note="Scenario price, not a Singapore transaction price." />
        <div className="sim-ctl" data-ctl="catalyst_price_source">
          <div className="sim-ctl-head"><label htmlFor="sim-catprice">Catalyst price</label><span className="sim-ctl-unit">USD/kg</span></div>
          <select id="sim-catprice" value={s.catalyst_price_source} disabled={!kin} onChange={(e) => set('catalyst_price_source', e.target.value as SimState['catalyst_price_source'])}>
            <option value="central">Central (metal prices of 20 Nov 2026), derived</option>
            <option value="low">Low (2025 average metal prices, no support term), derived</option>
            <option value="high">High (Ni at the 2022 average), derived</option>
            <option value="phase1_tea">Phase 1 published TEA price (Ni 33.4, Ru 542)</option>
          </select>
          <span className="sim-ctl-range">
            {kin
              ? <>Selected: <strong>{catPrice.usd_per_kg.toFixed(2)} USD/kg</strong> ({catPrice.label}).</>
              : 'An equilibrium reactor has no catalyst: the reference inventory at the Phase 1 TEA Ni price is used. Choose a kinetic mode to select a catalyst price.'}
          </span>
          <p className="sim-cat-note">Derived prices are computed from metal content ({d.model.economics.catalyst_prices.formula}), not supplier quotations: no quotation or published commercial price exists for any ammonia-cracking catalyst. Ru is a volatile market; the high Ru value equals the central one (no sourced higher value).</p>
        </div>
        <Segmented name="sim-carbon" label="Carbon pricing" value={s.carbon_mode} onChange={(v) => set('carbon_mode', v)}
          options={[{ id: 'actual', label: 'Actual Singapore boundary' }, { id: 'hypothetical', label: 'HYPOTHETICAL life-cycle price' }]} />
        {s.carbon_mode === 'hypothetical' ? (
          <>
            <p className="sim-hypo" role="note"><strong>HYPOTHETICAL</strong>, not Singapore law: a user carbon price times the life-cycle carbon intensity. It replaces the actual tax term.</p>
            <NumberControl id="carbon_price_SGD_per_t" basis={controlBasis(d, s, 'carbon_price_SGD_per_t')} label="Hypothetical carbon price" unit="SGD/tCO2e" range={ranges.carbon_price_SGD_per_t} value={s.carbon_price_SGD_per_t}
              step={5} onChange={(v) => set('carbon_price_SGD_per_t', v)} />
          </>
        ) : <p className="sim-ctl-range">Singapore carbon tax on direct facility emissions above the threshold, as the AmCraX economics model applies it. With ammonia self-firing it is zero.</p>}
      </Section>
      <Section title="Values held fixed" open={false}>
        <table className="sim-fixed" aria-label="Inputs held fixed by the simulator">
          <tbody>{fixedValues(d).map((f) => (
            <tr key={f.key} data-fixed={f.key}><th scope="row">{f.label}</th><td className="sim-num">{String(f.value)}{f.unit && f.unit !== '-' ? ` ${f.unit}` : ''}</td><td><span className="badge sim-badge src-assumption" title="Assumed input, exported from the Python defaults">Assumed</span></td></tr>
          ))}</tbody>
        </table>
        <p className="sim-ctl-range"><strong>Controls not offered, and why</strong></p>
        <ul className="sim-withheld">{WITHHELD.map((w) => <li key={w}>{w}</li>)}</ul>
      </Section>
    </div>
  )
}
