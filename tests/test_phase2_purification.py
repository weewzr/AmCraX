"""Phase 2 task D2: PSA against Pd-Ag membrane on the unified basis (deterministic, no network, no Aspen)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "results/research/purification/phase2_comparison.json"
VAL = ROOT / "results/research/validation/purification.json"
LIT = ROOT / "research/data/purification_literature.json"
FX = 1.288444


@pytest.fixture(scope="module")
def comp():
    if not COMP.exists():
        pytest.skip("run scripts/research/purification_phase2.py first")
    return json.loads(COMP.read_text(encoding="utf-8"))


def test_reference_basis_frozen(comp):
    assert comp["basis"]["baseline_lcoh_usd"] == pytest.approx(4.015, abs=5e-4)
    assert comp["basis"]["fx_SGD_per_USD"] == FX
    assert comp["basis"]["nh3_price_USD_per_t"] == 450.0


def test_every_configuration_has_sgd_trl_and_inputs(comp):
    for spec in ("industrial_99.9", "fuel_cell_grade_D"):
        cfgs = comp["specs"][spec]["configurations"]
        assert {"PSA_low_recovery", "PSA_central_recovery", "PSA_high_recovery", "MEM_cost_low", "MEM_central",
                "MEM_cost_high"} <= set(cfgs)
        for d in cfgs.values():
            assert d["readiness"]["trl"]
            assert d["lcoh_usd_per_kg_usable"] is not None
            assert d["lcoh_sgd_per_kg_usable"] == pytest.approx(d["lcoh_usd_per_kg_usable"] * FX, rel=1e-12)
            assert d["meets_spec_within_model_scope"]


def test_inputs_are_sourced_and_labelled(comp):
    I = comp["inputs"]
    assert I["psa_recovery"]["fuel_cell_grade_D"]["low"]["value"] == 0.555
    assert "DIFFERENT FEED" in I["psa_recovery"]["fuel_cell_grade_D"]["low"]["note"]
    assert I["membrane_cost_USD_per_m2"]["low"]["value"] == pytest.approx(6800 * 1.099, rel=1e-9)
    assert I["membrane_cost_USD_per_m2"]["high"]["value"] == 15000.0
    assert I["membrane_selectivity_H2_N2"]["low"]["value"] == pytest.approx(1.5e-6 / 3.7e-11, rel=1e-12)
    for k in ("ideal", "new", "trace NH3"):
        assert k.lower() in I["membrane_selectivity_H2_N2"]["caveats"].lower()


def test_ranking_not_claimed_robust_when_it_reverses(comp):
    for spec in ("industrial_99.9", "fuel_cell_grade_D"):
        fs = comp["specs"][spec]["factorial_summary"]
        lo, hi = fs["psa_minus_membrane_range_usd"]
        assert fs["ranking_robust"] == (lo > 0 or hi < 0)
        th = comp["specs"][spec]["thresholds"]
        r = th["psa_recovery_at_parity_with_central_membrane"]
        assert 0.555 < r < 0.85  # the parity recovery lies between the sourced pessimistic point and the assumption


def test_selectivity_requirement_reported_against_source(comp):
    s = comp["specs"]["fuel_cell_grade_D"]["thresholds"]["selectivity"]
    assert s["required_alpha_H2_N2"] == pytest.approx(12919, rel=2e-3)
    assert s["sourced_low"] > s["required_alpha_H2_N2"]
    assert "no numeric selectivity" not in comp["selectivity_statement"]["phase2"]


def test_row_evidence_block(comp):
    re_ = comp["row_evidence"]
    assert set(re_) == {"H4-a", "H4-b", "H4-c", "H4-d", "H4-e"}
    for row in re_.values():
        for k in ("proposed_verdict", "numbers", "assumptions", "uncertainty", "envelope", "threshold", "reason"):
            assert k in row
    assert re_["H4-a"]["proposed_verdict"] == "INCONCLUSIVE"
    assert re_["H4-d"]["proposed_verdict"] == "INCONCLUSIVE"


def test_h4e_threshold_is_physical(comp):
    r = comp["tradeoff"]["psa_recovery_where_tail_heat_equals_furnace_demand"]
    assert 0.6 < r < 0.85


def test_validation_items_have_kind_and_none_fail():
    if not VAL.exists():
        pytest.skip("no validation file")
    items = json.loads(VAL.read_text(encoding="utf-8"))
    kinds = {"numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation"}
    assert all(i["evidence_kind"] in kinds for i in items)
    assert not [i for i in items if i["evidence_kind"] == "experimental_validation"]
    assert not [i["id"] for i in items if i["status"] == "fail"]
    assert any(i["id"].startswith("P2-") for i in items) and any(i["id"] == "P-MB-1" for i in items)


def test_cechetto_correction_recorded():
    d = json.loads(LIT.read_text(encoding="utf-8"))
    p03 = next(e for e in d["entries"] if e["id"] == "P03")
    assert p03["value"] == 3.7e-11
    assert "CORRECTED" in p03["verbatim_or_derived"]


def test_no_private_paths_in_outputs():
    for f in (COMP, VAL, ROOT / "scripts/research/purification_phase2.py"):
        if f.exists():
            t = f.read_text(encoding="utf-8")
            # No absolute user path of any kind (no account name is written here on purpose).
            assert "Users\\" not in t and "Users/" not in t and "/home/" not in t
