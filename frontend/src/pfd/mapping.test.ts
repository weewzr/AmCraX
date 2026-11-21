import { describe, expect, it } from 'vitest'
import { demoCases, demoFlowsheet } from '../demo/fixture'
import { flowsheetToGraph, labelAnchor, type PfdOptions } from './mapping'

const opts = (hi: boolean): PfdOptions => ({ colorBy: 'component', overlays: { T: false, P: false, F: false }, animate: false, heatIntegration: hi })

describe('flowsheetToGraph', () => {
  it('every demo object has source "demo"', () => {
    expect(demoCases.every((c) => c.source === 'demo')).toBe(true)
  })
  it('with heat integration: FEHE, S3, S6 present and S2/S5 go to FEHE', () => {
    const g = flowsheetToGraph(demoFlowsheet, demoCases[0], opts(true))
    const ids = g.nodes.map((n) => n.id)
    expect(ids).toContain('FEHE')
    const e = Object.fromEntries(g.edges.map((x) => [x.id, x]))
    expect(e.S3).toBeDefined()
    expect(e.S6).toBeDefined()
    expect(e.S2.target).toBe('FEHE')
    expect(e.S5.target).toBe('FEHE')
  })
  it('without heat integration: FEHE, S3, S6 hidden and S2/S5 rerouted', () => {
    const g = flowsheetToGraph(demoFlowsheet, demoCases[1], opts(false))
    expect(g.nodes.map((n) => n.id)).not.toContain('FEHE')
    const e = Object.fromEntries(g.edges.map((x) => [x.id, x]))
    expect(e.S3).toBeUndefined()
    expect(e.S6).toBeUndefined()
    expect(e.S2.target).toBe('HEATER')
    expect(e.S5.target).toBe('COOLER')
  })
  it('every edge references existing nodes and has an orthogonal route', () => {
    for (const hi of [true, false]) {
      const g = flowsheetToGraph(demoFlowsheet, demoCases[hi ? 0 : 1], opts(hi))
      const ids = new Set(g.nodes.map((n) => n.id))
      for (const edge of g.edges) {
        expect(ids.has(edge.source)).toBe(true)
        expect(ids.has(edge.target)).toBe(true)
        const p = edge.data!.points
        for (let i = 0; i < p.length - 1; i++) expect(p[i].x === p[i + 1].x || p[i].y === p[i + 1].y).toBe(true)
      }
      expect(g.edges.length).toBe(hi ? 13 : 11)
    }
  })
  it('works without a result (all n/a, grey streams)', () => {
    const g = flowsheetToGraph(demoFlowsheet, null, opts(true))
    expect(g.edges.every((e) => e.data!.result === null)).toBe(true)
  })
  it('labelAnchor picks the longest segment', () => {
    const a = labelAnchor([{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 100 }])
    expect(a.horizontal).toBe(false)
  })
})
