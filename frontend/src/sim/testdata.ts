/// <reference types="node" />
/** Test helper: loads results/research/simulator/*.json from disk (node only; not used by the app). */
import { readFileSync } from 'node:fs'
import type { SimAnchors, SimData, SimModel } from './types'

const dir = new URL('../../../results/research/simulator/', import.meta.url)
const read = <T>(name: string): T => JSON.parse(readFileSync(new URL(name, dir), 'utf-8')) as T

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Vector = { kind: string; id: string; inputs: any; python: any; on_grid?: boolean }

export const model = read<SimModel>('model.json')
export const anchors = read<SimAnchors>('aspen_anchors.json')
export const data: SimData = { model, anchors }
export const vectors = read<{ vectors: Vector[]; tolerances: Record<string, number> }>('test_vectors.json')
export const resultsDir = dir
