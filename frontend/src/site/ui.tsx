import { useMemo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { DataSource } from '../api/types'
import { SourceBadge } from '../components/ui'
import { citeLabel } from './cite'
import { useRefs } from './data'

export function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`wordmark-site ${className}`} aria-label="AmCraX">
      <span>Am</span><span className="wm-cra">Cra</span><span className="wm-x">X</span>
    </span>
  )
}

/** External link: new tab, safe rel, announced to screen readers. */
export function ExtLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
      {children}<span className="sr-only"> (opens in a new tab)</span>
    </a>
  )
}

/** Page title block for the non-landing routes (the page's only h1). */
export function PageHero({ eyebrow, title, lead, children }: { eyebrow: string; title: string; lead?: ReactNode; children?: ReactNode }) {
  return (
    <header className="page-hero">
      <div className="wrap">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {lead ? <p className="lead">{lead}</p> : null}
        {children}
      </div>
    </header>
  )
}

/** A titled, anchorable block of a page. Headings: the page has one h1, sections are h2. */
export function Section({ id, title, intro, children, alt = false }: { id: string; title: string; intro?: ReactNode; children: ReactNode; alt?: boolean }) {
  return (
    <section id={id} className={`section ${alt ? 'section-alt' : ''}`} aria-labelledby={`${id}-h`}>
      <div className="wrap">
        <div className="section-head">
          <h2 id={`${id}-h`}>{title}</h2>
          {intro ? <p className="section-intro">{intro}</p> : null}
        </div>
        {children}
      </div>
    </section>
  )
}

/** In-text citation "(Cechetto et al., 2023, p. 10776)" linking to the reference list. Only keys of research/references.json. */
export function Cite({ k, p }: { k: string | string[]; p?: string }) {
  const refs = useRefs()
  const byKey = useMemo(() => new Map((refs.phase === 'ready' ? refs.data : []).map((r) => [r.citekey, r])), [refs])
  const keys = Array.isArray(k) ? k : [k]
  return (
    <span className="cite">
      (
      {keys.map((key, i) => (
        <span key={key}>
          {i > 0 ? '; ' : ''}
          <Link to={{ pathname: '/research', hash: `#ref-${key}` }} title={byKey.get(key)?.apa7 ?? key}>{citeLabel(byKey.get(key)?.apa7, key)}</Link>
          {p && keys.length === 1 ? `, p. ${p}` : ''}
        </span>
      ))}
      )
    </span>
  )
}

/** Chart wrapper: provenance already sits in the chart caption; this adds the one-sentence reading and the "what it is" line. */
export function Reading({ children }: { children: ReactNode }) {
  return <p className="reading"><strong>Reading the chart.</strong> {children}</p>
}

export function Callout({ kind = 'note', title, children }: { kind?: 'note' | 'warn'; title?: string; children: ReactNode }) {
  return (
    <aside className={`callout callout-${kind}`}>
      {title ? <strong>{title} </strong> : null}{children}
    </aside>
  )
}

/** Label for how a number was obtained; never implies the website runs Aspen. */
export function ExecLabel({ kind }: { kind: 'browser' | 'aspen' | 'python' }) {
  if (kind === 'browser') return <span className="badge badge-browser" title="Calculated by JavaScript in this page, using the ideal-gas model">calculated in your browser (ideal gas)</span>
  if (kind === 'aspen') return <span className="badge badge-aspen_plus_v15" title="Stored result of an Aspen Plus V15 run made offline">Aspen Plus V15 result (pre-computed)</span>
  return <span className="badge badge-python_model" title="Stored result of the independent Python model">Python model (pre-computed)</span>
}

export function Src({ s }: { s: DataSource }) {
  return <SourceBadge source={s} />
}
