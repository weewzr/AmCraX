"""Tests for amcrax.scenarios."""
from __future__ import annotations

import pytest

from amcrax import paths
from amcrax.optimisation import evaluate_result
from amcrax.scenarios import compare, flat_table, load_definitions, nh3_price_for_origin
from amcrax.schemas import SimulationResult


@pytest.fixture(scope="module")
def comp():
    return compare()


def test_all_scenarios_present(comp):
    ids = {s["id"] for s in load_definitions()["process_scenarios"]}
    assert {r["id"] for r in comp["rows"]} == ids


def test_reproduces_stored_aspen_kpis_exactly(comp):
    n = 0
    for r in comp["rows"]:
        p = paths.RESULTS_SIMULATIONS / f"{r['id']}.json"
        if not p.exists():
            continue
        s = SimulationResult.model_validate_json(p.read_text(encoding="utf-8"))
        if not s.status.converged:
            continue
        n += 1
        assert r["source"] == "aspen_plus_v15"
        assert r["stored_kpis"] == s.kpis.model_dump()
        for k in ("lhv_efficiency", "nh3_conversion", "h2_yield_overall", "net_fuel_heat_deficit_kW",
                  "total_external_heating_kW", "specific_heat_demand_kWh_per_kgH2", "h2_product_kg_h"):
            assert r["metrics"][k] == getattr(s.kpis, k)
        m = evaluate_result(s, nh3_price_USD_per_t=comp["settings"]["nh3_price"]["price_USD_per_t"])
        assert r["metrics"]["lcoh_USD_per_kg"] == m["lcoh_USD_per_kg"]
    assert n >= 1


def test_aspen_minus_python_and_deltas(comp):
    base = next(r for r in comp["rows"] if r["id"] == "baseline")
    assert all(v == 0 for v in base["delta_vs_baseline"].values() if v is not None)
    for r in comp["rows"]:
        if r["aspen_minus_python"] is not None:
            k = "lcoh_USD_per_kg"
            assert r["aspen_minus_python"][k] == pytest.approx(r["metrics"][k] - r["python_metrics"][k], abs=1e-12)


def test_low_pressure_has_compression(comp):
    lp = next(r for r in comp["rows"] if r["id"] == "scn_low_pressure")
    assert lp["metrics"]["compression_power_kW"] > 0


def test_price_policy():
    assert nh3_price_for_origin("blue")["price_basis"].startswith("base price kept")
    g = nh3_price_for_origin("green")
    assert g["price_USD_per_t"] != nh3_price_for_origin("grey")["price_USD_per_t"]
    assert "cho2026nickel" in g["price_source"]
    assert nh3_price_for_origin("green", "base")["price_USD_per_t"] == nh3_price_for_origin("grey")["price_USD_per_t"]


def test_overlays_and_flat(comp):
    base = next(r for r in comp["rows"] if r["id"] == "baseline")
    assert len(base["overlays"]) == 9
    rows = flat_table(comp)
    assert len(rows) == len(comp["rows"]) and "lcoh_USD_per_kg__aspen_minus_python" in rows[0]


def test_deterministic():
    a, b = compare(["scn_low_temperature"], overlays=False), compare(["scn_low_temperature"], overlays=False)
    assert [r["metrics"] for r in a["rows"]] == [r["metrics"] for r in b["rows"]]
