"""Phase 2 task X1: exchanger sizing and cost module (deterministic, no network, no Aspen)."""
import json
import math
from pathlib import Path

import pytest

from amcrax.heat_integration import exchanger as hx

ROOT = Path(__file__).resolve().parents[1]


def test_lmtd_and_equal_ends():
    assert hx.lmtd(50.0, 50.0) == 50.0
    assert hx.lmtd(150.0, 50.0) == pytest.approx(100.0 / math.log(3.0))
    with pytest.raises(ValueError):
        hx.lmtd(-1.0, 10.0)


def test_f_single_shell_closed_form():
    s = math.sqrt(5.0)
    ref = s * math.log((2 / 3) / (1 / 3)) / math.log((2 - (3 - s) / 3) / (2 - (3 + s) / 3))
    assert hx.f_correction(200.0, 100.0, 50.0, 100.0, 1) == pytest.approx(ref, rel=1e-12)


def test_f_multishell_increases_and_cross_needs_shells():
    # AmCraX baseline FEHE: temperature cross, one 1-2 shell infeasible
    args = (600.0, 228.38, 75.9, 550.0)
    assert hx.f_correction(*args, 1) is None
    n, f = hx.shells_needed(*args)
    assert n >= 2 and f >= hx.F_MIN
    assert hx.f_correction(*args, n + 1) > f


def test_turton_hand_value_and_escalation():
    c = hx.turton_cost(100.0, 0.0, "CS/CS", cepci_target=397.0)
    assert c["Cp0_per_unit_USD_2001"] == pytest.approx(10 ** (4.3247 - 0.3030 * 2 + 0.1634 * 4), rel=1e-12)
    assert c["F_BM"] == pytest.approx(1.63 + 1.66)
    c2 = hx.turton_cost(100.0, 0.0, "CS/CS", cepci_target=794.0)
    assert c2["installed_USD"] == pytest.approx(2.0 * c["installed_USD"], rel=1e-12)


def test_turton_split_above_range():
    c = hx.turton_cost(2500.0)
    assert c["n_units"] == 3 and c["area_per_unit_m2"] == pytest.approx(2500.0 / 3)


def test_size_and_cost_api_and_sgd():
    r = hx.size_and_cost(612.2, 600.0, 228.4, 75.9, 550.0, "central")
    for k in ("area_m2", "n_shells", "F", "purchase_USD", "installed_USD", "tci_equivalent_USD", "purchase_SGD",
              "annualised_USD_per_yr", "U_source"):
        assert k in r
    assert r["tci_equivalent_SGD"] == pytest.approx(r["tci_equivalent_USD"] * 1.288444, rel=1e-9)
    assert r["area_m2"] == pytest.approx(r["ua_kW_K"] * 1000.0 / (r["U_W_m2K"] * r["F"]))
    lo = hx.size_and_cost(612.2, 600.0, 228.4, 75.9, 550.0, "low")
    hi = hx.size_and_cost(612.2, 600.0, 228.4, 75.9, 550.0, "high")
    assert lo["area_m2"] > r["area_m2"] > hi["area_m2"]
    cc = hx.size_and_cost(612.2, 600.0, 228.4, 75.9, 550.0, "central", counter_current=True)
    assert cc["F"] == 1.0 and cc["tci_equivalent_USD"] < r["tci_equivalent_USD"]


def test_annual_charge_matches_singapore_fixed_opex_formula():
    # CRF 0.1101681 + (0.03 * 1.25 + 0.015) * 1.06
    assert hx.annual_charge_factor() == pytest.approx(0.11016807219 + (0.03 * 1.25 + 0.015) * 1.06, rel=1e-9)
    assert hx.capital_for_annual(hx.annualised_cost(1e6)) == pytest.approx(1e6)


def test_breakeven_U_inverts_cost():
    tci = hx.size_and_cost(612.2, 600.0, 228.4, 75.9, 550.0, 20.0)["tci_equivalent_USD"]
    u = hx.breakeven_U(612.2, 600.0, 228.4, 75.9, 550.0, tci)
    assert u == pytest.approx(20.0, rel=1e-6)


def test_u_cases_sourced_or_labelled():
    for k, v in hx.U_CASES.items():
        assert v["source_type"] and v["source"]
    assert hx.U_CASES["low"]["U_W_m2K"] < hx.U_CASES["central"]["U_W_m2K"] < hx.U_CASES["high"]["U_W_m2K"]


def test_stored_results_consistent():
    p = ROOT / "results/research/heat_exchanger/heat_exchanger_study.json"
    if not p.exists():
        pytest.skip("study not generated")
    d = json.loads(p.read_text(encoding="utf-8"))
    b = d["baseline"]
    assert b["lcoh_hi_USD_per_kg"] == pytest.approx(4.015461254695034, abs=1e-9)   # frozen reference basis
    assert b["saving_USD_per_kg"] == pytest.approx(0.2138, abs=5e-4)
    assert "H3-d" in d["row_evidence"]
    v = json.loads((ROOT / "results/research/validation/heat_exchanger.json").read_text(encoding="utf-8"))
    assert all(i["evidence_kind"] in ("numerical_verification", "python_vs_aspen", "literature_comparison") for i in v)
    diag = json.loads((ROOT / "results/research/heat_exchanger/fehe_duty_diagnosis.json").read_text(encoding="utf-8"))
    for r in diag["rows"]:
        assert r["state_effect_kW"] + r["property_effect_kW"] == pytest.approx(r["difference_kW"], abs=1e-6)
