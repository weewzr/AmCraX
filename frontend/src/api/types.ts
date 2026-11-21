/**
 * TypeScript mirror of backend/amcrax/schemas.py (pydantic v2). Keep field names identical.
 * Optional[...] fields are `T | null` (the API serialises None as null); fields with a default
 * are always present in API output, so they are non-optional here.
 */
export const SCHEMA_VERSION = '1.0'
export const COMPONENTS = ['NH3', 'H2', 'N2', 'H2O', 'O2'] as const
export type ComponentId = (typeof COMPONENTS)[number]

export const MOLAR_MASS: Record<ComponentId, number> = {
  NH3: 17.0305,
  H2: 2.01588,
  N2: 28.0134,
  H2O: 18.01528,
  O2: 31.9988,
}

export const LHV_KJ_PER_MOL = { H2: 241.826, NH3: 316.8 } as const

export type DataSource = 'aspen_plus_v15' | 'python_model' | 'literature' | 'assumption' | 'demo'

export interface CaseInputs {
  case_id: string
  feed_total_kmol_h: number
  feed_h2o_mole_frac: number
  reactor_temperature_C: number
  reactor_pressure_bar: number
  heat_integration: boolean
  fehe_hot_end_approach_K: number
  psa_feed_temperature_C: number
  psa_h2_recovery: number
  psa_n2_slip: number
  burner_excess_air: number
  stack_temperature_C: number
  property_method: string
}

export interface StreamResult {
  id: string
  name: string
  source_block: string | null
  dest_block: string | null
  phase: string | null
  temperature_C: number | null
  pressure_bar: number | null
  vapor_fraction: number | null
  mole_flow_kmol_h: number | null
  mass_flow_kg_h: number | null
  enthalpy_flow_kW: number | null
  mole_frac: Record<string, number>
  mass_frac: Record<string, number>
  component_mole_flow_kmol_h: Record<string, number>
}

export interface BlockResult {
  id: string
  name: string
  block_type: string
  duty_kW: number | null
  power_kW: number | null
  outlet_temperature_C: number | null
  outlet_pressure_bar: number | null
  details: Record<string, number | string | null>
}

export interface RunStatus {
  converged: boolean
  has_errors: boolean
  has_warnings: boolean
  messages: string[]
  engine_time_s: number | null
}

export interface KPIs {
  nh3_conversion: number | null
  h2_in_cracked_gas_kmol_h: number | null
  h2_product_kmol_h: number | null
  h2_product_kg_h: number | null
  h2_purity_mole_frac: number | null
  h2_yield_overall: number | null
  reactor_duty_kW: number | null
  preheat_duty_kW: number | null
  vaporiser_duty_kW: number | null
  recovered_heat_kW: number | null
  total_external_heating_kW: number | null
  cooling_duty_kW: number | null
  pump_power_kW: number | null
  tailgas_combustion_heat_kW: number | null
  tailgas_lhv_kW: number | null
  specific_heat_demand_kWh_per_kgH2: number | null
  net_fuel_heat_deficit_kW: number | null
  lhv_efficiency: number | null
}

export interface Balances {
  mass_in_kg_h: number | null
  mass_out_kg_h: number | null
  mass_closure_rel: number | null
  n_atoms_in_kmol_h: number | null
  n_atoms_out_kmol_h: number | null
  h_atoms_in_kmol_h: number | null
  h_atoms_out_kmol_h: number | null
  energy_in_kW: number | null
  energy_out_kW: number | null
  energy_closure_rel: number | null
}

export interface SimulationResult {
  schema_version: string
  case_id: string
  source: DataSource
  created_utc: string
  model_file: string | null
  inputs: CaseInputs
  status: RunStatus
  streams: Record<string, StreamResult>
  blocks: Record<string, BlockResult>
  kpis: KPIs
  balances: Balances
  notes: string[]
}

// ---- config/flowsheet.json (served by GET /api/flowsheet) ----
export interface FlowsheetSection {
  id: string
  label: string
}
export interface FlowsheetBlock {
  id: string
  name: string
  aspen_type: string
  section: string
  pfd: { x: number; y: number; symbol: string }
  role: string
  optional?: boolean
}
export interface FlowsheetStream {
  id: string
  name: string
  from: string | null
  to: string | null
  from_port?: string
  to_port?: string
  to_if_no_fehe?: string
  kind: 'feed' | 'process' | 'product'
  requires?: string
}
export interface Flowsheet {
  schema_version: string
  name: string
  description?: string
  components: string[]
  property_method: string
  sections: FlowsheetSection[]
  blocks: FlowsheetBlock[]
  streams: FlowsheetStream[]
  feed?: Record<string, unknown>
  air?: Record<string, unknown>
}

// ---- API envelope types (assumed from backend/amcrax/api/store.py; verified at runtime by the client) ----
export interface HealthInfo {
  status: string
  [k: string]: unknown
}
/** Summary row of GET /api/cases (see api/store.py list_cases). */
export interface CaseSummary {
  case_id: string
  valid: boolean
  source?: DataSource
  created_utc?: string
  converged?: boolean
  error?: string
}
export interface SnapshotManifest {
  exported_utc?: string
  files?: Array<{ path: string; source: string; bytes: number; how: string }>
  [k: string]: unknown
}
