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
  it('evidence matrix: verdicts, components, qualifier, disclosures and moved-row thresholds come from the matrix file', () => {
    const em = load('/api/research/evidence-matrix')
    const h = html(<EvidenceMatrix />)
    for (const hy of em.hypotheses) {
      expect(h).toContain(`data-verdict="${hy.verdict}"`)
      for (const c of hy.components ?? []) expect(h).toContain(`data-verdict="${c.verdict}"`)
      if (hy.components?.length) expect(h).toContain(`data-testid="components-${hy.id}"`)
      for (const r of hy.rows ?? []) if (r.verdict_v1 && r.verdict_v1 !== r.verdict) expect(h).toContain(`data-testid="threshold-${r.row_id}"`)
    }
    expect(h).toContain('data-testid="matrix-disclosures"')
    for (const d of em.provenance.disclosures) expect(h).toContain(d.slice(0, 40))
    const q = em.hypotheses.find((x: { verdict: string }) => x.verdict === 'PARTIALLY SUPPORTED')
    if (q) expect(h).toContain(`data-testid="qualifier-${q.id}"`)
    expect(h).not.toMatch(/fixed before the Phase 2 analysis/)
  })
  it('plain answers: every answer, its basis and the formal verdict beside it come from the matrix file', async () => {
    const { PlainAnswers } = await import('./PlainAnswers')
    const em = load('/api/research/evidence-matrix')
    const h = html(<PlainAnswers />)
    expect(h).toContain('data-testid="plain-answers-lead"')
    expect(h).toContain('reading aid')
    expect(h).not.toMatch(/NaN|undefined|\[object|missing in test snapshot/)
    for (const hy of em.hypotheses) {
      expect(h).toContain(`data-testid="plain-answers-${hy.id}"`)
      for (const a of hy.plain_answers) {
        expect(['Yes', 'No', 'Not established']).toContain(a.answer)
        expect(h).toContain(a.claim)
        expect(h).toContain(`data-answer="${a.answer}"`)
      }
      if (hy.published_figures_checked.length) expect(h).toContain(`data-testid="figures-checked-${hy.id}"`)
    }
    // the formal verdict precedes the plain answers of each hypothesis
    for (const hy of em.hypotheses) {
      const start = h.indexOf(`data-testid="plain-answers-${hy.id}"`)
      const v = h.indexOf(`data-verdict="${hy.verdict}"`, start)
      const firstAnswer = h.indexOf('data-answer=', start)
      expect(v).toBeGreaterThan(start)
      expect(v).toBeLessThan(firstAnswer)
    }
    const only = html(<PlainAnswers ids={['H3']} />)
    expect(only).toContain('data-testid="plain-answers-H3"')
    expect(only).not.toContain('data-testid="plain-answers-H1"')
  })
  it('purification table labels the capital column and prints the membrane module cost from the file', () => {
    const pc = load('/api/research/purification/phase2_comparison.json')
    const h = html(<PurificationPhase2 />)
    expect(h).toContain('Fixed capital, excluding membrane modules (MUSD)')
    expect(h).toContain('Membrane modules, purchase cost (MUSD)')
    expect(h).toContain('data-testid="capital-note"')
    expect(h).toContain(pc.csv_column_notes.capital_USD.slice(0, 40))
  })
  it('fuel-efficiency envelope and H1 fuel sensitivity are printed from the files; green carbon intensities carry their boundary', () => {
    const bl = load('/api/research/reference_scenario/baseline.json')
    const e = html(<EconomicsPhase2 />)
    expect(e).toContain('data-testid="fuel-envelope"')
    for (const c of bl.fuel_efficiency_sensitivity.cases) expect(e).toContain(loc(c.lcoh_USD_per_kg, 3))
    expect(e).toContain('data-testid="green-ci-note"')
    const tt = load('/api/research/enduse/turbine_threshold.json')
    const u = html(<EndUsePhase2 />)
    expect(u).toContain('data-testid="h1-fuel-envelope"')
    for (const c of tt.cracker_heat_fuel_efficiency_sensitivity.cases) expect(u).toContain(loc(c.full_fired.threshold_delta_fuel_pp_vs_direct_turbine, 2))
    const ci = load('/api/research/carbon_pricing/carbon_intensity.json')
    const t = html(<CarbonIntensityTable />)
    expect(t).toContain(loc(ci.routes.green.ci_kgCO2e_per_kgH2.central, 2))
    expect(t).toContain(loc(ci.routes.green_lee.ci_kgCO2e_per_kgH2.central, 2))
    expect(html(<LegacyBanner />)).toContain('data-testid="fuel-envelope-note"')
  })
})
