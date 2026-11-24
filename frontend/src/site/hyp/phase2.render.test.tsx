/**
 * Server-side render of the Phase 2 sections with the real snapshot files (frontend/public/snapshot, written by
 * scripts/export_snapshot.py). Catches crashes on the stored data shapes and checks that key numbers of the files
 * reach the markup. Skipped when the snapshot has not been exported.
 */
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

const snapDir = fileURLToPath(new URL('../../../public/snapshot/', import.meta.url))
function snapFor(url: string): string | null {
  if (url === '/api/research/evidence-matrix') return `${snapDir}research/evidence_matrix.json`
  const m = url.match(/^\/api\/research\/([^/]+)\/([^/]+)$/)
  return m ? `${snapDir}research/${m[1]}/${decodeURIComponent(m[2])}.json` : null
}
const load = (url: string) => { const p = snapFor(url); return p && existsSync(p) ? JSON.parse(readFileSync(p, 'utf-8')) : null }

vi.mock('../data', () => ({
  useJson: (url: string | null) => {
    const d = url ? load(url) : null
    return d === null ? { phase: 'error', data: null, error: 'missing in test snapshot', status: 404 } : { phase: 'ready', data: d, error: null, status: 200 }
  },
}))

vi.mock('../../data/DataContext', () => ({ useData: () => ({ phase: 'ready', mode: 'SNAPSHOT', manifest: null, cases: [] }) }))

const { CarbonIntensityTable, CatalystPhase2, EconomicsPhase2, EndUsePhase2, LegacyBanner, PurificationPhase2, ValidationByKind } = await import('./phase2')
const { EvidenceMatrix } = await import('./EvidenceMatrix')
const html = (el: React.ReactElement) => renderToString(<MemoryRouter>{el}</MemoryRouter>).replace(/<!-- -->/g, '')
const loc = (v: number, d: number) => v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
const have = existsSync(`${snapDir}research/phase2_index.json`)

describe.skipIf(!have)('Phase 2 sections render from the snapshot', () => {
  it('economics: unified baseline, adverse finding, Mode A default', () => {
    const bl = load('/api/research/reference_scenario/baseline.json')
    const h = html(<EconomicsPhase2 />)
    expect(h).toContain(loc(bl.lcoh_USD_per_kg, 3))
    expect(h).toContain(loc(bl.lcoh_SGD_per_kg, 3))
    expect(h).toContain(String(bl.fx_date))
    expect(h).toContain('data-mode="actual_sg"')
    expect(h).toContain('superseded for research outputs')
    expect(h).not.toMatch(/NaN|undefined|\[object/)
  })
  it('catalysts, purification, end use, validation, legacy banner and matrix render without missing data', () => {
    for (const el of [<CatalystPhase2 />, <PurificationPhase2 />, <EndUsePhase2 />, <CarbonIntensityTable />, <ValidationByKind />, <LegacyBanner />, <EvidenceMatrix />]) {
      const h = html(el)
      expect(h).not.toMatch(/NaN|undefined|\[object|missing in test snapshot/)
    }
    const e = html(<EndUsePhase2 />)
    expect(e).toContain('49.64 %')
    expect(e).toMatch(/approximately 8 to 17 %/)
    expect(html(<ValidationByKind />)).toContain('Independent experimental validation')
    expect(html(<EvidenceMatrix />)).toMatch(/verdict-chip/)
  })
})
