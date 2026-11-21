/**
 * One shared map from raw metric / variable keys (as stored in the result files) to human-readable labels with units.
 * Used by Sensitivity, Simulation, Optimisation: raw keys such as total_external_heating_kW never appear as axis titles.
 */
export interface MetricInfo { label: string; unit: string }

const M = (label: string, unit = ''): MetricInfo => ({ label, unit })

export const METRICS: Record<string, MetricInfo> = {
  // inputs / decision variables
  reactor_temperature_C: M('Cracker temperature', 'degC'),
  reactor_pressure_bar: M('Cracker pressure', 'bar'),
  psa_h2_recovery: M('PSA H2 recovery', '-'),
  psa_n2_slip: M('PSA N2 slip', '-'),
  psa_feed_temperature_C: M('PSA feed temperature', 'degC'),
  fehe_hot_end_approach_K: M('FEHE hot-end approach', 'K'),
  feed_total_kmol_h: M('Ammonia feed', 'kmol/h'),
  feed_h2o_mole_frac: M('Water in feed', 'mol/mol'),
  burner_excess_air: M('Burner excess air', '-'),
  stack_temperature_C: M('Stack temperature', 'degC'),
  // KPIs
  nh3_conversion: M('NH3 conversion', '-'),
  h2_yield_overall: M('Overall H2 yield', '-'),
  h2_purity_mole_frac: M('H2 purity', 'mol/mol'),
  lhv_efficiency: M('LHV efficiency', '-'),
  h2_product_kg_h: M('H2 product', 'kg/h'),
  h2_product_kmol_h: M('H2 product', 'kmol/h'),
  h2_in_cracked_gas_kmol_h: M('H2 in cracked gas', 'kmol/h'),
  reactor_duty_kW: M('Cracker duty', 'kW'),
  preheat_duty_kW: M('Preheater duty', 'kW'),
  vaporiser_duty_kW: M('Vaporiser duty', 'kW'),
  recovered_heat_kW: M('Recovered heat (FEHE)', 'kW'),
  total_external_heating_kW: M('Total external heating', 'kW'),
  cooling_duty_kW: M('Cooling duty', 'kW'),
  pump_power_kW: M('Pump power', 'kW'),
  compression_power_kW: M('Compression power', 'kW'),
  tailgas_combustion_heat_kW: M('Tail-gas combustion heat', 'kW'),
  tailgas_lhv_kW: M('Tail-gas LHV', 'kW'),
  net_fuel_heat_deficit_kW: M('Net fuel heat deficit', 'kW'),
  specific_heat_demand_kWh_per_kgH2: M('Specific heat demand', 'kWh/kg H2'),
  y_NH3_cracked: M('NH3 in cracked gas', 'mol/mol'),
  cracked_gas_nh3_mole_frac: M('NH3 in cracked gas', 'mol/mol'),
  fehe_min_internal_dT_K: M('FEHE minimum internal approach', 'K'),
  nh3_feed_kg_per_kgH2: M('NH3 feed per kg H2', 'kg/kg'),
  nh3_total_kg_per_kgH2: M('Total NH3 per kg H2 (feed + fuel)', 'kg/kg'),
  // economics / environment
  lcoh_USD_per_kg: M('LCOH (preliminary)', 'USD/kg H2'),
  carbon_intensity_kgCO2e_per_kgH2: M('Carbon intensity (simplified)', 'kg CO2e/kg H2'),
  lcoh_USD_per_kg_ng_grey: M('LCOH, grey NH3 + natural-gas heat', 'USD/kg H2'),
  carbon_intensity_ng_grey: M('Carbon intensity, grey NH3 + natural-gas heat', 'kg CO2e/kg H2'),
  lcoh_USD_per_kg_nh3_green: M('LCOH, green NH3 + self-firing', 'USD/kg H2'),
  carbon_intensity_nh3_green: M('Carbon intensity, green NH3 + self-firing', 'kg CO2e/kg H2'),
  lcoh_USD_per_kg_ng_green: M('LCOH, green NH3 + natural-gas heat', 'USD/kg H2'),
  carbon_intensity_ng_green: M('Carbon intensity, green NH3 + natural-gas heat', 'kg CO2e/kg H2'),
  ci_electricity: M('Carbon intensity, electricity', 'kg CO2e/kg H2'),
  ci_external_heat: M('Carbon intensity, external heat', 'kg CO2e/kg H2'),
  lcoh_cooling_water_USD_per_kg: M('LCOH, cooling-water item', 'USD/kg H2'),
  mass_closure_rel: M('Mass closure residual', '-'),
  energy_closure_rel: M('Energy closure residual', '-'),
}

const SUFFIX: [RegExp, string][] = [
  [/_C$/, 'degC'], [/_bar$/, 'bar'], [/_K$/, 'K'], [/kmol_h$/, 'kmol/h'], [/kg_h$/, 'kg/h'], [/kWh_per_kgH2$/, 'kWh/kg H2'],
  [/_kW$/, 'kW'], [/time_s$/, 's'], [/USD_per_kg$/, 'USD/kg'],
]

function humanise(key: string): string {
  const base = key.replace(/(_kWh_per_kgH2|_kmol_h|_kg_h|_kW|_bar|_K|_C|_USD_per_kg|_s)$/, '').replace(/_/g, ' ').trim()
  return base ? base.charAt(0).toUpperCase() + base.slice(1) : key
}

export function metricInfo(key: string): MetricInfo {
  const hit = METRICS[key]
  if (hit) return hit
  const u = SUFFIX.find(([re]) => re.test(key))?.[1] ?? (/conversion|yield|efficiency|purity|frac|recovery|slip|closure|excess_air/.test(key) ? '-' : '')
  return { label: humanise(key), unit: u }
}

/** "Total external heating" */
export const metricName = (key: string): string => metricInfo(key).label
/** "Total external heating [kW]" (dimensionless quantities carry no unit suffix) */
export const metricLabel = (key: string): string => {
  const { label, unit } = metricInfo(key)
  return unit && unit !== '-' ? `${label} [${unit}]` : label
}
export const metricUnit = (key: string): string => metricInfo(key).unit


const KEYS_LONGEST_FIRST = Object.keys(METRICS).sort((a, b) => b.length - a.length)
/** Replace raw metric keys inside free text (e.g. "Pareto point 1 (lcoh_USD_per_kg vs h2_yield_overall)") by their readable names. */
export function humaniseKeys(text: string): string {
  let out = text
  for (const k of KEYS_LONGEST_FIRST) if (out.includes(k)) out = out.split(k).join(METRICS[k].label)
  return out
}
