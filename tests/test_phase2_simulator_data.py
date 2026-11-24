"""Phase 2 S1: data of the browser-side simulator (scripts/research/export_simulator_data.py).

Deterministic, no network, no Aspen. Checks: the exporter is deterministic, model.json holds every rate law of the
registry, no private path or name is written, and the stored files are current with the registries.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research" / "simulator"
SCRIPT = ROOT / "scripts" / "research" / "export_simulator_data.py"


@pytest.fixture(scope="module")
def exporter():
    spec = importlib.util.spec_from_file_location("export_simulator_data", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fresh(exporter):
    return exporter.build_all()


def test_exporter_is_deterministic(exporter, fresh):
    again = exporter.build_all()
    assert again.keys() == fresh.keys()
    for name in fresh:
        assert again[name] == fresh[name], name


def test_model_holds_every_registry_law(fresh):
    reg = yaml.safe_load((ROOT / "backend" / "amcrax" / "data" / "kinetics.yaml").read_text(encoding="utf-8"))
    ids = list(reg["catalysts"]) + list(reg.get("research_catalysts") or {})
    model = json.loads(fresh["model.json"])
    assert sorted(model["kinetics"]["law_ids"]) == sorted(ids)
    for cid in ids:
        law = model["kinetics"]["laws"][cid]
        src = {**reg["catalysts"], **(reg.get("research_catalysts") or {})}[cid]
        assert law["parameters"] == src["parameters"]
        assert law["validity"] == src["validity"]
        assert law["citekey"] == src["source"]["citekey"]
        assert law["reversibility_treatment"]


def test_economics_marked_and_fx_dated(fresh):
    m = json.loads(fresh["model.json"])
    e = m["economics"]
    assert e["capex_mode"] == "reference" and "pre-unification" not in e["basis"]
    assert e["reference_scenario"]["id"] in e["basis"] and f"v{e['reference_scenario']['version']}" in e["basis"]
    assert e["capex_reference"]["method"] == "cho2026_itemised_v1" and e["capex_reference"]["cost_year"] == 2024
    from amcrax.economics.reference import load_reference_scenario  # the one exchange rate: the reference scenario's
    assert m["fx"]["SGD_per_USD"] == load_reference_scenario().fx_SGD_per_USD and m["fx"]["date"]


def test_catalyst_prices_from_metal_content_file_in_usd(fresh):
    model = json.loads(fresh["model.json"])
    e = model["economics"]
    cp = e["catalyst_prices"]
    src = json.loads((ROOT / "research" / "data" / "catalyst_prices.json").read_text(encoding="utf-8"))["scenarios_usd_per_kg_finished_catalyst"]
    assert set(cp["by_law"]) == set(model["kinetics"]["law_ids"])
    for ent in cp["by_law"].values():
        for lvl in ("low", "central", "high"):
            assert ent[lvl]["usd_per_kg"] == src[ent["formulation"]][lvl]["usd_per_kg"]
            assert "sgd" not in json.dumps(ent[lvl]).lower()     # the file's SGD (1.2801) is superseded: not exported
    assert "not supplier quotations" in cp["statement"].lower()
    assert e["catalyst_price_USD_per_kg"]["Ni"] == 33.4        # Phase 1 published TEA price stays selectable


def test_economics_vectors_equal_singapore_evaluate_default(fresh):
    """The stored baseline vector is the default (capex_mode 'reference') output of singapore.evaluate."""
    v = {x["id"]: x for x in json.loads(fresh["test_vectors.json"])["vectors"] if x["kind"] == "economics"}
    from amcrax.economics import singapore as sg
    d = json.loads((ROOT / "results" / "simulations" / "baseline.json").read_text(encoding="utf-8"))
    out = sg.evaluate(sg.extract_summary(d), "grey")
    assert v["econ_stored_baseline"]["python"]["lcoh_USD_per_kg"] == out["lcoh_USD_per_kg"]
    assert round(out["lcoh_USD_per_kg"], 3) == 4.015 and round(out["lcoh_SGD_per_kg"], 3) == 5.174
    assert v["econ_stored_baseline"]["python"]["npv_USD"] == out["npv_USD"]


def test_vectors_cover_every_kind(fresh):
    v = json.loads(fresh["test_vectors.json"])
    assert v["n_vectors"] >= 60
    kinds = {x["kind"] for x in v["vectors"]}
    assert {"rate", "pfr", "process", "purification", "economics", "carbon"} <= kinds
    reg_ids = set(json.loads(fresh["model.json"])["kinetics"]["law_ids"])
    assert {x["inputs"]["catalyst_id"] for x in v["vectors"] if x["kind"] == "pfr"} == reg_ids


def test_anchor_grid_complete(fresh):
    a = json.loads(fresh["aspen_anchors.json"])
    assert a["equilibrium_grid"]["n_points"] == 168
    assert a["kinetic_cases"] and all(c["source"] == "aspen" for c in a["kinetic_cases"])


PRIVATE = [re.compile(p) for p in (r"(?<![A-Za-z])[A-Za-z]:(\\\\|/)(?!/)", r"[/\\]Users[/\\]", r"\be\d{7}\b", r"(?i)downloads[/\\]",
                                    r"(?i)exam highlights", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")]


def test_no_private_path_or_name(fresh):
    for name, text in fresh.items():
        for p in PRIVATE:
            m = p.search(text)
            assert m is None, f"{name}: private pattern {p.pattern!r} found: {text[max(0, m.start() - 40):m.end() + 40]!r}"


def test_stored_files_current(fresh):
    for name, text in fresh.items():
        path = OUT / name
        assert path.exists(), f"{name} missing: run python scripts/research/export_simulator_data.py"
        assert path.read_text(encoding="utf-8") == text, f"{name} stale: run python scripts/research/export_simulator_data.py"


def test_carbon_pricing_vectors_copied_without_timestamp(fresh):
    """S4: the 18 Python carbon-pricing vectors reach the vitest parity test unchanged; the copy holds no generation time."""
    src = json.loads((ROOT / "results" / "research" / "carbon_pricing" / "test_vectors.json").read_text(encoding="utf-8"))
    out = json.loads(fresh["carbon_pricing_vectors.json"])
    assert out["n_vectors"] == len(src["vectors"]) == 18
    assert out["vectors"] == src["vectors"]
    assert out["tolerance_relative"] == src["tolerance_relative"] <= 1e-9
    assert "generated_utc" not in out["provenance"]


def test_stored_purification_comparison_equals_python_result(fresh):
    """S4: the stored PSA / membrane comparison in model.json equals results/research/purification/phase2_comparison.json."""
    src = json.loads((ROOT / "results" / "research" / "purification" / "phase2_comparison.json").read_text(encoding="utf-8"))
    sc = json.loads(fresh["model.json"])["purification"]["stored_comparison"]
    assert sc["source_type"] == "python" and "do not respond" in sc["statement"]
    assert set(sc["specs"]) == set(src["specs"])
    for sid, sp in src["specs"].items():
        for cid, c in sp["configurations"].items():
            row = sc["specs"][sid]["configurations"][cid]
            for k in ("h2_recovery", "n2_ppm", "lcoh_usd_per_kg_usable", "lcoh_sgd_per_kg_usable"):
                assert row[k] == c[k], (sid, cid, k)
            assert row["readiness"]["trl"] == c["readiness"]["trl"]
