/** Stored Aspen Plus V15 anchors (aspen_anchors.json): exact-match lookup and bilinear interpolation of the RGibbs grid. */
import type { CoreAnchor, KineticAnchor, SimAnchors, SourceLabel } from './types'

const same = (a: number | null | undefined, b: number | null | undefined, tol = 1e-9) =>
  a !== null && a !== undefined && b !== null && b !== undefined && Math.abs(a - b) <= tol * Math.max(1, Math.abs(b))

export interface AnchorQuery {
  catalyst_id: string; T_C: number; P_bar: number; W_kg: number; mode: string; pressure_drop: boolean
  n_tubes: number; configuration?: 'standalone' | 'integrated'; heat_integration?: boolean
  T_wall_C?: number; U_W_m2K?: number
}

/**
 * Stored Aspen kinetic case for EXACTLY these inputs, or null. Matches catalyst, T, P, catalyst mass, thermal mode
 * (Aspen 'coolant' = browser 'external' with the same coolant T and U), pressure-drop flag, tube count and, for
 * integrated cases, heat integration. Aspen feeds carry a small H2 seed (h2_seed_conversion); the match ignores it.
 */
export function findKineticAnchor(an: SimAnchors, q: AnchorQuery): KineticAnchor | null {
  const conf = q.configuration ?? 'standalone'
  for (const c of an.kinetic_cases) {
    if (c.catalyst_id !== q.catalyst_id || c.configuration !== conf) continue
    if (!same(c.T_C, q.T_C) || !same(c.P_bar, q.P_bar) || !same(c.catalyst_mass_kg, q.W_kg)) continue
    if (Boolean(c.pressure_drop) !== q.pressure_drop || c.n_tubes !== q.n_tubes) continue
    const mode = c.thermal_mode === 'coolant' ? 'external' : c.thermal_mode
    if (mode !== q.mode) continue
    if (mode === 'external' && !(same(c.coolant_temperature_C, q.T_wall_C) && same(c.U_W_m2K, q.U_W_m2K))) continue
    if (conf === 'integrated' && c.heat_integration !== (q.heat_integration ?? true)) continue
    return c
  }
  return null
}

/** Core Aspen flowsheet case (equilibrium cracker) whose inputs equal these, or null. */
export function findCoreAnchor(an: SimAnchors, q: { T_C: number; P_bar: number; heat_integration: boolean; psa_h2_recovery: number; feed_total_kmol_h: number }): CoreAnchor | null {
  for (const c of an.core_cases) {
    const i = c.inputs as Record<string, number | boolean>
    if (same(i.reactor_temperature_C as number, q.T_C) && same(i.reactor_pressure_bar as number, q.P_bar) && i.heat_integration === q.heat_integration
      && same(i.psa_h2_recovery as number, q.psa_h2_recovery) && same(i.feed_total_kmol_h as number, q.feed_total_kmol_h)) return c
  }
  return null
}

export interface GridValue { value: number; source: SourceLabel; inside: boolean }

/** Aspen RGibbs (PENG-ROB) equilibrium conversion of pure NH3: node -> 'aspen', inside -> 'interpolation', else null. */
export function aspenEquilibrium(an: SimAnchors, T_C: number, P_bar: number): GridValue | null {
  const g = an.equilibrium_grid
  const Ts = g.T_C, Ps = g.P_bar
  if (T_C < Ts[0] || T_C > Ts[Ts.length - 1] || P_bar < Ps[0] || P_bar > Ps[Ps.length - 1]) return null
  const at = (T: number, P: number) => g.points.find((p) => p.T_C === T && p.P_bar === P)?.conversion
  let i = 0; while (i < Ts.length - 2 && T_C > Ts[i + 1]) i++
  let j = 0; while (j < Ps.length - 2 && P_bar > Ps[j + 1]) j++
  const t = (T_C - Ts[i]) / (Ts[i + 1] - Ts[i]), u = (P_bar - Ps[j]) / (Ps[j + 1] - Ps[j])
  const c = [at(Ts[i], Ps[j]), at(Ts[i], Ps[j + 1]), at(Ts[i + 1], Ps[j]), at(Ts[i + 1], Ps[j + 1])]
  if (c.some((x) => x === undefined)) return null
  const [a, b, cc, d] = c as number[]
  const v = (1 - t) * ((1 - u) * a + u * b) + t * ((1 - u) * cc + u * d)
  const node = Ts.includes(T_C) && Ps.includes(P_bar)
  return { value: v, source: node ? 'aspen' : 'interpolation', inside: true }
}
