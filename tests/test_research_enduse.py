"""Tests for amcrax.enduse (workstream U): stoichiometry, energy balance, cost and CI consistency."""
from __future__ import annotations

import pytest

from amcrax.enduse import (alpha_of_cracked_share, breakeven_ef, carbon_intensity, cracked_share_for_h2_fraction,
                           h2_fraction_of_blend, hydrogen_activity, hydrogen_cost, power_activity, power_cost)
from amcrax.enduse import params as P
from amcrax.environmental import carbon_intensity as old_ci
from amcrax.enduse.pathways import load_result


@pytest.mark.parametrize("y", [0.1, 0.3, 0.45, 0.6, 0.73])
def test_blend_round_trip(y):
    f = cracked_share_for_h2_fraction(y, 0.97)
    assert h2_fraction_of_blend(f, 0.97) == pytest.approx(y, abs=1e-12)


def test_unreachable_fraction():
    with pytest.raises(ValueError):
        cracked_share_for_h2_fraction(0.75, 0.97)


@pytest.mark.parametrize("alpha,bypass", list(P.AHMAD_ALPHA_BYPASS.items())[:-1])
def test_matches_ahmad_bypass(alpha, bypass):
    from scipy.optimize import brentq
    if alpha == 0.0:
        return
    f = brentq(lambda f_: alpha_of_cracked_share(f_, 0.97) - alpha, 0, 1)
    assert f == pytest.approx(1 - bypass, abs=0.005)


def test_efficiency_bounds_and_energy():
    for kind, y in [("direct", None), ("partial_fired", 0.4), ("full_fired", None), ("full_purified", None), ("blend_purified", 0.4)]:
        a = power_activity(kind, y)
        assert 0 < a.efficiency < 1
        assert 3600.0 / (a.nh3_kg * P.LHV_NH3_MJ_KG) == pytest.approx(a.efficiency)


def test_direct_matches_ahmad_electricity():
    a = power_activity("direct")
    assert a.efficiency * P.LHV_NH3_MJ_KG == pytest.approx(P.ELEC_MJ_PER_KG_DIRECT)


def test_ahmad_lcoe_reproduction():
    c = power_cost(power_activity("direct"), 480.0, hours=7200.0)
    assert c["LCOE_USD_per_MWh"] / 1000 == pytest.approx(P.AHMAD_LCOE_2A, rel=0.01)


def test_fired_cracking_is_less_efficient_than_direct():
    d = power_activity("direct").efficiency
    assert power_activity("full_fired").efficiency < d
    assert power_activity("full_purified").efficiency < power_activity("full_fired").efficiency


def test_cost_linear_in_price():
    a = power_activity("full_purified")
    c1, c2, c3 = (power_cost(a, p)["LCOE_USD_per_MWh"] for p in (300, 600, 900))
    assert c2 - c1 == pytest.approx(c3 - c2, rel=1e-9)


def test_hydrogen_ci_reproduces_old_accounting():
    h = hydrogen_activity("baseline", "h", "", "")
    new = carbon_intensity(h, 1.16, 5000.0)["total"]
    old = old_ci(load_result("baseline"), "blue/self_firing").total_kgCO2e_per_kgH2
    assert new == pytest.approx(old, rel=1e-9)


def test_hydrogen_cost_matches_stored_lcoh():
    # The stored core result is the legacy correlation (superseded for research outputs, kept reproducible).
    legacy = hydrogen_cost("baseline", 450.0, electricity=0.084, capex_mode="legacy")
    assert legacy["USD_per_kg"] == pytest.approx(3.918842228, rel=1e-6)


def test_hydrogen_cost_default_is_the_reference_scenario():
    import json
    from pathlib import Path

    stored = json.loads((Path(__file__).resolve().parents[1] / "results" / "research" / "reference_scenario"
                         / "baseline.json").read_text(encoding="utf-8"))
    text = json.dumps(stored)
    value = hydrogen_cost("baseline", 450.0)["USD_per_kg"]
    assert f"{value:.4f}"[:5] in text  # the unified baseline LCOH (4.015 USD/kg) is the default basis


def test_breakeven_consistency():
    a = power_activity("direct")
    ef = breakeven_ef(a, 367.0, 5000.0)
    assert carbon_intensity(a, ef, 5000.0)["total"] == pytest.approx(367.0)


def test_no_is_not_in_co2e():
    a = power_activity("direct")
    assert a.no_kg and a.no_kg > 0
    zero = carbon_intensity(a, 0.0, 0.0, grid=0.0)["total"]
    assert zero == pytest.approx(a.n2o_kgCO2e)
