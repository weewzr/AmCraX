/**
 * Carbon intensity and carbon cost.
 *  - carbonIntensity: port of amcrax.environmental.carbon_intensity (simplified carbon-intensity accounting, NOT an LCA;
 *    factors from model.carbon.accounting = backend/amcrax/data/environmental.yaml).
 *  - carbonCost 'actual': the Singapore carbon tax as amcrax.economics.singapore.evaluate applies it (direct Scope-1
 *    CO2e of the facility only, only above the facility threshold) = breakdown.carbon_tax of the economics result.
 *  - carbonCost 'hypothetical' (NOT Singapore law): user price [SGD/tCO2e] x carbon intensity [kg CO2e/kg H2] / 1000.
 *    It REPLACES the actual tax term (every life-cycle emission, including any direct emission that the actual tax
 *    already covers, is charged exactly once).
 */
import type { EconResult } from './economics'
import type { SimModel } from './types'

export type Route = 'grey' | 'blue' | 'green' | string
export type Heating = 'natural_gas' | 'self_firing' | 'electric'

export interface CIInputs { h2_kg_h: number; nh3_feed_kg_h: number; heat_deficit_kW: number; pump_kW: number }

export interface CIResult {
  total_kgCO2e_per_kgH2: number
  breakdown_kgCO2e_per_kgH2: { upstream_ammonia: number; transport: number; electricity: number; external_heat: number }
  nh3_fuel_kg_h: number
  route: string
  heating: Heating
  statement: string
}

export function carbonIntensity(m: SimModel, x: CIInputs, route: Route = 'grey', heating: Heating = 'self_firing',
  opt: { grid?: string; distance_km?: number; nh3_ef_kg_per_kg?: number } = {}): CIResult {
  const f = m.carbon.accounting
  const efNH3 = opt.nh3_ef_kg_per_kg ?? f.upstream_ammonia[route]
  if (efNH3 === undefined) throw new RangeError(`unknown ammonia route ${route}`)
  const efGrid = f.electricity[opt.grid ?? 'singapore_2024']
  const dist = opt.distance_km ?? f.distance_km
  const deficit = Math.max(0, x.heat_deficit_kW)
  const fuelKW = deficit / f.fired_heater_efficiency_lhv
  const MM = m.thermo.molar_mass_g_mol, LHV = m.thermo.lhv_kJ_per_mol
  const lhvKg = (LHV.NH3 / MM.NH3) * 1000
  const ship = (f.ship_ef_kg_per_tkm * dist) / 1000
  let elec = x.pump_kW, heat = 0, fuelKg = 0
  if (heating === 'natural_gas') {
    heat = ((fuelKW * 3600) / 1e6 / 1000) * f.natural_gas_kg_per_TJ
  } else if (heating === 'self_firing') {
    fuelKg = (fuelKW * 3600) / lhvKg
    heat = fuelKg * (efNH3 + ship)
  } else {
    elec += deficit / f.electric_heater_efficiency
  }
  const br = { upstream_ammonia: (x.nh3_feed_kg_h * efNH3) / x.h2_kg_h, transport: (x.nh3_feed_kg_h * ship) / x.h2_kg_h,
    electricity: (elec * efGrid) / x.h2_kg_h, external_heat: heat / x.h2_kg_h }
  return { total_kgCO2e_per_kgH2: br.upstream_ammonia + br.transport + br.electricity + br.external_heat, breakdown_kgCO2e_per_kgH2: br,
    nh3_fuel_kg_h: fuelKg, route, heating, statement: 'simplified carbon-intensity accounting, not a life-cycle assessment' }
}

export interface CarbonCost {
  mode: 'actual' | 'hypothetical'
  USD_per_kg_H2: number
  SGD_per_kg_H2: number
  /** LCOH with this carbon treatment (actual: unchanged; hypothetical: actual tax term replaced) */
  lcoh_USD_per_kg: number
  lcoh_SGD_per_kg: number
  label: string
}

export function carbonCost(m: SimModel, econ: EconResult, ci: CIResult, mode: 'actual' | 'hypothetical', price_SGD_per_t = 0): CarbonCost {
  const fx = m.fx.SGD_per_USD
  if (mode === 'actual') {
    const c = econ.breakdown_USD_per_kg.carbon_tax
    return { mode, USD_per_kg_H2: c, SGD_per_kg_H2: c * fx, lcoh_USD_per_kg: econ.lcoh_USD_per_kg, lcoh_SGD_per_kg: econ.lcoh_SGD_per_kg,
      label: 'Singapore carbon tax, actual boundary (direct facility emissions above the threshold only)' }
  }
  const sgd = (price_SGD_per_t * ci.total_kgCO2e_per_kgH2) / 1000
  const usd = sgd / fx
  const lcoh = econ.lcoh_USD_per_kg - econ.breakdown_USD_per_kg.carbon_tax + usd
  return { mode, USD_per_kg_H2: usd, SGD_per_kg_H2: sgd, lcoh_USD_per_kg: lcoh, lcoh_SGD_per_kg: lcoh * fx,
    label: 'HYPOTHETICAL life-cycle carbon price (not Singapore law); replaces the actual tax term, no double counting' }
}

/**
 * HYPOTHETICAL life-cycle carbon price (SGD per tCO2e, not Singapore law) at which case A (lower carbon intensity, higher cost)
 * reaches the cost of case B: lcoh_a + p ci_a / (1000 fx) = lcoh_b + p ci_b / (1000 fx). Port of
 * amcrax.economics.carbon_pricing.crossover_price: 0 when A is already not dearer, null when A never overtakes (ci_b <= ci_a).
 */
export function crossoverPrice(lcoh_a_USD: number, ci_a: number, lcoh_b_USD: number, ci_b: number, fx: number): number | null {
  if (lcoh_a_USD <= lcoh_b_USD) return 0
  if (ci_b <= ci_a) return null
  return ((lcoh_a_USD - lcoh_b_USD) * fx * 1000) / (ci_b - ci_a)
}
