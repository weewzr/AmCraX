import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchJob, type Job } from '../../api/simulation'
import { ApiFail } from '../../api/http'

export const TERMINAL = ['succeeded', 'failed', 'timeout']

export interface JobTrack { job: Job | null; elapsedS: number; lastError: string | null; startedAt: number | null }

/** Poll GET /api/jobs/{id} until a terminal state. Connection refusals (API restarting) are tolerated and retried. */
export function useJob(onDone?: (j: Job) => void) {
  const [t, setT] = useState<JobTrack>({ job: null, elapsedS: 0, lastError: null, startedAt: null })
  const timer = useRef<number | null>(null)
  const tick = useRef<number | null>(null)
  const done = useRef(onDone)
  done.current = onDone
  const stop = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    if (tick.current !== null) window.clearInterval(tick.current)
    timer.current = null; tick.current = null
  }, [])
  useEffect(() => stop, [stop])

  const track = useCallback((first: Job) => {
    stop()
    const startedAt = Date.now()
    setT({ job: first, elapsedS: 0, lastError: null, startedAt })
    tick.current = window.setInterval(() => setT((p) => ({ ...p, elapsedS: (Date.now() - startedAt) / 1000 })), 500)
    const poll = async (id: string) => {
      let next: Job | null = null
      try {
        next = await fetchJob(id)
        setT((p) => ({ ...p, job: next, lastError: null }))
      } catch (e) {
        const msg = e instanceof ApiFail ? `${e.code}: ${e.message}` : String(e)
        setT((p) => ({ ...p, lastError: msg }))
        if (e instanceof ApiFail && e.status === 404) { stop(); return }
      }
      if (next && TERMINAL.includes(next.state)) {
        stop()
        setT((p) => ({ ...p, elapsedS: (Date.now() - startedAt) / 1000 }))
        done.current?.(next)
        return
      }
      timer.current = window.setTimeout(() => void poll(id), 1500)
    }
    if (TERMINAL.includes(first.state)) { stop(); done.current?.(first); return }
    timer.current = window.setTimeout(() => void poll(first.job_id), 800)
  }, [stop])

  const reset = useCallback(() => { stop(); setT({ job: null, elapsedS: 0, lastError: null, startedAt: null }) }, [stop])
  return { ...t, track, reset }
}
