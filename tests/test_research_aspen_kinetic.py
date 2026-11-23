"""Workstream A: kinetic RPLUG input writer (no Aspen needed) and regression of the existing flowsheet text."""
from __future__ import annotations

import json
import math
import re

import pytest

from amcrax.aspen.inp_writer import build_equilibrium_input, build_flowsheet_input
from amcrax.aspen.kinetic import (
    KineticCase,
    KineticReactorInputs,
    build_kinetic_reactor_input,
    load_spec,
    spec_from_registry,
)
from amcrax.paths import ROOT
from amcrax.schemas import CaseInputs

REG = ROOT / "aspen" / "models" / "research" / "regression"


@pytest.mark.parametrize("hi", [True, False])
@pytest.mark.parametrize("ns", [True, False])
def test_existing_flowsheet_text_unchanged(hi, ns):
    """Snapshots were written from the unmodified inp_writer before the kinetic option was added."""
    expected = (REG / f"flowsheet_hi{int(hi)}_ns{int(ns)}.inp").read_text(encoding="ascii")
    assert build_flowsheet_input(CaseInputs(heat_integration=hi), native_sensitivity=ns) == expected


def test_baseline_model_file_matches_generator():
    text = (ROOT / "aspen" / "models" / "baseline.inp").read_text(encoding="ascii")
    assert build_flowsheet_input(CaseInputs(), native_sensitivity=True) == text


def test_equilibrium_input_has_no_kinetics():
    assert "RPLUG" not in build_equilibrium_input() and "REACTIONS" not in build_equilibrium_input()


def test_kum_spec_unit_conversion():
    s = spec_from_registry("ru_kum_temkin_pyzhev")
    # ko 55245.9 mol g^-1 s^-1 bar^0.27 -> kmol kg^-1 s^-1 (x1000/1000), per 2 mol NH3 (/2)
    assert s.pre_exp_kmol_kgcat_s == pytest.approx(55245.9 / 2.0, rel=1e-12)
    assert s.activation_energy_kJ_mol == pytest.approx(114.224, rel=1e-12)
    assert s.exponents == pytest.approx({"NH3": 0.54, "H2": -0.81})
    assert s.stoichiometry == {"NH3": -2.0, "N2": 1.0, "H2": 3.0}
    assert s.reversible and s.rev_method == "AUTOMATIC"


def test_aspen_form_equals_kum_rate_law():
    """k pNH3^2b pH2^-3b (1 - Q2/K2) x 2 (per mol NH3) == the Python Kum law (keq from the same K)."""
    from amcrax.kinetics.rate_laws import kum_keq, rate_mol_per_kgcat_s

    s = spec_from_registry()
    T = 723.15
    p = {"NH3": 2.0, "H2": 2.2, "N2": 0.7}
    K2 = kum_keq(T, "amcrax_thermo") ** 2
    k = s.pre_exp_kmol_kgcat_s * math.exp(-s.activation_energy_kJ_mol * 1e3 / (8.314 * T))
    r_rxn = k * p["NH3"] ** s.exponents["NH3"] * p["H2"] ** s.exponents["H2"] * (1 - p["N2"] * p["H2"] ** 3 / (p["NH3"] ** 2 * K2))
    r_py = rate_mol_per_kgcat_s("ru_kum_temkin_pyzhev", T, p, keq_basis="amcrax_thermo")  # mol/(kg s)
    assert 2.0 * r_rxn * 1000.0 == pytest.approx(r_py, rel=1e-9)


def test_microkinetic_not_native():
    with pytest.raises(ValueError, match="not expressible"):
        spec_from_registry("ni_takahashi_microkinetic")


def test_load_spec_falls_back_to_registry(tmp_path):
    missing = tmp_path / "none.json"
    assert load_spec("ru_kum_temkin_pyzhev", missing) == spec_from_registry()
    ext = tmp_path / "spec.json"
    ext.write_text(json.dumps({"catalysts": [{"catalyst_id": "x_cat", "aspen": {
        "pre_exp_kmol_kgcat_s": 1.0, "activation_energy_kJ_mol": 50.0, "exponents": {"NH3": 1.0}}}]}))
    assert load_spec("x_cat", ext).pre_exp_kmol_kgcat_s == 1.0


def test_geometry_from_catalyst_mass():
    i = KineticReactorInputs(catalyst_mass_kg=20.0, n_tubes=50)
    assert i.catalyst_mass_total_kg == pytest.approx(20.0, rel=1e-12)
    assert i.reactor_length_m == pytest.approx(20.0 / ((1 - 0.36) * 980.0 * 50 * math.pi * 0.126 ** 2 / 4))


def test_inputs_validation():
    with pytest.raises(ValueError):
        KineticReactorInputs()  # neither mass nor length
    with pytest.raises(ValueError):
        KineticReactorInputs(catalyst_mass_kg=1.0, length_m=1.0)
    with pytest.raises(ValueError):
        KineticReactorInputs(catalyst_mass_kg=1.0, thermal_mode="coolant")


def test_seeded_feed_conserves_atoms():
    i = KineticReactorInputs(catalyst_mass_kg=1.0)
    f = i.seeded_feed()
    assert f["NH3"] + 0 * f["H2"] == pytest.approx(99.8 * (1 - i.h2_seed_conversion))
    assert f["NH3"] + 2 * f["N2"] == pytest.approx(99.8)          # N atoms
    assert 3 * f["NH3"] + 2 * f["H2"] == pytest.approx(3 * 99.8)  # H atoms


@pytest.mark.parametrize("mode,token", [("isothermal", "TYPE=T-SPEC"), ("adiabatic", "TYPE=ADIABATIC"),
                                        ("coolant", "TYPE=TCOOL-SPEC")])
def test_standalone_text(mode, token):
    kw = dict(coolant_temperature_C=550.0, U_W_m2K=100.0) if mode == "coolant" else {}
    i = KineticReactorInputs(case_id="t", catalyst_mass_kg=20.0, n_tubes=50, thermal_mode=mode, pressure_drop=True, **kw)
    t = build_kinetic_reactor_input(i, spec_from_registry())
    assert token in t
    assert "BLOCK RXR RPLUG" in t and "BLOCK REQ RGIBBS" in t
    assert "REACTIONS NH3KIN GENERAL" in t and "CBASIS=PARTIALPRES RBASIS=CAT-WT" in t
    assert "PRE-EXP=27622.95" in t and "ACT-ENERGY=114.224 <kJ/mol>" in t
    assert "DFORCE-EXP 1 MIXED NH3 0.54 / MIXED H2 -0.81" in t
    assert "DP-FCOR=ERGUN DIA-PART=0.0006 <meter>" in t
    assert ("T-SPEC 0. 450." in t) == (mode == "isothermal")
    assert ("COOLANT TEMP=550." in t) == (mode == "coolant")
    t.encode("ascii")


def test_integrated_text():
    ci = CaseInputs()
    kin = KineticReactorInputs(case_id="baseline", catalyst_mass_kg=200.0, n_tubes=50, include_equilibrium_reference=False)
    t = build_flowsheet_input(ci, kinetic_cracker=kin)
    base = build_flowsheet_input(ci)
    assert "BLOCK CRACKER RPLUG" in t and "BLOCK CRACKER RGIBBS" not in t
    assert "T-SPEC 0. 600." in t and "REACTIONS NH3KIN GENERAL" in t
    # connectivity identical apart from the H2 seed stream joining the HEATER
    fs = lambda x: re.search(r"FLOWSHEET\n(.*?)\n\n", x, re.S).group(1)  # noqa: E731
    assert fs(t).replace("IN=S3 H2SEED OUT=S4", "IN=S3 OUT=S4") == fs(base)
    assert "MOLE-FRAC NH3 0.998 / H2O 0.002\n" in t  # FEED unchanged
    m = re.search(r"STREAM H2SEED\n.*\n    MOLE-FLOW H2 ([\d.e-]+) / N2 ([\d.e-]+)", t)
    assert m and float(m.group(1)) == pytest.approx(1.5 * 1e-3 * 99.8) and float(m.group(2)) == pytest.approx(0.5 * 1e-3 * 99.8)
    with pytest.raises(ValueError):
        build_flowsheet_input(ci, native_sensitivity=True, kinetic_cracker=kin)
    t_no = build_flowsheet_input(CaseInputs(heat_integration=False), kinetic_cracker=kin)
    assert "BLOCK FEHE" not in t_no and "BLOCK CRACKER RPLUG" in t_no


def test_lhhw_writer_from_spec_entry():
    from amcrax.aspen.kinetic import lhhw_from_kinetics_spec, lhhw_reactions_block

    e = {"catalyst_id": "c", "stoichiometry": {"NH3": -1, "N2": 0.5, "H2": 1.5}, "concentration_basis": "Molarity",
         "kinetic_factor": {"k": 3.9e6, "n": 0.0, "E_kJ_per_mol": 124.0},
         "driving_force": {"term1": {"exponents": {"NH3": 1.0}, "lnK_coefficients": {"A": 7.0}},
                           "term2": {"exponents": {"H2": 1.5, "N2": 0.5}, "lnK_coefficients": {"A": 11.0, "B": 4800.0}}},
         "adsorption": {"exponent": 2.0, "terms": [{"exponents": {}, "lnK_coefficients": {}},
                                                    {"exponents": {"NH3": 1.0}, "lnK_coefficients": {"A": 7.0}}]}}
    t = lhhw_reactions_block(lhhw_from_kinetics_spec(e))
    assert "REAC-CLASS=LHHW" in t and "CBASIS=MOLARITY" in t and "REV-METH=USER-SPEC" in t
    assert "PARAM NTERM-ADS=2" in t and "CID=NH3 SSID=MIXED EXPONENT=0. 1." in t
    assert "ADSORP-POW REACNO=1 EXPONENT=2." in t and "DFORCE-EQ-2 REACNO=1 A=11. B=4800. C=0. D=0." in t


def test_resolve_spec_auto_prefers_powerlaw():
    from amcrax.aspen.kinetic import AspenPowerLawSpec, resolve_spec

    assert isinstance(resolve_spec("ru_kum_temkin_pyzhev"), AspenPowerLawSpec)


def test_case_from_json():
    c = KineticCase.from_json({"case_id": "a", "configuration": "integrated", "temperature_C": 550, "pressure_bar": 10,
                               "catalyst_mass_kg": 100, "flowsheet": {"heat_integration": False}})
    ci = c.case_inputs()
    assert ci.reactor_temperature_C == 550 and ci.reactor_pressure_bar == 10 and not ci.heat_integration
    assert c.reactor.include_equilibrium_reference is False
    assert "BLOCK CRACKER RPLUG" in c.input_text()
