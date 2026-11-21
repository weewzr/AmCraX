import type { Flowsheet, HealthInfo, SimulationResult, SnapshotManifest } from '../api/types'
import * as api from '../api/client'
import { IS_PAGES } from '../api/url'
import { demoCases, demoFlowsheet } from '../demo/fixture'

export type DataMode = 'LIVE' | 'SNAPSHOT' | 'DEMO'

export interface ModeDeps {
  fetchHealth: () => Promise<HealthInfo>
  fetchManifest: () => Promise<SnapshotManifest>
}

export interface ResolvedMode {
  mode: DataMode
  health?: HealthInfo
  manifest?: SnapshotManifest
}

/**
 * LIVE if the API answers /api/health; else SNAPSHOT if /snapshot/manifest.json exists;
 * else DEMO. Exactly one mode is ever active - data from different modes is never merged.
 */
export async function resolveDataMode(deps: ModeDeps): Promise<ResolvedMode> {
  try {
    const health = await deps.fetchHealth()
    return { mode: 'LIVE', health }
  } catch {
    /* API unreachable - try snapshot */
  }
  try {
    const manifest = await deps.fetchManifest()
    return { mode: 'SNAPSHOT', manifest }
  } catch {
    /* no snapshot */
  }
  return { mode: 'DEMO' }
}

/** ?mode=snapshot in the page URL forces SNAPSHOT mode (API never contacted); used to verify the static mirror. */
export const forcedSnapshot = (): boolean => {
  if (IS_PAGES) return true
  try { return new URLSearchParams(window.location.search).get('mode')?.toLowerCase() === 'snapshot' } catch { return false }
}

export const defaultDeps: ModeDeps = {
  fetchHealth: () => (forcedSnapshot() ? Promise.reject(new Error('SNAPSHOT mode forced by ?mode=snapshot')) : api.fetchHealth()),
  fetchManifest: () => api.fetchManifest(),
}

export interface Dataset {
  flowsheet: Flowsheet
  cases: SimulationResult[]
  /** Case ids that exist but could not be loaded (invalid, HTTP error) - reported, never hidden. */
  skipped: string[]
}

export async function loadDataset(r: ResolvedMode): Promise<Dataset> {
  if (r.mode === 'DEMO') return { flowsheet: demoFlowsheet, cases: demoCases, skipped: [] }
  const skipped: string[] = []
  const cases: SimulationResult[] = []
  if (r.mode === 'LIVE') {
    const [flowsheet, list] = await Promise.all([api.fetchFlowsheet(), api.fetchCaseList()])
    const settled = await Promise.allSettled(list.filter((c) => c.valid).map((c) => api.fetchCase(c.case_id)))
    settled.forEach((s, i) => (s.status === 'fulfilled' ? cases.push(s.value) : skipped.push(list.filter((c) => c.valid)[i].case_id)))
    list.filter((c) => !c.valid).forEach((c) => skipped.push(c.case_id))
    return { flowsheet, cases, skipped }
  }
  const [flowsheet, index] = await Promise.all([api.fetchSnapshotFlowsheet(), api.fetchSnapshotCaseIndex()])
  const settled = await Promise.allSettled(index.map((e) => api.fetchSnapshotCase(e)))
  settled.forEach((s, i) => (s.status === 'fulfilled' ? cases.push(s.value) : skipped.push(index[i].case_id)))
  return { flowsheet, cases, skipped }
}
