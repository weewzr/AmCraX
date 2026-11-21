/** Small JSON request helper that keeps the API error model {code, message, detail} (docs/api.md). */
export class ApiFail extends Error {
  status: number
  code: string
  detail: unknown
  constructor(status: number, code: string, message: string, detail?: unknown) {
    super(message)
    this.name = 'ApiFail'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

export async function requestJson<T>(url: string, init?: { method?: string; body?: unknown; signal?: AbortSignal }): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, {
      method: init?.method ?? 'GET',
      signal: init?.signal,
      headers: { Accept: 'application/json', ...(init?.body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
      body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
    })
  } catch (e) {
    if ((e as { name?: string })?.name === 'AbortError') throw e
    throw new ApiFail(0, 'network_error', 'API not reachable (it may be restarting); try again in a few seconds.')
  }
  const text = await res.text()
  let body: unknown = null
  try { body = text ? JSON.parse(text) : null } catch { body = null }
  if (!res.ok) {
    const b = body as { code?: string; message?: string; detail?: unknown } | null
    throw new ApiFail(res.status, b?.code ?? `http_${res.status}`, b?.message ?? `${url} -> HTTP ${res.status}`, b?.detail)
  }
  if (body === null && text) throw new ApiFail(res.status, 'not_json', `${url} did not return JSON`)
  return body as T
}

export function describeError(e: unknown): string {
  if (e instanceof ApiFail) return `${e.code}: ${e.message}`
  return e instanceof Error ? e.message : String(e)
}
