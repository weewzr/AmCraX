import type { Job } from '../../api/simulation'
import { StatusPill, type StatusKind } from '../../components/ui'

const KIND: Record<string, StatusKind> = { queued: 'neutral', running: 'info', succeeded: 'ok', failed: 'error', timeout: 'error' }

export function JobPanel(p: { job: Job | null; elapsedS: number; lastError: string | null; error?: string | null; title?: string }) {
  const { job } = p
  if (!job && !p.error) return null
  return (
    <div className="card job-panel" role="status" aria-live="polite">
      <div className="section-h">
        <strong>{p.title ?? 'Job'}{job ? <> <code>{job.job_id}</code></> : null}</strong>
        {job ? <StatusPill kind={KIND[job.state] ?? 'neutral'}>{job.state}</StatusPill> : null}
      </div>
      {job ? (
        <dl className="kv">
          <dt>Engine</dt><dd>{job.engine === 'aspen' ? 'Aspen Plus V15 (one job at a time; later jobs queue)' : 'Python model'}</dd>
          <dt>Elapsed</dt><dd>{p.elapsedS.toFixed(1)} s (browser clock){job.run_time_s !== null ? <> - engine run time {job.run_time_s.toFixed(1)} s</> : null}{job.queue_time_s ? <> - waited {job.queue_time_s.toFixed(1)} s in queue</> : null}</dd>
          <dt>Engine message</dt><dd>{job.message ?? 'n/a'}</dd>
          {job.case_id ? <><dt>Stored case</dt><dd><code>{job.case_id}</code></dd></> : null}
        </dl>
      ) : null}
      {job && (job.state === 'failed' || job.state === 'timeout') ? (
        <p className="err-text" role="alert">The job {job.state === 'timeout' ? 'timed out' : 'failed'}: {job.message ?? 'no message'}. Nothing was stored; no substitute result is shown.</p>
      ) : null}
      {p.error ? <p className="err-text" role="alert">{p.error}</p> : null}
      {p.lastError ? <p className="muted">Polling problem (retrying): {p.lastError}</p> : null}
    </div>
  )
}
