/// <reference types="node" />
/**
 * Browser model against stored Aspen Plus V15 results (and the measured deviation from the Python model).
 * These are COMPARISONS ('browser model against Aspen'), never validation. Nothing about Aspen is asserted.
 *
 * Re-run and write results/research/simulator/parity_report.json:
 *   (PowerShell, in frontend/)  $env:AMCRAX_WRITE_PARITY='1'; npx vitest run src/sim/parity.test.ts; Remove-Item Env:AMCRAX_WRITE_PARITY
 */
import { writeFileSync } from 'node:fs'
import { expect, it } from 'vitest'
import { carbonIntensity, type Heating } from './carbon'
import { evaluateEconomics } from './economics'
import { simulatePFR, type ThermalMode } from './pfr'
import { simulateProcess } from './process'
import { simulate } from './simulate'
import { anchors, data, model, resultsDir, vectors } from './testdata'
import { equilibriumConversion } from './thermo'

const relDev = (a: number, b: number) => (a - b) / Math.max(Math.abs(b), 1e-12)
const maxAbs = (xs: number[]) => xs.reduce((m, x) => (Number.isFinite(x) ? Math.max(m, Math.abs(x)) : m), 0)

function vsPython() {
  const conv: number[] = [], T: number[] = [], P: number[] = [], duty: number[] = []
  for (const v of vectors.vectors.filter((x) => x.kind === 'pfr')) {
    const i = v.inputs
    const r = simulatePFR(model, { catalyst_id: i.catalyst_id, W_kg: i.W_kg, T_in_C: i.T_in_C, P_in_bar: i.P_in_bar, mode: i.mode,
      pressure_drop: i.pressure_drop, n_tubes: i.n_tubes, T_wall_C: i.T_wall_C ?? undefined, U_W_m2K: i.U_W_m2K ?? undefined, n_points: v.python.W_kg.length })
    v.python.conversion.forEach((x: number, k: number) => conv.push(r.profiles.conversion[k] - x))
    v.python.T_K.forEach((x: number, k: number) => T.push(r.profiles.T_K[k] - x))
    v.python.P_bar.forEach((x: number, k: number) => P.push(r.profiles.P_bar[k] - x))
    if (Math.abs(v.python.outlet.heat_input_kW) > 1) duty.push(relDev(r.outlet.heat_input_kW, v.python.outlet.heat_input_kW))
  }
  const procOn: number[] = [], procOff: Record<string, number> = {}
  for (const v of vectors.vectors.filter((x) => x.kind === 'process')) {
    const i = v.inputs
    const r = simulateProcess(model, { T_C: i.T_C, P_bar: i.P_bar, heat_integration: i.heat_integration, feed_total_kmol_h: i.feed_total_kmol_h, psa_h2_recovery: i.psa_h2_recovery })
    for (const k of ['h2_product_kg_h', 'reactor_duty_kW', 'tailgas_lhv_kW', 'tailgas_combustion_heat_kW', 'preheat_duty_kW', 'vaporiser_duty_kW',
      'recovered_heat_kW', 'cooling_duty_kW', 'pump_power_kW', 'total_external_heating_kW', 'net_fuel_heat_deficit_kW'] as const) {
      const d = relDev(r[k], v.python[k])
      if (v.on_grid) procOn.push(d)
      else procOff[k] = Math.max(procOff[k] ?? 0, Math.abs(d))
    }
  }
  const lcoh: number[] = []
  for (const v of vectors.vectors.filter((x) => x.kind === 'economics')) {
    const r = evaluateEconomics(model, v.inputs.summary, v.inputs.scenario, v.inputs.overrides)
    lcoh.push(relDev(r.lcoh_USD_per_kg, v.python.lcoh_USD_per_kg))
  }
  const ci: number[] = []
  for (const v of vectors.vectors.filter((x) => x.kind === 'carbon')) {
    const [route, heat] = (v.inputs.scenario as string).split('/')
    ci.push(relDev(carbonIntensity(model, v.inputs, route, heat as Heating).total_kgCO2e_per_kgH2, v.python.total))
  }
  return {
    pfr_profiles: { max_abs_conversion: maxAbs(conv), max_abs_T_K: maxAbs(T), max_abs_P_bar: maxAbs(P), max_rel_heat_input: maxAbs(duty), n_cases: vectors.vectors.filter((x) => x.kind === 'pfr').length },
    process_on_grid_max_rel: maxAbs(procOn),
    process_off_grid_max_rel_by_field: procOff,
    process_off_grid_note: 'off-grid points: interpolated fields (pump, vaporiser, preheat, FEHE, cooler) carry bilinear-interpolation error of the Python grid; reported, not asserted',
    lcoh_max_rel: maxAbs(lcoh), carbon_intensity_max_rel: maxAbs(ci),
  }
}

function vsAspen() {
  const cases = []
  for (const c of anchors.kinetic_cases) {
    if (c.configuration !== 'standalone' && c.configuration !== 'integrated') continue
    const inl = (c as unknown as { inlet: { flows_kmol_h: Record<string, number> } }).inlet
    const feed = Object.fromEntries(Object.entries(inl.flows_kmol_h ?? {}).filter(([, v]) => v > 0))
    const mode: ThermalMode = c.thermal_mode === 'coolant' ? 'external' : (c.thermal_mode as ThermalMode)
    const P_in = (c as unknown as { inlet: { P_bar: number } }).inlet.P_bar ?? c.P_bar
    let r
    try {
      r = simulatePFR(model, { catalyst_id: c.catalyst_id, W_kg: c.catalyst_mass_kg, T_in_C: c.T_C, P_in_bar: P_in, feed_kmol_h: feed, mode,
        T_wall_C: c.coolant_temperature_C ?? undefined, U_W_m2K: c.U_W_m2K ?? undefined, n_tubes: c.n_tubes, tube_inner_diameter_m: c.tube_diameter_m,
        pressure_drop: Boolean(c.pressure_drop), n_points: 2 })
    } catch (e) {
      cases.push({ case_id: c.case_id, error: String(e) })
      continue
    }
    cases.push({ case_id: c.case_id, configuration: c.configuration, catalyst_id: c.catalyst_id, T_C: c.T_C, P_bar: c.P_bar, W_kg: c.catalyst_mass_kg, mode,
      aspen: { conversion: c.conversion, duty_kW: c.duty_kW, outlet_T_C: c.outlet.T_C, outlet_P_bar: c.outlet.P_bar },
      browser: { conversion: r.outlet.conversion, duty_kW: r.outlet.heat_input_kW, outlet_T_C: r.outlet.T_C, outlet_P_bar: r.outlet.P_bar },
      diff: { conversion: r.outlet.conversion - c.conversion, duty_rel: relDev(r.outlet.heat_input_kW, c.duty_kW), outlet_T_K: r.outlet.T_C - c.outlet.T_C,
        outlet_P_bar: r.outlet.P_bar - c.outlet.P_bar } })
  }
  const ok = cases.filter((x) => 'diff' in x) as { diff: Record<string, number>; mode: string; T_C: number; P_bar: number }[]
  const iso = ok.filter((x) => x.mode === 'isothermal')
  const integrated = []
  for (const c of anchors.kinetic_cases.filter((x) => x.configuration === 'integrated' && x.flowsheet_kpis)) {
    const s = simulate({ catalyst_id: c.catalyst_id, T_C: c.T_C, P_bar: c.P_bar, W_kg: c.catalyst_mass_kg, mode: 'isothermal', n_tubes: c.n_tubes,
      heat_integration: Boolean(c.heat_integration), nh3_route: 'grey', n_points: 2 }, data) // browser values (pfr.outlet), not the anchor
    const pr = simulateProcess(model, { T_C: c.T_C, P_bar: c.P_bar, heat_integration: Boolean(c.heat_integration),
      conversion: s.reactor.pfr.outlet.conversion, reactor_duty_kW: s.reactor.pfr.outlet.heat_input_kW })
    const k = c.flowsheet_kpis as Record<string, number>
    const d: Record<string, number> = {}
    for (const f of ['h2_product_kg_h', 'reactor_duty_kW', 'vaporiser_duty_kW', 'preheat_duty_kW', 'recovered_heat_kW', 'total_external_heating_kW',
      'cooling_duty_kW', 'tailgas_combustion_heat_kW', 'net_fuel_heat_deficit_kW'] as const) d[f] = relDev(pr[f], k[f])
    integrated.push({ case_id: c.case_id, rel_diff: d, conversion_diff: pr.conversion - k.nh3_conversion })
  }
  const core = anchors.core_cases.map((c) => {
    const i = c.inputs as Record<string, number | boolean>
    const pr = simulateProcess(model, { T_C: i.reactor_temperature_C as number, P_bar: i.reactor_pressure_bar as number, heat_integration: i.heat_integration as boolean,
      feed_total_kmol_h: i.feed_total_kmol_h as number, psa_h2_recovery: i.psa_h2_recovery as number, psa_n2_slip: i.psa_n2_slip as number })
    const d: Record<string, number> = {}
    for (const f of ['h2_product_kg_h', 'reactor_duty_kW', 'recovered_heat_kW', 'total_external_heating_kW', 'net_fuel_heat_deficit_kW', 'h2_purity_mole_frac'] as const)
      d[f] = relDev(pr[f], c.kpis[f])
    return { case_id: c.case_id, conversion_diff: pr.conversion - c.kpis.nh3_conversion, rel_diff: d, grid_on_node: pr.grid_on_node }
  })
  const eq = anchors.equilibrium_grid.points.map((p) => equilibriumConversion(model, p.T_C + 273.15, p.P_bar, { NH3: 1 }) - p.conversion)
  return {
    kinetic_cases: cases,
    kinetic_summary: { n: cases.length, n_failed: cases.length - ok.length,
      max_abs_conversion_diff_all: maxAbs(ok.map((x) => x.diff.conversion)), max_abs_conversion_diff_isothermal: maxAbs(iso.map((x) => x.diff.conversion)),
      max_abs_duty_rel_isothermal: maxAbs(iso.map((x) => x.diff.duty_rel)), max_abs_outlet_T_K_nonisothermal: maxAbs(ok.filter((x) => x.mode !== 'isothermal').map((x) => x.diff.outlet_T_K)) },
    integrated_flowsheet_cases: integrated,
    core_equilibrium_flowsheet_cases: core,
    equilibrium_grid: { n: eq.length, max_abs_conversion_diff_ideal_gas_vs_aspen_PR: maxAbs(eq),
      note: 'browser ideal-gas equilibrium against Aspen RGibbs PENG-ROB; the difference is a model-form (non-ideality) difference' },
  }
}

it('browser model against Python and against stored Aspen results (comparison, not validation)', () => {
  const rep = {
    schema: 'amcrax.simulator/1',
    statement: "Browser model against the Python model (numerical verification of the port) and browser model against stored Aspen Plus V15 results (python_vs_aspen-type comparison). Not validation; AmCraX has no experimental validation.",
    evidence_kind: { browser_vs_python: 'numerical_verification', browser_vs_aspen: 'python_vs_aspen' },
    tolerances_vs_python: vectors.tolerances,
    browser_vs_python: vsPython(),
    browser_vs_aspen: vsAspen(),
    provenance: { command: "cd frontend; $env:AMCRAX_WRITE_PARITY='1'; npx vitest run src/sim/parity.test.ts", source_type: 'browser-model',
      inputs: ['results/research/simulator/model.json', 'results/research/simulator/aspen_anchors.json', 'results/research/simulator/test_vectors.json'] },
  }
  expect(rep.browser_vs_aspen.kinetic_summary.n).toBeGreaterThan(0)
  if (process.env.AMCRAX_WRITE_PARITY === '1') writeFileSync(new URL('parity_report.json', resultsDir), JSON.stringify(rep, null, 1) + '\n', 'utf-8')
}, 300_000)
