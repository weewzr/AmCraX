import { useState } from 'react'

/** Long text cell: shows the first `max` characters; click to expand / collapse. Keyboard accessible. */
export function ClampCell({ text, max = 120 }: { text: string; max?: number }) {
  const [open, setOpen] = useState(false)
  if (!text) return <span className="muted">n/a</span>
  if (text.length <= max) return <span>{text}</span>
  return (
    <span className="clamp">
      {open ? text : `${text.slice(0, max).trimEnd()}... `}
      <button type="button" className="link-btn" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'show less' : 'show more'}</button>
    </span>
  )
}
