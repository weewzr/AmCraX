"""Phase 2 task C2: catalyst economics for H3 (amcrax.research.catalyst_economics). Deterministic, no network, no Aspen."""
import json
import math
from pathlib import Path

import pytest

from amcrax.economics.reference import load_reference_scenario, reference_capex
from amcrax.economics.singapore import evaluate
from amcrax.research import catalyst_comparison as cc
from amcrax.research import catalyst_economics as ce

ROOT = Path(__file__).resolve().parents[1]


def _synthetic(name, lcoh_ex_cat, W, p, L, H=2.0e6, capex=7.0e6, ops=None, T=550.0, i=0.10, n=25):
    cat = W * p / L / H
    ops = ops or {"heat_fuel": 0.30 * H, "electricity": 0.001 * H, "cooling_water": 0.001 * H, "fixed_opex": 0.28 * H}
    bd = {"capex": 0.42, "fixed_opex": 0.28, "ammonia_feed": 3.04, "heat_fuel": ops["heat_fuel"] / H,
          "electricity": ops["electricity"] / H, "cooling_water": ops["cooling_water"] / H, "catalyst": cat, "carbon_tax": 0.0}
    # shift capex so that the catalyst-free part equals lcoh_ex_cat exactly
    bd["capex"] += lcoh_ex_cat - (sum(bd.values()) - cat)
    annual = {k: v * H for k, v in bd.items()}
    f = i * (1 + i) ** n / ((1 + i) ** n - 1)
    return {"catalyst": name, "catalyst_id": name, "T_C": T, "W_kg": W, "lcoh_USD_per_kg": sum(bd.values()),
            "breakdown_USD_per_kg": bd, "annual_USD_per_yr": annual, "annual_h2_kg": H, "capex_total_USD": capex,
            "item_annualised_USD_per_kg": {"heat_exchangers": 0.05, "reactor": 0.02}, "discount_rate": i,
            "plant_life_yr": n, "crf": f, "fired_process_duty_kW": 500.0, "supplementary_nh3_kg_h": 100.0,
            "first_law_deficit_kW": 700.0, "catalyst_cost": ce.catalyst_cost(W, p, L, H)}


def test_derived_prices_recompute_price_file_and_low_is_metal_floor():
    for r in ce.price_table():
        for sc in cc.PRICE_SCENARIOS:
            assert r[sc]["USD_per_kg"] == pytest.approx(r[sc]["price_file_USD_per_kg"], abs=0.01)
        assert r["low"]["N_USD_per_kg"] == 0.0
    # hand: 8 wt% Ru at JM Nov 2026 spot + N 32.2
    assert ce.price("Ru/Al2O3", "central") == pytest.approx(0.08 * 59478.9 + 32.2, rel=1e-12)


def test_sgd_uses_reference_fx_and_eur_prices_use_reference_usd_per_eur():
    ref = load_reference_scenario()
    assert ce.FX == pytest.approx(1.288444, abs=1e-12)
    r = next(x for x in ce.price_table() if x["catalyst"] == "Ru/MgO")
    assert r["central"]["SGD_per_kg"] == pytest.approx(r["central"]["USD_per_kg"] * ref.fx_SGD_per_USD, rel=1e-12)
    c5 = next(x for x in ce.published_tea_prices() if x["id"] == "C5")
    assert c5["currency"] == "EUR" and c5["price_value"] == 143.0
    assert c5["USD_per_kg"] == pytest.approx(143.0 * 1.0990, rel=1e-12)
    assert c5["SGD_per_kg"] == pytest.approx(143.0 * 1.0990 * 1.288444, rel=1e-12)


def test_published_ru_tea_prices_are_below_ru_floor_and_kept_separate():
    c2 = next(x for x in ce.published_tea_prices() if x["id"] == "C2")
    assert c2["USD_per_kg"] == 542.0 and c2["below_Ru_metal_floor"] is True
    assert c2["Ru_metal_floor_USD_per_kg_USGS2025"] == pytest.approx(0.03 * 22184.0, rel=1e-12)
    # defaults of the comparison are the derived central prices; Cho prices only in the labelled case
    assert cc.CATALYSTS["ru_kum_temkin_pyzhev"]["price"] == pytest.approx(ce.price("Ru/Al2O3", "central"), abs=0.01)
    assert cc.PUBLISHED_TEA_PRICE["ru_kum_temkin_pyzhev"] == 542.0 and cc.PUBLISHED_TEA_PRICE[cc.REFERENCE_NI] == 33.4


def test_catalyst_cost_hand_calculation():
    c = ce.catalyst_cost(100.0, 3000.0, 2.0, 2.0e6)
    assert c["USD_per_kg_H2"] == pytest.approx(0.075, rel=1e-12)
    assert c["annual_USD_per_yr"] == pytest.approx(150000.0, rel=1e-12)
    assert c["SGD_per_kg_H2"] == pytest.approx(0.075 * 1.288444, rel=1e-12)


def test_breakeven_price_and_lifetime_hand_calculation():
    H = 2.0e6
    ref = _synthetic("ni", 4.02, 400.0, 37.0, 2.0)
    low = _synthetic("ru", 4.00, 40.0, 3000.0, 2.0)
    c = ce.compare(low, ref)
    margin = ref["lcoh_USD_per_kg"] - 4.00
    assert c["margin_for_low_T_catalyst_USD_per_kg"] == pytest.approx(margin, abs=1e-12)
    assert c["breakeven_price_fixed_design_USD_per_kg"] == pytest.approx(margin * 2.0 * H / 40.0, rel=1e-9)
    assert c["breakeven_lifetime_fixed_design_yr"] == pytest.approx(40.0 * 3000.0 / (margin * H), rel=1e-9)
    assert c["net_lcoh_delta_USD_per_kg"] == pytest.approx(low["lcoh_USD_per_kg"] - ref["lcoh_USD_per_kg"], abs=1e-12)
    assert c["decomposition_sum_check_USD_per_kg"] == pytest.approx(0.0, abs=1e-12)
    # at the break-even price the low design costs exactly the reference
    low_be = _synthetic("ru", 4.00, 40.0, c["breakeven_price_fixed_design_USD_per_kg"], 2.0)
    assert low_be["lcoh_USD_per_kg"] == pytest.approx(ref["lcoh_USD_per_kg"], abs=1e-12)


def test_no_breakeven_when_catalyst_free_cost_exceeds_reference():
    ref = _synthetic("ni", 4.00, 400.0, 37.0, 2.0)
    low = _synthetic("ru", 4.01, 40.0, 3000.0, 2.0)
    c = ce.compare(low, ref)
    assert c["breakeven_price_fixed_design_USD_per_kg"] is None
    assert c["breakeven_lifetime_fixed_design_yr"] is None


def test_npv_and_payback_hand_calculation():
    H, i, n = 2.0e6, 0.10, 25
    ref = _synthetic("ni", 4.02, 400.0, 37.0, 2.0, capex=7.0e6, ops={"heat_fuel": 0.30 * H, "electricity": 0.0,
                                                                   "cooling_water": 0.0, "fixed_opex": 0.28 * H})
    low = _synthetic("ru", 4.00, 40.0, 3000.0, 2.0, capex=7.1e6, ops={"heat_fuel": 0.25 * H, "electricity": 0.0,
                                                                    "cooling_water": 0.0, "fixed_opex": 0.28 * H})
    c = ce.compare(low, ref)
    S = 0.05 * H
    I0 = 0.1e6 + 40.0 * 3000.0 - 400.0 * 37.0
    a = (1 - (1 + i) ** -n) / i
    repl = sum((40.0 * 3000.0 - 400.0 * 37.0) * (1 + i) ** -(2.0 * k) for k in range(1, 13))  # years 2, 4, ..., 24
    assert c["incremental_investment_USD"] == pytest.approx(I0, rel=1e-12)
    assert c["annual_operating_saving_USD_per_yr"] == pytest.approx(S, rel=1e-9)
    assert c["npv_choose_low_USD"] == pytest.approx(-I0 + S * a - repl, rel=1e-9)
    s_net = S - (40.0 * 3000.0 - 400.0 * 37.0) / 2.0
    assert c["simple_payback_yr"] == pytest.approx(I0 / s_net, rel=1e-9)
    small = ce.compare(_synthetic("ru", 4.00, 40.0, 3000.0, 2.0, ops={"heat_fuel": 0.299 * H, "electricity": 0.0,
                                                                     "cooling_water": 0.0, "fixed_opex": 0.28 * H}), ref)
    assert small["simple_payback_yr"] is None   # saving below the smoothed replacement cost: never pays back
    assert c["npv_choose_low_smoothed_USD"] == pytest.approx(-(low["lcoh_USD_per_kg"] - ref["lcoh_USD_per_kg"]) * H / low["crf"], rel=1e-9)


def test_replacement_schedule_counts():
    assert ce._replacements_pv(1.0, 2.0, 0.0, 25) == pytest.approx(12.0)   # years 2..24
    assert ce._replacements_pv(1.0, 5.0, 0.0, 25) == pytest.approx(4.0)    # years 5..20 (25 = end of life)
    assert ce._replacements_pv(1.0, 1.0, 0.0, 25) == pytest.approx(24.0)


def test_exchanger_size_ratio_adds_exactly_the_fehe_tci():
    n = load_reference_scenario().nh3_feed_kmol_h
    base = reference_capex(n)
    r = ce.hx_size_ratio(1.5e6, n)
    cap = reference_capex(n, item_size_ratio={"heat_exchangers": r})
    assert cap["total_capex_USD"] - base["total_capex_USD"] == pytest.approx(1.5e6, rel=1e-9)
    assert ce.hx_size_ratio(0.0, n) == pytest.approx(base["size_ratio"]["heat_exchangers"], rel=1e-12)


def test_frozen_default_evaluate_unchanged():
    e = evaluate(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8")), "grey")
    assert e["lcoh_USD_per_kg"] == pytest.approx(4.015461254695034, abs=1e-9)


def test_kinetic_validity_labels():
    ni = cc.kinetic_validity(cc.REFERENCE_NI, 20.0)
    assert ni["kinetic_validity_class"] == "extrapolated" and ni["kinetic_result_label"] == "extrapolation"
    ru = cc.kinetic_validity("ru_kum_temkin_pyzhev", 20.0)
    assert ru["kinetic_validity_class"] == "validated_against_literature" and ru["kinetic_pressure_extrapolated"]
    lab = ce.kinetics_label("ru_kum_temkin_pyzhev", cc.REFERENCE_NI)
    assert lab["rests_on_extrapolated_law"] and lab["result_label"] == "extrapolation"
    assert not ce.kinetics_label("ru_kum_temkin_pyzhev", "nire_ceo2_5ni1ru_lucentini_lhhw")["rests_on_extrapolated_law"]


def test_design_catalyst_item_matches_hand_value():
    d = ce.design(cc.REFERENCE_NI, 560.0, 36.79, 2.0, W_kg=200.0, mode="exchanger")
    assert d["breakdown_USD_per_kg"]["catalyst"] == pytest.approx(200.0 * 36.79 / 2.0 / d["annual_h2_kg"], rel=1e-12)
    assert d["fehe"]["tci_equivalent_USD"] > 0


def test_stored_results_carry_evidence_kind_and_row_evidence():
    v = ROOT / "results/research/validation/catalyst_economics.json"
    r = ROOT / "results/research/catalyst_economics/catalyst_economics.json"
    if not (v.exists() and r.exists()):
        pytest.skip("results not generated")
    items = json.loads(v.read_text(encoding="utf-8"))
    kinds = {"numerical_verification", "python_vs_aspen", "literature_comparison"}
    assert items and all(i["evidence_kind"] in kinds for i in items)
    res = json.loads(r.read_text(encoding="utf-8"))
    assert set(res["row_evidence"]) == {"H3-a", "H3-b", "H3-c", "H3-e", "H3-f"}
    for k, e in res["row_evidence"].items():
        assert {"proposed_verdict", "numbers", "assumptions", "uncertainty", "envelope", "reason"} <= set(e)
    cv = json.loads((ROOT / "results/research/validation/catalyst_comparison.json").read_text(encoding="utf-8"))
    assert all("evidence_kind" in i for i in cv)
