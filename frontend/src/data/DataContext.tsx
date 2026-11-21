import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Flowsheet, HealthInfo, SimulationResult, SnapshotManifest } from '../api/types'
import { getJson, setSnapshotActive } from '../api/client'
import { withBase } from '../api/url'
import { humaniseKeys } from './metrics'
import { defaultDeps, loadDataset, resolveDataMode, type DataMode } from './mode'

interface DataState {
  phase: 'loading' | 'ready' | 'error'
  mode: DataMode | null
  health: HealthInfo | null
  manifest: SnapshotManifest | null
  flowsheet: Flowsheet | null
  cases: SimulationResult[]
  skipped: string[]
  error: string | null
  activeId: string | null
  active: SimulationResult | null
  setActiveId: (id: string) => void
  reload: () => void
  /** human label of a case from /api/scenarios/definitions (falls back to the case id) */
  caseLabel: (id: string) => string
}

/** Readable label for cases that are in no definition file (Python-model twins, user runs). */
function fallbackLabel(id: string): string {
  const py = id.match(/^python_(.+)$/)
  if (py) return `Python model twin of ${py[1].replace(/_pr$/, ' (Peng-Robinson)').replace(/_/g, ' ')}`
  if (/^user_/.test(id)) return `User run ${id.replace(/^user_/, '').replace(/_/g, ' ')}`
  return id
}

const Ctx = createContext<DataState | null>(null)

export function DataProvider({ children }: { children: ReactNode }) {
  const [s, setS] = useState<Omit<DataState, 'active' | 'setActiveId' | 'reload' | 'caseLabel'>>({
    phase: 'loading', mode: null, health: null, manifest: null, flowsheet: null, cases: [], skipped: [], error: null, activeId: null,
  })
  const [nonce, setNonce] = useState(0)
  const [labels, setLabels] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setS((p) => ({ ...p, phase: 'loading' }))
      const r = await resolveDataMode(defaultDeps)
      setSnapshotActive(r.mode === 'SNAPSHOT')
      if (r.mode !== 'DEMO') {
        getJson<{ process_scenarios?: { id: string; label: string }[] }>(r.mode === 'LIVE' ? '/api/scenarios/definitions' : withBase('/snapshot/scenarios_definitions.json'))
          .then((d) => { if (!cancelled) setLabels((p) => ({ ...p, ...Object.fromEntries((d.process_scenarios ?? []).map((s) => [s.id, s.label])) })) })
          .catch(() => { /* labels are optional */ })
        getJson<{ candidates?: { case_id?: string; label?: string }[] }>('/api/data/optimisation/aspen_verification')
          .then((d) => { if (!cancelled) setLabels((p) => ({ ...p, ...Object.fromEntries((d.candidates ?? []).filter((c) => c.case_id && c.label).map((c) => [c.case_id as string, `Optimisation: ${humaniseKeys(c.label as string)}`])) })) })
          .catch(() => { /* labels are optional */ })
      }
      try {
        const d = await loadDataset(r)
        if (cancelled) return
        const baseline = d.cases.find((c) => c.case_id === 'baseline') ?? d.cases[0]
        setS({
          phase: 'ready', mode: r.mode, health: r.health ?? null, manifest: r.manifest ?? null, flowsheet: d.flowsheet,
          cases: d.cases, skipped: d.skipped, error: null, activeId: baseline?.case_id ?? null,
        })
      } catch (e) {
        // A reachable API / snapshot that fails to load is an error, NOT a silent switch to demo data.
        if (cancelled) return
        setS((p) => ({ ...p, phase: 'error', mode: r.mode, health: r.health ?? null, manifest: r.manifest ?? null, error: e instanceof Error ? e.message : String(e) }))
      }
    })()
    return () => { cancelled = true }
  }, [nonce])

  const setActiveId = useCallback((id: string) => setS((p) => ({ ...p, activeId: id })), [])
  const reload = useCallback(() => setNonce((n) => n + 1), [])
  const caseLabel = useCallback((id: string) => labels[id] ?? fallbackLabel(id), [labels])
  const value = useMemo<DataState>(
    () => ({ ...s, active: s.cases.find((c) => c.case_id === s.activeId) ?? null, setActiveId, reload, caseLabel }),
    [s, setActiveId, reload, caseLabel],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useData(): DataState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useData outside DataProvider')
  return v
}



