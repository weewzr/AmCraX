"""Phase 2 addendum of 24 November 2026: three papers read in full (Halim et al. 2025; Abdoos et al. 2025; Sayas et al.
2020). The new computed comparisons are recomputed here from the model and checked against the stored values; the frozen
baseline, the coded rules' inputs and every verdict are checked unchanged. Deterministic, no network, no Aspen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts" / "research"))

from amcrax.economics.singapore import breakeven_nh3_price, evaluate  # noqa: E402
from amcrax.enduse import params as P  # noqa: E402

RES = ROOT / "results" / "research"
FROZEN_LCOH = 4.015461254695034
S, I, C, M, PS = "SUPPORTED", "INCONCLUSIVE", "CONTRADICTED", "MIXED", "PARTIALLY SUPPORTED"


def _j(rel):
    return json.loads((RES / rel).read_text(encoding="utf-8"))


def _sim(name):
    return json.loads((ROOT / "results" / "simulations" / name).read_text(encoding="utf-8"))


# ---- 2c baseline sensitivity to PSA recovery ---------------------------------------------------
def test_baseline_frozen_and_psa_recovery_sensitivity():
    b = _j("reference_scenario/baseline.json")
    assert abs(b["lcoh_USD_per_kg"] - FROZEN_LCOH) <= 1e-12
    blk = b["psa_recovery_sensitivity"]
    assert blk["reference_lcoh_USD_per_kg"] == b["lcoh_USD_per_kg"]
    cases = {c["psa_recovery"]: c for c in blk["cases"]}
    assert set(cases) == {0.85, 0.8192, 0.7744}
    hi = _sim("baseline.json")
    for R, c in cases.items():
        x = evaluate(hi, "grey", {"psa_recovery": R})
        assert c["lcoh_USD_per_kg"] == pytest.approx(x["lcoh_USD_per_kg"], rel=1e-12)
        assert c["npv_USD"] == pytest.approx(x["npv_USD"], rel=1e-12)
        assert c["breakeven_nh3_USD_per_t_vs_marker"] == pytest.approx(
            breakeven_nh3_price(hi, blk["h2_selling_price_USD_per_kg"], {"psa_recovery": R}), rel=1e-12)
    assert abs(cases[0.85]["lcoh_USD_per_kg"] - FROZEN_LCOH) < 1e-7   # override path reproduces the stored reference
    lc = [cases[R]["lcoh_USD_per_kg"] for R in (0.85, 0.8192, 0.7744)]
    be = [cases[R]["breakeven_nh3_USD_per_t_vs_marker"] for R in (0.85, 0.8192, 0.7744)]
    assert lc == sorted(lc) and be == sorted(be, reverse=True)
    assert cases[0.8192]["lcoh_USD_per_kg"] == pytest.approx(4.0658, abs=5e-4)
    assert cases[0.7744]["lcoh_USD_per_kg"] == pytest.approx(4.1461, abs=5e-4)
    # the fuel-efficiency envelope is untouched
    assert b["fuel_efficiency_sensitivity"]["cases"][0]["lcoh_USD_per_kg"] == pytest.approx(FROZEN_LCOH, abs=1e-12)


# ---- 2a H1-b on the paper's own basis -----------------------------------------------------------
def test_h1b_fuel_cost_gap_on_paper_basis():
    tt = _j("enduse/turbine_threshold.json")
    ff = tt["forty_percent_figure"]
    fb = ff["fuel_cost_gap_on_paper_basis"]
    assert fb["lhv_MJ_per_kg"]["NH3"] == pytest.approx(P.LHV_NH3_MJ_KG, rel=1e-15)
    assert fb["lhv_MJ_per_kg"]["H2"] == pytest.approx(P.LHV_H2_MJ_KG, rel=1e-15)
    k = P.LHV_H2_MJ_KG / P.LHV_NH3_MJ_KG
    res = {"on": _sim("baseline.json"), "off": _sim("baseline_no_hi.json")}
    seen = set()
    for c in fb["cases"]:
        e = evaluate(res[c["heat_integration"]], c["NH3_USD_per_t"])
        gap = 100.0 * (1.0 - c["NH3_USD_per_t"] / 1000.0 * k / e["lcoh_USD_per_kg"])
        assert c["gap_pct_1_minus_direct_over_cracked"] == pytest.approx(gap, rel=1e-12)
        seen.add((c["price_case"], c["heat_integration"]))
    for pc in ("grey", "blue", "green_2050", "green_2030", "green_current", "halim_green_FOB", "halim_blue_FOB"):
        assert (pc, "on") in seen and (pc, "off") in seen
    g = {(c["price_case"], c["heat_integration"]): c["gap_pct_1_minus_direct_over_cracked"] for c in fb["cases"]}
    assert g[("grey", "on")] == pytest.approx(27.73, abs=0.01)
    assert g[("halim_green_FOB", "on")] == pytest.approx(20.38, abs=0.01)
    assert g[("halim_blue_FOB", "on")] == pytest.approx(29.36, abs=0.01)
    # same direction as the paper, smaller gap; heat integration off widens it
    assert g[("halim_green_FOB", "on")] < 39 and g[("halim_blue_FOB", "on")] < 44
    assert all(g[(p, "off")] > g[(p, "on")] for p, _ in seen)
    # reconciliation closes on the paper's printed figures (printed integers; LHV basis 18.60 against 18.737)
    for kk, printed in (("green", 39), ("blue", 44)):
        r = fb["reconciliation"][kk]
        assert r["paper_gap_pct_printed"] == printed
        assert abs(r["steps"][-1]["gap_pct"] - printed) <= 1.0
        assert r["paper_energy_retained_as_h2_derived"] == pytest.approx(8579.9 / 12347.2, rel=1e-12)
        assert r["amcrax_energy_retained_as_h2"] == pytest.approx(0.877, abs=1e-3)
    # the existing cost-of-electricity comparison is kept as it was
    assert ff["largest_computed_pct"] == pytest.approx(16.634, abs=1e-3)
    assert "full text read" in ff["halim_status"].lower() and "not a cost of electricity" in ff["halim_status"].lower()


# ---- 2b PSA recovery from the published front ---------------------------------------------------
def test_abdoos_sourced_case():
    import purification_phase2 as p2
    pc = _j("purification/phase2_comparison.json")
    ab = pc["abdoos2025_sourced_case"]
    pts = {p["id"]: (p["purity"], p["recovery"], p["P_ads_bar"]) for p in ab["points"]}
    assert pts == {"P04": (0.9903, 0.8392, 7.87), "P03": (0.9995, 0.8192, 11.29), "P02": (0.9999, 0.7744, 11.6)}
    cv = p2.central_vals()
    for spec, d in ab["lcoh_by_specification"].items():
        for pid, x in d.items():
            assert x["lcoh_usd_per_kg_usable"] == pytest.approx(p2.lcoh_psa(spec, pts[pid][1], cv["elec"]), rel=1e-12)
    res = ab["model_resolution_USD_per_kg"]
    ce = _j("catalyst_economics/catalyst_economics.json")
    assert res == ce["resolution"]["max_abs_python_minus_aspen_lcoh_USD_per_kg"]
    inc = ab["equal_delivery_increment"]
    assert inc["abdoos2025_table8"]["increment"] > res and inc["abdoos2025_interpolated_at_modelled_purities"]["increment"] > res
    assert inc["psa_yanez_different_feed"]["increment"] > res
    assert inc["psa_mass_balance_assumption"]["increment"] < res
    assert inc["abdoos2025_table8"]["increment"] == pytest.approx(0.0803, abs=5e-4)
    # within the 3 point surrogate scatter the increment can change sign (reported, not hidden)
    sc = {(x["scatter_points"], x["direction"].split()[0]): x for x in ab["equal_delivery_increment_surrogate_scatter"]}
    assert sc[(0.01, "adverse")]["increment"] > res and sc[(0.03, "adverse")]["increment"] < 0
    assert sc[(0.03, "favourable")]["increment"] > inc["abdoos2025_table8"]["increment"]
    for x in sc.values():
        c30 = lambda spec, R: p2.ps.purification_cost(p2.psa_cfg(spec, R), p2.CASE, 30.0, elec=cv["elec"])["usd_per_kg_product_h2"]  # noqa: E731
        assert x["increment"] == pytest.approx(c30("fuel_cell_grade_D", x["grade_D_recovery"]) - c30("industrial_99.9", x["industrial_recovery"]), rel=1e-9)
    pos = ab["position"]
    gD = pos["grade_D"]
    assert gD["parity_recovery_high_cost_membrane"] < gD["abdoos_recovery"] < gD["parity_recovery_central_membrane"]
    assert pos["industrial"]["abdoos_recovery"] > max(pos["industrial"]["parity_recovery_central_membrane"],
                                                      pos["industrial"]["parity_recovery_high_cost_membrane"])
    fb = pos["furnace_balance"]
    assert fb["all_above"] and 0 < fb["grade_D_point_margin"] < 0.03
    assert fb["recovery_where_tail_heat_equals_furnace_demand"] == pytest.approx(0.765, abs=1e-3)
    # labelled case beside the existing ones: no existing input replaced, the coded rules read the same keys
    I_ = pc["inputs"]["psa_recovery"]
    assert I_["fuel_cell_grade_D"]["low"]["value"] == 0.555 and I_["fuel_cell_grade_D"]["high"]["value"] == 0.81
    assert I_["industrial_99.9"]["high"]["value"] == 0.85
    assert set(pc["row_evidence"]["H4-b"]["numbers"]["equal_delivery_increment"]) == {
        "psa_yanez_different_feed", "psa_mass_balance_assumption", "membrane_central"}
    for spec in p2.SPECS:
        names = set(pc["psa_recovery_sensitivity"]["points"][spec])
        assert {"assumption_0.85", "yanez_pessimistic", "mass_balance_central", "hansen_0.71", "mehr_0.81"} <= names
        assert {"abdoos2025_99.03", "abdoos2025_99.95", "abdoos2025_99.99"} <= names


# ---- 2d Sayas comparison points and the cross-catalyst caution ---------------------------------
def test_sayas_points_and_cross_catalyst_context():
    from amcrax.reactor.pfr import simulate_pfr
    kv = _j("kinetics/validity_classification.json")
    assert kv["counts"] == {"validated_at_relevant_conditions": 0, "validated_against_literature": 3, "extrapolated": 2, "unmodelled": 3}
    ruk = next(r for r in kv["laws"] if r["catalyst"] == "Ru-K/CaO")
    assert ruk["class"] == "unmodelled" and ruk["fitted_range"] is None
    assert "supplementary information" in ruk["reason"] and "nothing was" in ruk["reason"].lower()
    sp = kv["literature_comparison_points_sayas2020"]
    assert sp["used_by_any_model"] is False and sp["n_points"] == 15 == len(sp["points"])
    assert {p["P_bar"] for p in sp["points"]} == {10.0, 20.0, 40.0}
    by = {(p["P_bar"], p["T_C"]): p["X_measured"] for p in sp["points"]}
    assert by[(20.0, 500.0)] == pytest.approx(0.68) and by[(40.0, 550.0)] == pytest.approx(0.845)
    cx = kv["cross_catalyst_context_sayas2020"]
    assert "not a test" in cx["label"]
    case = cx["cases"][0]
    row = next(r for r in case["rows"] if r["P_bar"] == 20.0 and r["T_C"] == 500.0)
    X = simulate_pfr("ru_kum_temkin_pyzhev", case["W_RuAl2O3_kg_s_per_mol"], T_in_C=500.0, P_in_bar=20.0,
                     feed_kmol_h={"NH3": 3.6}, pressure_drop=False, n_points=2).outlet["conversion"]
    assert row["X_RuAl2O3_law_equal_Ru"] == pytest.approx(X, rel=1e-9)
    assert case["g_Ru_h_per_mol_NH3"] == pytest.approx(0.2 * 0.028 / (30e-3 * 60.0 / 22.414), rel=1e-12)
    assert all(x > row["X_measured_RuK_CaO"] + 0.2 for x in cx["headline_20bar_500C"]["X_RuAl2O3_law_equal_Ru"])


# ---- validation items --------------------------------------------------------------------------
@pytest.mark.parametrize("area, item, status", [
    ("enduse", "EU-P2-halim-fuel-basis", "informational"), ("enduse", "EU-P2-halim-reconcile", "pass"),
    ("purification", "P2-PSA-ABDOOS-1", "informational"), ("purification", "P2-PSA-ABDOOS-2", "informational"),
    ("purification", "P2-PSA-ABDOOS-3", "pass"), ("purification", "P2-PSA-ABDOOS-4", "informational"),
    ("purification", "P2-PSA-ABDOOS-BASELINE", "informational"),
    ("kinetics", "K1P2-SAYAS-POINTS", "informational"), ("kinetics", "K1P2-SAYAS-RUAL2O3-CONTEXT", "informational")])
def test_addendum_validation_items(area, item, status):
    items = {i["id"]: i for i in _j(f"validation/{area}.json")}
    assert item in items
    assert items[item]["status"] == status
    if status == "informational":
        assert items[item]["evidence_kind"] == "literature_comparison"


# ---- verdicts, record and references -----------------------------------------------------------
def test_verdicts_unchanged_and_addendum_recorded():
    m = _j("evidence_matrix.json")
    assert {h["id"]: h["verdict"] for h in m["hypotheses"]} == {"H1": I, "H2": M, "H3": PS, "H4": I}
    comps = {c["id"]: c["verdict"] for h in m["hypotheses"] for c in h["components"]}
    assert comps == {"H1-P": I, "H1-Q": I, "H2-E": PS, "H2-C": S, "H2-X": C, "H3-T": PS, "H3-H": I, "H3-K": I, "H4-B": I}
    rows = {r["row_id"]: r["verdict"] for h in m["hypotheses"] for r in h["rows"]}
    assert rows == {"H1-a": I, "H1-b": C, "H1-c": I, "H1-d": I, "H2-a": S, "H2-b": I, "H2-c": S, "H2-d": S, "H2-e": C,
                    "H3-a": S, "H3-b": I, "H3-c": I, "H3-d": I, "H3-e": I, "H3-f": I,
                    "H4-a": I, "H4-b": I, "H4-c": C, "H4-d": I, "H4-e": I}
    ad = _j("addendum_2026-11-24.json")
    assert ad["verdict_changes"] == [] and ad["verdicts_checked"] == 33
    assert ad["baseline_check"]["abs_difference"] <= 1e-12
    assert {x["key"] for x in ad["new_computed_blocks"]} >= {"psa_recovery_sensitivity", "abdoos2025_sourced_case",
                                                              "forty_percent_figure/fuel_cost_gap_on_paper_basis"}
    md = (ROOT / "docs" / "research" / "phase2_findings_changed.md").read_text(encoding="utf-8")
    assert "## Addendum after reading three papers in full (24 November 2026)" in md
    blob = json.dumps(m)
    for stale in ("full text was not accessible", "Only sourced slope", "Halim et al. 2025 (abstract only)",
                  "full text not obtained; values unverified", "Halim's inputs were not accessed"):
        assert stale not in blob, stale
    h1b = next(r for h in m["hypotheses"] for r in h["rows"] if r["row_id"] == "H1-b")
    assert any("paper's own basis" in x for x in h1b["numerical_conclusions"])


def test_one_reference_record_per_paper():
    adds = {}
    for p in sorted((ROOT / "research" / "reference_additions").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for r in (d if isinstance(d, list) else d.get("references") or d.get("entries") or []):
            adds.setdefault(r.get("citekey"), []).append(p.name)
    assert "halim2025ammoniapower" not in adds
    assert adds.get("abdoos2025psa") == ["phase2_fulltext_abdoos.json"]
    assert adds.get("sayas2020rukcao") == ["phase2_fulltext_sayas.json"]
    assert adds.get("halim2025ammonia") == ["phase2_fulltext_halim.json"]
    refs = {r["citekey"]: r for r in json.loads((ROOT / "research" / "references.json").read_text(encoding="utf-8"))}
    for k in ("halim2025ammonia", "sayas2020rukcao"):
        assert "read" in refs[k]["verification"] and "24 November 2026" in refs[k]["verification"]
