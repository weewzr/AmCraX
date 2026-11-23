"""Hand-calculation tests for amcrax.economics.singapore (workstream E)."""
from __future__ import annotations

import json
import math

import pytest

from amcrax import paths
from amcrax.economics import compute_lcoh
from amcrax.economics.singapore import (breakeven_nh3_price, default_electricity_USD_per_kWh, evaluate, extract_summary,
                                        load_singapore_data)
from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, SimulationResult

SUMMARY = {"case_id": "hand", "source": "python_model", "h2_kg_h": 100.0, "nh3_feed_kmol_h": 50.0, "heat_deficit_kW": 0.0,
           "cooling_kW": 0.0, "pump_kW": 0.0, "h2_cracked_kmol_h": None, "psa_recovery": None, "tailgas_lhv_kW": None,
           "tailgas_heat_kW": None}


def _crf(i, n):
    return i * (1 + i) ** n / ((1 + i) ** n - 1)


EQ = {"capex_mode": "equipment"}  # Phase 1 Farokhi feed-scaled method (superseded; still selectable)


def test_equipment_capex_hand_calc():
    e = evaluate(SUMMARY, 450, EQ)
    assert e["capex"]["total_capex_USD"] == pytest.approx(1702e3 * (50 / 500) ** 0.8 * 5.93, rel=1e-12)


def test_lcoh_hand_calc_no_heat_no_power():
    e = evaluate(SUMMARY, 450, EQ)
    capex = 1702e3 * (50 / 500) ** 0.8 * 5.93
    h = 8000.0
    maint, ins, lab = 0.03 * capex, 0.015 * capex, 109756.0
    fixed = (maint + ins + lab + 0.25 * (lab + maint)) * 1.06
    feed = 50 * MOLAR_MASS["NH3"] * 0.450 * h
    m_cat = 50 * 1000 * 22.414 * 1000 / 9000 / 1000
    cat = m_cat * 33.4 / 2.0
    expected = (capex * _crf(0.10, 25) + fixed + feed + cat) / (100 * h)
    assert e["lcoh_USD_per_kg"] == pytest.approx(expected, rel=1e-12)
    assert e["rec_USD_per_kg"] == pytest.approx(expected - feed / (100 * h), rel=1e-12)
    assert e["breakdown_USD_per_kg"]["carbon_tax"] == 0.0
    assert sum(e["breakdown_USD_per_kg"].values()) == pytest.approx(e["lcoh_USD_per_kg"], rel=1e-12)


def test_ammonia_fuel_has_no_direct_co2_and_no_tax():
    e = evaluate({**SUMMARY, "heat_deficit_kW": 1000.0}, 450, {"carbon_tax_SGD_per_t": 80.0})
    assert e["direct_emissions_tCO2e_per_yr"] == 0.0
    assert e["breakdown_USD_per_kg"]["carbon_tax"] == 0.0
    fuel_kg_h = 1000.0 / LHV_KJ_PER_MOL["NH3"] * 3600.0 * MOLAR_MASS["NH3"] / 1000.0
    assert e["kg_nh3_fuel_per_kg_h2"] == pytest.approx(fuel_kg_h / 100.0, rel=1e-12)


def test_carbon_tax_gas_heat_threshold_and_rate():
    s = {**SUMMARY, "heat_deficit_kW": 1000.0}
    gj = 1000.0 * 3600.0 / 1e6 * 8000.0            # 28,800 GJ/yr
    t_co2 = gj * 56.1 / 1000.0                      # 1,615.7 t
    below = evaluate(s, 450, {"heat_fuel": "natural_gas"})
    assert below["direct_emissions_tCO2e_per_yr"] == pytest.approx(t_co2)
    assert below["carbon_tax_liable"] is False and below["breakdown_USD_per_kg"]["carbon_tax"] == 0.0
    above = evaluate(s, 450, {"heat_fuel": "natural_gas", "apply_threshold": False})
    from amcrax.economics.reference import load_reference_scenario
    fx = load_reference_scenario().fx_SGD_per_USD
    assert above["breakdown_USD_per_kg"]["carbon_tax"] == pytest.approx(t_co2 * 45.0 / fx / (100 * 8000.0), rel=1e-12)
    other = evaluate(s, 450, {"heat_fuel": "natural_gas", "other_facility_emissions_tCO2e": 24000.0})
    assert other["carbon_tax_liable"] is True      # 24,000 + 1,615.7 >= 25,000


def test_npv_identity_and_breakeven():
    e = evaluate(SUMMARY, 450, {"h2_price_USD_per_kg": 6.0})
    annual = 100 * 8000.0
    assert e["npv_USD"] == pytest.approx((6.0 - e["lcoh_USD_per_kg"]) * annual / _crf(0.10, 25), rel=1e-9)
    assert e["irr"] is not None and e["irr"] > 0.10
    p = breakeven_nh3_price(SUMMARY, 5.0)
    assert evaluate(SUMMARY, p)["lcoh_USD_per_kg"] == pytest.approx(5.0, rel=1e-12)
    assert evaluate(SUMMARY, 450)["landed_cost_USD_per_kg"] is None
    assert evaluate(SUMMARY, 450, {"transport_USD_per_kg_H2": 1.0})["landed_cost_USD_per_kg"] == pytest.approx(
        evaluate(SUMMARY, 450)["lcoh_USD_per_kg"] + 1.0)


def test_capacity_scaling_and_recovery():
    a, b = evaluate(SUMMARY, 450), evaluate(SUMMARY, 450, {"capacity_scale": 2.0})  # reference method, all items on feed
    assert b["capex"]["total_capex_USD"] == pytest.approx(a["capex"]["total_capex_USD"] * 2 ** 0.8, rel=1e-12)
    assert b["annual_h2_kg"] == pytest.approx(2 * a["annual_h2_kg"])
    s = {**SUMMARY, "h2_cracked_kmol_h": 150.0, "psa_recovery": 0.8, "tailgas_lhv_kW": 1000.0, "tailgas_heat_kW": 900.0, "heat_deficit_kW": 500.0}
    r = evaluate(s, 450, {"psa_recovery": 0.9})
    assert r["h2_product_kg_h"] == pytest.approx(150.0 * 0.9 * MOLAR_MASS["H2"])


def test_electricity_default_derivation():
    d = load_singapore_data()
    usep = d["electricity"]["usep_2025_monthly_SGD_per_MWh"]["value"]
    sgd = sum(usep) / 12 / 1000 + 0.0610 + 0.0031
    from amcrax.economics.reference import load_reference_scenario
    fx = load_reference_scenario().fx_SGD_per_USD   # Phase 2: one FX in the reference scenario (was 1.290)
    assert default_electricity_USD_per_kWh() == pytest.approx(sgd / fx, rel=1e-12)


def test_legacy_mode_reproduces_stored_lcoh():
    path = paths.ROOT / "results" / "simulations" / "baseline.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    e = evaluate(d, 450, {"capex_mode": "legacy", "electricity_price_USD_per_kWh": 0.084})
    old = compute_lcoh(SimulationResult.model_validate(d))
    assert e["lcoh_USD_per_kg"] == pytest.approx(old.lcoh_USD_per_kg, rel=1e-12)
    assert e["lcoh_USD_per_kg"] == pytest.approx(3.918842228473241, rel=1e-9)
    # SimulationResult and dict inputs agree
    assert extract_summary(SimulationResult.model_validate(d))["h2_kg_h"] == extract_summary(d)["h2_kg_h"]


def test_unknown_override_rejected():
    with pytest.raises(KeyError):
        evaluate(SUMMARY, "grey", {"not_a_key": 1})
    assert math.isfinite(evaluate(SUMMARY, "green_2030")["lcoh_USD_per_kg"])
