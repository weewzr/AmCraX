import { describe, expect, it } from 'vitest'
import { conversionCurve, equilibriumAt, equilibriumConstant, KELVIN, STOICH_CONST } from './equilibrium'

/** Rows copied from results/validation/equilibrium_python_grid.csv (eos = ideal): independent Python/SciPy solver. */
const REF: { T: number; P: number; X: number; yNH3: number; yH2: number; yN2: number; K: number; dH: number }[] = [
  { T: 250, P: 1, X: 0.897608686, yNH3: 0.05395807616, yH2: 0.7095314429, yN2: 0.236510481, K: 5.386742402, dH: 50.27264358 },
  { T: 300, P: 10, X: 0.7306350369, yNH3: 0.1556451576, yH2: 0.6332661318, yN2: 0.2110887106, K: 14.87566134, dH: 51.03277053 },
  { T: 350, P: 20, X: 0.75909871, yNH3: 0.1369458625, yH2: 0.6472906032, yN2: 0.2157635344, K: 35.32800047, dH: 51.71527823 },
  { T: 400, P: 30, X: 0.8102280958, yNH3: 0.1048331449, yH2: 0.6713751414, yN2: 0.2237917138, K: 74.47191589, dH: 52.32668896 },
  { T: 500, P: 5, X: 0.9873831134, yNH3: 0.006348492385, yH2: 0.7452386307, yN2: 0.2484128769, K: 252.5396024, dH: 53.3682629 },
  { T: 600, P: 20, X: 0.9808364443, yNH3: 0.009674476552, yH2: 0.7427441426, yN2: 0.2475813809, K: 658.4463023, dH: 54.21554726 },
  { T: 700, P: 40, X: 0.9822546234, yNH3: 0.008952117643, yH2: 0.7432859118, yN2: 0.2477619706, K: 1425.231412, dH: 54.88824034 },
  { T: 900, P: 1, X: 0.999857957, yNH3: 7.102654314e-05, yH2: 0.7499467301, yN2: 0.2499822434, K: 4571.718975, dH: 55.70335375 },
  { T: 900, P: 40, X: 0.9943650585, yNH3: 0.002825431303, yH2: 0.7478809265, yN2: 0.2492936422, K: 4571.718975, dH: 55.70335375 },
]

describe('ideal-gas equilibrium (TypeScript port of the Python model)', () => {
  it.each(REF)('matches the Python reference at $T degC, $P bar (conversion within 1e-4)', (r) => {
    const e = equilibriumAt(r.T, r.P)
    expect(Math.abs(e.conversion - r.X)).toBeLessThan(1e-4)
    expect(Math.abs(e.y.NH3 - r.yNH3)).toBeLessThan(1e-4)
    expect(Math.abs(e.y.H2 - r.yH2)).toBeLessThan(1e-4)
    expect(Math.abs(e.y.N2 - r.yN2)).toBeLessThan(1e-4)
    expect(Math.abs(e.K / r.K - 1)).toBeLessThan(1e-5)
    expect(Math.abs(e.dH_kJ_per_mol_NH3 - r.dH)).toBeLessThan(5e-3)
  })

  it('reproduces the baseline of the technical report (600 degC, 20 bar: X = 0.9808, K = 658.4)', () => {
    const e = equilibriumAt(600, 20)
    expect(e.conversion).toBeCloseTo(0.98084, 4)
    expect(e.K).toBeCloseTo(658.4, 0)
  })

  it('closed form is consistent with the mass-action law K = (3 sqrt3 / 4) X^2 / (1 - X^2) P', () => {
    for (const [T, P] of [[300, 5], [550, 12], [800, 33]]) {
      const e = equilibriumAt(T, P)
      const K = STOICH_CONST * (e.conversion ** 2 / (1 - e.conversion ** 2)) * P
      expect(Math.abs(K / equilibriumConstant(T + KELVIN) - 1)).toBeLessThan(1e-12)
    }
  })

  it('mole fractions sum to one and conversion falls with pressure, rises with temperature', () => {
    const e = equilibriumAt(450, 15)
    expect(e.y.NH3 + e.y.H2 + e.y.N2).toBeCloseTo(1, 12)
    expect(equilibriumAt(450, 30).conversion).toBeLessThan(equilibriumAt(450, 5).conversion)
    expect(equilibriumAt(700, 10).conversion).toBeGreaterThan(equilibriumAt(400, 10).conversion)
  })

  it('curves cover the requested range and reject bad pressure', () => {
    const c = conversionCurve(20, 250, 900, 50)
    expect(c[0].T_C).toBe(250)
    expect(c[c.length - 1].T_C).toBe(900)
    expect(() => equilibriumAt(500, 0)).toThrow()
  })
})
