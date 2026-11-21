import { useEffect, useState, type DependencyList } from 'react'

export type Async<T> =
  | { phase: 'idle' | 'loading'; data: null; error: null; status: null }
  | { phase: 'ready'; data: T; error: null; status: 200 }
  | { phase: 'error'; data: null; error: string; status: number | null }

/** Run an abortable async loader whenever deps change; `enabled=false` keeps the state idle. */
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, deps: DependencyList, enabled = true): Async<T> {
  const [s, setS] = useState<Async<T>>({ phase: 'idle', data: null, error: null, status: null })
  useEffect(() => {
    if (!enabled) { setS({ phase: 'idle', data: null, error: null, status: null }); return }
    const ac = new AbortController()
    setS({ phase: 'loading', data: null, error: null, status: null })
    load(ac.signal).then(
      (data) => { if (!ac.signal.aborted) setS({ phase: 'ready', data, error: null, status: 200 }) },
      (e: unknown) => {
        if (ac.signal.aborted) return
        const st = typeof (e as { status?: unknown })?.status === 'number' ? (e as { status: number }).status : null
        setS({ phase: 'error', data: null, error: e instanceof Error ? e.message : String(e), status: st })
      },
    )
    return () => ac.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled])
  return s
}

/** Derive an Async view from another one (same phase, mapped data). */
export function mapAsync<T, U>(a: Async<T>, fn: (d: T) => U): Async<U> {
  return a.phase === 'ready' ? { phase: 'ready', data: fn(a.data), error: null, status: 200 } : (a as unknown as Async<U>)
}
