"""Model and code fixes of the Phase 2 fix pass (docs/internal/phase2_fix_plan.md section 4).

- fuel-efficiency envelope of the frozen baseline (review C M1) and the fired-cracking threshold shift;
- Sobol first-order estimator on centred outputs (review C m1): total-effect indices unchanged;
- membrane annualised with the capital recovery factor at the membrane life (review C m2);
- break-even capital recovery factor solved (review C M3);
- CEPCI labels (review C m5) and the superseded rates in catalyst_prices.json (review C m9).
Deterministic, no network, no Aspen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from amcrax.economics.lcoh import crf  # noqa: E402
from amcrax.economics.reference import load_reference_scenario  # noqa: E402
from amcrax.enduse import power_activity  # noqa: E402
from amcrax.heat_integration import exchanger as hx  # noqa: E402
from amcrax.uq.sobol import indices_from_outputs, ishigami, ishigami_analytic, sobol_base  # noqa: E402

RES = ROOT / "results" / "research"
FROZEN_LCOH = 4.015461254695034


def _j(rel):
    return json.loads((RES / rel).read_text(encoding="utf-8"))


# ---- fuel efficiency (C-M1) -------------------------------------------------------------------
def test_baseline_frozen_and_fuel_efficiency_envelope():
    b = _j("reference_scenario/baseline.json")
    assert abs(b["lcoh_USD_per_kg"] - FROZEN_LCOH) < 1e-9
    fe = b["fuel_efficiency_sensitivity"]
    cases = {c["fuel_efficiency"]: c for c in fe["cases"]}
    assert set(cases) == {1.0, round(fe["flowsheet_tailgas_ratio_exact"], 4), 0.85}
    assert abs(cases[1.0]["lcoh_USD_per_kg"] - FROZEN_LCOH) < 1e-12
    assert fe["flowsheet_tailgas_ratio_exact"] == pytest.approx(0.9225, abs=5e-5)
    lc = [c["lcoh_USD_per_kg"] for c in fe["cases"]]
    assert lc == sorted(lc)  # less heat per kg fuel: dearer
    assert cases[0.85]["lcoh_USD_per_kg"] == pytest.approx(4.063, abs=5e-4)
    assert cases[0.9225]["lcoh_USD_per_kg"] == pytest.approx(4.038, abs=5e-4)
    # the extra cost is the heat-fuel term only: heat fuel scales as 1/eta
    assert cases[0.85]["heat_fuel_USD_per_kg"] == pytest.approx(cases[1.0]["heat_fuel_USD_per_kg"] / 0.85, rel=1e-12)
    be = [c["breakeven_nh3_USD_per_t_vs_marker"] for c in fe["cases"]]
    assert be == sorted(be, reverse=True)


def test_enduse_default_unchanged_and_fired_threshold_shift():
    for k in ("full_fired", "full_purified", "blend_purified"):
        y = 0.4 if k == "blend_purified" else None
        assert power_activity(k, y).efficiency == power_activity(k, y, heat_fuel_efficiency=1.0).efficiency
    assert power_activity("full_fired", heat_fuel_efficiency=0.85).efficiency < power_activity("full_fired").efficiency
    assert power_activity("full_exhaust", heat_fuel_efficiency=0.85).efficiency == power_activity("full_exhaust").efficiency
    with pytest.raises(ValueError):
        power_activity("full_fired", heat_fuel_efficiency=0.0)
    tt = _j("enduse/turbine_threshold.json")
    blk = tt["cracker_heat_fuel_efficiency_sensitivity"]
    t = [c["full_fired"]["threshold_delta_fuel_pp_vs_direct_turbine"] for c in blk["cases"]]
    assert t[0] == pytest.approx(tt["thresholds"]["full_fired"]["threshold_delta_pp_reference"], abs=1e-6)
    assert t == sorted(t) and t[-1] > t[0]


# ---- Sobol centring (C-m1) --------------------------------------------------------------------
def test_sobol_centred_first_order_same_expectation_lower_variance():
    A, B = sobol_base(2 ** 12, 3, 7)
    to_x = lambda u: -np.pi + 2 * np.pi * u  # noqa: E731
    fA, fB = ishigami(to_x(A)), ishigami(to_x(B))
    fAB = np.stack([ishigami(to_x(np.where(np.arange(3) == i, B, A))) for i in range(3)])
    S, ST, V = indices_from_outputs(fA, fB, fAB)
    S_shift, ST_shift, _ = indices_from_outputs(fA + 100.0, fB + 100.0, fAB + 100.0)
    # centring makes S invariant to an output shift (the uncentred form was not); ST uses differences only
    assert np.allclose(S, S_shift, atol=1e-9) and np.allclose(ST, ST_shift, atol=1e-12)
    an = ishigami_analytic()
    assert np.allclose(S, an["S"], atol=0.02) and np.allclose(ST, an["ST"], atol=0.02)


def test_stored_total_effect_indices_unchanged_by_centring():
    """ST is computed from differences only; the stored file must still carry the ST bootstrap intervals."""
    re_ = _j("uq/row_evidence.json")["row_evidence"]["H2-a"]["numbers"]["sobol_nh3_price_lcoh_HIon"]["grey"]
    assert re_["ST"] == pytest.approx(0.896, abs=1e-3)
    lo, hi = re_["S1_ci"]
    assert hi - lo < 0.1  # centred estimator: interval about [0.870, 0.921] (was [0.66, 1.13])


# ---- membrane annualisation (C-m2) ------------------------------------------------------------
def test_membrane_annualised_with_crf_at_membrane_life():
    sys.path.insert(0, str(ROOT / "scripts" / "research"))
    import purification_study as ps  # noqa: E402
    r = load_reference_scenario()
    assert ps.mem_crf(3.0) == pytest.approx(crf(r.discount_rate, 3.0), rel=1e-15)
    assert ps.mem_crf(3.0) == pytest.approx(0.40211, abs=1e-5)
    study = _j("purification/purification_study.json")
    cfg = next(c for c in study["cases"]["20bar_baseline"]["configs"] if c["id"] == "MEM_1bar_polish")
    named = cfg["costs"]["fuel_cell_grade_D"]["annual_named_items_USD"]["membrane_replacement"]
    expected = cfg["area_m2"] * ps.MEM_EUR_PER_M2 * ps.EURUSD_PARITY * crf(r.discount_rate, ps.MEM_LIFE_Y)
    assert named == pytest.approx(expected, rel=1e-12)


def test_parity_recoveries_after_crf_fix():
    pc = _j("purification/phase2_comparison.json")["specs"]
    assert pc["fuel_cell_grade_D"]["thresholds"]["psa_recovery_at_parity_with_central_membrane"] == pytest.approx(0.783, abs=1e-3)
    assert pc["industrial_99.9"]["thresholds"]["psa_recovery_at_parity_with_central_membrane"] == pytest.approx(0.795, abs=1e-3)
    assert pc["fuel_cell_grade_D"]["configurations"]["MEM_central"]["lcoh_usd_per_kg_usable"] == pytest.approx(4.353, abs=1e-3)


# ---- break-even CRF (C-M3) and labels (C-m5, C-m9) --------------------------------------------
def test_breakeven_crf_solved():
    h = _j("heat_exchanger/heat_exchanger_study.json")
    be = h["row_evidence"]["H3-d"]["breakeven_crf_solved"]
    assert be["low"] == pytest.approx(0.186, abs=1e-3)
    assert be["central"] == pytest.approx(0.223, abs=1e-3)
    assert be["high"] == pytest.approx(0.244, abs=1e-3)
    tci = h["baseline"]["sizing_turton"]["low"]["tci_equivalent_USD"]
    saving_yr = 1e6
    c = hx.breakeven_crf(saving_yr, tci)
    assert hx.annualised_cost(tci, c) == pytest.approx(saving_yr, rel=1e-12)


def test_cepci_and_fx_labels():
    assert "proxy" in hx.CEPCI["target_2024_central"]["label"]
    assert "not a 2024 index" in hx.CEPCI["target_2024_low"]["label"]
    cp = json.loads((ROOT / "research" / "data" / "catalyst_prices.json").read_text(encoding="utf-8"))
    assert cp["fx"]["status"].startswith("Superseded for conversion; kept as the value used when the prices were gathered")
    key = _j("catalyst_economics/catalyst_economics.json")["findings"]["energy_and_cost"]["key_descriptions"]
    assert "MIS-NAMED" in key["fixed_inventory_aspen_HI_exchanger"]
