import type { ReactNode } from 'react'
import type { Async } from './useAsync'
import { useData } from '../../data/DataContext'

export function Notice({ kind = 'info', title, children }: { kind?: 'info' | 'warn' | 'error'; title?: string; children?: ReactNode }) {
  return (
    <div className={`card notice ${kind === 'warn' ? 'notice-warn' : kind === 'error' ? 'notice-error' : ''}`} role={kind === 'error' ? 'alert' : 'status'}>
      {title ? <strong>{title} </strong> : null}{children}
    </div>
  )
}

/** Renders loading / error / not-available states for an Async; calls children(data) when ready. */
export function AsyncView<T>({ a, what, children }: { a: Async<T>; what: string; children: (d: T) => ReactNode }) {
  const { mode } = useData()
  if (a.phase === 'idle') return null
  if (a.phase === 'loading') return <Notice>Loading {what} ...</Notice>
  if (a.phase === 'error') {
    if (mode === 'SNAPSHOT' && (a.status === 404 || a.status === 503)) {
      return <Notice kind="warn" title="Not in the SNAPSHOT export.">{what} is not part of the stored snapshot (it needs the live API or was not exported). Nothing is shown rather than placeholder values.</Notice>
    }
    if (a.status === 404 || a.status === 503) {
      return <Notice kind="warn" title="Data not available yet.">{what}: the API answered HTTP {a.status} ({a.error}). Nothing is shown rather than placeholder values.</Notice>
    }
    return <Notice kind="error" title="Could not load.">{what}: {a.error}</Notice>
  }
  return <>{children(a.data as T)}</>
}

/** LIVE-mode gate: true when server-side actions (runs, recalculation, sweeps) may be used. */
export function useLive(): boolean {
  return useData().mode === 'LIVE'
}

/** True when stored, read-only data can be shown: LIVE (API) or SNAPSHOT (static mirror under /snapshot/). */
export function useReadable(): boolean {
  const { mode, phase } = useData()
  return (mode === 'LIVE' || mode === 'SNAPSHOT') && phase === 'ready'
}

/** Notice for an action that needs the server. Silent in LIVE; explains the restriction in SNAPSHOT and DEMO. */
export function ModeGate({ what }: { what: string }) {
  const { mode } = useData()
  if (mode === 'LIVE') return null
  if (mode === 'SNAPSHOT') return <Notice title="SNAPSHOT mode.">{what} needs the live API and is disabled; stored results are shown read-only.</Notice>
  return <Notice kind="warn" title={`${mode ?? 'No'} mode.`}>{what} needs the live API; it is disabled in {mode ?? 'this'} mode. Start the API (scripts\run_api.ps1) to enable it.</Notice>
}
