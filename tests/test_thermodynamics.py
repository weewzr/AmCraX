"""Tests for amcrax.thermodynamics (independent NH3-cracking equilibrium model).

Validation layers
  (a) solver check   - Cantera equilibrate("TP") with the SAME GRI-Mech 3.0 data: near-identical
                       results are expected; this verifies the root solve, not the data.
  (b) data check     - NIST-JANAF 4th ed. tables (independent data, 1 bar standard state).
  (c) internal       - element balances, van't Hoff consistency, Le Chatelier trends, limits,
                       PR EOS thermodynamic consistency and comparison with CoolProp reference EOS.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

import amcrax.thermodynamics as th
from amcrax.thermodynamics import peng_robinson as pr

JANAF = json.loads((Path(th.__file__).parent / "reference" / "janaf.json").read_text())
COL = {c: i for i, c in enumerate(JANAF["columns"])}


def janaf(sp, T, col):
    for r in JANAF["species"][sp]["rows"]:
        if abs(r[0] - T) < 1e-6:
            return r[COL[col]]
    raise KeyError((sp, T))


def janaf_T(sp, lo=298.15, hi=1500.0):
    return [r[0] for r in JANAF["species"][sp]["rows"] if lo <= r[0] <= hi]


# ------------------------------------------------------------------ (b) data vs NIST-JANAF
def test_formation_and_reaction_enthalpy_298():
    # JANAF H-083: dHf(NH3, 298.15) = -45.898 kJ/mol -> dHrxn = +45.898 kJ per mol NH3
    assert th.species_enthalpy_kJ_mol("NH3", 298.15) == pytest.approx(-45.898, abs=0.05)
    assert th.species_enthalpy_kJ_mol("H2O", 298.15) == pytest.approx(-241.826, abs=0.05)
    for el in ("H2", "N2", "O2"):
        assert abs(th.species_enthalpy_kJ_mol(el, 298.15)) < 0.005
    assert th.reaction_enthalpy_kJ_mol(298.15) == pytest.approx(45.898, abs=0.05)
    assert th.reaction_gibbs_kJ_mol(298.15) == pytest.approx(16.367, abs=0.05)  # = -dGf(NH3)


@pytest.mark.parametrize("sp", ["NH3", "N2", "H2", "H2O", "O2"])
def test_species_vs_janaf(sp):
    for T in janaf_T(sp):
        assert th.species_cp_J_molK(sp, T) == pytest.approx(janaf(sp, T, "Cp_J_molK"), abs=0.25), T
        # entropy at 1 bar: proves the GRI polynomials are 1-bar data (a 1 atm shift = 0.109 J/mol/K)
        assert th.species_entropy_J_molK(sp, T) == pytest.approx(janaf(sp, T, "S_J_molK"), abs=0.15), T
        dh = th.species_enthalpy_kJ_mol(sp, T) - th.species_enthalpy_kJ_mol(sp, 298.15)
        assert dh == pytest.approx(janaf(sp, T, "H_minus_HTr_kJ_mol"), abs=0.1), T


def test_equilibrium_constant_vs_janaf_logKf():
    # AmCraX reaction is the reverse of the JANAF formation reaction: log10 K = -log10 Kf
    devs = []
    for T in janaf_T("NH3", 400, 1500):
        ref = -janaf("NH3", T, "log10_Kf")
        devs.append(math.log10(th.equilibrium_constant(T)) - ref)
    assert max(abs(d) for d in devs) < 0.01, devs   # < 2.3 % in K


# ------------------------------------------------------------------ (c) internal consistency
@pytest.mark.parametrize("T", [500.0, 700.0, 900.0, 1100.0])
def test_vant_hoff(T):
    h = 0.01
    dlnK = (math.log(th.equilibrium_constant(T + h)) - math.log(th.equilibrium_constant(T - h))) / (2 * h)
    assert dlnK == pytest.approx(th.reaction_enthalpy_kJ_mol(T) * 1000 / (th.R_J_molK * T**2), rel=1e-6)


def test_cp_is_dh_dT():
    for sp in th.species_list():
        for T in (400.0, 800.0, 1200.0):
            d = (th.species_enthalpy_kJ_mol(sp, T + 0.01) - th.species_enthalpy_kJ_mol(sp, T - 0.01)) / 0.02 * 1000
            assert d == pytest.approx(th.species_cp_J_molK(sp, T), rel=1e-6)


@pytest.mark.parametrize("eos", ["ideal", "pr"])
def test_element_balance_and_equilibrium_condition(eos):
    feed = {"NH3": 0.9, "H2": 0.05, "N2": 0.03, "H2O": 0.02}
    for T in (523.15, 773.15, 1073.15):
        for P in (1.0, 20.0, 60.0):
            r = th.solve_equilibrium(T, P, feed, eos=eos)
            for el, comp in (("N", {"NH3": 1, "N2": 2}), ("H", {"NH3": 3, "H2": 2, "H2O": 2})):
                e_in = sum(feed.get(s, 0) * k for s, k in comp.items())
                e_out = sum(r.n_out[s] * k for s, k in comp.items())
                assert e_out == pytest.approx(e_in, rel=1e-12)
            assert r.n_out["H2O"] == feed["H2O"]
            assert sum(r.y.values()) == pytest.approx(1.0, abs=1e-14)
            Q = math.prod((r.y[s] * r.phi[s] * P) ** nu for s, nu in th.NU.items())
            assert Q == pytest.approx(r.K_eq, rel=1e-8)


@pytest.mark.parametrize("eos", ["ideal", "pr"])
def test_le_chatelier(eos):
    Ts = np.arange(523.15, 1173.16, 25.0)
    for P in (1.0, 10.0, 40.0):
        X = [th.solve_equilibrium(T, P, {"NH3": 1.0}, eos=eos).conversion for T in Ts]
        assert all(np.diff(X) > 0), (P, X)      # endothermic: up with T
    for T in (623.15, 773.15, 923.15):
        X = [th.solve_equilibrium(T, P, {"NH3": 1.0}, eos=eos).conversion for P in (1, 5, 10, 20, 40, 80)]
        assert all(np.diff(X) < 0), (T, X)      # mole increase: down with P


def test_limits():
    # conversion -> 1 at high T / low P, resolved in relative precision
    r = th.solve_equilibrium(1500.0, 0.1, {"NH3": 1.0})
    assert 0 < 1 - r.conversion < 1e-5 and r.n_out["NH3"] > 0
    # ideal-gas analytic check for pure NH3 feed: K = (0.5X)^0.5 (1.5X)^1.5 P / ((1-X)(1+X))
    for T, P in ((673.15, 1.0), (873.15, 20.0), (523.15, 40.0)):
        r = th.solve_equilibrium(T, P, {"NH3": 1.0})
        X = r.conversion
        assert (0.5 * X) ** 0.5 * (1.5 * X) ** 1.5 * P / ((1 - X) * (1 + X)) == pytest.approx(r.K_eq, rel=1e-9)
    # reverse direction (synthesis from 3 H2 + N2) and same answer from the NH3 side
    a = th.solve_equilibrium(673.15, 40.0, {"H2": 3.0, "N2": 1.0})
    b = th.solve_equilibrium(673.15, 40.0, {"NH3": 2.0})
    assert a.extent < 0
    for s in ("NH3", "H2", "N2"):
        assert a.y[s] == pytest.approx(b.y[s], rel=1e-9)
    # scale invariance
    c = th.solve_equilibrium(873.15, 20.0, {"NH3": 99.8, "H2O": 0.2})
    d = th.solve_equilibrium(873.15, 20.0, {"NH3": 0.998, "H2O": 0.002})
    assert c.conversion == pytest.approx(d.conversion, rel=1e-12)
    with pytest.raises(ValueError):
        th.solve_equilibrium(873.15, 20.0, {"H2O": 1.0})
    with pytest.raises(ValueError):
        th.solve_equilibrium(873.15, 20.0, {"NH3": 1.0}, eos="srk")


def test_reactor_duty():
    T = 873.15
    n_in = {"NH3": 100.0}
    r = th.solve_equilibrium(T, 20.0, n_in)
    Q = th.isothermal_reactor_duty_kW(n_in, T, r.n_out, T)
    # ideal gas, isothermal: Q = extent * dH_rxn(T)
    assert Q == pytest.approx(r.extent * th.reaction_enthalpy_kJ_mol(T) * 1000 / 3600, rel=1e-10)
    assert Q > 0
    assert th.mixture_enthalpy_kW({"NH3": 3.6}, 298.15) == pytest.approx(-45.898, abs=0.05)  # 1 mol/s


# ------------------------------------------------------------------ PR EOS
def test_pr_ideal_limit_and_consistency():
    y = {"NH3": 0.2, "H2": 0.6, "N2": 0.2}
    phi = pr.fugacity_coefficients(y, 800.0, 1e-4)
    assert all(abs(v - 1) < 1e-5 for v in phi.values())
    T, P = 700.0, 40.0
    phi = pr.fugacity_coefficients(y, T, P)
    # ln phi_mix from sum_i y_i ln phi_i must equal integral of (Z-1)/P dP
    Ps = np.linspace(1e-6, P, 4001)
    Z = np.array([pr.compressibility(y, T, p) for p in Ps])
    integral = np.trapezoid((Z - 1) / Ps, Ps)
    assert sum(y[s] * math.log(phi[s]) for s in y) == pytest.approx(integral, rel=1e-4)
    # H_dep = -R T^2 sum_i y_i d ln phi_i / dT
    h = 0.01
    lp = lambda TT: sum(y[s] * math.log(v) for s, v in pr.fugacity_coefficients(y, TT, P).items())
    hdep = -th.R_J_molK * T**2 * (lp(T + h) - lp(T - h)) / (2 * h)
    assert pr.enthalpy_departure_J_mol(y, T, P) == pytest.approx(hdep, rel=1e-4)


def test_pr_vs_coolprop_reference_eos():
    CP = pytest.importorskip("CoolProp.CoolProp")
    # Z of pure gases at conditions inside the AmCraX range; PR should agree within ~1.5 %
    for sp, fl, T, P in (("N2", "Nitrogen", 600.0, 40.0), ("H2", "Hydrogen", 600.0, 40.0),
                         ("NH3", "Ammonia", 600.0, 40.0), ("NH3", "Ammonia", 523.15, 20.0)):
        z_ref = CP.PropsSI("Z", "T", T, "P", P * 1e5, fl)
        assert pr.compressibility({sp: 1.0}, T, P) == pytest.approx(z_ref, rel=0.015), sp


# ------------------------------------------------------------------ PR binary interaction parameters (kij)
KIJ = {("NH3", "H2"): 0.12, ("N2", "NH3"): -0.07, ("H2", "N2"): 0.03}


def test_kij_regression_matmul_shape_and_dict_forms():
    # regression: a kij argument used to crash (matrix sized for the non-zero species only)
    zero = {("NH3", "H2"): 0.0, ("NH3", "N2"): 0.0, ("H2", "N2"): 0.0}
    a = th.solve_equilibrium(873.15, 20.0, {"NH3": 1.0}, eos="pr", kij=zero)
    b = th.solve_equilibrium(873.15, 20.0, {"NH3": 1.0}, eos="pr")
    assert a.conversion == b.conversion and a.phi == b.phi          # k_ij = 0 limit: bit-for-bit
    c = th.solve_equilibrium(873.15, 20.0, {"NH3": 1.0}, eos="pr", kij=KIJ)
    assert c.conversion != b.conversion
    # order-insensitive keys, symmetric matrix
    rev = {(j, i): v for (i, j), v in KIJ.items()}
    d = th.solve_equilibrium(873.15, 20.0, {"NH3": 1.0}, eos="pr", kij=rev)
    assert d.conversion == c.conversion
    K = pr.kij_matrix(["NH3", "H2", "N2", "H2O"], KIJ)
    assert np.array_equal(K, K.T) and K[0, 1] == 0.12 and K[0, 2] == -0.07 and K[3].sum() == 0.0
    with pytest.raises(TypeError):
        pr.fugacity_coefficients({"NH3": 1.0}, 700.0, 20.0, kij=np.zeros((3, 3)))   # positional matrix rejected
    with pytest.raises(ValueError):
        pr.normalise_kij({("NH3", "H2"): 0.1, ("H2", "NH3"): 0.2})                  # conflicting duplicate
    with pytest.raises(KeyError):
        pr.normalise_kij({("NH3", "Ar"): 0.1})
    with pytest.raises(ValueError):
        th.solve_equilibrium(873.15, 20.0, {"NH3": 1.0}, eos="pr", kij={("NH3", "NH3"): 0.1})


def test_kij_none_bit_for_bit_with_previous_implementation():
    # values written by the implementation before the kij repair (captured 2026-11-21, PYTHONHASHSEED=0); the
    # kij=None path must reproduce them exactly (==, not approx)
    phi = pr.fugacity_coefficients({"NH3": 0.2, "H2": 0.6, "N2": 0.2, "H2O": 0.0, "O2": 0.0}, 523.15, 40.0)
    assert phi == {"NH3": 0.9711782281397329, "H2": 1.0127327477096348, "N2": 1.0133982344312813,
                   "H2O": 0.9436741350678646, "O2": 1.0049762880578776}
    assert pr.enthalpy_departure_J_mol({"NH3": 0.2, "H2": 0.6, "N2": 0.2}, 700.0, 80.0) == -41.66496430132581
    assert pr.compressibility({"NH3": 0.2, "H2": 0.6, "N2": 0.2}, 700.0, 80.0) == 1.0156859617862357
    r = th.solve_equilibrium(523.15, 40.0, {"NH3": 1.0}, eos="pr")
    assert r.conversion == 0.2935755326224443
    assert r.phi == {"NH3": 0.9538058024521866, "H2": 1.0246920856076829, "N2": 1.0215603937934281}


def test_species_order_independent_of_input_order():
    y1 = {"NH3": 0.2, "H2": 0.6, "N2": 0.19, "H2O": 0.01, "O2": 0.0}
    y2 = dict(reversed(list(y1.items())))
    for kij in (None, KIJ):
        assert pr.fugacity_coefficients(y1, 600.0, 50.0, kij=kij) == pr.fugacity_coefficients(y2, 600.0, 50.0, kij=kij)
        assert pr.enthalpy_departure_J_mol(y1, 600.0, 50.0, kij=kij) == pr.enthalpy_departure_J_mol(y2, 600.0, 50.0, kij=kij)


def test_kij_binary_hand_calculation():
    # binary NH3-H2: a_m = y1^2 a1 + 2 y1 y2 sqrt(a1 a2)(1-k) + y2^2 a2, then PR eq. 15 written out by hand
    T, P, k, y1 = 650.0, 60.0, 0.15, 0.3
    y2 = 1 - y1
    (a1, a2), (b1, b2) = pr._pure_params(["NH3", "H2"], T, "standard")
    a12 = math.sqrt(a1 * a2) * (1 - k)
    am = y1 * y1 * a1 + 2 * y1 * y2 * a12 + y2 * y2 * a2
    bm = y1 * b1 + y2 * b2
    RT = th.R_J_molK * T
    A, B = am * P * 1e5 / RT**2, bm * P * 1e5 / RT
    Z = max(r.real for r in np.roots([1, -(1 - B), A - 3 * B * B - 2 * B, -(A * B - B * B - B**3)]) if abs(r.imag) < 1e-12)
    lg = math.log((Z + (1 + math.sqrt(2)) * B) / (Z + (1 - math.sqrt(2)) * B))
    ln1 = b1 / bm * (Z - 1) - math.log(Z - B) - A / (2 * math.sqrt(2) * B) * (2 * (y1 * a1 + y2 * a12) / am - b1 / bm) * lg
    ln2 = b2 / bm * (Z - 1) - math.log(Z - B) - A / (2 * math.sqrt(2) * B) * (2 * (y1 * a12 + y2 * a2) / am - b2 / bm) * lg
    phi = pr.fugacity_coefficients({"H2": y2, "NH3": y1}, T, P, kij={("H2", "NH3"): k})
    assert phi["NH3"] == pytest.approx(math.exp(ln1), rel=1e-13)
    assert phi["H2"] == pytest.approx(math.exp(ln2), rel=1e-13)


def test_kij_infinite_dilution_applies_kij():
    # phi of a zero-fraction species is the y_i -> 0 limit of the same formula, with (1 - k_ij) applied
    y = {"NH3": 0.2, "H2": 0.6, "N2": 0.2, "H2O": 0.0}
    k = dict(KIJ)
    k[("H2O", "NH3")] = -0.25
    p0 = pr.fugacity_coefficients(y, 700.0, 40.0, kij=k)["H2O"]
    for eps in (1e-6, 1e-8):
        ye = {s: v * (1 - eps) for s, v in y.items()}
        ye["H2O"] = eps
        assert pr.fugacity_coefficients(ye, 700.0, 40.0, kij=k)["H2O"] == pytest.approx(p0, rel=10 * eps)
    assert p0 != pr.fugacity_coefficients(y, 700.0, 40.0, kij=KIJ)["H2O"]   # the H2O-NH3 k_ij is used


def test_kij_against_coolprop_pr_backend():
    """CoolProp's cubic PR backend with k_ij set through set_binary_interaction_double.

    CoolProp's PR uses its own Tc, Pc, omega and the exact Omega_a, Omega_b; the AmCraX constants are swapped
    for CoolProp's here, so the remaining difference (~1e-6 in phi) is the rounded Omega_a = 0.45724,
    Omega_b = 0.07780 of Peng & Robinson (1976). The k_ij-induced shift of ln phi is compared separately."""
    CP = pytest.importorskip("CoolProp.CoolProp")
    fl = {"NH3": "Ammonia", "H2": "Hydrogen", "N2": "Nitrogen", "H2O": "Water"}
    names = ["NH3", "H2", "N2", "H2O"]
    consts = {}
    for s in names:
        a = CP.AbstractState("PR", fl[s])
        consts[s] = {"Tc_K": a.T_critical(), "Pc_bar": a.p_critical() / 1e5, "omega": a.acentric_factor()}
    k = dict(KIJ)
    k[("H2O", "NH3")] = -0.25
    y = {"NH3": 0.2, "H2": 0.55, "N2": 0.2, "H2O": 0.05}

    def coolprop(kset, T, P):
        st = CP.AbstractState("PR", "&".join(fl[s] for s in names))
        for (i, j), v in kset.items():
            st.set_binary_interaction_double(names.index(i), names.index(j), "kij", v)
        st.set_mole_fractions([y[s] for s in names])
        st.specify_phase(CP.iphase_gas)
        st.update(CP.PT_INPUTS, P * 1e5, T)
        return {s: math.log(st.fugacity_coefficient(n)) for n, s in enumerate(names)}

    orig = pr.critical_properties
    pr.critical_properties = lambda: consts
    try:
        for T, P in ((700.0, 40.0), (523.15, 80.0)):
            ref0, ref = coolprop({}, T, P), coolprop(k, T, P)
            py0 = {s: math.log(v) for s, v in pr.fugacity_coefficients(y, T, P).items()}
            py = {s: math.log(v) for s, v in pr.fugacity_coefficients(y, T, P, kij=k).items()}
            for s in names:
                assert py[s] == pytest.approx(ref[s], abs=5e-6), (T, P, s)
                shift_ref, shift_py = ref[s] - ref0[s], py[s] - py0[s]
                assert abs(shift_ref) > 1e-4                       # the k_ij effect is resolved
                assert shift_py == pytest.approx(shift_ref, rel=2e-3, abs=2e-7), (T, P, s)
    finally:
        pr.critical_properties = orig


def test_pr_dew_point_limits():
    CP = pytest.importorskip("CoolProp.CoolProp")
    # pure NH3: PR saturation temperature close to the reference EOS (PR vapour pressure of NH3 within ~1 K here)
    T_pr = pr.dew_point_K(20.8, {"NH3": 1.0})[0]
    T_ref = CP.PropsSI("T", "P", 20.8e5, "Q", 1, "Ammonia")
    assert abs(T_pr - T_ref) < 1.5
    # 0.2 mol% water raises the dew point; a negative NH3-H2O k_ij (more attraction) raises it further
    y = {"NH3": 0.998, "H2O": 0.002}
    T0, x0 = pr.dew_point_K(20.8, y)
    T1, x1 = pr.dew_point_K(20.8, y, kij={("NH3", "H2O"): -0.25})
    assert T_pr < T0 < T1
    assert x0["H2O"] > 10 * y["H2O"] and x1["H2O"] > x0["H2O"] and abs(sum(x0.values()) - 1) < 1e-12
    # measured (2026-11-21): PR kij=0 52.68 degC, kij=-0.25 65.14 degC, pure-NH3 PR 50.83 degC (reference 50.88)
    assert T0 - 273.15 == pytest.approx(52.68, abs=0.05) and T1 - 273.15 == pytest.approx(65.14, abs=0.05)


def test_pr_deviation_small_at_moderate_pressure():
    for T in (673.15, 873.15):
        for P in (1.0, 20.0, 40.0):
            a = th.solve_equilibrium(T, P, {"NH3": 1.0}).conversion
            b = th.solve_equilibrium(T, P, {"NH3": 1.0}, eos="pr").conversion
            assert abs(a - b) < 0.01


# ------------------------------------------------------------------ (a) solver vs Cantera
def test_solver_vs_cantera_same_data():
    ct = pytest.importorskip("cantera")
    names = ("NH3", "H2", "N2", "H2O")
    allsp = {s.name: s for s in ct.Species.list_from_file("gri30.yaml")}
    gas = ct.Solution(thermo="ideal-gas", species=[allsp[n] for n in names])
    worst = 0.0
    for T_C in range(250, 901, 50):
        for P in (1.0, 5.0, 10.0, 20.0, 30.0, 40.0):
            T = T_C + 273.15
            # Cantera assigns the polynomials a 1 atm standard state; this model a 1 bar one (see nasa7.py),
            # so the same physics is Cantera at P atm <-> AmCraX at P bar.
            gas.TPX = T, P * ct.one_atm, {"NH3": 0.998, "H2O": 0.002}
            gas.equilibrate("TP")
            y = dict(zip(gas.species_names, gas.X))
            x_ct = 1 - y["NH3"] / (y["NH3"] + 2 * y["N2"])
            r = th.solve_equilibrium(T, P, {"NH3": 0.998, "H2O": 0.002})
            worst = max(worst, abs(r.conversion - x_ct))
            for s in ("NH3", "H2", "N2"):
                assert r.y[s] == pytest.approx(y[s], rel=1e-5, abs=1e-9)
    assert worst < 1e-6
