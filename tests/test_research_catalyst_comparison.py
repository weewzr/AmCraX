"""Workstream H: catalyst comparison coupled to heat integration (amcrax.research.catalyst_comparison)."""
import json
import math
from pathlib import Path

import pytest

from amcrax.research import catalyst_comparison as cc
from amcrax.schemas import SimulationResult

ROOT = Path(__file__).resolve().parents[1]


def test_kinetic_flowsheet_holds_conversion_and_closes_balances():
    r = cc.kinetic_flowsheet(550.0, 20.0, 0.95, True)
    assert r.kpis.nh3_conversion == pytest.approx(0.95, abs=1e-9)
    assert abs(r.balances.energy_closure_rel) < 1e-6
    assert abs(r.balances.mass_closure_rel) < 1e-5


def test_kinetic_flowsheet_refuses_conversion_above_equilibrium():
    with pytest.raises(ValueError):
        cc.kinetic_flowsheet(480.0, 20.0, 0.95, True)  # X_eq(480 C, 20 bar) < 0.95


def test_heat_accounting_reproduces_baseline_pinch_import():
    base = SimulationResult.model_validate(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8")))
    h = cc.heat_accounting(base, 20.0)
    assert h["external_heat_import_kW"] == pytest.approx(752.6, abs=0.1)


def test_required_mass_decreases_with_temperature_and_nan_below_equilibrium():
    cid = "ru_kum_temkin_pyzhev"
    w1, w2 = cc.required_mass_kg(cid, 520.0, 20.0, 0.95), cc.required_mass_kg(cid, 560.0, 20.0, 0.95)
    assert w1 > w2 > 0
    assert math.isnan(cc.required_mass_kg(cid, 480.0, 20.0, 0.95))


def test_kinetic_factor_scales_mass_inversely():
    cid = "nire_ceo2_5ni1ru_lucentini_lhhw"
    a = cc.lcoh_curve(cid, [600.0])
    b = cc.lcoh_curve(cid, [600.0], kinetic_factor=4.0)
    assert b[0]["W_kg"] == pytest.approx(a[0]["W_kg"] / 4.0, rel=1e-12)


def test_catalyst_cost_added_analytically_matches_full_evaluation():
    cid = "ru_takahashi_microkinetic"
    c = cc.lcoh_curve(cid, [560.0])[0]
    d = cc.design_point(cid, 560.0, 20.0, 0.95, W_kg=c["W_kg"])
    assert c["lcoh_USD_per_kg"] == pytest.approx(d["lcoh_USD_per_kg"], abs=1e-9)
    assert d["breakdown_USD_per_kg"]["catalyst"] == pytest.approx(
        c["W_kg"] * cc.CATALYSTS[cid]["price"] / cc.CATALYST_LIFETIME_YR / d["annual_h2_kg"], rel=1e-9)


def test_supplementary_fuel_from_fired_duty():
    h = {"external_heat_import_kW": 100.0, "reactor_duty_kW": 1000.0, "preheat_duty_kW": 0.0}
    f = cc.fired_duty(h, furnace_efficiency=0.5, loss_fraction=0.02)
    assert f["fired_process_duty_kW"] == pytest.approx(120.0)
    assert f["furnace_fuel_LHV_kW"] == pytest.approx(240.0)
    assert f["supplementary_fuel_needed"]


def test_no_heat_integration_needs_more_fired_heat():
    a = cc.design_point("ni_takahashi_microkinetic", 600.0, 20.0, 0.95, heat_integration=True, W_kg=85.0)
    b = cc.design_point("ni_takahashi_microkinetic", 600.0, 20.0, 0.95, heat_integration=False, W_kg=85.0)
    assert b["fired_process_duty_kW"] > a["fired_process_duty_kW"]
    assert b["lcoh_USD_per_kg"] > a["lcoh_USD_per_kg"]
    assert a["h2_product_kg_h"] == pytest.approx(b["h2_product_kg_h"], rel=1e-9)
