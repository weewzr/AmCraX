import { useEffect, useRef, useState, type ReactNode } from 'react'

export interface LightboxItem { src: string; alt: string; title: string; caption: ReactNode }

/**
 * Full-size view of one image of a gallery: a native modal dialog with the image at its natural size (it scrolls inside the
 * dialog when larger than the window), its caption, previous and next buttons and a link to the original file.
 * Keys: Left and Right step through the gallery, Escape closes; focus returns to the thumbnail that opened it.
 * The "Actual size" toggle switches between fitting the window and the natural pixel size.
 */
export function Lightbox({ items, index, onIndex, onClose }: { items: LightboxItem[]; index: number | null; onIndex: (i: number) => void; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const opener = useRef<Element | null>(null)
  const [actual, setActual] = useState(false)
  const open = index !== null && index >= 0 && index < items.length

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) { opener.current = document.activeElement; d.showModal() }
    if (!open && d.open) d.close()
  }, [open])

  const close = () => {
    setActual(false)
    onClose()
    const o = opener.current
    window.requestAnimationFrame(() => { if (o instanceof HTMLElement) o.focus() })
  }
  const step = (delta: number) => { if (index !== null && items.length) onIndex((index + delta + items.length) % items.length) }
  const it = open ? items[index as number] : null

  return (
    <dialog ref={ref} className="lightbox" aria-labelledby="lightbox-title" aria-describedby="lightbox-caption"
      onCancel={(e) => { e.preventDefault(); close() }}
      onKeyDown={(e) => {
        if (e.key === 'ArrowRight') { e.preventDefault(); step(1) }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1) }
      }}>
      {it ? (
        <div className="lightbox-box">
          <div className="lightbox-bar">
            <h2 id="lightbox-title" className="lightbox-title">{it.title}</h2>
            <span className="lightbox-count" aria-live="polite">{(index as number) + 1} of {items.length}</span>
            <div className="lightbox-actions">
              <button type="button" className="btn" onClick={() => step(-1)} aria-keyshortcuts="ArrowLeft">Previous</button>
              <button type="button" className="btn" onClick={() => step(1)} aria-keyshortcuts="ArrowRight">Next</button>
              <button type="button" className="btn" aria-pressed={actual} onClick={() => setActual((a) => !a)}>Actual size</button>
              <a className="btn" href={it.src} target="_blank" rel="noopener noreferrer">Original file<span className="sr-only"> (opens in a new tab)</span></a>
              <button type="button" className="btn" onClick={close} autoFocus>Close</button>
            </div>
          </div>
          <div className={`lightbox-img${actual ? ' is-actual' : ''}`} tabIndex={0} role="region" aria-label="Image, scrolls when shown at actual size">
            <img src={it.src} alt={it.alt} />
          </div>
          <div id="lightbox-caption" className="lightbox-cap">{it.caption}</div>
          <p className="lightbox-keys"><kbd>Left</kbd> and <kbd>Right</kbd> step through the gallery; <kbd>Esc</kbd> closes.</p>
        </div>
      ) : null}
    </dialog>
  )
}
