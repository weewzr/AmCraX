"""Tests of the independent Python process model (amcrax.process_model)."""
from __future__ import annotations

import json
import math
import subprocess
import sys

import pytest

from amcrax.process_model import FlowsheetSpecError, compare_results, run_python_case
from amcrax.process_model import properties as pp
from amcrax.schemas import COMPONENTS, LHV_KJ_PER_MOL, MOLAR_MASS, CaseInputs, DataSource, SimulationResult
from amcrax.thermodynamics import reaction_enthalpy_kJ_mol, solve_equilibrium, species_enthalpy_kJ_mol

TOL = 1e-6


@pytest.fixture(scope="module")
def base():
    return run_python_case(CaseInputs())


@pytest.fixture(scope="module")
def base_no_hi():
    return run_python_case(CaseInputs(heat_integration=False))


def _closure(r: SimulationResult):
    b = r.balances
    assert abs(b.mass_closure_rel) < TOL
    assert b.n_atoms_in_kmol_h == pytest.approx(b.n_atoms_out_kmol_h, rel=1e-12)
    assert b.h_atoms_in_kmol_h == pytest.approx(b.h_atoms_out_kmol_h, rel=1e-12)
    assert abs(b.energy_closure_rel) < TOL


@pytest.mark.parametrize("hi", [True, False])
@pytest.mark.parametrize("eos", ["ideal", "pr"])
@pytest.mark.parametrize("T_C,P_bar", [(600, 20), (450, 5), (800, 40)])
def test_closures(hi, eos, T_C, P_bar):
    r = run_python_case(CaseInputs(reactor_temperature_C=T_C, reactor_pressure_bar=P_bar, heat_integration=hi), eos=eos)
    _closure(r)
    assert r.source == DataSource.PYTHON
    assert r.status.converged


def test_stream_set_and_pressures(base, base_no_hi):
    full = {"FEED", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "H2PROD", "TAILGAS", "AIR", "FLUE", "STACK"}
    assert set(base.streams) == full
    assert set(base_no_hi.streams) == full - {"S3", "S6"}
    assert "FEHE" not in base_no_hi.blocks
    P = 20.0
    exp = {"S1": P + 1.0, "S2": P + 0.8, "S3": P + 0.5, "S4": P + 0.2, "S5": P, "S6": P - 0.3, "S7": P - 0.5,
           "H2PROD": P - 1.0, "TAILGAS": 1.3, "AIR": 1.3, "FLUE": 1.2, "STACK": 1.1, "FEED": 1.013}
    for s, p in exp.items():
        assert base.streams[s].pressure_bar == pytest.approx(p)


def test_all_fields_filled_nonnegative(base):
    for s in base.streams.values():
        for f in ("phase", "temperature_C", "pressure_bar", "vapor_fraction", "mole_flow_kmol_h", "mass_flow_kg_h",
                  "enthalpy_flow_kW"):
            assert getattr(s, f) is not None, (s.id, f)
        assert set(s.component_mole_flow_kmol_h) == set(COMPONENTS)
        assert all(v >= 0 for v in s.component_mole_flow_kmol_h.values())
        assert sum(s.mole_frac.values()) == pytest.approx(1.0)
        assert sum(s.mass_frac.values()) == pytest.approx(1.0)
    for f, v in base.kpis.model_dump().items():
        assert v is not None, f


def test_conversion_equals_solve_equilibrium(base):
    for eos in ("ideal", "pr"):
        r = run_python_case(CaseInputs(), eos=eos)
        eq = solve_equilibrium(873.15, 20.0, {"NH3": 99.8, "H2O": 0.2}, eos=eos)
        assert r.kpis.nh3_conversion == pytest.approx(eq.conversion, rel=1e-12)
        for c in ("NH3", "H2", "N2"):
            assert r.streams["S5"].component_mole_flow_kmol_h[c] == pytest.approx(eq.n_out[c], rel=1e-12, abs=1e-14)


def test_cracker_duty_equals_extent_times_reaction_enthalpy(base):
    xi = base.blocks["CRACKER"].details["extent_kmol_h"]
    assert base.blocks["CRACKER"].duty_kW == pytest.approx(xi * reaction_enthalpy_kJ_mol(873.15) / 3.6, rel=1e-10)


def test_heat_integration_shifts_heater_duty_by_fehe_duty(base, base_no_hi):
    q_fehe = base.blocks["FEHE"].duty_kW
    assert q_fehe > 0
    assert base_no_hi.blocks["HEATER"].duty_kW - base.blocks["HEATER"].duty_kW == pytest.approx(q_fehe, rel=1e-9)
    assert base.blocks["COOLER"].duty_kW - base_no_hi.blocks["COOLER"].duty_kW == pytest.approx(q_fehe, rel=1e-9)
    assert base.kpis.recovered_heat_kW == pytest.approx(q_fehe)
    assert base_no_hi.kpis.recovered_heat_kW == 0.0


def test_fehe_approach_and_no_cross(base):
    s = base.streams
    assert s["S5"].temperature_C - s["S3"].temperature_C == pytest.approx(50.0)
    assert s["S6"].temperature_C > s["S2"].temperature_C
    assert base.blocks["FEHE"].details["min_internal_dT_K"] > 0


def _fehe_reference(r: SimulationResult, n: int = 401, cold: str = "nasa"):
    """Independent counter-current FEHE profile on a fine grid from the result's terminal states.

    cold="nasa": NASA-7 ideal gas + reference-EOS NH3 residual (the model's documented cold-side basis);
    cold="coolprop": full CoolProp reference EOS for NH3 (its own ideal-gas part). Hot side: NASA-7 + PR.
    Pressures vary linearly along the exchanger between the terminal pressures; Q from the cold side."""
    from scipy.optimize import brentq
    s = r.streams
    nf, n5 = s["S2"].component_mole_flow_kmol_h, s["S5"].component_mole_flow_kmol_h
    P2, P3, P5, P6 = (s[k].pressure_bar for k in ("S2", "S3", "S5", "S6"))
    T2, T3, T5 = (s[k].temperature_C + 273.15 for k in ("S2", "S3", "S5"))
    if cold == "nasa":
        hc = lambda T, P: pp.feed_gas_enthalpy_kW(nf, T, P)  # noqa: E731
    else:
        hc = lambda T, P: pp.feed_section_enthalpy_kW(nf, T, P, "gas")  # noqa: E731
    hh = lambda T, P: pp.gas_enthalpy_kW(n5, T, P, "pr")  # noqa: E731
    Hc2 = hc(T2, P2)
    Q = hc(T3, P3) - Hc2
    Hh6 = hh(T5, P5) - Q
    T6 = brentq(lambda T: hh(T, P6) - Hh6, 250.0, T5)
    dts = []
    for i in range(n):
        f = i / (n - 1)
        Pc, Ph = P2 + f * (P3 - P2), P6 + f * (P5 - P6)
        Tc = brentq(lambda T: hc(T, Pc) - (Hc2 + f * Q), T2 - 2.0, T3 + 2.0)
        Th = brentq(lambda T: hh(T, Ph) - (Hh6 + f * Q), T6 - 2.0, T5 + 2.0)
        dts.append(Th - Tc)
    return min(dts), Q, T6 - 273.15


# Reviewer cases: (inputs, expected limiting location). With the former mixed basis (ideal-gas S3, ideal hot side)
# 420 C / 80 bar / 10 K raised "-19.23 K cross" and 450 C / 60 bar / 5 K reported 0.48 K instead of 5.00 K.
FEHE_CASES = [dict(),
              dict(reactor_temperature_C=420, reactor_pressure_bar=80, fehe_hot_end_approach_K=10),
              dict(reactor_temperature_C=450, reactor_pressure_bar=60, fehe_hot_end_approach_K=5)]


@pytest.mark.parametrize("eos", ["ideal", "pr"])
@pytest.mark.parametrize("kw", FEHE_CASES)
def test_fehe_real_gas_basis_against_reference_profile(kw, eos):
    r = run_python_case(CaseInputs(**kw), eos=eos)      # must not raise: all three specifications are feasible
    fe = r.blocks["FEHE"]
    dT_ref, Q_ref, T6_ref = _fehe_reference(r)
    # same property basis, independent fine-grid evaluation. Tolerances: Q 0.2 kW (the S2 enthalpy is the
    # CoolProp-anchored value, which differs from NASA-7 + residual by the ideal-gas cp integral 298.15 K -> T2,
    # measured <= 0.09 kW); min dT 0.1 K and T6 0.1 K (the model blends that inlet offset linearly, 41 points).
    assert fe.duty_kW == pytest.approx(Q_ref, abs=0.2)
    assert fe.details["min_internal_dT_K"] == pytest.approx(dT_ref, abs=0.1)
    assert fe.details["hot_outlet_C"] == pytest.approx(T6_ref, abs=0.1)
    assert fe.details["min_internal_dT_K"] <= kw.get("fehe_hot_end_approach_K", 50.0) + 1e-9
    if kw.get("fehe_hot_end_approach_K") == 5:
        assert fe.details["min_internal_dT_K"] == pytest.approx(5.0, abs=1e-6)   # limited at the hot end
    # full CoolProp reference EOS on the cold side (incl. its ideal-gas part): also feasible; the difference is
    # the ideal-gas cp source (CoolProp's NH3 ideal-gas part is 0.04-0.06 kJ/mol below NIST-JANAF at 600-700 K,
    # NASA-7 within 0.012 kJ/mol), which lowers Q by 1.4-2.5 kW and raises T6 by ~1 K at these states.
    dT_cp, Q_cp, _ = _fehe_reference(r, cold="coolprop")
    assert dT_cp > 0
    assert abs(fe.details["min_internal_dT_K"] - dT_cp) < 1.5
    assert 0 < fe.duty_kW - Q_cp < 3.0


@pytest.mark.parametrize("kw", FEHE_CASES[1:] + [dict(reactor_temperature_C=500, reactor_pressure_bar=100,
                                                      fehe_hot_end_approach_K=10)])
def test_fehe_hot_side_interpolation_matches_exact_solve(kw):
    """The model inverts the hot-side PR enthalpy by PCHIP on an exact grid; redo the 41-point profile with an
    exact root solve at every point (the model's own algorithm otherwise) and compare the minimum."""
    from amcrax.process_model.flowsheet import FEHE_PROFILE_POINTS
    r = run_python_case(CaseInputs(**kw), eos="ideal")
    s = r.streams
    nf, n5 = s["S2"].component_mole_flow_kmol_h, s["S5"].component_mole_flow_kmol_h
    P, P3, P6 = s["S5"].pressure_bar, s["S3"].pressure_bar, s["S6"].pressure_bar
    T2, T3, TR = (s[k].temperature_C + 273.15 for k in ("S2", "S3", "S5"))
    T6 = s["S6"].temperature_C + 273.15
    H2, Q = s["S2"].enthalpy_flow_kW, r.blocks["FEHE"].duty_kW
    cold = lambda T: pp.feed_gas_enthalpy_kW(nf, T, P3)  # noqa: E731
    hot = lambda T: pp.gas_enthalpy_kW(n5, T, P6, "pr")  # noqa: E731
    H6r = pp.gas_enthalpy_kW(n5, TR, P, "pr") - Q
    dc = H2 - cold(T2)
    dmin = math.inf
    for i in range(FEHE_PROFILE_POINTS):
        f = i / (FEHE_PROFILE_POINTS - 1)
        Tc = T2 if i == 0 else (T3 if i == FEHE_PROFILE_POINTS - 1 else
                                pp.solve_T_for_enthalpy(lambda T: cold(T) + (1 - f) * dc, H2 + f * Q, T2 - 5, T3 + 5))
        Th = T6 if i == 0 else (TR if i == FEHE_PROFILE_POINTS - 1 else
                                pp.solve_T_for_enthalpy(hot, H6r + f * Q, T6 - 5, TR + 5))
        dmin = min(dmin, Th - Tc)
    assert r.blocks["FEHE"].details["min_internal_dT_K"] == pytest.approx(dmin, abs=1e-3)


def test_fehe_cold_side_nasa_closer_to_janaf_than_coolprop_ideal_part():
    # justification of the cold-side basis choice (NASA-7 ideal gas + reference-EOS residual)
    import json
    from pathlib import Path
    import amcrax.thermodynamics as th
    J = json.loads((Path(th.__file__).parent / "reference" / "janaf.json").read_text())
    c = J["columns"]
    rows = {r[c.index("T_K")]: r[c.index("H_minus_HTr_kJ_mol")] for r in J["species"]["NH3"]["rows"]}
    h0 = pp.CP.PropsSI("Hmolar", "T", 298.15, "P", 1.0, "Ammonia")
    for T in (500.0, 600.0, 700.0, 800.0, 900.0):
        d_nasa = species_enthalpy_kJ_mol("NH3", T) - species_enthalpy_kJ_mol("NH3", 298.15) - rows[T]
        d_cp = (pp.CP.PropsSI("Hmolar", "T", T, "P", 1.0, "Ammonia") - h0) / 1000 - rows[T]
        assert abs(d_nasa) < 0.015 and abs(d_nasa) < abs(d_cp)


def test_fehe_ideal_mode_bookkeeping_exact():
    # in eos="ideal" the stream table stays on the ideal-gas basis (closure exact), temperatures come from the
    # real-gas FEHE balance; the offsets are reported, and vanish in eos="pr" for the hot side
    ri, rp = run_python_case(CaseInputs(), eos="ideal"), run_python_case(CaseInputs(), eos="pr")
    for r in (ri, rp):
        s = r.streams
        assert s["S5"].enthalpy_flow_kW - s["S6"].enthalpy_flow_kW == pytest.approx(r.blocks["FEHE"].duty_kW, rel=1e-12)
        assert s["S3"].enthalpy_flow_kW - s["S2"].enthalpy_flow_kW == pytest.approx(r.blocks["FEHE"].duty_kW, rel=1e-12)
    assert rp.blocks["FEHE"].details["s6_enthalpy_minus_eos_basis_at_T6_kW"] == pytest.approx(0.0, abs=1e-9)
    assert abs(ri.blocks["FEHE"].details["s6_enthalpy_minus_eos_basis_at_T6_kW"]) < 2.0
    # the FEHE duty is the same in both modes (cold side on one real-gas basis); the HEATER carries the S4 basis
    assert ri.blocks["FEHE"].duty_kW == rp.blocks["FEHE"].duty_kW
    for r in (ri, rp):
        h = r.blocks["HEATER"]
        assert h.duty_kW == pytest.approx(r.streams["S4"].enthalpy_flow_kW - r.streams["S3"].enthalpy_flow_kW, rel=1e-12)
    assert abs(rp.blocks["HEATER"].details["s4_basis_minus_reference_real_gas_kW"]) < 1.0
    assert 0 < ri.blocks["HEATER"].details["s4_basis_minus_reference_real_gas_kW"] < 5.0


def test_kpis_use_shared_definition_low_flame_temperature():
    """Regression (A1): the Python engine used its own KPI block (comb = -Q_FLUEHX without max(., 0) and no +FLUEHX
    in external heating). With psa_h2_recovery = 1 at 900 C / 3 bar the flame (49 C) is below the stack (150 C)."""
    from amcrax.kpis import compute_balances, compute_kpis
    r = run_python_case(CaseInputs(reactor_temperature_C=900, reactor_pressure_bar=3, psa_h2_recovery=1.0))
    q = r.blocks["FLUEHX"].duty_kW
    assert r.blocks["BURNER"].outlet_temperature_C < r.inputs.stack_temperature_C and q > 0
    assert r.kpis == compute_kpis(r.streams, r.blocks)
    assert r.balances == compute_balances(r.streams, r.blocks)
    k, b = r.kpis, r.blocks
    assert k.tailgas_combustion_heat_kW == 0.0
    assert k.total_external_heating_kW == pytest.approx(b["VAPORIZR"].duty_kW + b["HEATER"].duty_kW
                                                        + b["CRACKER"].duty_kW + q, rel=1e-12)
    assert k.specific_heat_demand_kWh_per_kgH2 == pytest.approx(k.total_external_heating_kW / k.h2_product_kg_h)
    assert k.net_fuel_heat_deficit_kW == pytest.approx(k.total_external_heating_kW)
    assert r.blocks["FLUEHX"].details["flame_below_stack_temperature"] == "yes"
    assert r.status.has_warnings


def test_kpis_baseline_unchanged_by_shared_definition(base):
    """Regression (A1): for a normal case (flame above stack T) the shared amcrax.kpis definitions give exactly the
    values of the former Python-only KPI block (written out here)."""
    from amcrax.kpis import compute_kpis
    s, b = base.streams, base.blocks
    old_ext = b["VAPORIZR"].duty_kW + b["HEATER"].duty_kW + b["CRACKER"].duty_kW
    old_comb = -b["FLUEHX"].duty_kW
    h2 = s["H2PROD"].component_mole_flow_kmol_h["H2"]
    old = {"total_external_heating_kW": old_ext, "tailgas_combustion_heat_kW": old_comb,
           "net_fuel_heat_deficit_kW": old_ext - old_comb,
           "specific_heat_demand_kWh_per_kgH2": old_ext / (h2 * MOLAR_MASS["H2"]),
           "lhv_efficiency": h2 * LHV_KJ_PER_MOL["H2"] / 3.6 / (
               s["FEED"].component_mole_flow_kmol_h["NH3"] * LHV_KJ_PER_MOL["NH3"] / 3.6
               + max(old_ext - old_comb, 0.0) + b["PUMP"].power_kW),
           "nh3_conversion": b["CRACKER"].details["conversion"]}
    for key, v in old.items():
        assert getattr(base.kpis, key) == pytest.approx(v, rel=1e-14), key
    assert base.kpis == compute_kpis(s, b)


def test_fehe_infeasible_raises():
    with pytest.raises(FlowsheetSpecError):
        run_python_case(CaseInputs(reactor_temperature_C=350, fehe_hot_end_approach_K=300))


def test_low_pressure_rejected():
    with pytest.raises(FlowsheetSpecError):
        run_python_case(CaseInputs(reactor_pressure_bar=2.0))


def test_vaporiser_outlet_superheated(base):
    v = base.blocks["VAPORIZR"]
    assert v.outlet_temperature_C == pytest.approx(v.details["dew_point_C"] + 10.0)
    # pure-NH3 saturation at 20.8 bar is below the (water-containing) Raoult dew point
    assert pp.CP.PropsSI("T", "P", 20.8e5, "Q", 1, "Ammonia") - 273.15 < v.details["dew_point_C"]
    assert base.streams["FEED"].phase == "liquid" and base.streams["S2"].phase == "vapor"


def test_feed_is_saturated_liquid(base):
    # within 0.5 K of pure-NH3 normal boiling point (-33.3 degC)
    assert base.streams["FEED"].temperature_C == pytest.approx(-33.33, abs=0.5)


def test_coolprop_anchor_consistent_with_nasa():
    # low-pressure ammonia: anchored CoolProp (Gao 2020 EOS) vs NASA (GRI-Mech) ideal gas.
    # Feed-section range 250-400 K (where CoolProp is used): within 0.01 kJ/mol.
    for T in (250.0, 300.0, 350.0, 400.0):
        assert pp.nh3_enthalpy_kJ_mol(T, 1e-5, "gas") == pytest.approx(species_enthalpy_kJ_mol("NH3", T), abs=0.01)
    # up to 700 K (near the EOS limit, not used by the flowsheet): within 0.5 % of the sensible enthalpy
    # (measured 0.35 % at 700 K: the two ideal-gas cp sources differ slightly)
    h0 = species_enthalpy_kJ_mol("NH3", 298.15)
    for T in (500.0, 600.0, 700.0):
        d = pp.nh3_enthalpy_kJ_mol(T, 1e-5, "gas") - species_enthalpy_kJ_mol("NH3", T)
        assert abs(d) < 0.005 * (species_enthalpy_kJ_mol("NH3", T) - h0)
    # vaporisation enthalpy at the normal boiling point ~ 23.3 kJ/mol (CoolProp reference EOS)
    T = pp.bubble_point_K(1.01325, 1.0)
    dh = pp.nh3_enthalpy_kJ_mol(T + 1e-3, 1.01325, "gas") - pp.nh3_enthalpy_kJ_mol(T - 1e-3, 1.01325, "liquid")
    assert 22.5 < dh < 24.0


def test_pump_power_incompressible(base):
    v = pp.nh3_liquid_molar_volume_m3_mol(base.streams["FEED"].temperature_C + 273.15, 1.013)
    w = 100 * 1000 / 3600 * v * (21.0 - 1.013) * 1e5 / 1000 / 0.75
    assert base.kpis.pump_power_kW == pytest.approx(w, rel=1e-12)
    assert base.streams["S1"].enthalpy_flow_kW - base.streams["FEED"].enthalpy_flow_kW == pytest.approx(w, rel=1e-9)


def test_burner_adiabatic_and_air(base):
    t = base.streams["TAILGAS"].component_mole_flow_kmol_h
    air = base.streams["AIR"].mole_flow_kmol_h
    assert air == pytest.approx((0.5 * t["H2"] + 0.75 * t["NH3"]) * 1.15 / 0.21, rel=1e-12)
    f = base.streams["FLUE"]
    assert f.enthalpy_flow_kW == pytest.approx(base.streams["TAILGAS"].enthalpy_flow_kW + base.streams["AIR"].enthalpy_flow_kW)
    assert f.component_mole_flow_kmol_h["H2"] == 0 and f.component_mole_flow_kmol_h["NH3"] == 0
    assert f.component_mole_flow_kmol_h["O2"] == pytest.approx(0.15 * 0.21 * air / 1.15, rel=1e-9)
    assert 1000 < f.temperature_C < 2500


def test_kpi_definitions_consistent(base):
    k, s, b = base.kpis, base.streams, base.blocks
    assert k.h2_product_kmol_h == s["H2PROD"].component_mole_flow_kmol_h["H2"]
    assert k.h2_product_kg_h == pytest.approx(k.h2_product_kmol_h * MOLAR_MASS["H2"])
    assert k.h2_purity_mole_frac == pytest.approx(s["H2PROD"].mole_frac["H2"])
    nh3_in = s["FEED"].component_mole_flow_kmol_h["NH3"]
    assert k.nh3_conversion == pytest.approx(1 - s["S5"].component_mole_flow_kmol_h["NH3"] / nh3_in)
    assert k.h2_yield_overall == pytest.approx(k.h2_product_kmol_h / (1.5 * nh3_in))
    assert k.h2_product_kmol_h == pytest.approx(0.85 * s["S5"].component_mole_flow_kmol_h["H2"])
    assert k.total_external_heating_kW == pytest.approx(
        b["VAPORIZR"].duty_kW + b["HEATER"].duty_kW + b["CRACKER"].duty_kW)
    assert k.tailgas_combustion_heat_kW == pytest.approx(-b["FLUEHX"].duty_kW)
    assert k.net_fuel_heat_deficit_kW == pytest.approx(k.total_external_heating_kW - k.tailgas_combustion_heat_kW)
    assert k.cooling_duty_kW == pytest.approx(-b["COOLER"].duty_kW)
    lhv_h2 = k.h2_product_kmol_h * LHV_KJ_PER_MOL["H2"] / 3.6
    lhv_nh3 = nh3_in * LHV_KJ_PER_MOL["NH3"] / 3.6
    assert k.lhv_efficiency == pytest.approx(lhv_h2 / (lhv_nh3 + max(k.net_fuel_heat_deficit_kW, 0) + k.pump_power_kW))
    assert k.specific_heat_demand_kWh_per_kgH2 == pytest.approx(k.total_external_heating_kW / k.h2_product_kg_h)
    # combustion heat cannot exceed the tail-gas LHV plus sensible heat above stack T of inlets (sanity)
    assert 0 < k.tailgas_combustion_heat_kW < k.tailgas_lhv_kW
    assert 0 < k.lhv_efficiency < 1


def test_monotonic_trends():
    Ts = [450, 500, 550, 600, 700, 800]
    rs = [run_python_case(CaseInputs(reactor_temperature_C=T)) for T in Ts]
    conv = [r.kpis.nh3_conversion for r in rs]
    duty = [r.kpis.reactor_duty_kW for r in rs]
    assert all(a < b for a, b in zip(conv, conv[1:]))
    assert all(a < b for a, b in zip(duty, duty[1:]))
    Ps = [5, 10, 20, 40]
    conv_p = [run_python_case(CaseInputs(reactor_pressure_bar=P)).kpis.nh3_conversion for P in Ps]
    assert all(a > b for a, b in zip(conv_p, conv_p[1:]))
    recs = [0.7, 0.8, 0.9]
    rr = [run_python_case(CaseInputs(psa_h2_recovery=x)) for x in recs]
    h2 = [r.kpis.h2_product_kmol_h for r in rr]
    tg = [r.kpis.tailgas_lhv_kW for r in rr]
    assert all(a < b for a, b in zip(h2, h2[1:])) and all(a > b for a, b in zip(tg, tg[1:]))
    appr = [30, 50, 100]
    heater = [run_python_case(CaseInputs(fehe_hot_end_approach_K=a)).kpis.preheat_duty_kW for a in appr]
    assert all(a < b for a, b in zip(heater, heater[1:]))


def test_scale_invariance():
    a = run_python_case(CaseInputs())
    b = run_python_case(CaseInputs(feed_total_kmol_h=250.0))
    assert b.kpis.reactor_duty_kW == pytest.approx(2.5 * a.kpis.reactor_duty_kW, rel=1e-9)
    assert b.kpis.lhv_efficiency == pytest.approx(a.kpis.lhv_efficiency, rel=1e-9)


def test_json_roundtrip_and_compare(base, base_no_hi, tmp_path):
    rt = SimulationResult.model_validate_json(base.model_dump_json())
    rows = compare_results(base, rt)
    assert rows and all(r["abs_diff"] in (None, 0.0) for r in rows if r["a"] is not None and r["b"] is not None)
    rows2 = {r["quantity"]: r for r in compare_results(base, base_no_hi)}
    assert rows2["stream.S3.temperature_C"]["b"] is None
    r = rows2["block.HEATER.duty_kW"]
    assert r["abs_diff"] == pytest.approx(base.blocks["FEHE"].duty_kW, rel=1e-9)
    assert r["rel_diff"] == pytest.approx(r["abs_diff"] / abs(r["a"]))
    # CLI
    pa, pb, out = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "c.csv"
    pa.write_text(base.model_dump_json(), encoding="utf-8")
    pb.write_text(base_no_hi.model_dump_json(), encoding="utf-8")
    cp = subprocess.run([sys.executable, "-m", "amcrax.process_model.compare", str(pa), str(pb), "--csv", str(out)],
                        capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "quantity,a,b,abs_diff,rel_diff" and len(lines) == len(rows2) + 1
