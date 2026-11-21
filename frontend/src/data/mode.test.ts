import { describe, expect, it } from 'vitest'
import { resolveDataMode } from './mode'

const fail = () => Promise.reject(new Error('down'))

describe('resolveDataMode', () => {
  it('LIVE when the API answers', async () => {
    const r = await resolveDataMode({ fetchHealth: () => Promise.resolve({ status: 'ok' }), fetchManifest: () => Promise.resolve({}) })
    expect(r.mode).toBe('LIVE')
  })
  it('SNAPSHOT when the API is down but the manifest exists', async () => {
    const r = await resolveDataMode({ fetchHealth: fail, fetchManifest: () => Promise.resolve({ exported_utc: '2026-01-01T00:00:00Z' }) })
    expect(r.mode).toBe('SNAPSHOT')
    expect(r.manifest?.exported_utc).toBe('2026-01-01T00:00:00Z')
  })
  it('DEMO when neither is available', async () => {
    const r = await resolveDataMode({ fetchHealth: fail, fetchManifest: fail })
    expect(r.mode).toBe('DEMO')
  })
})
