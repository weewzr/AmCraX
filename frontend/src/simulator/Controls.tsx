import { useId, useState, type ReactNode } from 'react'
import type { Range, SimData } from '../sim'
import { REACTOR_MODES, type Action, type SimState } from './model'

/** Validity class of a rate law from the exported classification (null when absent). */
export function validityClass(d: SimData, id: string): string | null {
  const v = d.model.kinetics.laws[id]?.validity_classification as { class?: string } | null | undefined
  return v && typeof v.class === 'string' ? v.class.replace(/_/g, ' ') : null
}

const decimals = (step: number) => { const s = String(step); const i = s.indexOf('.'); return i < 0 ? 0 : s.length - i - 1 }

/** Slider + number box with unit, valid range and a domain warning (pattern of the NUS-H2 parameters page). */
export function NumberControl(p: { id: string; label: string; unit: string; range: Range; value: number; step?: number; disabled?: boolean
  warn?: string[]; note?: ReactNode; onChange: (v: number) => void }) {
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
            {kin ? '' : ' Not used by the equilibrium reactor except for the catalyst cost.'}
          </span>
        </div>
        <NumberControl id="T_C" label="Reactor temperature" unit="degC" range={ranges.T_C} value={s.T_C} warn={wT} onChange={(v) => set('T_C', v)} note={ranges.T_C.note} />
        <NumberControl id="P_bar" label="Reactor pressure" unit="bar" range={ranges.P_bar} value={s.P_bar} step={0.5} warn={wP} onChange={(v) => set('P_bar', v)} note={ranges.P_bar.note} />
        <NumberControl id="W_kg" label="Catalyst mass" unit="kg" range={ranges.W_kg} value={s.W_kg} step={1} onChange={(v) => set('W_kg', v)} note={kin ? 'Total over 50 tubes.' : 'Enters the catalyst cost only.'} />
        <NumberControl id="duty_kW" label="Additional heat input to the reactor" unit="kW" range={ranges.duty_kW} value={s.duty_kW} step={10} disabled={s.reactor !== 'duty'}
          onChange={(v) => set('duty_kW', v)} note={s.reactor === 'duty' ? 'Spread evenly over the catalyst (browser-only mode).' : 'Used in the "Specified heat duty" mode only.'} />
        <label className="sim-check">
          <input type="checkbox" checked={s.pressure_drop && kin} disabled={!kin} onChange={(e) => set('pressure_drop', e.target.checked)} />
          Bed pressure drop (Ergun){kin ? '' : ': kinetic modes only'}. Off in the stored Aspen cases.
        </label>
      </Section>
      <Section title="Feed and heat recovery" open={!compact}>
        <NumberControl id="feed_total_kmol_h" label="Ammonia feed flow rate" unit="kmol/h" range={ranges.feed_total_kmol_h} value={s.feed_total_kmol_h} step={1}
          onChange={(v) => set('feed_total_kmol_h', v)} note={ranges.feed_total_kmol_h.note} />
        <label className="sim-switch">
          <input type="checkbox" role="switch" checked={s.heat_integration} aria-checked={s.heat_integration} onChange={(e) => set('heat_integration', e.target.checked)} />
          <span>Heat integration (feed-effluent exchanger) {s.heat_integration ? 'on' : 'off: FEHE bypassed'}</span>
        </label>
      </Section>
      <Section title="Purification" open={!compact}>
        <Segmented name="sim-pur" label="Purification technology" value={s.purification} onChange={(v) => set('purification', v)}
          options={[{ id: 'psa', label: 'PSA' }, { id: 'membrane', label: 'Pd-Ag membrane' }]} />
        {s.purification === 'membrane' ? <p className="sim-ctl-warn-p">The membrane is not modelled in the browser: purification and downstream outputs show "not modelled".</p> : null}
        <NumberControl id="psa_h2_recovery" label="Hydrogen recovery" unit="-" range={ranges.psa_h2_recovery} value={s.psa_h2_recovery} step={0.01} disabled={s.purification !== 'psa'}
          onChange={(v) => set('psa_h2_recovery', v)} note="Assumed input of the reduced-order PSA (fraction)." />
      </Section>
      <Section title="Ammonia and carbon pricing" open={!compact}>
        <Segmented name="sim-route" label="Ammonia route" value={s.nh3_route} onChange={(v) => set('nh3_route', v)}
          options={[{ id: 'grey', label: 'Grey' }, { id: 'blue', label: 'Blue' }, { id: 'green', label: 'Green' }]} />
        <label className="sim-check">
          <input type="checkbox" checked={s.nh3_price_USD_per_t === null} onChange={(e) => set('nh3_price_USD_per_t', e.target.checked ? null : routePrice)} />
          Use the route's price scenario ({routePrice} USD/t)
        </label>
        <NumberControl id="nh3_price_USD_per_t" label="Ammonia price" unit="USD/t NH3" range={ranges.nh3_price_USD_per_t} value={s.nh3_price_USD_per_t ?? routePrice} step={5}
          disabled={s.nh3_price_USD_per_t === null} onChange={(v) => set('nh3_price_USD_per_t', v)} note="Scenario price, not a Singapore transaction price." />
        <Segmented name="sim-carbon" label="Carbon pricing" value={s.carbon_mode} onChange={(v) => set('carbon_mode', v)}
          options={[{ id: 'actual', label: 'Actual Singapore boundary' }, { id: 'hypothetical', label: 'HYPOTHETICAL life-cycle price' }]} />
        {s.carbon_mode === 'hypothetical' ? (
          <>
            <p className="sim-hypo" role="note"><strong>HYPOTHETICAL</strong>, not Singapore law: a user carbon price times the life-cycle carbon intensity. It replaces the actual tax term.</p>
            <NumberControl id="carbon_price_SGD_per_t" label="Hypothetical carbon price" unit="SGD/tCO2e" range={ranges.carbon_price_SGD_per_t} value={s.carbon_price_SGD_per_t}
              step={5} onChange={(v) => set('carbon_price_SGD_per_t', v)} />
          </>
        ) : <p className="sim-ctl-range">Singapore carbon tax on direct facility emissions above the threshold, as the AmCraX economics model applies it. With ammonia self-firing it is zero.</p>}
      </Section>
    </div>
  )
}
