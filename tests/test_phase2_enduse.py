"""Phase 2 H1 end-use (task E2): optional turbine-efficiency and capital arguments, thresholds, no double counting."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from scipy.optimize import brentq

from amcrax.enduse import params as P
from amcrax.enduse import pathways as pw
from amcrax.enduse import power_activity, power_cost

ROOT = Path(__file__).resolve().parents[1]
STORED = {r["id"]: r for r in json.loads((ROOT / "results/research/enduse/enduse_results.json").read_text(encoding="utf-8"))["power_pathways"]}


@pytest.mark.parametrize("pid,kind,y", [("direct", "direct", None), ("full_fired", "full_fired", None), ("full_purified", "full_purified", None),
                                        ("full_exhaust", "full_exhaust", None), ("partial_exhaust_40", "partial_exhaust", 0.4)])
def test_defaults_unchanged(pid, kind, y):
    assert power_cost(power_activity(kind, y), 450.0)["LCOE_USD_per_MWh"] == pytest.approx(STORED[pid]["cost_USD_per_MWh_at_450"], rel=1e-9)


def test_unified_numbers():
    d = power_cost(power_activity("direct"), 450.0)["LCOE_USD_per_MWh"]
    assert d == pytest.approx(258.9, abs=0.05)
    for k, v in (("full_fired", 280.1), ("full_purified", 310.2), ("full_exhaust", 255.6)):
        assert power_cost(power_activity(k), 450.0)["LCOE_USD_per_MWh"] == pytest.approx(v, abs=0.05)


def test_eta_default_and_monotonic():
    assert power_activity("full_fired", eta_h2_fuel=P.ETA_GT_GAS).efficiency == pytest.approx(power_activity("full_fired").efficiency, abs=1e-15)
    lo = power_cost(power_activity("full_purified", eta_h2_fuel=0.50), 450.0)["LCOE_USD_per_MWh"]
    hi = power_cost(power_activity("full_purified", eta_h2_fuel=0.60), 450.0)["LCOE_USD_per_MWh"]
    assert hi < lo


def test_exhaust_not_double_counted():
    for e in (0.3, 0.7):
        a = power_activity("full_exhaust", eta_h2_fuel=e)
        assert a.efficiency * P.LHV_NH3_MJ_KG == pytest.approx(0.54 * 18.8, abs=1e-12)
    implied = P.ELEC_MJ_PER_KG_FULL / pw.fuel_lhv_mj_per_kg_nh3_fed(1.0, pw.load_cracker("baseline").conversion)
    assert implied < P.ETA_GT_GAS   # exhaust heat goes to the cracker, not the steam cycle


def test_capex_factors_neutral_at_one():
    a = power_activity("full_fired")
    base = power_cost(a, 450.0)["LCOE_USD_per_MWh"]
    assert power_cost(a, 450.0, cracker_capex_factor=1.0, plant_capex_factor=1.0, extra_capex_USD_per_kW=0.0)["LCOE_USD_per_MWh"] == base
    assert power_cost(a, 450.0, cracker_capex_factor=2.0)["LCOE_USD_per_MWh"] > base


def test_stored_threshold_reproduces():
    th = json.loads((ROOT / "results/research/enduse/turbine_threshold.json").read_text(encoding="utf-8"))["thresholds"]
    d = power_cost(power_activity("direct"), 450.0)["LCOE_USD_per_MWh"]
    e = brentq(lambda x: power_cost(power_activity("full_purified", eta_h2_fuel=x), 450.0)["LCOE_USD_per_MWh"] - d, 0.3, 0.95, xtol=1e-12)
    assert (e - P.ETA_GT_GAS) * 100 == pytest.approx(th["full_purified"]["threshold_delta_pp_reference"], abs=1e-6)
    assert th["full_purified"]["threshold_delta_pp_reference"] > 7.3   # above the NETL pure-H2 upper bound


def test_validation_items_have_evidence_kind():
    items = json.loads((ROOT / "results/research/validation/enduse.json").read_text(encoding="utf-8"))
    kinds = {"numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation"}
    assert all(i.get("evidence_kind") in kinds for i in items)
    assert not any(i["evidence_kind"] == "experimental_validation" for i in items)
    assert not [i["id"] for i in items if i["status"] == "fail"]


def test_tax_uses_cpa_gwp():
    rows = STORED["direct"]
    assert rows["N2O_kgCO2e_per_MWh_CPA_GWP265"] == pytest.approx(rows["N2O_kgCO2e_per_MWh"] * 265 / 273, rel=1e-12)
