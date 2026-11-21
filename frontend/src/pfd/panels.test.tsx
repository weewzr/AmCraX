import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { demoCases, demoFlowsheet } from '../demo/fixture'
import { BlockPanel, StreamPanel } from './panels'
import { Value } from '../components/ui'
import { createElement } from 'react'

describe('panels and Value', () => {
  const r = demoCases[0]
  it('stream panel shows composition and the demo provenance badge', () => {
    const html = renderToString(createElement(StreamPanel, {
      stream: demoFlowsheet.streams[5], result: r.streams.S5, destLabel: 'FEHE', source: r.source, converged: true, onClose: () => {},
    }))
    expect(html).toContain('S5')
    expect(html).toContain('ILLUSTRATIVE')
    expect(html).toContain('H2')
  })
  it('block panel renders and shows n/a for missing result', () => {
    const html = renderToString(createElement(BlockPanel, { block: demoFlowsheet.blocks[0], result: null, source: null, converged: null, onClose: () => {} }))
    expect(html).toContain('n/a')
    expect(html).toContain('No result')
  })
  it('Value renders n/a for null and never a number', () => {
    const html = renderToString(createElement(Value, { v: null, unit: 'kW', source: 'aspen_plus_v15' }))
    expect(html).toContain('n/a')
    expect(html).not.toContain('kW')
  })
})
