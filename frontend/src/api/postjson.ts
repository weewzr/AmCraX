import { ApiError } from './client'

/** POST a JSON body and parse a JSON answer; errors carry the HTTP status (and the API message when present). */
export async function postJson<T>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, {
    method: 'POST', signal, body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
  })
  const text = await res.text()
  if (!res.ok) {
    let msg = `${url} -> HTTP ${res.status}`
    try {
      const j = JSON.parse(text) as { message?: string; detail?: unknown }
      if (j.message) msg += `: ${j.message}`
      if (typeof j.detail === 'string') msg += ` (${j.detail})`
    } catch { /* not JSON */ }
    throw new ApiError(msg, res.status)
  }
  try { return JSON.parse(text) as T } catch { throw new ApiError(`${url} did not return JSON`, res.status) }
}

/** Rows of a generic data file: GET /api/data/{category}/{name}. */
export interface DataFile<R = Record<string, unknown>> { name: string; category: string; columns?: string[]; rows?: R[] }