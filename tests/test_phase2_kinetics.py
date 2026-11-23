"""Phase 2 task K1: kinetic validity, equilibrium consistency, Takahashi re-derivation, labels (no Aspen, no network)."""
from __future__ import annotations

import importlib.util
import json
import math

import pytest

from amcrax.aspen.kinetic import (
    KineticReactorInputs,
    build_kinetic_reactor_input,
    correct_cracker_block_entry,
    resolve_spec,
)
from amcrax.kinetics import rate_mol_per_kgcat_s
from amcrax.paths import ROOT

KIN = ROOT / "results" / "research" / "kinetics"
AK = ROOT / "results" / "research" / "aspen_kinetic"
VAL = ROOT / "results" / "research" / "validation"
SPEC = KIN / "aspen_kinetics_spec.json"
LUC = ["nire_ceo2_5ni1ru_lucentini_lhhw", "nire_ceo2_2p5ni0p5ru_lucentini_lhhw"]
needs_spec = pytest.mark.skipif(not SPEC.exists(), reason="kinetics spec not present")


def _script(name):
    p = ROOT / "scripts" / "research" / f"{name}.py"
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _lnk(d, T):
    return d["A"] + d["B"] / T + d["C"] * math.log(T) + d["D"] * T


def _aspen_rate(s, T, p_pa):
    """Evaluate an Aspen LHHW spec on a partial-pressure (Pa) basis, mol/(kg s)."""
    k = s.k_kmol_kgcat_s * math.exp(-s.activation_energy_kJ_mol * 1e6 / (8314.0 * T))
    df = math.exp(_lnk(s.term1_lnK, T)) * p_pa["NH3"] ** s.term1_exponents.get("NH3", 0.0) \
        - math.exp(_lnk(s.term2_lnK, T)) * p_pa["N2"] ** 0.5 * p_pa["H2"] ** 1.5
    den = 0.0
    for t in s.adsorption_terms:
        v = math.exp(_lnk(t["lnK_coefficients"], T))
        for c, a in (t.get("exponents") or {}).items():
            v *= p_pa[c] ** a
        den += v
    return k * df / den ** s.adsorption_exponent * 1000.0


@needs_spec
@pytest.mark.parametrize("cid", LUC)
@pytest.mark.parametrize("T,P,y", [(873.15, 20.0, {"NH3": 0.3, "H2": 0.525, "N2": 0.175}),
                                   (773.15, 40.0, {"NH3": 0.6, "H2": 0.3, "N2": 0.1}),
                                   (823.15, 1.01325, {"NH3": 0.9, "H2": 0.075, "N2": 0.025}),
                                   (723.15, 5.0, {"NH3": 0.95, "H2": 0.0375, "N2": 0.0125})])
def test_partialpres_form_reproduces_python_rate(cid, T, P, y):
    s = resolve_spec(cid, "lhhw_partialpres")
    assert s.cbasis == "PARTIALPRES"
    ra = _aspen_rate(s, T, {k: v * P * 1e5 for k, v in y.items()})
    rp = rate_mol_per_kgcat_s(cid, T, {k: v * P for k, v in y.items()})
    assert ra == pytest.approx(rp, rel=1e-5)   # only the ln Kp fit (2.8e-4 in K) enters near equilibrium


@needs_spec
def test_partialpres_form_equilibrium_is_ideal_gas_kp():
    s = resolve_spec(LUC[0], "lhhw_partialpres")
    fit = json.loads(SPEC.read_text(encoding="utf-8"))["equilibrium_constant_fit"]
    T = 850.0
    # driving force zero at Q_p = K1'/K2' = Kp * 1e5 Pa
    lnQ = _lnk(s.term1_lnK, T) - _lnk(s.term2_lnK, T)
    assert lnQ == pytest.approx(_lnk(fit, T) + math.log(1e5), abs=1e-12)


@needs_spec
def test_partialpres_kinetic_form_builds_input():
    i = KineticReactorInputs(case_id="t", catalyst_id=LUC[1], kinetic_form="lhhw_partialpres", temperature_C=600,
                             pressure_bar=40, catalyst_mass_kg=100, n_tubes=50, feed_kmol_h={"NH3": 100.0},
                             particle_density_kg_m3=1651.8, particle_diameter_m=1e-4)
    txt = build_kinetic_reactor_input(i)
    assert "CBASIS=PARTIALPRES" in txt and 'PRES-UNIT="N/sqm"' in txt


def test_partialpres_refuses_non_molarity_entry():
    with pytest.raises(ValueError):
        resolve_spec("ru_kum_temkin_pyzhev", "lhhw_partialpres")


def test_correct_cracker_block_entry_idempotent():
    fr = {"blocks": {"CRACKER": {"id": "CRACKER", "block_type": "RGibbs", "duty_kW": 10.0,
                                 "outlet_temperature_C": 1.0, "outlet_pressure_bar": 1.0, "details": {}}}}
    ko = {"cracker_outlet": {"T_C": 572.0, "P_bar": 20.2}, "rplug": {"duty": 10.0}}
    a = correct_cracker_block_entry(fr, ko)
    b = correct_cracker_block_entry(json.loads(json.dumps(a)), ko)
    assert a == b
    c = a["blocks"]["CRACKER"]
    assert c["block_type"] == "RPlug" and c["outlet_temperature_C"] == 572.0 and c["outlet_pressure_bar"] == 20.2
    assert c["duty_kW"] == 10.0


def test_stored_integrated_cases_label_cracker_as_rplug():
    files = sorted(AK.glob("ci_*.json")) + sorted(AK.glob("ki_*.json"))
    assert files
    for f in files:
        a = json.loads(f.read_text(encoding="utf-8"))["aspen"]
        cr = a["flowsheet_result"]["blocks"]["CRACKER"]
        assert cr["block_type"] == "RPlug", f.name
        assert cr["outlet_temperature_C"] == a["cracker_outlet"]["T_C"]
        assert cr["duty_kW"] == pytest.approx(a["rplug"]["duty"])


def test_validity_classification():
    d = json.loads((KIN / "validity_classification.json").read_text(encoding="utf-8"))
    by = {r["catalyst"]: r for r in d["laws"]}
    for c in ["Ni/MgO", "Ru/MgO", "Ru/Al2O3", "5Ni1Ru/CeO2", "2.5Ni0.5Ru/CeO2", "Ni/CeO2", "Ru/CeO2", "Ru-K/CaO"]:
        assert c in by
        assert by[c]["class"] in d["classes"]
        assert by[c]["experimental_validation"] is False
    assert d["counts"]["validated_at_relevant_conditions"] == 0
    assert by["Ni/MgO"]["class"] == by["Ru/MgO"]["class"] == "extrapolated"
    for c in ["Ni/CeO2", "Ru/CeO2", "Ru-K/CaO"]:
        assert by[c]["class"] == "unmodelled"
    for r in d["laws"]:
        if r["class"] != "unmodelled":
            fr = r["fitted_range"]
            assert len(fr["T_C"]) == 2 and len(fr["P_bar"]) == 2 and fr["P_bar"][1] < 20.0
            assert r["domain_warning"]["pressure_extrapolated_at_20_bar"] is True


def test_classification_rule():
    m = _script("kinetics_validity_classification")
    law = {"literature_comparisons": [{"id": "x", "status": "pass", "observed": 0, "tolerance": 1, "P_bar": 20.0,
                                       "T_C": [500, 600], "comparison_uses_fitting_data": False}]}
    assert m.classify(law)[0] == "validated_at_relevant_conditions"
    law["literature_comparisons"][0]["P_bar"] = 1.0
    assert m.classify(law)[0] == "validated_against_literature"
    law["literature_comparisons"][0]["status"] = "fail"
    assert m.classify(law)[0] == "extrapolated"


@pytest.mark.parametrize("name", ["kinetics", "aspen_kinetic"])
def test_every_item_has_evidence_kind(name):
    items = json.loads((VAL / f"{name}.json").read_text(encoding="utf-8"))
    kinds = {"numerical_verification", "python_vs_aspen", "literature_comparison"}
    assert items and all(i.get("evidence_kind") in kinds for i in items)


def test_original_failures_kept_with_same_tolerance():
    k = {i["id"]: i for i in json.loads((VAL / "kinetics.json").read_text(encoding="utf-8"))}
    for i, obs in (("EXISTING-KIN-NI-PRED", 0.1096), ("EXISTING-KIN-RU-PRED", 0.1113)):
        assert k[i]["status"] == "fail" and k[i]["tolerance"] == 0.05
        assert k[i]["observed"] == pytest.approx(obs, abs=1e-4)
    a = {i["id"]: i for i in json.loads((VAL / "aspen_kinetic.json").read_text(encoding="utf-8"))}
    for cid in LUC + ["ru_takahashi_microkinetic"]:
        it = a[f"cat_{cid}_below_equilibrium"]
        assert it["status"] == "fail" and it["tolerance"] == 1e-4
        assert f"k1p2_{cid}_below_equilibrium_cause" in a


def test_equilibrium_cause_is_quantitative():
    d = json.loads((KIN / "equilibrium_consistency.json").read_text(encoding="utf-8"))
    fails = [r for r in d["rows"] if r["fails_1e-4_check"]]
    assert fails
    for r in fails:
        # the RPLUG outlet sits where the Aspen driving force (ideal-gas K, basis-specific Z) vanishes
        assert abs(r["rplug_minus_predicted_stop"]) < 2e-5
        assert r["K_phi_PR"] > 1.0


def test_takahashi_reimplementation_matches_stored():
    d = json.loads((KIN / "takahashi_rederivation.json").read_text(encoding="utf-8"))
    for cid in ("ni_takahashi_microkinetic", "ru_takahashi_microkinetic"):
        r = d["results"][cid]
        assert r["A_reproduces_stored_validation_max_abs_diff"] < 1e-6
        assert min(v["max_abs_deviation"] for v in r.values() if isinstance(v, dict)) > 0.05
