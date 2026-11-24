import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { collectEntries, type PageEntry as Entry } from './siteHelpers'

/**
 * "On this page" list for the long research pages. The entries are read from the rendered page (the sections arrive as
 * their data files load), so the list cannot disagree with the headings it points to.
 */
export function OnThisPage({ scope = 'site-main' }: { scope?: string }) {
  const { pathname } = useLocation()
  const [entries, setEntries] = useState<Entry[]>([])
  useEffect(() => {
    const root = document.getElementById(scope)
    if (!root) return
    let timer = 0
    const update = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        const next = collectEntries(root)
        setEntries((prev) => (prev.length === next.length && prev.every((e, i) => e.id === next[i].id && e.label === next[i].label) ? prev : next))
      }, 120)
    }
    update()
    const mo = new MutationObserver(update)
    mo.observe(root, { childList: true, subtree: true })
    return () => { mo.disconnect(); window.clearTimeout(timer) }
  }, [scope, pathname])
  if (entries.length < 2) return null
  return (
    <nav className="otp" aria-label="On this page">
      <h2 className="otp-h">On this page</h2>
      <ol className="otp-list">
        {entries.map((e) => <li key={e.id}><Link to={{ pathname, hash: `#${e.id}` }}>{e.label}</Link></li>)}
      </ol>
    </nav>
  )
}
