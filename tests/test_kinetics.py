"""Tests for amcrax.kinetics (literature rate laws)."""
import math

import pytest
import yaml

from amcrax.kinetics import (
    BAR_PER_ATM,
    G_PER_KG,
    get_catalyst,
    kum_keq,
    list_catalysts,
    rate_mol_per_kgcat_s,
    takahashi_constants,
    takahashi_coverages,
)
from amcrax.kinetics.rate_laws import _DATA, _registry
from amcrax.thermodynamics import equilibrium_constant, solve_equilibrium

CATS = ["ni_takahashi_microkinetic", "ru_takahashi_microkinetic", "ru_kum_temkin_pyzhev"]


def _p_eq(T_K, P_bar):
    eq = solve_equilibrium(T_K, P_bar, {"NH3": 1.0})
    return {s: eq.y[s] * P_bar for s in ("NH3", "H2", "N2")}


def test_registry_has_ni_and_ru_and_metadata():
    cats = {c.id: c for c in list_catalysts()}
    assert {"Ni", "Ru"} <= {c.metal for c in cats.values()}
    for cid in CATS:
        c = cats[cid]
        assert c.usable and c.source["citekey"] and c.source["page"] and c.source["locator"]
        assert c.validity["T_min_K"] < c.validity["T_max_K"]
        assert c.rate_law_text and c.composition and c.limitations
        for name, p in c.parameters.items():
            assert {"value", "unit", "citekey", "page", "locator"} <= set(p), name
            assert isinstance(p["value"], (int, float)) and not isinstance(p["value"], bool), \
                f"{cid}.{name} not parsed as a number"


def test_yaml_numbers_are_floats():
    """Guard against PyYAML reading '1.5e10' (no exponent sign) as a string."""
    with open(_DATA, encoding="utf-8") as fh:
        d = yaml.safe_load(fh)

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            with pytest.raises(ValueError):
                float(o)
    walk(d)


@pytest.mark.parametrize("cid", CATS[:2])
def test_takahashi_table2_reproduced(cid):
    """Table 1 -> Table 2 at 500 degC within 10 % (paper rounding gives 2-7 %; not tuned)."""
    ref = _registry()["catalysts"][cid]["reference_values_773K"]
    calc = takahashi_constants(cid, 773.15)
    for k in ("k_minus1", "k2", "k3", "k4", "k_minus4", "K4"):
        assert calc[k] == pytest.approx(ref[k], rel=0.10), k


@pytest.mark.parametrize("cid", CATS[:2])
def test_takahashi_qss_and_site_balance(cid):
    c = takahashi_constants(cid, 800.0)
    cov = takahashi_coverages(cid, 800.0, 0.6, 0.3)
    s = cov["theta_s"] + cov["theta_NH3"] + cov["theta_N"] + cov["theta_H"]
    assert s == pytest.approx(1.0, abs=1e-10)
    r1 = c["k1"] * 0.6 * cov["theta_s"] - c["k_minus1"] * cov["theta_NH3"]
    r2 = c["k2"] * cov["theta_NH3"] * cov["theta_s"] ** 3
    r3 = c["k3"] * cov["theta_N"] ** 2
    r4 = c["k4"] * cov["theta_H"] ** 2 - c["k_minus4"] * 0.3 * cov["theta_s"] ** 2
    assert r1 == pytest.approx(r2, rel=1e-6)
    assert r2 == pytest.approx(2 * r3, rel=1e-8)
    assert 3 * r2 == pytest.approx(2 * r4, rel=1e-8)
    assert cov["r_mol_per_g_s"] == pytest.approx(r2)


def test_unit_conversion_round_trip():
    cid = "ru_takahashi_microkinetic"
    p = {"NH3": 0.8, "H2": 0.15, "N2": 0.05}
    r_kg = rate_mol_per_kgcat_s(cid, 750.0, p, approach_factor=False)
    r_g = takahashi_coverages(cid, 750.0, 0.8, 0.15)["r_mol_per_g_s"]
    assert G_PER_KG == 1000.0
    assert r_kg / G_PER_KG == pytest.approx(r_g, rel=1e-12)
    # mole-fraction basis: identical in atm and bar for the same composition
    p_atm = {k: v * BAR_PER_ATM for k, v in p.items()}
    assert rate_mol_per_kgcat_s(cid, 750.0, p_atm, approach_factor=False) == pytest.approx(r_kg, rel=1e-10)
    # Kum: manual evaluation of the published expression in mol/(g s) then x1000
    pk = {"NH3": 5.0, "H2": 3.0, "N2": 1.0}
    T = 700.0
    k = 55245.9 * math.exp(-114224 / (8.314 * T))
    keq = kum_keq(T, "published")
    manual = k * ((25 / 27) ** 0.27 - (1.0 / keq**2) * (27 / 25) ** 0.73)
    assert rate_mol_per_kgcat_s("ru_kum_temkin_pyzhev", T, pk) == pytest.approx(manual * 1000, rel=1e-12)


def test_kum_keq_basis_matches_thermo():
    """Eq. 4 read as J per 2 mol NH3 gives Keq per mol NH3 within 5 % of amcrax.thermodynamics."""
    for T in (623.15, 723.15, 873.15):
        assert kum_keq(T, "published") == pytest.approx(equilibrium_constant(T), rel=0.05)


@pytest.mark.parametrize("T_K,P_bar", [(673.15, 1.0), (773.15, 10.0), (873.15, 20.0)])
def test_kum_rate_zero_at_equilibrium(T_K, P_bar):
    p = _p_eq(T_K, P_bar)
    r_eq = rate_mol_per_kgcat_s("ru_kum_temkin_pyzhev", T_K, p, keq_basis="amcrax_thermo")
    p_far = {"NH3": P_bar * 0.9, "H2": P_bar * 0.075, "N2": P_bar * 0.025}
    r_far = rate_mol_per_kgcat_s("ru_kum_temkin_pyzhev", T_K, p_far, keq_basis="amcrax_thermo")
    assert abs(r_eq) < 1e-9 * abs(r_far)
    # beyond equilibrium (more NH3-lean) the rate reverses sign
    p_beyond = dict(p)
    p_beyond["NH3"] *= 0.5
    assert rate_mol_per_kgcat_s("ru_kum_temkin_pyzhev", T_K, p_beyond, keq_basis="amcrax_thermo") < 0


@pytest.mark.parametrize("cid", CATS[:2])
def test_takahashi_approach_factor(cid):
    T, P = 873.15, 20.0
    p = _p_eq(T, P)
    assert abs(rate_mol_per_kgcat_s(cid, T, p)) < 1e-9 * rate_mol_per_kgcat_s(cid, T, {"NH3": 19, "H2": 0.75, "N2": 0.25})
    # published form (switch off) is irreversible: positive at equilibrium
    assert rate_mol_per_kgcat_s(cid, T, p, approach_factor=False) > 0


@pytest.mark.parametrize("cid", CATS)
def test_arrhenius_behaviour(cid):
    """Far from equilibrium the rate increases with T; Kum apparent Ea equals the published Ea exactly."""
    p = {"NH3": 0.9, "H2": 0.075, "N2": 0.025}
    T = [650.0, 700.0, 750.0, 800.0]
    r = [rate_mol_per_kgcat_s(cid, t, p, approach_factor=False) for t in T]
    assert all(b > a for a, b in zip(r, r[1:]))
    if cid == "ru_kum_temkin_pyzhev":
        # at low conversion the reverse term is negligible -> ln r vs 1/T slope = -Ea/R
        r1, r2 = (rate_mol_per_kgcat_s(cid, t, {"NH3": 1.0, "H2": 1e-3, "N2": 1e-6}) for t in (650.0, 700.0))
        Ea = -8.314 * math.log(r2 / r1) / (1 / 700.0 - 1 / 650.0)
        assert Ea == pytest.approx(114224, rel=1e-3)


def test_h2_inhibition_takahashi():
    for cid in CATS[:2]:
        r0 = rate_mol_per_kgcat_s(cid, 773.15, {"NH3": 0.3, "H2": 0.0, "Ar": 0.7}, approach_factor=False)
        r1 = rate_mol_per_kgcat_s(cid, 773.15, {"NH3": 0.3, "H2": 0.5, "Ar": 0.2}, approach_factor=False)
        assert r1 < r0


def test_unknown_and_singular():
    with pytest.raises(KeyError):
        get_catalyst("nope")
    with pytest.raises(ValueError):
        rate_mol_per_kgcat_s("ru_kum_temkin_pyzhev", 800.0, {"NH3": 1.0, "H2": 0.0})
