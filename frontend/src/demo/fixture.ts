/**
 * DEMONSTRATION DATA - NOT SIMULATION RESULTS.
 * Every object here has source "demo". Numbers are hand-written placeholders chosen only so the
 * diagram has something to draw; they are not from Aspen, not from the Python model, and not
 * consistent to any balance. The topology (flowsheet) is a copy of config/flowsheet.json.
 */
import type { BlockResult, Flowsheet, SimulationResult, StreamResult } from '../api/types'
import { MOLAR_MASS } from '../api/types'

export const demoFlowsheet: Flowsheet = {
  schema_version: '1.0',
  name: 'AmCraX baseline ammonia-cracking flowsheet (demo copy of config/flowsheet.json)',
  components: ['NH3', 'H2', 'N2', 'H2O', 'O2'],
  property_method: 'PENG-ROB',
  sections: [
    { id: 'feed', label: 'Feed conditioning' },
    { id: 'reaction', label: 'Preheat and cracking' },
    { id: 'recovery', label: 'Heat recovery and cooling' },
    { id: 'purification', label: 'Hydrogen purification' },
    { id: 'combustion', label: 'Tail-gas combustion' },
  ],
  blocks: [
    { id: 'PUMP', name: 'Ammonia feed pump', aspen_type: 'Pump', section: 'feed', pfd: { x: 160, y: 260, symbol: 'pump' },
      role: 'Raises refrigerated liquid ammonia from storage pressure (1.013 bar) to the reactor-train pressure. Pumping a liquid is far cheaper than compressing the cracked gas.' },
    { id: 'VAPORIZR', name: 'Ammonia vaporiser', aspen_type: 'Heater', section: 'feed', pfd: { x: 360, y: 260, symbol: 'heater' },
      role: 'Vaporises the pressurised liquid ammonia and superheats it by 10 K so that the downstream exchanger handles single-phase gas.' },
    { id: 'FEHE', name: 'Feed/effluent heat exchanger', aspen_type: 'HeatX', section: 'recovery', pfd: { x: 580, y: 260, symbol: 'exchanger' },
      role: 'Recovers sensible heat from the hot cracked gas to preheat the ammonia feed. Only present when heat integration is enabled.', optional: true },
    { id: 'HEATER', name: 'Fired trim preheater', aspen_type: 'Heater', section: 'reaction', pfd: { x: 800, y: 260, symbol: 'furnace' },
      role: 'Raises the preheated ammonia to the reactor inlet temperature.' },
    { id: 'CRACKER', name: 'Ammonia cracking reactor', aspen_type: 'RGibbs', section: 'reaction', pfd: { x: 1020, y: 260, symbol: 'reactor' },
      role: 'Isothermal equilibrium reactor (Gibbs free-energy minimisation) for 2 NH3 <-> N2 + 3 H2. Its duty is the endothermic heat of reaction.' },
    { id: 'COOLER', name: 'Cracked-gas cooler', aspen_type: 'Heater', section: 'recovery', pfd: { x: 580, y: 470, symbol: 'cooler' },
      role: 'Cools the cracked gas leaving the FEHE to the purification feed temperature.' },
    { id: 'PSA', name: 'Hydrogen purification (reduced-order PSA)', aspen_type: 'Sep', section: 'purification', pfd: { x: 800, y: 470, symbol: 'psa' },
      role: 'Component splitter with specified H2 recovery and N2 slip. It represents the material balance of a PSA unit; it is NOT a designed adsorption model.' },
    { id: 'BURNER', name: 'Tail-gas burner', aspen_type: 'RStoic', section: 'combustion', pfd: { x: 1020, y: 640, symbol: 'burner' },
      role: 'Adiabatic complete combustion of the PSA tail gas (unrecovered H2, residual NH3, N2) with air.' },
    { id: 'FLUEHX', name: 'Flue-gas heat recovery', aspen_type: 'Heater', section: 'combustion', pfd: { x: 1240, y: 640, symbol: 'cooler' },
      role: 'Cools the flue gas to the stack temperature. Its duty is the heat available from tail-gas combustion, compared with the process heat demand in the heat-integration analysis.' },
  ],
  streams: [
    { id: 'FEED', name: 'Liquid ammonia feed', from: null, to: 'PUMP', kind: 'feed' },
    { id: 'S1', name: 'Pressurised liquid ammonia', from: 'PUMP', to: 'VAPORIZR', kind: 'process' },
    { id: 'S2', name: 'Ammonia vapour', from: 'VAPORIZR', to: 'FEHE', to_port: 'cold_in', to_if_no_fehe: 'HEATER', kind: 'process' },
    { id: 'S3', name: 'Preheated ammonia', from: 'FEHE', from_port: 'cold_out', to: 'HEATER', kind: 'process', requires: 'FEHE' },
    { id: 'S4', name: 'Reactor feed', from: 'HEATER', to: 'CRACKER', kind: 'process' },
    { id: 'S5', name: 'Hot cracked gas', from: 'CRACKER', to: 'FEHE', to_port: 'hot_in', to_if_no_fehe: 'COOLER', kind: 'process' },
    { id: 'S6', name: 'Partly cooled cracked gas', from: 'FEHE', from_port: 'hot_out', to: 'COOLER', kind: 'process', requires: 'FEHE' },
    { id: 'S7', name: 'PSA feed', from: 'COOLER', to: 'PSA', kind: 'process' },
    { id: 'H2PROD', name: 'Hydrogen product', from: 'PSA', to: null, kind: 'product' },
    { id: 'TAILGAS', name: 'PSA tail gas (N2-rich off-gas)', from: 'PSA', to: 'BURNER', kind: 'process' },
    { id: 'AIR', name: 'Combustion air', from: null, to: 'BURNER', kind: 'feed' },
    { id: 'FLUE', name: 'Hot flue gas', from: 'BURNER', to: 'FLUEHX', kind: 'process' },
    { id: 'STACK', name: 'Stack gas', from: 'FLUEHX', to: null, kind: 'product' },
  ],
}

type Comp = Record<string, number>

function stream(id: string, name: string, src: string | null, dst: string | null,
  T: number, P: number, vf: number, nFlow: number, x: Comp): StreamResult {
  const mass = Object.entries(x).reduce((s, [c, v]) => s + v * nFlow * (MOLAR_MASS as Record<string, number>)[c], 0)
  const massFrac: Comp = {}
  const compFlow: Comp = {}
  for (const [c, v] of Object.entries(x)) {
    massFrac[c] = (v * nFlow * (MOLAR_MASS as Record<string, number>)[c]) / mass
    compFlow[c] = v * nFlow
  }
  return {
    id, name, source_block: src, dest_block: dst,
    phase: vf === 0 ? 'liquid' : vf === 1 ? 'vapor' : 'mixed',
    temperature_C: T, pressure_bar: P, vapor_fraction: vf,
    mole_flow_kmol_h: nFlow, mass_flow_kg_h: mass, enthalpy_flow_kW: null,
    mole_frac: x, mass_frac: massFrac, component_mole_flow_kmol_h: compFlow,
  }
}

function block(id: string, name: string, type: string, duty: number | null, T: number | null, P: number | null,
  power: number | null = null): BlockResult {
  return { id, name, block_type: type, duty_kW: duty, power_kW: power, outlet_temperature_C: T, outlet_pressure_bar: P, details: {} }
}

function makeDemo(heatIntegration: boolean): SimulationResult {
  const nh3 = { NH3: 0.998, H2O: 0.002 }
  const cracked = { NH3: 0.01, H2: 0.74, N2: 0.249, H2O: 0.001 }
  const streams: StreamResult[] = [
    stream('FEED', 'Liquid ammonia feed', null, 'PUMP', -33, 1.013, 0, 100, nh3),
    stream('S1', 'Pressurised liquid ammonia', 'PUMP', 'VAPORIZR', -32, 21, 0, 100, nh3),
    stream('S2', 'Ammonia vapour', 'VAPORIZR', heatIntegration ? 'FEHE' : 'HEATER', 60, 20.8, 1, 100, nh3),
    ...(heatIntegration ? [stream('S3', 'Preheated ammonia', 'FEHE', 'HEATER', 450, 20.5, 1, 100, nh3)] : []),
    stream('S4', 'Reactor feed', 'HEATER', 'CRACKER', 600, 20.2, 1, 100, nh3),
    stream('S5', 'Hot cracked gas', 'CRACKER', heatIntegration ? 'FEHE' : 'COOLER', 600, 20, 1, 198, cracked),
    ...(heatIntegration ? [stream('S6', 'Partly cooled cracked gas', 'FEHE', 'COOLER', 120, 19.7, 1, 198, cracked)] : []),
    stream('S7', 'PSA feed', 'COOLER', 'PSA', 40, 19.5, 1, 198, cracked),
    stream('H2PROD', 'Hydrogen product', 'PSA', null, 40, 19, 1, 125, { H2: 0.999, N2: 0.001 }),
    stream('TAILGAS', 'PSA tail gas', 'PSA', 'BURNER', 40, 1.3, 1, 73, { NH3: 0.027, H2: 0.30, N2: 0.67, H2O: 0.003 }),
    stream('AIR', 'Combustion air', null, 'BURNER', 25, 1.3, 1, 60, { N2: 0.79, O2: 0.21 }),
    stream('FLUE', 'Hot flue gas', 'BURNER', 'FLUEHX', 900, 1.2, 1, 130, { N2: 0.8, H2O: 0.15, O2: 0.05 }),
    stream('STACK', 'Stack gas', 'FLUEHX', null, 150, 1.1, 1, 130, { N2: 0.8, H2O: 0.15, O2: 0.05 }),
  ]
  const blocks: BlockResult[] = [
    block('PUMP', 'Ammonia feed pump', 'Pump', null, -32, 21, 1.0),
    block('VAPORIZR', 'Ammonia vaporiser', 'Heater', 100, 60, 20.8),
    ...(heatIntegration ? [block('FEHE', 'Feed/effluent heat exchanger', 'HeatX', 100, 450, 20.5)] : []),
    block('HEATER', 'Fired trim preheater', 'Heater', 100, 600, 20.2),
    block('CRACKER', 'Ammonia cracking reactor', 'RGibbs', 100, 600, 20),
    block('COOLER', 'Cracked-gas cooler', 'Heater', -100, 40, 19.5),
    block('PSA', 'Hydrogen purification (reduced-order PSA)', 'Sep', null, 40, 19),
    block('BURNER', 'Tail-gas burner', 'RStoic', null, 900, 1.2),
    block('FLUEHX', 'Flue-gas heat recovery', 'Heater', -100, 150, 1.1),
  ]
  const ci = heatIntegration ? 'demo_baseline' : 'demo_no_heat_integration'
  return {
    schema_version: '1.0', case_id: ci, source: 'demo', created_utc: '1970-01-01T00:00:00+00:00', model_file: null,
    inputs: {
      case_id: ci, feed_total_kmol_h: 100, feed_h2o_mole_frac: 0.002, reactor_temperature_C: 600, reactor_pressure_bar: 20,
      heat_integration: heatIntegration, fehe_hot_end_approach_K: 50, psa_feed_temperature_C: 40, psa_h2_recovery: 0.85,
      psa_n2_slip: 0.001, burner_excess_air: 0.15, stack_temperature_C: 150, property_method: 'PENG-ROB',
    },
    status: { converged: true, has_errors: false, has_warnings: true, messages: ['DEMONSTRATION DATA: no simulation was run.'], engine_time_s: null },
    streams: Object.fromEntries(streams.map((s) => [s.id, s])),
    blocks: Object.fromEntries(blocks.map((b) => [b.id, b])),
    kpis: {
      nh3_conversion: 0.99, h2_in_cracked_gas_kmol_h: 147, h2_product_kmol_h: 125, h2_product_kg_h: 252, h2_purity_mole_frac: 0.999,
      h2_yield_overall: 0.83, reactor_duty_kW: 100, preheat_duty_kW: 100, vaporiser_duty_kW: 100, recovered_heat_kW: heatIntegration ? 100 : 0,
      total_external_heating_kW: 300, cooling_duty_kW: 100, pump_power_kW: 1, tailgas_combustion_heat_kW: 100, tailgas_lhv_kW: 100,
      specific_heat_demand_kWh_per_kgH2: 1, net_fuel_heat_deficit_kW: 100, lhv_efficiency: 0.5,
    },
    balances: {
      mass_in_kg_h: null, mass_out_kg_h: null, mass_closure_rel: null, n_atoms_in_kmol_h: null, n_atoms_out_kmol_h: null,
      h_atoms_in_kmol_h: null, h_atoms_out_kmol_h: null, energy_in_kW: null, energy_out_kW: null, energy_closure_rel: null,
    },
    notes: ['DEMONSTRATION DATA - not simulation results. Values are arbitrary placeholders.'],
  }
}

export const demoCases: SimulationResult[] = [makeDemo(true), makeDemo(false)]
