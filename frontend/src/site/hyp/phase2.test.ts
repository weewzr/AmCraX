import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { availableDownloads, DOWNLOADS } from '../downloads'
import { v1Of } from './EvidenceMatrix'
import { at, modeBRoute } from './phase2'
import { interpRows } from './shape'

const repo = (p: string) => fileURLToPath(new URL(`../../../../${p}`, import.meta.url))
const SWEEP = repo('results/research/carbon_pricing/price_sweep.csv')
const SCEN = repo('results/research/carbon_pricing/scenarios.json')

function readCsv(p: string): Record<string, unknown>[] {
  const [head, ...lines] = readFileSync(p, 'utf-8').trim().split(/\r?\n/)
  const cols = head.split(',')
  return lines.map((l) => Object.fromEntries(l.split(',').map((v, i) => [cols[i], v === '' ? null : Number.isFinite(Number(v)) ? Number(v) : v])))
}

describe('at', () => {
  it('reads dotted and array paths', () => {
    const o = { a: { 'b.c': 2, d: { e: 3 } } }
    expect(at(o, 'a.d.e')).toBe(3)
    expect(at(o, ['a', 'b.c'])).toBe(2)
    expect(at(o, 'a.x.y')).toBeUndefined()
    expect(at(null, 'a')).toBeUndefined()
  })
})

describe.skipIf(!existsSync(SWEEP) || !existsSync(SCEN))('Mode B interpolation against the stored Python results', () => {
  const sweep = readCsv(SWEEP)
  const scen = JSON.parse(readFileSync(SCEN, 'utf-8')) as { cases: Record<string, unknown>[] }
  const cases = scen.cases.filter((c) => c.mode === 'hypothetical_lca' && (c.ci_level ?? 'central') === 'central')
  it('reproduces every stored hypothetical case (LCOH from the sweep, NPV and break-even from the cases)', () => {
    expect(cases.length).toBeGreaterThan(0)
    for (const c of cases) {
      const b = modeBRoute(sweep, scen.cases as never, String(c.route), Number(c.carbon_price_SGD_per_tCO2e))
      expect(b.lcoh).not.toBeNull()
      expect(Math.abs((b.lcoh as number) - Number(c.lcoh_USD_per_kg))).toBeLessThan(1e-6)
      expect(b.npv).toBeCloseTo(Number(c.npv_at_carbon_adjusted_benchmark_USD), 3)
      expect(b.breakeven).toBeCloseTo(Number(c.breakeven_nh3_vs_carbon_adjusted_benchmark_USD_per_t), 6)
    }
  })
  it('covers 0 to 500 SGD/tCO2e and returns null outside the stored sweep', () => {
    expect(interpRows(sweep, 'price_SGD_per_tCO2e', 'lcoh_grey_central_USD_per_kg', 0)).not.toBeNull()
    expect(interpRows(sweep, 'price_SGD_per_tCO2e', 'lcoh_grey_central_USD_per_kg', 500)).not.toBeNull()
    expect(modeBRoute(sweep, scen.cases as never, 'grey', 501).lcoh).toBeNull()
  })
  it('keeps the low and high LCOH around the central value', () => {
    for (const p of [5, 33, 127.44, 305, 499]) {
      const b = modeBRoute(sweep, scen.cases as never, 'blue', p)
      expect(b.lcohLow as number).toBeLessThanOrEqual(b.lcoh as number)
      expect(b.lcohHigh as number).toBeGreaterThanOrEqual(b.lcoh as number)
    }
  })
})

describe('downloads', () => {
  it('keeps the fixed list when the copy index is missing', () => {
    expect(availableDownloads(null)).toEqual(DOWNLOADS)
  })
  it('skips files that were not copied and adds paper PDFs found by pattern', () => {
    const out = availableDownloads([{ file: 'AmCraX_Technical_Report.pdf', bytes: 10 }, { file: 'amcrax_paper.pdf', kind: 'paper', source: 'docs/paper/build/amcrax_paper.pdf' }])
    expect(out.map((d) => d.file)).toEqual(['AmCraX_Technical_Report.pdf', 'amcrax_paper.pdf'])
    expect(out[0].bytes).toBe(10)
    expect(out[1].kind).toBe('paper')
  })
  it('lists the preserved 23 November 2026 release and the Phase 2 notes', () => {
    const files = DOWNLOADS.map((d) => d.file)
    for (const f of ['AmCraX_Technical_Report_2026-11-23.pdf', 'AmCraX_Executive_Summary.pdf', 'AmCraX_Paper.pdf', 'verdict_methodology_v2.md', 'unified_baseline.md', 'uncertainty_quantification.md', 'methodology_transfer_matrix.md', 'phase2_findings_changed.md']) expect(files).toContain(f)
  })
})

describe('evidence matrix v1 and v2', () => {
  it('takes the stored v1 verdict of a v2 file and the verdict itself of a v1 file', () => {
    expect(v1Of({ verdict: 'MIXED', verdict_v1: 'INCONCLUSIVE' }, 2)).toBe('INCONCLUSIVE')
    expect(v1Of({ verdict: 'INCONCLUSIVE' }, undefined)).toBe('INCONCLUSIVE')
    expect(v1Of({ verdict: 'MIXED' }, 2)).toBeUndefined()
  })
})
