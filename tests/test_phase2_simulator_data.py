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
    assert m["economics"]["basis"] == "pre-unification"
    assert m["fx"]["SGD_per_USD"] > 0 and m["fx"]["date"]


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
