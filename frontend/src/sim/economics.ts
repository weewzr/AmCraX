/**
 * Port of amcrax.economics.singapore.evaluate (basis 'pre-unification'; parameters from model.json.economics).
 * All USD (cost basis as model.economics.cost_basis); SGD = USD x model.fx.SGD_per_USD.
 * Not ported: the psa_recovery re-scaling override (the browser re-computes the process instead), capex_mode 'legacy',
 * IRR (NPV and payback are ported).
 */
import type { SimModel } from './types'

export interface EconSummary {
  h2_kg_h: number; nh3_feed_kmol_h: number; heat_deficit_kW: number; cooling_kW: number; pump_kW: number
}

export interface EconOverrides {
  nh3_price_USD_per_t?: number
  catalyst?: 'Ni' | 'Ru'
  catalyst_price_USD_per_kg?: number
  catalyst_mass_kg?: number
  heat_fuel?: 'ammonia' | 'natural_gas'
  apply_threshold?: boolean
  carbon_tax_SGD_per_t?: number
  capacity_scale?: number
  electricity_price_USD_per_kWh?: number
  discount_rate?: number
  plant_life_yr?: number
  catalyst_lifetime_yr?: number
  h2_price_USD_per_kg?: number
}

export type CostKey = 'capex' | 'fixed_opex' | 'ammonia_feed' | 'heat_fuel' | 'electricity' | 'cooling_water' | 'catalyst' | 'carbon_tax'

export interface EconResult {
  lcoh_USD_per_kg: number
  lcoh_SGD_per_kg: number
  rec_USD_per_kg: number
  breakdown_USD_per_kg: Record<CostKey, number>
  breakdown_SGD_per_kg: Record<CostKey, number>
  catalyst_mass_kg: number
  catalyst_price_USD_per_kg: number
  direct_emissions_tCO2e_per_yr: number
  carbon_tax_liable: boolean
  capex_total_USD: number
  npv_USD: number
  payback_yr: number | null
  annual_h2_kg: number
  h2_product_kg_h: number
  nh3_price_USD_per_t: number
  kg_nh3_fuel_per_kg_h2: number
  fx_SGD_per_USD: number
  notes: string[]
}

export function crf(i: number, n: number): number {
  return i === 0 ? 1 / n : (i * (1 + i) ** n) / ((1 + i) ** n - 1)
}

export function scenarioPrice(m: SimModel, scenario: string | number): number {
  if (typeof scenario === 'number') return scenario
  const v = m.economics.nh3_price_scenarios_USD_per_t[scenario]
  if (v === undefined) throw new RangeError(`unknown ammonia price scenario ${scenario}`)
  return v
}

export function evaluateEconomics(m: SimModel, s: EconSummary, scenario: string | number = 'grey', o: EconOverrides = {}): EconResult {
  const E = m.economics
  const a = E.economic_assumptions as Record<string, number | string | null>
  const sp = E.sg_params as Record<string, number | string | boolean | null>
  const num = (k: string, ov?: number) => (ov ?? (a[k] as number))
  const notes: string[] = []
  const price = o.nh3_price_USD_per_t ?? scenarioPrice(m, scenario)
  const sc = o.capacity_scale ?? (sp.capacity_scale as number)
  const hours = num('operating_hours_h_per_yr')
  let deficit = s.heat_deficit_kW * sc
  const h2 = s.h2_kg_h * sc, nh3 = s.nh3_feed_kmol_h * sc, cooling = Math.abs(s.cooling_kW) * sc, pump = s.pump_kW * sc
  if (deficit < 0) { notes.push(`Heat surplus ${(-deficit).toFixed(1)} kW not credited.`); deficit = 0 }
  const annualH2 = h2 * hours
  const nh3USDkg = price / 1000
  const effF = (sp.fuel_efficiency as number | null) ?? num('ammonia_fuel_heat_efficiency')
  const MM = m.thermo.molar_mass_g_mol, LHV = m.thermo.lhv_kJ_per_mol
  const feedKg = nh3 * MM.NH3
  const fx = m.fx.SGD_per_USD
  const heatFuel = o.heat_fuel ?? (sp.heat_fuel as string)
  let co2 = 0, heatUSD = 0, fuelKg = 0
  if (heatFuel === 'ammonia') {
    fuelKg = (deficit / (LHV.NH3 * effF)) * 3600 * MM.NH3 / 1000
    heatUSD = fuelKg * nh3USDkg * hours
  } else if (heatFuel === 'natural_gas') {
    const pr = (sp.gas_heat_price_USD_per_kJ as number | null) ?? num('fired_heat_price_USD_per_kJ')
    const gj = (deficit / effF) * 3600 / 1e6 * hours
    heatUSD = gj * 1e6 * pr
    co2 = gj * E.natural_gas_co2_factor_kg_per_GJ / 1000
  } else throw new RangeError('heat_fuel must be ammonia or natural_gas')
  const direct = co2 + (sp.n2o_tCO2e_per_yr as number)
  const thr = E.carbon_tax.threshold_tCO2e_per_yr
  const applyThr = o.apply_threshold ?? (sp.apply_threshold as boolean)
  const liable = !applyThr || direct + (sp.other_facility_emissions_tCO2e as number) >= thr
  const taxRate = o.carbon_tax_SGD_per_t ?? (sp.carbon_tax_SGD_per_t as number)
  const taxUSD = liable ? (direct * taxRate) / fx : 0
  if (direct === 0) notes.push('Direct CO2e = 0 (ammonia-fuelled heat, no carbon in the feed); N2O not quantified; carbon tax 0.')
  else if (!liable) notes.push(`Direct emissions ${direct.toFixed(0)} tCO2e/yr below the ${thr} t threshold: no tax liability.`)
  const elecUSD = pump * (o.electricity_price_USD_per_kWh ?? (sp.electricity_price_USD_per_kWh as number)) * hours
  const coolUSD = cooling * 3600 * num('cooling_water_price_USD_per_kJ') * hours
  let mcat = (nh3 * 1000 * num('normal_molar_volume_L_per_mol') * 1000) / num('catalyst_space_velocity_mL_NH3_per_gcat_h') / 1000
  const mOv = o.catalyst_mass_kg ?? (a.catalyst_mass_kg as number | null)
  if (mOv !== null && mOv !== undefined) mcat = mOv * sc
  const cat = o.catalyst ?? (a.catalyst as 'Ni' | 'Ru')
  const catPrice = o.catalyst_price_USD_per_kg ?? (a.catalyst_price_USD_per_kg as number | null) ?? E.catalyst_price_USD_per_kg[cat]
  const catLife = num('catalyst_lifetime_yr', o.catalyst_lifetime_yr)
  const catUSD = (mcat * catPrice) / catLife
  // equipment capex
  const c = E.capex_equipment
  const shares = c.equipment_shares_pct
  const ssum = Object.values(shares).reduce((x, y) => x + y, 0)
  const ratio = nh3 / c.reference_feed_kmol_h
  const n = (sp.capex_scaling_exponent as number | null) ?? c.scaling_exponent
  let pecTot = 0
  for (const v of Object.values(shares)) pecTot += ((c.pec_reference_kUSD * 1e3 * v) / ssum) * ratio ** n * c.singapore_location_factor
  const capex = pecTot * c.tci_over_pec * num('capex_multiplier')
  const i = num('discount_rate', o.discount_rate), life = num('plant_life_yr', o.plant_life_yr)
  const f = crf(i, life)
  const maint = num('maintenance_frac_capex_per_yr') * capex
  const ins = num('insurance_frac_capex_per_yr') * capex
  const lab = num('labour_USD_per_yr') * ((sp.labour_scales_with_capacity as boolean) ? sc : 1)
  const over = num('plant_overhead_frac_labour_maint') * (lab + maint)
  const fixed = (maint + ins + lab + over) * (1 + num('g_and_a_frac_fixed_opex'))
  const annual: Record<CostKey, number> = { capex: capex * f, fixed_opex: fixed, ammonia_feed: feedKg * nh3USDkg * hours, heat_fuel: heatUSD,
    electricity: elecUSD, cooling_water: coolUSD, catalyst: catUSD, carbon_tax: taxUSD }
  const br = {} as Record<CostKey, number>, brS = {} as Record<CostKey, number>
  let lcoh = 0
  for (const k of Object.keys(annual) as CostKey[]) { br[k] = annual[k] / annualH2; brS[k] = br[k] * fx; lcoh += br[k] }
  const opex = Object.entries(annual).filter(([k]) => k !== 'capex').reduce((x, [, v]) => x + v, 0)
  const h2price = o.h2_price_USD_per_kg ?? (sp.h2_price_USD_per_kg as number)
  const net = h2price * annualH2 - opex
  const nn = Math.round(life)
  const npv = i > 0 ? -capex + (net * (1 - (1 + i) ** -nn)) / i : -capex + net * nn
  notes.push('Ammonia price is a scenario (delivered, international basis), not a Singapore transaction price.')
  return {
    lcoh_USD_per_kg: lcoh, lcoh_SGD_per_kg: lcoh * fx, rec_USD_per_kg: lcoh - br.ammonia_feed, breakdown_USD_per_kg: br,
    breakdown_SGD_per_kg: brS, catalyst_mass_kg: mcat, catalyst_price_USD_per_kg: catPrice, direct_emissions_tCO2e_per_yr: direct,
    carbon_tax_liable: liable, capex_total_USD: capex, npv_USD: npv, payback_yr: net > 0 ? capex / net : null, annual_h2_kg: annualH2,
    h2_product_kg_h: h2, nh3_price_USD_per_t: price, kg_nh3_fuel_per_kg_h2: fuelKg / h2, fx_SGD_per_USD: fx, notes,
  }
}

/** Economic metal of a rate law (model.economics.catalyst_metal_map; Ni-Ru priced as Ru = assumption). */
export function economicMetal(m: SimModel, metal: string): 'Ni' | 'Ru' {
  return (m.economics.catalyst_metal_map[metal] ?? 'Ru') as 'Ni' | 'Ru'
}
