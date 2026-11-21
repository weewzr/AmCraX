import { ApiError, getJson } from './client'

export type Eos = 'ideal' | 'pr'

export interface EquilibriumResult {
  T_K: number
  P_bar: number
  eos: string
  conversion: number
  extent: number
  n_out: Record<string, number>
  y: Record<string, number>
  K_eq: number | null
  phi: Record<string, number>
  residual: number | null
}
export interface EquilibriumResponse { T_C: number; P_bar: number; eos: string; basis: string; source: 'python_model'; result: EquilibriumResult }
export interface GridPoint { T_C: number; P_bar: number; conversion: number; result: EquilibriumResult }
export interface GridResponse { eos: string; source: 'python_model'; count: number; points: GridPoint[] }

export const fetchEquilibrium = (T_C: number, P_bar: number, eos: Eos, signal?: AbortSignal) =>
  getJson<EquilibriumResponse>(`/api/thermo/equilibrium?T_C=${T_C}&P_bar=${P_bar}&eos=${eos}`, signal)

export const fetchGrid = (eos: Eos, pressures: number[], tMin = 250, tMax = 900, nT = 14, signal?: AbortSignal) =>
  getJson<GridResponse>(
    `/api/thermo/grid?eos=${eos}&T_min_C=${tMin}&T_max_C=${tMax}&n_T=${nT}&P_bar=${pressures.join(',')}`, signal)

// ---- kinetics / PFR (module may be unavailable: API answers 503) ----
export interface PfrRequest {
  catalyst_id: string | null
  T_C: number
  P_bar: number
  feed_nh3_kmol_h: number
  catalyst_mass_kg: number | null
  n_points: number
}
export const fetchCatalysts = (signal?: AbortSignal) => getJson<unknown>('/api/kinetics/catalysts', signal)

export async function runPfr(req: PfrRequest, signal?: AbortSignal): Promise<unknown> {
  const res = await fetch('/api/reactor/pfr', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(req),
  })
  const text = await res.text()
  if (!res.ok) {
    let detail = text.slice(0, 300)
    try { const j = JSON.parse(text) as { detail?: unknown }; if (j.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch { /* keep raw text */ }
    throw new ApiError(`PFR run failed (HTTP ${res.status}): ${detail}`, res.status)
  }
  return JSON.parse(text) as unknown
}
