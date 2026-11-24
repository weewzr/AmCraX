import { useEffect, useRef, type KeyboardEvent } from 'react'
import type { CaseResult } from './model'
import { FactList, OutputValueList } from './Outputs'
import type { UnitView } from './pfdData'
import { TOUR_STEPS } from './tourSteps'

/** Interval of the optional auto-advance (off by default, unavailable under reduced motion). Not shown as a duration. */
const AUTO_MS = 9000

/**
 * Guided tour card: Previous / Next / Exit, "Step n of 7", a segmented track. Esc exits and returns focus to the opener.
 * The tour selects units on the diagram; it does not animate anything as if time passed.
 */
export function Tour({ step, setStep, onExit, c, units, auto, setAuto, reduced }: { step: number; setStep: (n: number) => void; onExit: () => void
  c: CaseResult; units: Record<string, UnitView>; auto: boolean; setAuto: (v: boolean) => void; reduced: boolean }) {
  const st = TOUR_STEPS[step]
  const head = useRef<HTMLHeadingElement>(null)
  const n = TOUR_STEPS.length
  useEffect(() => { head.current?.focus() }, [step])
  useEffect(() => {
    if (!auto || reduced) return
    const t = window.setTimeout(() => { if (step < n - 1) setStep(step + 1); else setAuto(false) }, AUTO_MS)
    return () => window.clearTimeout(t)
  }, [auto, reduced, step, n, setStep, setAuto])
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') { e.preventDefault(); onExit() }
  }
  const uv = units[st.unit]
  const showFacts = step < n - 1 && uv
  return (
    <div className="sim-tour" role="region" aria-label="Guided process tour" onKeyDown={onKey} data-tour-step={step + 1}>
      <div className="sim-tour-top">
        <span className="sim-tour-count">Step {step + 1} of {n}</span>
        <ol className="sim-tour-track" aria-hidden="true">{TOUR_STEPS.map((s, i) => <li key={s.id} className={i === step ? 'is-on' : i < step ? 'is-done' : ''} />)}</ol>
      </div>
      <h3 ref={head} tabIndex={-1} className="sim-tour-h">{st.title}</h3>
      <p className="sim-tour-text">{st.text}</p>
      {showFacts ? <FactList facts={uv.facts} /> : null}
      {st.rows.length ? <OutputValueList c={c} keys={st.rows} /> : null}
      <div className="sim-tour-bar">
        <button type="button" className="btn" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>Previous</button>
        <button type="button" className="btn sim-tour-next" onClick={() => (step < n - 1 ? setStep(step + 1) : onExit())}>{step < n - 1 ? 'Next' : 'Finish'}</button>
        <button type="button" className="btn" onClick={onExit}>Exit tour</button>
        <label className="sim-check sim-tour-auto">
          <input type="checkbox" checked={auto && !reduced} disabled={reduced} onChange={(e) => setAuto(e.target.checked)} />
          Auto-advance{reduced ? ' (off: your system asks for reduced motion)' : ''}
        </label>
      </div>
      <p className="sim-tour-note">Steady-state solution of the current inputs; the tour moves through the plant, not through time.</p>
    </div>
  )
}
