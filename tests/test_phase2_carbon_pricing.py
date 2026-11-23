"""Phase 2 C3: carbon pricing (actual Singapore boundary and hypothetical life-cycle price). Deterministic, no Aspen."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from amcrax.economics import carbon_pricing as cp
from amcrax.economics import singapore
from amcrax.economics.reference import load_reference_scenario

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "results" / "simulations" / "baseline.json").read_text(encoding="utf-8"))
OUT = ROOT / "results" / "research" / "carbon_pricing"


def test_frozen_default_unchanged():
    e = singapore.evaluate(BASE)
    assert e["lcoh_USD_per_kg"] == pytest.approx(4.015461254695034, abs=1e-9)
    assert e["breakdown_USD_per_kg"]["carbon_tax"] == 0.0


def test_policy_matches_sourced_file():
    j = json.loads((ROOT / "research" / "data" / "carbon_policy_sg.json").read_text(encoding="utf-8"))
    facts = {f["id"]: f for f in j["facts"]}
    assert facts["rate_2019_2023"]["value"] == cp.legislated_rate_SGD(2023)
    assert facts["rate_2024_2025"]["value"] == cp.legislated_rate_SGD(2025)
    assert facts["rate_2026_onward"]["value"] == cp.legislated_rate_SGD(2026) == cp.legislated_rate_SGD(2035)
    assert facts["threshold_taxable"]["value"] == cp.POLICY["threshold_tCO2e_per_yr"]
    assert facts["gases_covered"]["value"]["N2O"] == cp.POLICY["gwp"]["N2O"] == 265


def test_mode_a_is_zero_for_self_firing_and_route_independent():
    for r in ("grey", "blue", "green_current"):
        c = cp.route_case(BASE, r, "actual_sg")
        assert c["carbon_cost_USD_per_kg"] == 0.0 and not c["hypothetical"]
        assert c["lcoh_USD_per_kg"] == pytest.approx(singapore.evaluate(BASE, r)["lcoh_USD_per_kg"], abs=1e-12)
    ab = cp.actual_boundary(BASE)
    assert ab["liable"] is False and ab["direct_tCO2e_per_yr"] == 0.0


def test_mode_a_threshold_with_n2o():
    tt = cp.n2o_threshold_test(BASE, singapore.evaluate(BASE))
    below = cp.actual_boundary(BASE, n2o_kg_per_h=0.99 * tt["n2o_needed_kg_per_h"])
    above = cp.actual_boundary(BASE, n2o_kg_per_h=1.01 * tt["n2o_needed_kg_per_h"])
    assert not below["liable"] and below["carbon_tax_USD_per_kg"] == 0.0
    assert above["liable"] and above["carbon_tax_USD_per_kg"] > 0.0
    fx = load_reference_scenario().fx_SGD_per_USD
    exp = above["n2o_tCO2e_per_yr"] * 45.0 / fx / above["econ"]["annual_h2_kg"]
    assert above["carbon_tax_USD_per_kg"] == pytest.approx(exp, rel=1e-12)


def test_mode_b_replaces_not_adds():
    e = singapore.evaluate(BASE, "grey", {"heat_fuel": "natural_gas", "apply_threshold": False})
    assert e["breakdown_USD_per_kg"]["carbon_tax"] > 0
    c = cp.carbon_cost(e, 10.0, "hypothetical_lca", 100.0)
    fx = e["fx_SGD_per_USD"]
    assert c["lcoh_USD_per_kg"] == pytest.approx(e["lcoh_USD_per_kg"] - e["breakdown_USD_per_kg"]["carbon_tax"] + 100 * 10 / 1000 / fx, abs=1e-12)
    assert "HYPOTHETICAL" in c["label"] and "not Singapore law" in c["label"] and c["hypothetical"]


def test_mode_b_zero_price_equals_mode_a():
    for r in ("grey", "blue", "green_2030"):
        a = cp.route_case(BASE, r, "actual_sg")
        b = cp.route_case(BASE, r, "hypothetical_lca", 0.0)
        assert b["lcoh_USD_per_kg"] == pytest.approx(a["lcoh_USD_per_kg"], abs=1e-12)
        assert b["npv_USD"] == pytest.approx(a["npv_USD"], rel=1e-12)


def test_negative_price_rejected():
    with pytest.raises(ValueError):
        cp.carbon_cost(singapore.evaluate(BASE), 1.0, "hypothetical_lca", -1.0)


def test_crossover_closed_form_and_sweep_consistency():
    fx = load_reference_scenario().fx_SGD_per_USD
    P = cp.crossover_price(4.3, 9.0, 4.0, 19.5, fx)
    assert 4.3 + P * 9.0 / 1000 / fx == pytest.approx(4.0 + P * 19.5 / 1000 / fx, abs=1e-12)
    assert cp.crossover_price(4.0, 9.0, 4.3, 19.5, fx) == 0.0
    assert cp.crossover_price(4.3, 20.0, 4.0, 19.5, fx) is None


def test_ci_reproduces_lca_results():
    lca = json.loads((ROOT / "results" / "research" / "lca" / "lca_results.json").read_text(encoding="utf-8"))
    by = {r["route"]: r for r in lca["routes"]}
    x = cp.ci_inputs_from_result(BASE)
    for r in ("grey", "blue", "green"):
        ef = cp.route_gate_ef(r)["central"]
        assert cp.carbon_intensity_h2(x, ef)["total_kgCO2e_per_kgH2"] == pytest.approx(by[r]["H2_kgCO2e_per_kg"], rel=1e-9)


def test_vectors_round_trip():
    v = json.loads((OUT / "test_vectors.json").read_text(encoding="utf-8"))
    assert len(v["vectors"]) >= 12
    for t in v["vectors"]:
        i = t["inputs"]
        if t["function"] == "carbonIntensity":
            fac = cp.CIFactors(**i["factors"])
            got = cp.carbon_intensity_h2(i["x"], i["nh3_ef_kg_per_kg"], i["heating"], i["distance_km"], fac)
            assert got["total_kgCO2e_per_kgH2"] == pytest.approx(t["expected"]["total_kgCO2e_per_kgH2"], rel=1e-9)
        elif t["function"] == "carbonCost":
            got = cp.carbon_cost(i["econ"], i["ci_total_kgCO2e_per_kgH2"], i["mode"], i["price_SGD_per_t"])
            for k in ("USD_per_kg_H2", "SGD_per_kg_H2", "lcoh_USD_per_kg", "lcoh_SGD_per_kg"):
                assert got[k] == pytest.approx(t["expected"][k], rel=1e-9, abs=1e-12)
        else:
            got = cp.crossover_price(i["lcoh_a"], i["ci_a"], i["lcoh_b"], i["ci_b"], i["fx"])
            assert got == pytest.approx(t["expected"], rel=1e-9)


def test_validation_file_has_no_failures_and_evidence_kinds():
    v = json.loads((ROOT / "results" / "research" / "validation" / "carbon_pricing.json").read_text(encoding="utf-8"))
    kinds = {"numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation"}
    assert all(i["evidence_kind"] in kinds for i in v["items"])
    assert v["summary"]["fail"] == 0
    assert not any(i["evidence_kind"] == "experimental_validation" and i["status"] == "pass" for i in v["items"])


def test_outputs_label_hypothetical_and_privacy():
    for name in ("scenarios.json", "thresholds.json", "site_summary.json", "row_evidence.json", "feed_dominance.json",
                 "carbon_intensity.json", "test_vectors.json"):
        txt = (OUT / name).read_text(encoding="utf-8")
        assert "Users\\\\" not in txt and "C:\\\\" not in txt and "@" not in txt.replace("@{", "")
    s = json.loads((OUT / "scenarios.json").read_text(encoding="utf-8"))
    for c in s["cases"]:
        if c["mode"] == "hypothetical_lca":
            assert c["hypothetical"] and "not Singapore law" in c["label"]
    re_ = json.loads((OUT / "row_evidence.json").read_text(encoding="utf-8"))["row_evidence"]
    assert {"H2-a", "H2-b", "H2-c", "H2-d", "H2-e_mode_A_actual_policy", "H2-e_mode_B_hypothetical_conditional"} <= set(re_)


def test_eu_ets_conversion():
    assert cp.eu_ets_SGD_per_t() == pytest.approx(90.0 * 1.0990 * 1.288444, rel=1e-12)
    assert math.isfinite(cp.eu_ets_SGD_per_t())
