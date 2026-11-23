/**
 * Types of the browser-side simulator data (results/research/simulator/*.json, exported by
 * scripts/research/export_simulator_data.py). The TypeScript code holds no scientific parameter values:
 * every number comes from these files.
 */

/** Source label of every simulator output. */
export type SourceLabel = 'aspen' | 'interpolation' | 'browser-model' | 'extrapolation' | 'assumption'

export interface Labelled<T = number> {
  value: T
  source: SourceLabel
  /** short reason for the label (e.g. "outside the fitted T range of the rate law") */
  note?: string
  unit?: string
}

export interface Nasa7Species {
  Tmin: number; Tmid: number; Tmax: number; low: number[]; high: number[]; ds_R: number
  composition: Record<string, number>
}

export interface LawParam { value: number; unit: string; citekey: string; page?: number | string; locator?: string; uncertainty?: number }

export type RateForm = 'takahashi_microkinetic' | 'temkin_pyzhev' | 'lhhw_lucentini'

export interface RateLaw {
  id: string; short: string; registry_section: string; label: string; metal: string; composition: string
  form: RateForm; usable: boolean; rate_law_text: string; rate_unit_published: string; rate_unit_model: string
  pressure_basis: string; parameters: Record<string, LawParam>
  validity: { T_min_K: number; T_max_K: number; P_min_bar: number; P_max_bar: number; note: string }
  irreversible_published: boolean; reversibility_treatment: string
  equilibrium_constant: { dGr_coefficients_J: number[]; [k: string]: unknown } | null
  bed_properties: Record<string, unknown> | null
  limitations: string[]; source: Record<string, unknown>; citekey: string; amcrax_extensions: string[]
  validity_classification: unknown
}

export interface ProcessGridNode {
  vaporiser_kW: number; pump_kW: number; preheat_kW: number; recovered_kW: number; cooling_kW: number
  combustion_over_lhv: number
}

export interface SimModel {
  schema: string
  thermo: {
    R_J_molK: number; standard_pressure_bar: number; species: Record<string, Nasa7Species>; argon_cp_J_molK: number
    molar_mass_g_mol: Record<string, number>; lhv_kJ_per_mol: Record<string, number>; source: string
  }
  kinetics: {
    unit_conversions: { g_per_kg: number; bar_per_atm: number; gas_constant_J_per_mol_K: number }
    equilibrium_approach_factor: { applies_to_forms: string[]; default_on: boolean; expression: string; label: string }
    laws: Record<string, RateLaw>; law_ids: string[]; takahashi_root_bracket_ln_theta_s: [number, number]
    validity_classification_status: string
  }
  reactor: {
    default_bed: { eps_b: number; rho_particle_kg_m3: number; dp_m: number; tube_inner_diameter_m: number }
    baseline_feed_kmol_h: Record<string, number>; molar_mass_kg_mol: Record<string, number>
    normal_T_K: number; normal_P_Pa: number; x_seed_temkin: number; hydraulic_stop_fraction_of_inlet_pressure: number
    ergun: { viscous: number; inertial: number }; default_n_tubes: number; default_keq_basis: string
    viscosity: { T_K: number[]; X: number[]; mu_Pa_s: number[][] }
  }
  process: {
    inputs_defaults: Record<string, number | boolean | string>
    grid: { T_C: number[]; P_bar: number[]; per_kmol_h_total_feed: { hi: (ProcessGridNode | null)[][]; nohi: (ProcessGridNode | null)[][] } }
    min_flowsheet_pressure_bar: number
    air: { T_C: number; O2: number; N2: number }
    reduction: string
  }
  purification: { psa_h2_recovery_default: number; psa_n2_slip_default: number; purity_label: string; membrane: string }
  economics: {
    basis: string
    economic_assumptions: Record<string, number | string | boolean | null>
    sg_params: Record<string, number | string | boolean | null>
    catalyst_price_USD_per_kg: Record<string, number>
    catalyst_metal_map: Record<string, string>
    nh3_price_scenarios_USD_per_t: Record<string, number>
    capex_equipment: { equipment_shares_pct: Record<string, number>; pec_reference_kUSD: number; reference_feed_kmol_h: number
      scaling_exponent: number; singapore_location_factor: number; tci_over_pec: number }
    carbon_tax: { rate_2026_SGD_per_tCO2e: number; threshold_tCO2e_per_yr: number }
    natural_gas_co2_factor_kg_per_GJ: number
    cost_basis: string
  }
  fx: { SGD_per_USD: number; date: string | number | null; access_date: string | null; source: string | null; url: string | null; stored_in: string }
  carbon: {
    accounting: { upstream_ammonia: Record<string, number>; electricity: Record<string, number>; ship_ef_kg_per_tkm: number
      distance_km: number; natural_gas_kg_per_TJ: number; fired_heater_efficiency_lhv: number; electric_heater_efficiency: number }
    lca_routes: Record<string, { ef_kg_per_kg_nh3: number; low: number; high: number; label: string; source_type: string }>
    actual_boundary: string; hypothetical_boundary: string
  }
  tolerances: Record<string, number | string>
}

export interface KineticAnchor {
  case_id: string; configuration: string; catalyst_id: string; T_C: number; P_bar: number; catalyst_mass_kg: number
  thermal_mode: string; coolant_temperature_C: number | null; U_W_m2K: number | null; pressure_drop: boolean
  n_tubes: number; tube_diameter_m: number; heat_integration: boolean | null
  conversion: number; duty_kW: number; reactor_length_m: number; residence_time_s: number | null
  outlet: { T_C: number; P_bar: number; flows_kmol_h: Record<string, number>; y: Record<string, number> }
  profiles: { length_m: number[] | null; T_C: number[] | null; P_bar: number[] | null; conversion: (number | null)[] | null
    catalyst_mass_kg: number[] | null }
  flowsheet_kpis: Record<string, number> | null; model_file: string; file: string
}

export interface CoreAnchor { case_id: string; source: string; inputs: Record<string, unknown>; kpis: Record<string, number>; file: string }

export interface SimAnchors {
  kinetic_cases: KineticAnchor[]
  core_cases: CoreAnchor[]
  equilibrium_grid: { T_C: number[]; P_bar: number[]; points: { T_C: number; P_bar: number; conversion: number; heat_duty_kJ_per_mol_NH3_fed: number }[] }
}

export interface SimData { model: SimModel; anchors: SimAnchors }
