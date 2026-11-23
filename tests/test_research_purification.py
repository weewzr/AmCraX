"""Tests for workstream P (hydrogen purification): ISO 14687 evaluation, PSA relation, membrane with leakage."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from amcrax.separation.membrane import permeance, sieverts_flux
from amcrax.separation.purification import (GRADES, closure, evaluate_product, membrane_area_for_recovery,
                                            membrane_with_leakage, pinch_recovery, psa_recovery_at_purity, psa_split,
                                            psa_tail_h2_fraction_from_point, required_selectivity)

ROOT = Path(__file__).resolve().parents[1]
FEED = {"NH3": 1.91512572, "H2": 146.827311, "N2": 48.9424371, "H2O": 0.2}  # Aspen baseline S7, test input
T = 673.15


def test_grade_d_values():
    g = GRADES["D"]
    assert g["index_min_pct"] == 99.97 and g["total_non_h2_max_ppm"] == 300.0
    assert g["limits_ppm"]["NH3"] == 0.1 and g["limits_ppm"]["N2"] == 300.0 and g["limits_ppm"]["H2O"] == 5.0
    assert GRADES["B"]["index_min_pct"] == 99.9


def test_evaluate_separates_purity_and_contaminants():
    # overall index 99.98 % passes but NH3 at 0.5 ppm fails the individual limit
    ev = evaluate_product({"NH3": 0.5, "N2": 150.0, "H2O": 1.0}, "D")
    by = {c["item"]: c for c in ev["checks"]}
    assert by["hydrogen fuel index"]["pass"] and by["total non-hydrogen gases (modelled species)"]["pass"]
    assert not by["NH3"]["pass"]
    assert not ev["meets_within_model_scope"]
    assert "O2" in ev["not_evaluated"] and "CO" in ev["not_evaluated"]


def test_pass_still_lists_unmodelled():
    ev = evaluate_product({"NH3": 0.05, "N2": 200.0, "H2O": 2.0}, "D")
    assert ev["meets_within_model_scope"]
    assert ev["not_evaluated"]  # never empty: unmodelled contaminants are always reported


def test_raw_cracked_gas_fails_everything():
    ppm = {sp: 1e6 * FEED[sp] / sum(FEED.values()) for sp in ("NH3", "N2", "H2O")}
    for g in ("D", "B", "E3"):
        assert not evaluate_product(ppm, g)["meets_within_model_scope"]


def test_psa_relation_reproduces_anchor_and_closes():
    yt = psa_tail_h2_fraction_from_point(FEED, 0.756, 0.9911)
    assert psa_recovery_at_purity(FEED, 0.9911, yt) == pytest.approx(0.756, abs=1e-9)
    prod, tail = psa_split(FEED, 0.756, 0.9911)
    assert closure(FEED, [prod, tail])["max_abs_rel_error"] < 1e-12
    # higher purity never raises recovery in the relation
    assert psa_recovery_at_purity(FEED, 0.9998, yt) <= psa_recovery_at_purity(FEED, 0.99, yt)


def test_sieverts_hand_calculation():
    k = 4.57e-8 * math.exp(-9230.0 / (8.314462618 * T)) / 5.2e-6
    assert permeance(T) == pytest.approx(k, rel=1e-6)
    J = k * ((0.7 * 20e5) ** 0.5 - (1e5) ** 0.5)
    assert sieverts_flux(0.7 * 20e5, 1e5, permeance(T)) == pytest.approx(J, rel=1e-6)


def test_membrane_area_and_pinch():
    P, Pp = 19.5, 1.0
    rmax = pinch_recovery(FEED, P, Pp)
    assert 0.9 < rmax < 1.0
    A = membrane_area_for_recovery(FEED, 0.9, P, Pp, T)
    m = membrane_with_leakage(FEED, A, P, Pp, T)
    assert m["h2_recovery"] == pytest.approx(0.9, abs=1e-6)
    assert m["n2_in_permeate_ppm"] == 0.0  # infinite selectivity
    assert membrane_area_for_recovery(FEED, rmax + 1e-3, P, Pp, T) is None
    big = membrane_with_leakage(FEED, 1e6, P, Pp, T)
    assert big["h2_recovery"] == pytest.approx(rmax, abs=1e-4)


def test_membrane_leakage_and_required_selectivity():
    P, Pp = 19.5, 1.0
    A = membrane_area_for_recovery(FEED, 0.9, P, Pp, T)
    ppm = [membrane_with_leakage(FEED, A, P, Pp, T, alpha_H2_N2=a)["n2_in_permeate_ppm"] for a in (1e2, 1e3, 1e4)]
    assert ppm[0] > ppm[1] > ppm[2] > 0
    a = required_selectivity(FEED, A, P, Pp, T, 300.0)
    assert a is not None
    assert membrane_with_leakage(FEED, A, P, Pp, T, alpha_H2_N2=a)["n2_in_permeate_ppm"] == pytest.approx(300.0, rel=1e-3)


def test_membrane_balance_closes():
    A = membrane_area_for_recovery(FEED, 0.8, 19.5, 1.0, T)
    m = membrane_with_leakage(FEED, A, 19.5, 1.0, T, alpha_H2_N2=5000.0)
    assert closure(FEED, [m["permeate_kmol_h"], {k: v for k, v in m["retentate_kmol_h"].items()}])["max_abs_rel_error"] < 1e-6


def test_study_outputs_if_present():
    f = ROOT / "results/research/validation/purification.json"
    if not f.exists():
        pytest.skip("run scripts/research/purification_study.py first")
    items = json.loads(f.read_text(encoding="utf-8"))
    assert items and all(i["status"] in ("pass", "fail", "informational") for i in items)
    assert not [i["id"] for i in items if i["status"] == "fail"]
    study = json.loads((ROOT / "results/research/purification/purification_study.json").read_text(encoding="utf-8"))
    for case in study["cases"].values():
        for c in case["configs"]:
            assert c["closure"]["max_abs_rel_error"] < 1e-9
            assert c["spec_evaluation"]["D"]["not_evaluated"]
    # the baseline PSA product is not called fuel-cell grade
    base = next(c for c in study["cases"]["20bar_baseline"]["configs"] if c["id"] == "PSA_AMCRAX")
    assert not base["spec_evaluation"]["D"]["meets_within_model_scope"]
