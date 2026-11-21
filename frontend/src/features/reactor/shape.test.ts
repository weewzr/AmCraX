import { describe, expect, it } from 'vitest'
import type { GridPoint } from '../../api/reactor'
import { aspenMethodFor, enthalpyRows, extractProfile, lookupEnthalpy, mergeEquilibriumRows, normaliseCatalysts } from './shape'

const pt = (T_C: number, P_bar: number, conversion: number): GridPoint => ({
  T_C, P_bar, conversion,
  result: { T_K: T_C + 273.15, P_bar, eos: 'ideal', conversion, extent: conversion, n_out: {}, y: { NH3: 0.1, H2: 0.7, N2: 0.2 }, K_eq: 1, phi: {}, residual: 0 },
})

describe('equilibrium shaping', () => {
  it('maps the EOS toggle to the Aspen property method', () => {
    expect(aspenMethodFor('ideal')).toBe('IDEAL')
    expect(aspenMethodFor('pr')).toBe('PENG-ROB')
  })
  it('merges python lines and matching aspen markers by temperature, in percent', () => {
    const aspen = [
      { T_C: 300, P_bar: 1, property_method: 'IDEAL', nh3_conversion: '0.95' },
      { T_C: 300, P_bar: 1, property_method: 'PENG-ROB', nh3_conversion: 0.5 },
      { T_C: 350, P_bar: 5, property_method: 'IDEAL', nh3_conversion: 0.9 },
    ]
    const rows = mergeEquilibriumRows([pt(350, 1, 0.98), pt(300, 1, 0.96)], aspen, [1], 'conversion', 'IDEAL')
    expect(rows.map((r) => r.T_C)).toEqual([300, 350])
    expect(rows[0].py_1).toBeCloseTo(96)
    expect(rows[0].as_1).toBeCloseTo(95)
    expect(rows[1].as_1).toBeUndefined() // the 5 bar Aspen row is not selected; PENG-ROB row filtered out
  })
  it('builds enthalpy rows and exact lookups only on tabulated points', () => {
    const py = [{ T_C: 600, P_bar: 20, eos: 'ideal', dH_rxn_kJ_per_mol_NH3: 54.2, heat_duty_kJ_per_mol_NH3_fed: 50 }]
    expect(enthalpyRows(py, [], 20, 'ideal', 'IDEAL')[0].py_dH).toBe(54.2)
    expect(enthalpyRows(py, [], 5, 'ideal', 'IDEAL')).toEqual([])
    expect(lookupEnthalpy(py, 600, 20, 'ideal')).toBe(54.2)
    expect(lookupEnthalpy(py, 601, 20, 'ideal')).toBeNull()
  })
})

describe('kinetics payload shaping', () => {
  it('normalises catalyst lists and keyed objects, stringifying nested parameters', () => {
    const a = normaliseCatalysts({ catalysts: [{ id: 'ru', name: 'Ru/Al2O3', rate_law: 'Temkin', parameters: { A: 1 }, citation: 'X (2020)' }] })
    expect(a[0]).toMatchObject({ id: 'ru', catalyst: 'Ru/Al2O3', source: 'X (2020)' })
    expect(a[0].parameters).toBe('A: 1')
    expect(normaliseCatalysts([{ id: 'z', parameters: { A1: { value: 75.5, unit: 'x' } }, limitations: ['l1', 'l2'], source: { citekey: 'k', page: 4 } }])[0])
      .toMatchObject({ parameters: 'A1: 75.5 x', limitations: 'l1\nl2', source: 'citekey: k\npage: 4' })
    const b = normaliseCatalysts({ catalysts: { ni: { name: 'Ni' } } })
    expect(b[0].id).toBe('ni')
    expect(normaliseCatalysts(null)).toEqual([])
  })
  it('finds an axial profile as columns or rows, and returns null when none exists', () => {
    const cols = extractProfile({ profile: { catalyst_mass_kg: [0, 1, 2], conversion: [0, 0.2, 0.4], equilibrium_conversion: [0.9, 0.9, 0.9], T_C: [500, 500, 500] } })
    expect(cols?.xKey).toBe('catalyst_mass_kg')
    expect(cols?.conv).toBe('conversion')
    expect(cols?.eq).toBe('equilibrium_conversion')
    expect(cols?.temp).toBe('T_C')
    const rows = extractProfile([{ z: 0, X_NH3: 0 }, { z: 1, X_NH3: 0.3 }])
    expect(rows?.conv).toBe('X_NH3')
    expect(extractProfile({ message: 'nothing here' })).toBeNull()
  })
})
