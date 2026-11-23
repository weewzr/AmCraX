"""Phase 2 task C1: the unified techno-economic reference scenario is the single basis of every research cost path.

Deterministic; no network, no Aspen. Result-file tests read the regenerated results/research outputs.
"""
from __future__ import annotations

import hashlib
import json
import re

import pytest
import yaml

from amcrax import paths
from amcrax.economics import compute_lcoh
from amcrax.economics.reference import (DATA_FILE, load_reference_scenario, provenance_stamp, reference_capex,
                                        reference_catalyst_mass_kg, reference_item_costs)
from amcrax.economics.singapore import default_electricity_USD_per_kWh, evaluate, extract_summary
from amcrax.schemas import SimulationResult

ROOT = paths.ROOT
RES = ROOT / "results" / "research"
REL = 1e-6


def _j(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _baseline_result() -> dict:
    return _j("results/simulations/baseline.json")


# ------------------------------------------------------------------------------------------ loader
def test_loader_typed_cached_and_hashed():
    a, b = load_reference_scenario(), load_reference_scenario()
    assert a is b
    assert a.sha256 == hashlib.sha256(DATA_FILE.read_bytes()).hexdigest()
    assert a.capex_method == "cho2026_itemised_v1"
    for name in ("discount_rate", "plant_life_yr", "operating_hours_h_per_yr", "fx_SGD_per_USD", "electricity_USD_per_kWh"):
        assert isinstance(getattr(a, name), float)
    st = provenance_stamp()
    assert st["file"] == "backend/amcrax/data/reference_scenario.yaml" and st["sha256"] == a.sha256 and st["version"] == a.version


def test_every_entry_has_value_unit_source_type_source_note():
    raw = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8"))
    bad = []

    def walk(d, path):
        for k, v in d.items():
            if isinstance(v, dict) and "value" in v:
                missing = [f for f in ("value", "unit", "source_type", "source", "note") if f not in v]
                if missing:
                    bad.append((path + k, missing))
            elif isinstance(v, dict):
                walk(v, path + k + ".")
    walk(raw, "")
    assert not bad, bad


def test_plant_block_matches_stored_aspen_baseline():
    r = load_reference_scenario()
    s = extract_summary(_baseline_result())
    assert s["h2_kg_h"] == pytest.approx(r.h2_product_kg_h, rel=1e-12)
    assert s["nh3_feed_kmol_h"] == pytest.approx(r.nh3_feed_kmol_h, rel=1e-12)


def test_nh3_scenarios_match_the_singapore_source_records():
    from amcrax.economics.singapore import load_singapore_data
    sg = load_singapore_data()["nh3_price_scenarios_USD_per_t"]
    for k, v in load_reference_scenario().nh3_prices_USD_per_t.items():
        assert v == pytest.approx(float(sg[k]["value"]), rel=1e-12), k


def test_electricity_and_fx_consistency():
    r = load_reference_scenario()
    # the stored reference value equals its derivation from the singapore.yaml components at the reference FX
    assert r.electricity_USD_per_kWh == pytest.approx(default_electricity_USD_per_kWh(), rel=1e-5)
    assert r.fx_SGD_per_USD == pytest.approx(1.4160 / 1.0990, rel=1e-6)   # ECB cross rate 20 Nov 2026


# ------------------------------------------------------------------------------------------ CAPEX method
def test_reference_capex_hand_calc():
    ic = reference_item_costs()
    fac = 1.12 * 1.28
    assert ic["indirect_factor"] == pytest.approx(fac, rel=1e-12)
    crf = 0.085 * 1.085 ** 25 / (1.085 ** 25 - 1)
    assert ic["installed_USD"]["boiler"] == pytest.approx(0.126 * 82.3 * 8000 / crf, rel=1e-12)
    assert sum(ic["unit_USD_per_kg_h2"].values()) == pytest.approx(0.586 / fac, rel=1e-12)  # ISBL closes
    n = 99.8
    cap = reference_capex(n)
    ratio = n / (630.0 / 17.031)
    exp_total = sum(v for k, v in ic["installed_USD"].items() if k != "compressor") * ratio ** 0.8 * fac
    assert cap["total_capex_USD"] == pytest.approx(exp_total, rel=1e-4)   # 630/17.031 rounded in the yaml
    assert "compressor" not in cap["tci_by_item_USD"]
    assert sum(cap["tci_by_item_USD"].values()) == pytest.approx(cap["total_capex_USD"], rel=1e-12)
    # reactor follows the catalyst inventory only when asked; doubling the inventory scales that item by 2^0.8
    m = reference_catalyst_mass_kg() * ratio
    c2 = reference_capex(n, catalyst_mass_kg=2 * m, reactor_size_driver="catalyst_mass")
    assert c2["isbl_USD"]["reactor"] == pytest.approx(cap["isbl_USD"]["reactor"] * 2 ** 0.8, rel=1e-4)
    assert c2["isbl_USD"]["boiler"] == pytest.approx(cap["isbl_USD"]["boiler"], rel=1e-12)


# ------------------------------------------------------------------------------------------ one baseline everywhere
def test_reference_baseline_file_matches_fresh_evaluation():
    b = _j("results/research/reference_scenario/baseline.json")
    e = evaluate(_baseline_result(), "grey")
    assert b["lcoh_USD_per_kg"] == pytest.approx(e["lcoh_USD_per_kg"], rel=REL)
    assert b["capex_total_USD"] == pytest.approx(e["capex"]["total_capex_USD"], rel=REL)
    assert sum(b["breakdown_USD_per_kg"].values()) == pytest.approx(b["lcoh_USD_per_kg"], rel=1e-12)
    assert b["provenance"]["reference_scenario"]["sha256"] == load_reference_scenario().sha256


def test_singapore_baseline_agrees():
    b = _j("results/research/reference_scenario/baseline.json")
    s = _j("results/research/singapore/scenario_results.json")["results"]["grey|heat_integration_on"]
    assert s["lcoh_USD_per_kg"] == pytest.approx(b["lcoh_USD_per_kg"], rel=REL)
    assert s["rec_USD_per_kg"] == pytest.approx(b["rec_USD_per_kg"], rel=REL)


def test_enduse_hydrogen_pathway_agrees():
    b = _j("results/research/reference_scenario/baseline.json")
    rows = {r["id"]: r for r in _j("results/research/enduse/enduse_results.json")["hydrogen_pathways"]}
    assert rows["h2_industrial"]["cost_USD_per_kg_at_grey_450"] == pytest.approx(b["lcoh_USD_per_kg"], rel=REL)


def test_purification_psa_amcrax_equals_baseline_plus_named_items():
    """PSA_AMCRAX (the baseline plant's splitter) differs from the baseline only by named items: compression to the
    delivery pressure and the imported heat recomputed from its own tail gas. Annual totals must close exactly."""
    b = _j("results/research/reference_scenario/baseline.json")
    study = _j("results/research/purification/purification_study.json")
    cfg = {c["id"]: c for c in study["cases"]["20bar_baseline"]["configs"]}["PSA_AMCRAX"]
    ref_total = sum(b["annual_USD_per_yr"].values())
    for eu, c in cfg["costs"].items():
        named = c["annual_named_items_USD"]
        rebuilt = (c["annual_total_USD"] - named["compression_electricity"] - named["imported_heat"]
                   + b["annual_USD_per_yr"]["heat_fuel"])
        assert named["membrane_replacement"] == 0.0
        assert rebuilt == pytest.approx(ref_total, rel=REL), eu


# ------------------------------------------------------------------------------------------ no local constants
SCRIPTS = ["scripts/research/economics_singapore.py", "scripts/research/economics_reference_scenario.py",
           "scripts/research/enduse_run.py", "scripts/research/purification_study.py",
           "scripts/research/catalyst_comparison.py", "scripts/research/lca_run.py",
           "backend/amcrax/enduse/params.py", "backend/amcrax/enduse/pathways.py"]
PATTERNS = [
    # cost constants by name (component lives such as a membrane life, or physical energies, are not cost constants)
    re.compile(r"^\s*(\w*ELECTRICITY\w*|PRICE_ELEC\w*|ELEC_(PRICE|LO|HI)\w*|electricity_price\w*|\w*DISCOUNT\w*|discount\w*|"
               r"\w*PLANT_LIFE\w*|plant_life\w*|LIFE_YEARS|life_yr|FX\w*|fx\w*|\w*EURUSD\w*|\w*HOURS\w*|operating_hours\w*)"
               r"(\s*,\s*\w+)*\s*=\s*[-+]?\d", re.M),
    re.compile(r"[\"'](discount_rate|electricity_price_USD_per_kWh|plant_life_yr|fx_SGD_per_USD|operating_hours_h_per_yr)[\"']\s*:\s*[-+]?\d"),
    re.compile(r"\b(discount|life|hours|electricity|electricity_price|elec)\s*(:\s*float\s*)?=\s*\d+(\.\d+)?\s*[,)]"),
]


def test_constant_patterns_catch_the_phase1_forms():
    """The search must flag the forms the Phase 1 scripts used (guards against a regex that never matches)."""
    samples = ['HOURS = 8000.0  # x', 'EURUSD_PARITY = 1.0', 'ELEC_LO, ELEC_HI = 0.084, 1', "FX = 1.29",
               'cho_ov = {"discount_rate": 0.085, "electricity_price_USD_per_kWh": 0.084}',
               'def power_cost(a, p, hours: float = 8000.0, discount: float = 0.10,', 'lc("direct", hours=7200.0)']
    for s in samples:
        assert any(p.search(s) for p in PATTERNS), s


@pytest.mark.parametrize("rel", SCRIPTS)
def test_no_local_cost_constants(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    hits = [m.group(0).strip() for p in PATTERNS for m in p.finditer(text)]
    assert not hits, f"{rel}: local cost constant(s) {hits}; put them in data/reference_scenario.yaml"


# ------------------------------------------------------------------------------------------ SGD and provenance
def test_sgd_equals_usd_times_fx():
    fx = load_reference_scenario().fx_SGD_per_USD
    b = _j("results/research/reference_scenario/baseline.json")
    assert b["lcoh_SGD_per_kg"] == pytest.approx(b["lcoh_USD_per_kg"] * fx, rel=1e-12)
    assert b["capex_total_SGD"] == pytest.approx(b["capex_total_USD"] * fx, rel=1e-12)
    for k, v in b["breakdown_USD_per_kg"].items():
        assert b["breakdown_SGD_per_kg"][k] == pytest.approx(v * fx, rel=1e-12)
    for v in _j("results/research/singapore/scenario_results.json")["results"].values():
        assert v["lcoh_SGD_per_kg"] == pytest.approx(v["lcoh_USD_per_kg"] * fx, rel=1e-12)
    for r in _j("results/research/enduse/enduse_results.json")["power_pathways"]:
        assert r["cost_SGD_per_MWh_at_450"] == pytest.approx(r["cost_USD_per_MWh_at_450"] * fx, rel=1e-12)
    cfg = _j("results/research/purification/purification_study.json")["cases"]["20bar_baseline"]["configs"][1]
    for c in cfg["costs"].values():
        assert c["sgd_per_kg_product_h2"] == pytest.approx(c["usd_per_kg_product_h2"] * fx, rel=1e-12)


@pytest.mark.parametrize("rel", ["results/research/reference_scenario/baseline.json",
                                 "results/research/reference_scenario/capex_audit.json",
                                 "results/research/singapore/scenario_results.json",
                                 "results/research/enduse/enduse_results.json",
                                 "results/research/purification/purification_study.json",
                                 "results/research/catalyst_comparison/catalyst_comparison.json",
                                 "results/research/lca/lca_results.json"])
def test_outputs_carry_reference_provenance(rel):
    st = _j(rel)["provenance"]["reference_scenario"]
    r = load_reference_scenario()
    assert st["sha256"] == r.sha256 and st["version"] == r.version and st["file"].endswith("reference_scenario.yaml")


# ------------------------------------------------------------------------------------------ legacy untouched
def test_legacy_model_and_stored_result_unchanged():
    d = _baseline_result()
    assert compute_lcoh(SimulationResult.model_validate(d)).lcoh_USD_per_kg == pytest.approx(3.918842228473241, rel=1e-9)
    assert _j("results/simulations/economics_baseline.json")["lcoh_USD_per_kg"] == pytest.approx(3.918842228473241, rel=1e-9)


def test_supersession_lists_both_old_baselines():
    rows = _j("results/research/reference_scenario/supersession.json")["rows"]
    olds = [round(r["old_value"], 2) for r in rows if "baseline LCOH" in r["quantity"]]
    assert 3.92 in olds and 3.61 in olds
    for r in rows:
        assert set(("quantity", "file", "key", "old_value", "new_value", "unit", "reason")) <= set(r)
