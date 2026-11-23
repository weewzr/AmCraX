"""Workstream K: research kinetics additions (Lucentini et al. 2021 LHHW) - fast tests."""
from __future__ import annotations

import math

import pytest

from amcrax.kinetics import (get_catalyst, list_catalysts, list_research_catalysts, lucentini_rate_mol_per_g_s,
                             rate_mol_per_kgcat_s)
from amcrax.reactor.pfr import simulate_pfr
from amcrax.thermodynamics import equilibrium_constant

LUC = ("nire_ceo2_5ni1ru_lucentini_lhhw", "nire_ceo2_2p5ni0p5ru_lucentini_lhhw")
R = 8.314


def test_original_registry_unchanged():
    assert [c.id for c in list_catalysts()] == ["ni_takahashi_microkinetic", "ru_takahashi_microkinetic", "ru_kum_temkin_pyzhev"]
    assert {c.id for c in list_research_catalysts()} == set(LUC)


@pytest.mark.parametrize("cid,T,af,expected", [
    # values of the unchanged laws at p = {NH3 10, H2 6, N2 2, H2O 0.1} bar; identical to the pre-change code (checked)
    ("ni_takahashi_microkinetic", 873.15, None, 0.8353319096062062),
    ("ru_takahashi_microkinetic", 873.15, None, 2.7890322238245613),
    ("ru_kum_temkin_pyzhev", 873.15, None, 6.5841517654264505),
    ("ni_takahashi_microkinetic", 773.15, False, 0.07374817905941868),
    ("ru_kum_temkin_pyzhev", 773.15, False, 0.8602506288972365),
])
def test_existing_rates_numerically_unchanged(cid, T, af, expected):
    p = {"NH3": 10.0, "H2": 6.0, "N2": 2.0, "H2O": 0.1}
    assert rate_mol_per_kgcat_s(cid, T, p, approach_factor=af) == pytest.approx(expected, rel=1e-12)


def test_lucentini_parameters_and_hand_calculation():
    c = get_catalyst(LUC[0])
    par = {k: v["value"] for k, v in c.parameters.items()}
    assert par == {"k0": 3.9e6, "Ek": 124.0, "K1": 1.1, "K4": 4.7e-2}
    assert c.source["citekey"] == "lucentini2021nirukinetic"
    T, p = 723.15, {"NH3": 0.4, "H2": 0.3, "N2": 0.1, "Ar": 0.21325}
    cn, ch = 0.4e5 / (R * T), 0.3e5 / (R * T)
    k = 3.9e6 * math.exp(-124e3 / (R * T))
    hand = k * 1.1 * cn / (1 + 1.1 * cn + math.sqrt(ch / 4.7e-2)) ** 2
    assert lucentini_rate_mol_per_g_s(LUC[0], T, p) == pytest.approx(hand, rel=1e-12)
    assert rate_mol_per_kgcat_s(LUC[0], T, p, approach_factor=False) == pytest.approx(1000 * hand, rel=1e-12)


@pytest.mark.parametrize("cid", LUC)
def test_lucentini_rate_vanishes_at_equilibrium(cid):
    T, P = 673.15, 20.0
    K = equilibrium_constant(T)
    # build a composition with Q = K: choose y_H2, y_N2 and solve y_NH3
    yh, yn2 = 0.6, 0.2
    ynh3 = yn2 ** 0.5 * yh ** 1.5 * P / K
    assert ynh3 + yh + yn2 < 1.0
    p = {"NH3": ynh3 * P, "H2": yh * P, "N2": yn2 * P, "Ar": (1 - yh - yn2 - ynh3) * P}
    assert abs(rate_mol_per_kgcat_s(cid, T, p)) < 1e-9 * rate_mol_per_kgcat_s(cid, T, p, approach_factor=False)


def test_lucentini_reproduces_table1_point():
    # 0.1 g, 25 mL/min (0 degC, 1 atm), Ar:NH3 1.2:1, 450 degC, 1 atm -> 86.1 % (Table 1, p. 10)
    n = 25e-3 * 60 / 22.414 / 1000
    r = simulate_pfr(LUC[0], 1e-4, T_in_C=450, P_in_bar=1.01325, feed_kmol_h={"NH3": n / 2.2, "Ar": n * 1.2 / 2.2},
                     mode="isothermal", pressure_drop=False, n_points=3)
    assert abs(r.outlet["conversion"] - 0.861) < 0.05


def test_aspen_lhhw_form_is_exact_for_lucentini():
    cid = LUC[1]
    par = {k: v["value"] for k, v in get_catalyst(cid).parameters.items()}
    T, p = 823.15, {"NH3": 6.0, "H2": 9.0, "N2": 3.0}
    C = {s: v * 1e5 / (R * T) / 1000 for s, v in p.items()}          # kmol/m3
    Kc = equilibrium_constant(T) * 1e5 / (R * T) / 1000                 # kmol/m3
    K1, K4 = par["K1"] * 1000, par["K4"] / 1000
    k = par["k0"] * math.exp(-par["Ek"] * 1e3 / (R * T))
    r_aspen = k * (K1 * C["NH3"] - K1 / Kc * C["N2"] ** 0.5 * C["H2"] ** 1.5) / (1 + K1 * C["NH3"] + K4 ** -0.5 * C["H2"] ** 0.5) ** 2
    assert 1000 * r_aspen == pytest.approx(rate_mol_per_kgcat_s(cid, T, p), rel=1e-9)


def test_pfr_assumption_label_for_lhhw():
    r = simulate_pfr(LUC[0], 10.0, T_in_C=500, P_in_bar=1.01325, feed_kmol_h={"NH3": 1.0}, pressure_drop=False, n_points=2)
    assert any("Lucentini" in a for a in r.assumptions)
    assert 0.0 < r.outlet["conversion"] <= r.outlet["X_eq_outlet"] + 1e-9
