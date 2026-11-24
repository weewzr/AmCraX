import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJson } from './data'
import { filterItems, pageItems, type PaletteItem } from './siteHelpers'

/**
 * Command palette: a hand-written modal dialog (native <dialog>) holding a WAI-ARIA combobox (an input that controls a
 * listbox through aria-activedescendant). It lists every page of the route table, the four hypotheses of the evidence
 * matrix and the stored simulator scenarios. Everything it offers is also reachable through the normal navigation.
 *
 * Keys: Ctrl+K or Cmd+K opens it (SiteLayout); Up and Down move, Enter opens, Escape clears the text, then closes.
 * Tab moves between the input and the Close button only (the listbox is not a tab stop; its options follow the input).
 * There is no single-key shortcut (WCAG 2.1.4).
 */
interface Hyp { id?: string; statement?: string; verdict?: string; verdict_v1?: string }

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const closeBtn = useRef<HTMLButtonElement>(null)
  const navigate = useNavigate()
  const uid = useId()
  const [q, setQ] = useState('')
  const [act, setAct] = useState(0)
  const [presets, setPresets] = useState<PaletteItem[]>([])
  const matrix = useJson<{ hypotheses?: Hyp[] }>(open ? '/api/research/evidence-matrix' : null)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) { d.showModal(); input.current?.focus() }
    if (!open && d.open) d.close()
  }, [open])

  // the scenario list lives in the simulator chunk; load it only when the palette is first opened
  useEffect(() => {
    if (!open || presets.length) return
    let live = true
    import('../simulator/model').then((m) => {
      if (live) setPresets(m.PRESETS.map((p) => ({ id: `scn:${p.id}`, group: 'Simulator scenarios', label: p.label, hint: `${p.kind}: ${p.about}`, to: `/?preset=${encodeURIComponent(p.id)}` })))
    }, () => { /* scenarios are optional in the palette */ })
    return () => { live = false }
  }, [open, presets.length])

  const items = useMemo(() => {
    const hyps: PaletteItem[] = matrix.phase === 'ready' ? (matrix.data.hypotheses ?? []).filter((h) => h.id).map((h) => ({
      id: `hyp:${h.id}`, group: 'Hypotheses', label: `${h.id}: ${String(h.statement ?? '').split(':')[0]}`,
      hint: `Verdict ${h.verdict ?? 'not stored'}${h.verdict_v1 ? ` (version 1: ${h.verdict_v1})` : ''}`, to: `/hypotheses#${h.id}`,
    })) : []
    return [...pageItems(), ...hyps, ...presets]
  }, [matrix, presets])
  const shown = useMemo(() => filterItems(items, q), [items, q])
  const active = shown.length ? Math.min(act, shown.length - 1) : -1
  const optId = (i: number) => `${uid}-opt-${i}`

  useEffect(() => { if (open && active >= 0) document.getElementById(optId(active))?.scrollIntoView({ block: 'nearest' }) })

  const close = () => { setQ(''); setAct(0); onClose() }
  const go = (it: PaletteItem) => { close(); navigate(it.to) }
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setAct(shown.length ? (active + 1) % shown.length : 0) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setAct(shown.length ? (active - 1 + shown.length) % shown.length : 0) }
    else if (e.key === 'Enter') { e.preventDefault(); if (active >= 0) go(shown[active]) }
    // the dialog has two tab stops (Close, then the input); Tab from the input returns to Close instead of leaving the dialog
    else if (e.key === 'Tab' && !e.shiftKey && closeBtn.current) { e.preventDefault(); closeBtn.current.focus() }
  }
  const onCloseKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'Tab' && e.shiftKey && input.current) { e.preventDefault(); input.current.focus() }
  }

  // groups in order of first appearance
  const groups: { name: string; rows: { it: PaletteItem; i: number }[] }[] = []
  shown.forEach((it, i) => {
    const g = groups.find((x) => x.name === it.group)
    if (g) g.rows.push({ it, i }); else groups.push({ name: it.group, rows: [{ it, i }] })
  })

  return (
    <dialog ref={ref} className="palette" aria-labelledby={`${uid}-title`}
      onCancel={(e) => { if (q) { e.preventDefault(); setQ(''); setAct(0) } else { e.preventDefault(); close() } }}
      onClick={(e) => { if (e.target === ref.current) close() }}>
      <div className="palette-box">
        <div className="palette-head">
          <h2 id={`${uid}-title`} className="palette-title">Go to a page, hypothesis or scenario</h2>
          <button type="button" ref={closeBtn} className="btn palette-close" onClick={close} onKeyDown={onCloseKey}>Close<span className="sr-only"> the search</span></button>
        </div>
        <input ref={input} className="palette-input" type="text" role="combobox" aria-expanded="true" aria-autocomplete="list"
          aria-controls={`${uid}-list`} aria-activedescendant={active >= 0 ? optId(active) : undefined} aria-describedby={`${uid}-keys`}
          aria-label="Search pages, hypotheses and scenarios" placeholder="Type to filter, for example purification or 700 degC"
          value={q} onChange={(e) => { setQ(e.target.value); setAct(0) }} onKeyDown={onKey} autoComplete="off" spellCheck={false} />
        <div id={`${uid}-list`} role="listbox" aria-label="Results" className="palette-list" tabIndex={-1}>
          {groups.map((g, gi) => (
            <div key={g.name} role="group" aria-labelledby={`${uid}-g${gi}`}>
              <div id={`${uid}-g${gi}`} role="presentation" className="palette-group">{g.name}</div>
              {g.rows.map(({ it, i }) => (
                <div key={it.id} id={optId(i)} role="option" aria-selected={i === active} className={`palette-opt${i === active ? ' is-active' : ''}`}
                  onMouseMove={() => { if (i !== active) setAct(i) }} onClick={() => go(it)}>
                  <span className="palette-label">{it.label}</span>
                  {it.hint ? <span className="palette-hint">{it.hint}</span> : null}
                </div>
              ))}
            </div>
          ))}
          {!shown.length ? <p className="palette-empty" role="status">Nothing matches "{q}".</p> : null}
        </div>
        <p id={`${uid}-keys`} className="palette-keys">
          <kbd>Up</kbd> <kbd>Down</kbd> move, <kbd>Enter</kbd> opens, <kbd>Esc</kbd> clears the text and then closes. Open this list from any page with <kbd>Ctrl</kbd> + <kbd>K</kbd> (<kbd>Cmd</kbd> + <kbd>K</kbd> on a Mac).
        </p>
      </div>
    </dialog>
  )
}
