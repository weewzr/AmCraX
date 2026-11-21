"""Tests for amcrax.reactor (packed-bed PFR)."""
import math

import numpy as np
import pytest

from amcrax.reactor import catalyst_mass_for_conversion, simulate_pfr
from amcrax.thermodynamics import reaction_enthalpy_kJ_mol, solve_equilibrium, species_cp_J_molK

CATS = ["ni_takahashi_microkinetic", "ru_takahashi_microkinetic", "ru_kum_temkin_pyzhev"]
FEED = {"NH3": 99.8, "H2O": 0.2}


@pytest.mark.parametrize("cid", CATS)
def test_conversion_bounded_and_approaches_equilibrium(cid):
    r = simulate_pfr(cid, 2000.0, T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED, pressure_drop=False)
    Xe = solve_equilibrium(873.15, 20.0, FEED).conversion
    X = np.array(r.conversion)
    assert np.all(X <= Xe + 1e-7)
    # monotone to within the integrator tolerance (rtol 1e-8): ~1e-10 jitter occurs once X sits at X_eq
    assert np.all(np.diff(X) >= -1e-8)
    assert X[-1] == pytest.approx(Xe, abs=2e-4)
    assert r.source == "python_model"


@pytest.mark.parametrize("cid", CATS)
def test_element_balance_along_bed(cid):
    r = simulate_pfr(cid, 30.0, T_in_C=550.0, P_in_bar=20.0, feed_kmol_h=FEED, n_tubes=20, mode="adiabatic")
    F0 = sum(FEED.values())
    N_in, H_in = FEED["NH3"], 3 * FEED["NH3"] + 2 * FEED["H2O"]
    for i in range(len(r.W_kg)):
        Ft = F0 * (1 + r.conversion[i] * FEED["NH3"] / F0)  # 1 mol NH3 -> 2 mol products
        y = {s: r.y[s][i] for s in r.y}
        N = Ft * (y["NH3"] + 2 * y["N2"])
        H = Ft * (3 * y["NH3"] + 2 * y["H2"] + 2 * y["H2O"])
        assert N == pytest.approx(N_in, rel=1e-10)
        assert H == pytest.approx(H_in, rel=1e-10)
        assert sum(y.values()) == pytest.approx(1.0, abs=1e-12)


def test_adiabatic_temperature_drop_consistent_with_enthalpy():
    feed = {"NH3": 99.8, "H2O": 0.2}
    r = simulate_pfr("ru_kum_temkin_pyzhev", 50.0, T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=feed, mode="adiabatic",
                     n_tubes=20)
    # first-law closure: adiabatic -> outlet enthalpy flow equals inlet enthalpy flow
    assert abs(r.outlet["heat_input_kW"]) < 1e-3 * 46.0 * 99.8 / 3.6
    T_out = r.T_K[-1]
    assert T_out < 873.15
    # simple estimate dT ~ X dH F_NH3 / (F cp) within 10 %
    X = r.conversion[-1]
    Tm = 0.5 * (873.15 + T_out)
    Fcp = sum(v * species_cp_J_molK(s, Tm) for s, v in r.outlet["flows_kmol_h"].items() if v > 0)
    Fcp_in = sum(v * species_cp_J_molK(s, Tm) for s, v in feed.items())
    dT_est = X * 99.8 * reaction_enthalpy_kJ_mol(Tm) * 1000 / (0.5 * (Fcp + Fcp_in))
    assert 873.15 - T_out == pytest.approx(dT_est, rel=0.10)


def test_isothermal_duty_matches_reaction_enthalpy():
    r = simulate_pfr("ru_kum_temkin_pyzhev", 100.0, T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED, pressure_drop=False)
    Q_expected = r.conversion[-1] * 99.8 / 3.6 * reaction_enthalpy_kJ_mol(873.15)  # kmol/h -> mol/s * kJ/mol = kW
    assert r.outlet["heat_input_kW"] == pytest.approx(Q_expected, rel=1e-6)
    assert all(t == pytest.approx(873.15) for t in r.T_K)


def test_external_heating_bounds():
    kw = dict(T_in_C=550.0, P_in_bar=20.0, feed_kmol_h=FEED, n_tubes=20)
    ad = simulate_pfr("ru_kum_temkin_pyzhev", 100.0, mode="adiabatic", **kw)
    ex = simulate_pfr("ru_kum_temkin_pyzhev", 100.0, mode="external", T_wall_C=700.0, U_W_m2K=100.0, **kw)
    assert ex.conversion[-1] > ad.conversion[-1]
    assert max(ex.T_K) < 700.0 + 273.15
    with pytest.raises(ValueError):
        simulate_pfr("ru_kum_temkin_pyzhev", 1.0, mode="external", **kw)


def test_pressure_drop_ergun_scaling():
    kw = dict(T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED)
    a = simulate_pfr("ru_kum_temkin_pyzhev", 20.0, n_tubes=40, **kw).outlet["pressure_drop_bar"]
    b = simulate_pfr("ru_kum_temkin_pyzhev", 20.0, n_tubes=80, **kw).outlet["pressure_drop_bar"]
    assert a > 0 and b > 0
    # same W, doubled area: bed length halves, superficial mass flux halves -> dP falls 4-8x
    assert 3.5 < a / b < 8.5
    nodp = simulate_pfr("ru_kum_temkin_pyzhev", 20.0, n_tubes=40, pressure_drop=False, **kw)
    assert nodp.outlet["pressure_drop_bar"] == 0.0


def test_catalyst_mass_root_finding():
    kw = dict(T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED, n_tubes=40)
    w = catalyst_mass_for_conversion("ru_kum_temkin_pyzhev", fraction_of_equilibrium=0.95, **kw)
    Xe = solve_equilibrium(873.15, 20.0, FEED).conversion
    X = simulate_pfr("ru_kum_temkin_pyzhev", w, n_points=2, **kw).outlet["conversion"]
    assert X == pytest.approx(0.95 * Xe, abs=1e-4)
    w99 = catalyst_mass_for_conversion("ru_kum_temkin_pyzhev", fraction_of_equilibrium=0.99, **kw)
    assert w99 > w
    assert math.isnan(catalyst_mass_for_conversion("ru_kum_temkin_pyzhev", target_conversion=0.9999, W_max_kg=1e4, **kw))


HYD = dict(n_tubes=50, P_in_bar=1.01325, T_in_C=500.0)   # 1 atm, 50 tubes: Ergun stop at ~47 kg (< 100 kg)


def test_hydraulic_stop_outlet_is_event_state_independent_of_grid():
    # regression: the outlet used to be the last t_eval point before the terminal low-pressure event
    # (n_points=3 -> W = 0, X = 0, P = P_in)
    coarse = simulate_pfr("ni_takahashi_microkinetic", 100.0, n_points=3, **HYD)
    fine = simulate_pfr("ni_takahashi_microkinetic", 100.0, n_points=2001, **HYD)
    for r in (coarse, fine):
        o = r.outlet
        assert o["hydraulic_limit"] is True
        assert o["W_requested_kg"] == 100.0
        assert 0.0 < o["W_reached_kg"] < 100.0
        assert o["P_bar"] == pytest.approx(0.05 * HYD["P_in_bar"], rel=1e-6)
        assert o["conversion"] > 0.2
        assert r.W_kg[-1] == o["W_reached_kg"] and r.conversion[-1] == o["conversion"]
        assert len(r.W_kg) == len(r.rate_mol_per_kgcat_s) == len(r.y["NH3"])
        assert any("hydraulic limit" in a for a in r.assumptions)
    assert coarse.outlet["W_reached_kg"] == pytest.approx(fine.outlet["W_reached_kg"], rel=1e-6)
    assert coarse.outlet["conversion"] == pytest.approx(fine.outlet["conversion"], rel=1e-6)
    # no stop -> flag False and the outlet is at the requested mass
    ok = simulate_pfr("ni_takahashi_microkinetic", 10.0, n_points=2, **HYD).outlet
    assert ok["hydraulic_limit"] is False and ok["W_reached_kg"] == pytest.approx(10.0)


def test_catalyst_mass_with_trial_masses_beyond_hydraulic_stop():
    # regression: trial masses past the stop read X = 0, the bracket never closed and nan was returned
    w = catalyst_mass_for_conversion("ni_takahashi_microkinetic", 0.15, **HYD)
    assert math.isfinite(w)
    o = simulate_pfr("ni_takahashi_microkinetic", w, n_points=2, **HYD).outlet
    assert o["hydraulic_limit"] is False
    assert o["conversion"] == pytest.approx(0.15, abs=1e-5)
    # a target above the conversion at the stop is unreachable: nan with an explicit reason
    d = catalyst_mass_for_conversion("ni_takahashi_microkinetic", 0.30, return_details=True, **HYD)
    assert math.isnan(d["W_kg"]) and d["reachable"] is False and d["hydraulic_limit"] is True
    assert "hydraulic limit" in d["reason"] and d["X_reached"] < 0.30
    with pytest.warns(RuntimeWarning, match="hydraulic limit"):
        assert math.isnan(catalyst_mass_for_conversion("ni_takahashi_microkinetic", 0.30, **HYD))


def test_catalyst_mass_last_trial_clamped_to_W_max():
    # regression: geometric growth (1e-3 * 4^k) stopped at 4.096 kg < W_max_kg = 5 kg
    kw = dict(T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED, n_tubes=40, pressure_drop=False)
    X45 = simulate_pfr("ru_kum_temkin_pyzhev", 4.5, n_points=2, **kw).outlet["conversion"]
    X4096 = simulate_pfr("ru_kum_temkin_pyzhev", 4.096, n_points=2, **kw).outlet["conversion"]
    assert X45 > X4096
    w = catalyst_mass_for_conversion("ru_kum_temkin_pyzhev", X45, W_max_kg=5.0, **kw)
    assert w == pytest.approx(4.5, rel=1e-4)
    d = catalyst_mass_for_conversion("ru_kum_temkin_pyzhev", 0.9999, W_max_kg=5.0, return_details=True, **kw)
    assert math.isnan(d["W_kg"]) and "W_max_kg" in d["reason"]


def test_h2_seed_insensitivity():
    kw = dict(T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED, pressure_drop=False, n_points=2)
    a = simulate_pfr("ru_kum_temkin_pyzhev", 5.0, x_seed=1e-6, **kw).outlet["conversion"]
    b = simulate_pfr("ru_kum_temkin_pyzhev", 5.0, x_seed=1e-8, **kw).outlet["conversion"]
    assert a == pytest.approx(b, abs=1e-5)


def test_space_velocity_and_residence_time():
    r = simulate_pfr("ru_kum_temkin_pyzhev", 10.0, T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=FEED, pressure_drop=False)
    rho_bed = (1 - 0.36) * 980.0
    V = 10.0 / rho_bed
    Qn = 100.0 / 3.6 * 8.314462618 * 273.15 / 101325.0 * 3600.0
    assert r.GHSV_h_inv == pytest.approx(Qn / V, rel=1e-4)
    assert r.W_over_F_kg_s_per_mol_NH3 == pytest.approx(10.0 / (99.8 / 3.6))
    assert r.residence_time_s[-1] > 0
